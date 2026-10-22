#!/usr/bin/env python3
"""
Trigger Engine — Evaluate encounters, quest triggers, and world events.

Checks game state + recent actions against trigger conditions defined in
YAML data. Fires encounters, advances quests, and applies consequences
when conditions are met.

Trigger conditions are pattern-based: they match against action types,
targets, locations, player knowledge, inventory, NPC dispositions, and
session flags. Each trigger has a condition set (all must pass) and a
priority for conflict resolution.

Designed for procedural scaling: triggers can reference region state,
NPC states, and item states by ID — so a procedurally generated world
just needs to register its triggers in the same format.
"""

import re
from typing import Any, Optional

from game_state import (
    get_player, get_location, get_npc, get_npcs_at_location,
    get_npc_disposition, get_active_quests, get_quest, get_quest_stage,
    player_has_item, player_knows, get_faction_reputation,
    find_entity, record_event, update_npc_disposition, advance_quest,
    add_player_knowledge,
)


# ---------------------------------------------------------------------------
# Condition types
# ---------------------------------------------------------------------------

CONDITION_EVALUATORS = {}


def condition(name: str):
    """Decorator to register a condition evaluator."""
    def decorator(fn):
        CONDITION_EVALUATORS[name] = fn
        return fn
    return decorator


@condition("at_location")
def _cond_at_location(params: Any, ctx: dict) -> bool:
    """Player is at a specific location."""
    target = params if isinstance(params, str) else params.get("location", "")
    player_loc = ctx["player"].get("location", "")
    return player_loc == target


@condition("action_type")
def _cond_action_type(params: Any, ctx: dict) -> bool:
    """Last action was of a specific type."""
    if isinstance(params, str):
        target = params
    else:
        # Check "action_type" key first, fall back to "type" (which may
        # collide with the condition-type field, so prefer the explicit key).
        target = params.get("action_type", "") or params.get("type", "")
    action = ctx.get("action", {})
    return action.get("action_type", "") == target


@condition("action_target")
def _cond_action_target(params: Any, ctx: dict) -> bool:
    """Last action targeted a specific entity."""
    target = params if isinstance(params, str) else params.get("target", "")
    action = ctx.get("action", {})
    action_target = action.get("target_id", "") or action.get("target", "")
    return action_target.lower() == target.lower()


@condition("action_topic")
def _cond_action_topic(params: Any, ctx: dict) -> bool:
    """Last action had a specific topic (or topic contains keyword)."""
    target = params if isinstance(params, str) else params.get("topic", "")
    action = ctx.get("action", {})
    topic = action.get("topic", "")
    return target.lower() in topic.lower()


@condition("has_item")
def _cond_has_item(params: Any, ctx: dict) -> bool:
    """Player has a specific item."""
    item_id = params if isinstance(params, str) else params.get("item_id", "")
    return player_has_item(ctx["data"], item_id)


@condition("missing_item")
def _cond_missing_item(params: Any, ctx: dict) -> bool:
    """Player does NOT have a specific item."""
    item_id = params if isinstance(params, str) else params.get("item_id", "")
    return not player_has_item(ctx["data"], item_id)


@condition("knows_fact")
def _cond_knows_fact(params: Any, ctx: dict) -> bool:
    """Player knows a specific fact."""
    fact_id = params if isinstance(params, str) else params.get("fact_id", "")
    return player_knows(ctx["data"], fact_id)


@condition("not_knows_fact")
def _cond_not_knows_fact(params: Any, ctx: dict) -> bool:
    """Player does NOT know a specific fact."""
    fact_id = params if isinstance(params, str) else params.get("fact_id", "")
    return not player_knows(ctx["data"], fact_id)


@condition("npc_disposition")
def _cond_npc_disposition(params: dict, ctx: dict) -> bool:
    """NPC has a specific disposition toward player."""
    npc_id = params.get("npc_id", "")
    required_state = params.get("state", "")
    npc = get_npc(ctx["data"], npc_id)
    if not npc:
        return False
    disp = get_npc_disposition(npc)
    return disp.get("state", "") == required_state


@condition("quest_status")
def _cond_quest_status(params: dict, ctx: dict) -> bool:
    """Quest is in a specific status."""
    quest_id = params.get("quest_id", "")
    required_status = params.get("status", "")
    quest = get_quest(ctx["data"], quest_id)
    if not quest:
        return False
    return quest.get("status", "inactive") == required_status


@condition("quest_stage")
def _cond_quest_stage(params: dict, ctx: dict) -> bool:
    """Quest is at a specific stage index."""
    quest_id = params.get("quest_id", "")
    required_stage = params.get("stage", 0)
    quest = get_quest(ctx["data"], quest_id)
    if not quest:
        return False
    return quest.get("current_stage", 0) == required_stage


@condition("faction_reputation")
def _cond_faction_reputation(params: dict, ctx: dict) -> bool:
    """Player reputation with a faction meets a threshold."""
    faction_id = params.get("faction_id", "")
    min_level = params.get("min_level", "")
    rep = get_faction_reputation(ctx["data"], faction_id)

    level_order = ["hostile", "unfriendly", "neutral", "unknown", "friendly", "allied"]
    current_idx = level_order.index(rep.get("level", "neutral")) if rep.get("level", "neutral") in level_order else 2
    required_idx = level_order.index(min_level) if min_level in level_order else 2
    return current_idx >= required_idx


@condition("session_flag")
def _cond_session_flag(params: Any, ctx: dict) -> bool:
    """Session has a specific flag set."""
    flag = params if isinstance(params, str) else params.get("flag", "")
    session = ctx.get("session", {})
    return bool(session.get("flags", {}).get(flag))


@condition("not_session_flag")
def _cond_not_session_flag(params: Any, ctx: dict) -> bool:
    """Session does NOT have a specific flag set."""
    flag = params if isinstance(params, str) else params.get("flag", "")
    session = ctx.get("session", {})
    return not session.get("flags", {}).get(flag)


@condition("turn_count")
def _cond_turn_count(params: Any, ctx: dict) -> bool:
    """Session turn count meets a threshold."""
    if isinstance(params, int):
        min_turns = params
    else:
        min_turns = params.get("min", 0)
    session = ctx.get("session", {})
    return session.get("turn", 0) >= min_turns


@condition("location_state")
def _cond_location_state(params: dict, ctx: dict) -> bool:
    """A location is in a specific state."""
    loc_id = params.get("location_id", "")
    required_state = params.get("state", "")
    loc = get_location(ctx["data"], loc_id)
    if not loc:
        return False
    return loc.get("state", "normal") == required_state


@condition("text_contains")
def _cond_text_contains(params: Any, ctx: dict) -> bool:
    """Player's raw input contains a keyword."""
    if isinstance(params, str):
        keywords = [params]
    elif isinstance(params, list):
        keywords = params
    else:
        keywords = params.get("keywords", [])

    raw_input = ctx.get("action", {}).get("raw_input", "").lower()
    return any(kw.lower() in raw_input for kw in keywords)


# ---------------------------------------------------------------------------
# Trigger evaluation
# ---------------------------------------------------------------------------

def evaluate_trigger(trigger: dict, ctx: dict) -> bool:
    """Evaluate whether a single trigger's conditions are all met.

    A trigger has a list of conditions, ALL of which must pass.
    Each condition is: {"type": "condition_name", ...params}
    """
    conditions = trigger.get("conditions", [])
    if not conditions:
        return False

    for cond in conditions:
        cond_type = cond.get("type", "")
        evaluator = CONDITION_EVALUATORS.get(cond_type)
        if not evaluator:
            # Unknown condition type — fail safe.
            return False
        if not evaluator(cond, ctx):
            return False

    return True


def build_trigger_context(data: dict, action: dict = None,
                          session: dict = None) -> dict:
    """Build the context dict needed for trigger evaluation."""
    return {
        "data": data,
        "player": get_player(data),
        "action": action or {},
        "session": session or {},
    }


# ---------------------------------------------------------------------------
# Encounter evaluation
# ---------------------------------------------------------------------------

def check_encounters(data: dict, action: dict = None,
                     session: dict = None) -> list[dict]:
    """Check all encounter triggers. Returns encounters that should fire.

    Each encounter can have a `conditions` list (machine-parseable) and/or
    a `trigger` string (for the original human-readable format — evaluated
    with fuzzy text matching as a fallback).
    """
    ctx = build_trigger_context(data, action, session)
    player = get_player(data)
    player_loc = player.get("location", "")
    fired = []

    for encounter in data.get("encounters", []):
        enc_id = encounter.get("id", "")

        # Skip if already fired this session.
        if session:
            fired_flag = f"encounter_fired_{enc_id}"
            if session.get("flags", {}).get(fired_flag):
                continue

        # Location check — encounter must match player's location.
        enc_location = encounter.get("location", "")
        if enc_location and enc_location != player_loc:
            continue

        # Check structured conditions first.
        conditions = encounter.get("conditions", [])
        if conditions:
            if evaluate_trigger({"conditions": conditions}, ctx):
                fired.append(encounter)
                continue

        # Fallback: fuzzy match on trigger text.
        trigger_text = encounter.get("trigger", "")
        if trigger_text and action:
            if _fuzzy_trigger_match(trigger_text, action, player_loc, data, session):
                fired.append(encounter)

    return fired


def _fuzzy_trigger_match(trigger_text: str, action: dict,
                         player_loc: str, data: dict,
                         session: dict = None) -> bool:
    """Fuzzy-match a human-readable trigger string against the current action.

    Extracts keywords from the trigger text and checks if the action
    roughly matches. This is the fallback for legacy trigger strings.
    """
    trigger_lower = trigger_text.lower()
    raw_input = action.get("raw_input", "").lower()
    action_type = action.get("action_type", "")
    target = action.get("target", "").lower()
    topic = action.get("topic", "").lower()

    # Extract potential entity names and keywords from trigger text.
    # Match patterns like "Ask Maren about Thornwood", "Read the notice"
    trigger_verbs = {
        "ask": "talk", "speak": "talk", "talk": "talk", "tell": "talk",
        "mention": "talk", "examine": "look", "read": "look",
        "inspect": "look", "investigate": "look", "enter": "move",
        "go": "move", "visit": "move",
    }

    # Check if action type loosely matches trigger intent.
    type_match = False
    for verb, atype in trigger_verbs.items():
        if verb in trigger_lower and atype == action_type:
            type_match = True
            break

    if not type_match:
        return False

    # Check if any NPC/location/topic from the trigger appears in the action.
    # Extract proper nouns and significant words from trigger text.
    significant_words = set()
    for word in re.findall(r'\b[A-Z][a-z]+\b', trigger_text):
        significant_words.add(word.lower())
    for word in re.findall(r'\b\w+\b', trigger_lower):
        if len(word) > 4 and word not in {"about", "should", "their", "there", "where", "which", "could", "would"}:
            significant_words.add(word)

    # Remove common verbs.
    significant_words -= {"player", "spends", "makes", "examines", "mentions", "closely"}

    # Check if any significant word appears in the action's target or topic.
    match_count = 0
    for word in significant_words:
        if word in target or word in topic or word in raw_input:
            match_count += 1

    # Require at least one significant match beyond the verb.
    return match_count >= 1


# ---------------------------------------------------------------------------
# Quest trigger evaluation
# ---------------------------------------------------------------------------

def check_quest_triggers(data: dict, action: dict = None,
                         session: dict = None) -> list[dict]:
    """Check quest stage triggers. Returns quests ready to advance.

    Checks both active quests (for stage advancement) and inactive quests
    (for activation). Returns a list of dicts:
        {"quest": quest, "stage_idx": int, "match_type": str}
    """
    ctx = build_trigger_context(data, action, session)
    results = []

    for quest in data.get("quests", []):
        quest_status = quest.get("status", "inactive")
        stages = quest.get("stages", [])

        if quest_status == "completed":
            continue

        # Determine which stage to check.
        if quest_status == "inactive":
            stage_idx = 0
        else:
            stage_idx = quest.get("current_stage", 0)

        if stage_idx >= len(stages):
            continue

        stage = stages[stage_idx]

        # Check structured conditions first.
        conditions = stage.get("conditions", [])
        if conditions:
            if evaluate_trigger({"conditions": conditions}, ctx):
                results.append({
                    "quest": quest,
                    "stage_idx": stage_idx,
                    "match_type": "structured",
                })
            # Structured conditions exist — don't fall back to fuzzy.
            continue

        # Fallback: check trigger strings (only for stages with no
        # structured conditions, i.e. legacy data).
        triggers = stage.get("triggers", [])
        if triggers and action:
            for trigger_text in triggers:
                if _fuzzy_trigger_match(trigger_text, action,
                                       ctx["player"].get("location", ""),
                                       data, session):
                    results.append({
                        "quest": quest,
                        "stage_idx": stage_idx,
                        "match_type": "fuzzy",
                    })
                    break

    return results


# ---------------------------------------------------------------------------
# Apply triggered effects
# ---------------------------------------------------------------------------

def apply_encounter_effects(encounter: dict, data: dict,
                            session: dict = None) -> list[str]:
    """Apply an encounter's consequences to game state. Returns log entries."""
    log = []
    enc_id = encounter.get("id", "")

    # Mark as fired in session.
    if session:
        session.setdefault("flags", {})[f"encounter_fired_{enc_id}"] = True

    # Record the event.
    record_event(data, {
        "type": "encounter",
        "encounter_id": enc_id,
        "name": encounter.get("name", ""),
        "description": f"Encounter triggered: {encounter.get('name', enc_id)}",
    })
    log.append(f"Encounter: {encounter.get('name', enc_id)}")

    # Apply consequences.
    for c in encounter.get("consequences", []):
        ctype = c.get("type", "")

        if ctype == "learn":
            fact = c.get("fact", {})
            add_player_knowledge(data, fact)
            log.append(f"Learned: {fact.get('id', '?')}")

        elif ctype == "npc_disposition":
            update_npc_disposition(
                data, c.get("npc_id", ""),
                c.get("new_state", "neutral"),
                c.get("reason", ""),
            )
            log.append(f"NPC {c.get('npc_id', '?')} -> {c.get('new_state', '?')}")

        elif ctype == "advance_quest":
            quest = get_quest(data, c.get("quest_id", ""))
            if quest:
                if quest.get("status", "inactive") == "inactive":
                    quest["status"] = "active"
                    log.append(f"Quest activated: {quest.get('name', '?')}")
                else:
                    advance_quest(data, c.get("quest_id", ""))
                    log.append(f"Quest advanced: {quest.get('name', '?')}")

        elif ctype == "set_flag" and session:
            session.setdefault("flags", {})[c.get("flag", "")] = c.get("value", True)
            log.append(f"Flag set: {c.get('flag', '?')}")

        elif ctype == "location_state":
            from game_state import set_location_state
            set_location_state(
                data, c.get("location_id", ""),
                c.get("new_state", "normal"),
                c.get("reason", "encounter effect"),
            )
            log.append(f"Location {c.get('location_id', '?')} -> {c.get('new_state', '?')}")

    return log


def apply_quest_trigger(quest_result: dict, data: dict,
                        session: dict = None) -> list[str]:
    """Apply a quest trigger result — activate or advance the quest."""
    log = []
    quest = quest_result["quest"]
    quest_id = quest.get("id", "")

    if quest.get("status", "inactive") == "inactive":
        quest["status"] = "active"
        quest["current_stage"] = 0
        record_event(data, {
            "type": "quest_activated",
            "quest_id": quest_id,
            "description": f"Quest started: {quest.get('name', quest_id)}",
        })
        log.append(f"Quest activated: {quest.get('name', quest_id)}")
    else:
        new_stage = advance_quest(data, quest_id)
        record_event(data, {
            "type": "quest_advanced",
            "quest_id": quest_id,
            "description": f"Quest advanced: {quest.get('name', quest_id)}",
        })
        log.append(f"Quest advanced: {quest.get('name', quest_id)}")
        if new_stage.get("status") == "completed":
            log.append(f"Quest completed: {quest.get('name', quest_id)}")

    # Mark in session.
    if session:
        session.setdefault("flags", {})[f"quest_stage_{quest_id}_{quest.get('current_stage', 0)}"] = True

    return log


# ---------------------------------------------------------------------------
# Master evaluation (run all triggers)
# ---------------------------------------------------------------------------

def evaluate_all(data: dict, action: dict = None,
                 session: dict = None) -> dict[str, list]:
    """Run all trigger checks and return what fired.

    Returns:
        {
            "encounters": [encounter dicts that fired],
            "quest_triggers": [quest trigger results],
        }
    """
    encounters = check_encounters(data, action, session)
    quest_triggers = check_quest_triggers(data, action, session)

    return {
        "encounters": encounters,
        "quest_triggers": quest_triggers,
    }


def apply_all_triggers(fired: dict, data: dict,
                       session: dict = None) -> list[str]:
    """Apply all fired triggers and return combined log."""
    log = []

    for encounter in fired.get("encounters", []):
        log.extend(apply_encounter_effects(encounter, data, session))

    for qt in fired.get("quest_triggers", []):
        log.extend(apply_quest_trigger(qt, data, session))

    return log


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from game_state import load_game_data

    if len(sys.argv) < 2:
        print("Usage: python trigger_engine.py <game_data_dir> [action_text]")
        sys.exit(1)

    game_dir = sys.argv[1]
    data = load_game_data(game_dir)

    print("=== Trigger Engine Test ===\n")

    # Build a mock session.
    mock_session = {
        "turn": 5,
        "flags": {},
        "conversation": [],
        "history": [],
    }

    if len(sys.argv) > 2:
        from action_resolver import classify_action
        player_input = " ".join(sys.argv[2:])
        action = classify_action(player_input, data)
        print(f"Action: {action['action_type']} target={action['target']} topic={action['topic']}")
    else:
        action = {"action_type": "look", "target": "", "topic": "", "raw_input": "look around"}

    print()

    # Check encounters.
    encounters = check_encounters(data, action, mock_session)
    print(f"Encounters fired: {len(encounters)}")
    for enc in encounters:
        print(f"  - {enc.get('id')}: {enc.get('name')}")

    # Check quest triggers.
    quest_triggers = check_quest_triggers(data, action, mock_session)
    print(f"\nQuest triggers fired: {len(quest_triggers)}")
    for qt in quest_triggers:
        quest = qt["quest"]
        print(f"  - {quest.get('id')}: {quest.get('name')} (stage {qt['stage_idx']}, {qt['match_type']})")

    # Run all.
    print("\n--- Full evaluation ---")
    fired = evaluate_all(data, action, mock_session)
    log = apply_all_triggers(fired, data, mock_session)
    for entry in log:
        print(f"  * {entry}")
