#!/usr/bin/env python3
"""
Scene Engine — Resolve game state into narrative prompts.

Takes the current game situation (location, NPCs present, active quests,
player state, recent events) and assembles a complete prompt that gives
an LLM everything it needs to generate narrative text.

Adapted from Writer's Hand scene_writer.py (resolve_manifest + build_writing_prompt).
"""

import warnings
from pathlib import Path
from typing import Any, Optional

import yaml

from game_state import (
    get_location, get_npcs_at_location, get_npc_disposition,
    get_active_quests, get_quest_stage, get_player, get_player_inventory,
    get_player_knowledge, get_connected_locations, get_faction_reputation,
)


# ---------------------------------------------------------------------------
# Context resolution
# ---------------------------------------------------------------------------

def resolve_scene_context(data: dict, scene_type: str = "exploration",
                          session: dict = None) -> dict[str, Any]:
    """Build a complete scene context from current game state.

    scene_type: "exploration", "dialogue", "combat", "discovery", "rest"
    session: optional session dict for conversation history and turn tracking

    Returns a resolved dict with everything a narrative agent needs.
    """
    player = get_player(data)
    location_id = player.get("location", "")
    location = get_location(data, location_id)

    context: dict[str, Any] = {
        "scene_type": scene_type,
        "turn": session.get("turn", 0) if session else 0,
        "location": _resolve_location(data, location_id),
        "npcs_present": _resolve_npcs(data, location_id),
        "player_state": _resolve_player(data),
        "active_quests": _resolve_quests(data, location_id),
        "available_exits": _resolve_exits(data, location_id),
        "world_rules": _resolve_world_rules(data, scene_type),
        "tone_direction": _resolve_tone(data, location, scene_type),
        "information_state": _resolve_information(data, location_id),
        "recent_events": _get_recent_events(data, count=5),
        "conversation_history": _resolve_conversation(session),
        "triggered_events": [],  # Populated by game_master after trigger eval.
    }

    return context


def resolve_dialogue_context(data: dict, npc_id: str,
                             session: dict = None) -> dict[str, Any]:
    """Build context specifically for an NPC dialogue scene."""
    from game_state import get_npc
    npc = get_npc(data, npc_id)
    if not npc:
        warnings.warn(f"NPC '{npc_id}' not found.")
        return {}

    base = resolve_scene_context(data, scene_type="dialogue", session=session)
    base["dialogue_target"] = _resolve_npc_full(data, npc)
    return base


def resolve_combat_context(data: dict, enemies: list[str],
                           session: dict = None) -> dict[str, Any]:
    """Build context specifically for a combat encounter."""
    base = resolve_scene_context(data, scene_type="combat", session=session)
    base["enemies"] = []
    for enemy_id in enemies:
        from game_state import get_npc
        enemy = get_npc(data, enemy_id)
        if enemy:
            base["enemies"].append(_resolve_npc_full(data, enemy))
    return base


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

def _resolve_location(data: dict, location_id: str) -> dict:
    """Pull full location profile with state-dependent sensory overrides."""
    loc = get_location(data, location_id)
    if not loc:
        return {"id": location_id, "name": "Unknown", "description": ""}

    sensory = dict(loc.get("sensory", {}))
    state = loc.get("state", "normal")

    # Merge state-specific sensory overrides if present.
    state_sensory = loc.get("state_sensory", {}).get(state, {})
    if state_sensory:
        sensory.update(state_sensory)

    return {
        "id": loc.get("id", ""),
        "name": loc.get("name", ""),
        "description": loc.get("description", ""),
        "sensory": sensory,
        "atmosphere": loc.get("atmosphere", ""),
        "tags": loc.get("tags", []),
        "state": state,
    }


def _resolve_npcs(data: dict, location_id: str) -> list[dict]:
    """Get all NPCs at current location with their states."""
    npcs = get_npcs_at_location(data, location_id)
    return [_resolve_npc_brief(data, npc) for npc in npcs]


def _resolve_npc_brief(data: dict, npc: dict) -> dict:
    """Brief NPC profile for scene context."""
    disposition = get_npc_disposition(npc)
    return {
        "id": npc.get("id", ""),
        "name": npc.get("name", ""),
        "role": npc.get("role", ""),
        "appearance_brief": npc.get("appearance_brief", ""),
        "disposition": disposition.get("state", "neutral"),
        "current_activity": npc.get("current_activity", ""),
    }


def _resolve_npc_full(data: dict, npc: dict) -> dict:
    """Full NPC profile for dialogue/interaction context."""
    disposition = get_npc_disposition(npc)
    return {
        "id": npc.get("id", ""),
        "name": npc.get("name", ""),
        "role": npc.get("role", ""),
        "appearance": npc.get("appearance", ""),
        "personality": npc.get("personality", ""),
        "disposition": disposition,
        "voice_profile": npc.get("voice_profile", {}),
        "knowledge": npc.get("knowledge", []),
        "secrets": npc.get("secrets", []),
        "dialogue_hooks": npc.get("dialogue_hooks", []),
        "faction": npc.get("faction", ""),
    }


def _resolve_player(data: dict) -> dict:
    """Resolve player state for prompt context."""
    player = get_player(data)
    inventory = get_player_inventory(data)
    knowledge = get_player_knowledge(data)
    return {
        "name": player.get("name", "the adventurer"),
        "class": player.get("class", ""),
        "level": player.get("level", 1),
        "stats": player.get("stats", {}),
        "conditions": player.get("conditions", []),
        "inventory_summary": [
            {"id": i.get("id", ""), "name": i.get("name", "")}
            for i in inventory[:20]  # Cap for prompt size.
        ],
        "notable_items": [
            i for i in inventory if i.get("notable", False)
        ],
        "knowledge_count": len(knowledge),
        "recent_knowledge": knowledge[-5:] if knowledge else [],
    }


def _resolve_quests(data: dict, location_id: str) -> list[dict]:
    """Get active quests relevant to the current location."""
    active = get_active_quests(data)
    relevant = []
    for quest in active:
        stage = get_quest_stage(quest)
        # Include if quest stage references this location or is globally relevant.
        stage_location = stage.get("location", "")
        if stage_location == location_id or stage_location == "any" or not stage_location:
            relevant.append({
                "id": quest.get("id", ""),
                "name": quest.get("name", ""),
                "current_objective": stage.get("objective", ""),
                "hints": stage.get("hints", []),
            })
    return relevant


def _resolve_exits(data: dict, location_id: str) -> list[dict]:
    """Get available exits from current location."""
    connections = get_connected_locations(data, location_id)
    exits = []
    for conn in connections:
        loc = conn["location"]
        exits.append({
            "direction": conn.get("direction", ""),
            "destination": loc.get("name", loc.get("id", "")),
            "destination_id": loc.get("id", ""),
            "blocked": conn.get("blocked_by") is not None,
            "blocked_by": conn.get("blocked_by", ""),
        })
    return exits


def _resolve_world_rules(data: dict, scene_type: str) -> dict:
    """Pull relevant world rules for the scene type."""
    rules = data.get("world_rules", {})
    if not rules:
        return {}
    # Return general rules + scene-type-specific rules.
    relevant = {
        "setting": rules.get("setting", ""),
        "tone": rules.get("tone", ""),
        "magic_system": rules.get("magic_system", ""),
    }
    scene_rules = rules.get(f"{scene_type}_rules", {})
    if scene_rules:
        relevant["scene_specific"] = scene_rules
    return relevant


def _resolve_tone(data: dict, location: Optional[dict],
                  scene_type: str) -> dict:
    """Determine tone direction for this scene."""
    rules = data.get("world_rules", {})
    base_tone = rules.get("tone", "")

    # Location can override tone.
    loc_atmosphere = ""
    if location:
        loc_atmosphere = location.get("atmosphere", "")

    return {
        "base_tone": base_tone,
        "location_atmosphere": loc_atmosphere,
        "scene_type": scene_type,
    }


def _resolve_information(data: dict, location_id: str) -> dict:
    """What the player knows and doesn't know at this location."""
    player = get_player(data)
    knowledge = player.get("knowledge", [])
    known_facts = {k.get("id", k.get("fact_id", "")) for k in knowledge}

    # Check NPCs for secrets the player doesn't know yet.
    npcs = get_npcs_at_location(data, location_id)
    available_secrets = []
    for npc in npcs:
        for secret in npc.get("secrets", []):
            secret_id = secret.get("id", "")
            if secret_id and secret_id not in known_facts:
                available_secrets.append({
                    "npc": npc.get("id", ""),
                    "secret_id": secret_id,
                    "hint": secret.get("hint", ""),
                })

    return {
        "player_knows": len(known_facts),
        "undiscovered_secrets": len(available_secrets),
        "available_hooks": available_secrets[:5],
    }


def _get_recent_events(data: dict, count: int = 5) -> list[dict]:
    """Get the most recent events from the player's event log."""
    player = data.get("player", {})
    event_log = player.get("event_log", [])
    return event_log[-count:] if event_log else []


def _resolve_conversation(session: Optional[dict]) -> list[dict]:
    """Pull recent conversation exchanges from the session."""
    if not session:
        return []
    return session.get("conversation", [])[-5:]


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def build_narrative_prompt(context: dict[str, Any],
                           action: str = "",
                           outcome: Optional[dict] = None) -> str:
    """Assemble a complete narrative prompt from resolved context.

    Sections:
        SCENE CONTEXT
        LOCATION
        CHARACTERS PRESENT
        PLAYER STATE
        ACTIVE QUESTS
        AVAILABLE EXITS
        WORLD RULES
        TONE DIRECTION
        RECENT EVENTS
        PLAYER ACTION (if provided)
        ACTION OUTCOME (if provided)
        INSTRUCTIONS
    """
    sections: list[str] = []

    # Scene type header.
    scene_type = context.get("scene_type", "exploration")
    sections.append(_section("SCENE CONTEXT", f"Type: {scene_type}"))

    # Location.
    sections.append(_section("LOCATION", _fmt_location(context)))

    # NPCs.
    npcs = context.get("npcs_present", [])
    if npcs:
        sections.append(_section("CHARACTERS PRESENT", _fmt_npcs(npcs)))

    # Dialogue target (if dialogue scene).
    dialogue_target = context.get("dialogue_target")
    if dialogue_target:
        sections.append(_section("DIALOGUE TARGET", _fmt_npc_full(dialogue_target)))

    # Player state.
    sections.append(_section("PLAYER STATE", _fmt_player(context)))

    # Active quests.
    quests = context.get("active_quests", [])
    if quests:
        sections.append(_section("ACTIVE QUESTS", _fmt_quests(quests)))

    # Available exits.
    exits = context.get("available_exits", [])
    if exits:
        sections.append(_section("AVAILABLE EXITS", _fmt_exits(exits)))

    # World rules.
    rules = context.get("world_rules", {})
    if rules:
        sections.append(_section("WORLD RULES", _fmt_rules(rules)))

    # Tone direction.
    tone = context.get("tone_direction", {})
    if tone:
        sections.append(_section("TONE DIRECTION", _fmt_tone(tone)))

    # Conversation history.
    conversation = context.get("conversation_history", [])
    if conversation:
        sections.append(_section("CONVERSATION HISTORY", _fmt_conversation(conversation)))

    # Recent events (reader memory equivalent).
    events = context.get("recent_events", [])
    if events:
        sections.append(_section("RECENT EVENTS", _fmt_events(events)))

    # Triggered events (encounters, quest advances from this turn).
    triggered = context.get("triggered_events", [])
    if triggered:
        sections.append(_section("TRIGGERED EVENTS", _fmt_triggered(triggered)))

    # Combat state (if combat scene with active combat).
    combat_context = context.get("combat_state")
    if combat_context:
        sections.append(_section("COMBAT STATE", _fmt_combat_state(combat_context)))

    # Simulation events (NPC movements, faction dynamics, world events).
    sim_events = context.get("simulation_events", "")
    if sim_events:
        sections.append(_section("WORLD SIMULATION", sim_events))

    # Player action.
    if action:
        sections.append(_section("PLAYER ACTION", action))

    # Action outcome (mechanics result).
    if outcome:
        sections.append(_section("ACTION OUTCOME", _fmt_outcome(outcome)))

    # Writing instructions.
    sections.append(_section("INSTRUCTIONS", _build_instructions(scene_type, context)))

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _section(title: str, body: str) -> str:
    rule = "=" * len(title)
    return f"{rule}\n{title}\n{rule}\n\n{body}"


def _fmt_location(ctx: dict) -> str:
    loc = ctx.get("location", {})
    lines = [f"{loc.get('name', 'Unknown')}"]
    if loc.get("description"):
        lines.append(loc["description"])
    sensory = loc.get("sensory", {})
    if sensory:
        lines.append("")
        for sense, detail in sensory.items():
            lines.append(f"  {sense.capitalize()}: {detail}")
    if loc.get("atmosphere"):
        lines.append(f"\nAtmosphere: {loc['atmosphere']}")
    return "\n".join(lines)


def _fmt_npcs(npcs: list[dict]) -> str:
    lines = []
    for npc in npcs:
        entry = f"- {npc.get('name', '?')} ({npc.get('role', 'unknown')})"
        # Include brief appearance anchor so the model doesn't guess gender/looks wrong.
        brief = npc.get("appearance_brief", "")
        if brief:
            entry += f" [{brief}]"
        if npc.get("disposition") and npc["disposition"] != "neutral":
            entry += f" — disposition: {npc['disposition']}"
        if npc.get("current_activity"):
            entry += f" — {npc['current_activity']}"
        lines.append(entry)
    return "\n".join(lines)


def _fmt_npc_full(npc: dict) -> str:
    lines = [f"Name: {npc.get('name', '?')}"]
    if npc.get("role"):
        lines.append(f"Role: {npc['role']}")
    if npc.get("appearance"):
        lines.append(f"Appearance: {npc['appearance']}")
    if npc.get("personality"):
        lines.append(f"Personality: {npc['personality']}")
    disp = npc.get("disposition", {})
    if isinstance(disp, dict):
        lines.append(f"Disposition toward player: {disp.get('state', 'neutral')}")
        if disp.get("reason"):
            lines.append(f"  Reason: {disp['reason']}")
    voice = npc.get("voice_profile", {})
    if voice:
        lines.append(f"\nVoice profile:")
        for k, v in voice.items():
            lines.append(f"  {k}: {v}")
    hooks = npc.get("dialogue_hooks", [])
    if hooks:
        lines.append(f"\nDialogue hooks:")
        for h in hooks:
            if isinstance(h, dict):
                lines.append(f"  - {h.get('topic', '?')}: {h.get('response_style', '')}")
            else:
                lines.append(f"  - {h}")
    return "\n".join(lines)


def _fmt_player(ctx: dict) -> str:
    ps = ctx.get("player_state", {})
    lines = [f"Name: {ps.get('name', 'the adventurer')}"]
    if ps.get("class"):
        lines.append(f"Class: {ps['class']}")
    if ps.get("level"):
        lines.append(f"Level: {ps['level']}")
    stats = ps.get("stats", {})
    if stats:
        lines.append(f"Stats: {', '.join(f'{k}={v}' for k, v in stats.items())}")
    conditions = ps.get("conditions", [])
    if conditions:
        lines.append(f"Conditions: {', '.join(conditions)}")
    notable = ps.get("notable_items", [])
    if notable:
        lines.append(f"Notable items: {', '.join(i.get('name', '?') for i in notable)}")
    inv = ps.get("inventory_summary", [])
    if inv:
        lines.append(f"Inventory ({len(inv)} items): {', '.join(i.get('name', '?') for i in inv[:10])}")
        if len(inv) > 10:
            lines.append(f"  ... and {len(inv) - 10} more")
    return "\n".join(lines)


def _fmt_quests(quests: list[dict]) -> str:
    lines = []
    for q in quests:
        lines.append(f"- [{q.get('id', '?')}] {q.get('name', '?')}")
        if q.get("current_objective"):
            lines.append(f"  Objective: {q['current_objective']}")
        for hint in q.get("hints", []):
            lines.append(f"  Hint: {hint}")
    return "\n".join(lines)


def _fmt_exits(exits: list[dict]) -> str:
    lines = []
    for ex in exits:
        entry = f"- {ex.get('direction', '?')}: {ex.get('destination', '?')}"
        if ex.get("blocked"):
            entry += f" [BLOCKED: {ex.get('blocked_by', 'unknown')}]"
        lines.append(entry)
    return "\n".join(lines)


def _fmt_rules(rules: dict) -> str:
    lines = []
    for k, v in rules.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for sk, sv in v.items():
                lines.append(f"  {sk}: {sv}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)


def _fmt_tone(tone: dict) -> str:
    lines = []
    if tone.get("base_tone"):
        lines.append(f"Base tone: {tone['base_tone']}")
    if tone.get("location_atmosphere"):
        lines.append(f"Location atmosphere: {tone['location_atmosphere']}")
    lines.append(f"Scene type: {tone.get('scene_type', 'exploration')}")
    return "\n".join(lines)


def _fmt_events(events: list[dict]) -> str:
    lines = []
    for e in events:
        desc = e.get("description", e.get("event", "?"))
        lines.append(f"- {desc}")
    return "\n".join(lines)


def _fmt_conversation(conversation: list[dict]) -> str:
    lines = []
    for ex in conversation:
        turn = ex.get("turn", "?")
        player_said = ex.get("player", "")
        narrative = ex.get("narrative", "")
        loc = ex.get("location", "")
        lines.append(f"[Turn {turn}] (at {loc})")
        if player_said:
            lines.append(f"  Player: {player_said}")
        if narrative:
            truncated = narrative[:300] + "..." if len(narrative) > 300 else narrative
            lines.append(f"  Narrator: {truncated}")
    return "\n".join(lines)


def _fmt_triggered(triggered: list[dict]) -> str:
    lines = []
    for event in triggered:
        etype = event.get("type", "")
        if etype == "encounter":
            lines.append(f"ENCOUNTER: {event.get('name', '?')}")
            if event.get("description"):
                lines.append(f"  {event['description']}")
            if event.get("tone_direction"):
                lines.append(f"  Tone: {event['tone_direction']}")
            enemies = event.get("enemies", [])
            for enemy in enemies:
                lines.append(f"  Enemy: {enemy.get('name', '?')} — {enemy.get('description', '')}")
        elif etype == "quest_activated":
            lines.append(f"QUEST STARTED: {event.get('name', '?')}")
            if event.get("objective"):
                lines.append(f"  Objective: {event['objective']}")
        elif etype == "quest_advanced":
            lines.append(f"QUEST ADVANCED: {event.get('name', '?')}")
            if event.get("objective"):
                lines.append(f"  New objective: {event['objective']}")
        else:
            lines.append(f"EVENT: {event.get('description', '?')}")
    return "\n".join(lines)


def _fmt_combat_state(combat_context: dict) -> str:
    """Format combat state for narrative prompt."""
    lines = [f"Round: {combat_context.get('round', 0)}"]
    lines.append(f"Player HP: {combat_context.get('player_health', '?')}/{combat_context.get('player_max_health', '?')}")
    lines.append(f"Player Stamina: {combat_context.get('player_stamina', '?')}")

    for enemy in combat_context.get("enemies", []):
        status = f"{enemy['health']}/{enemy['max_health']} HP" if enemy.get("alive") else "defeated"
        lines.append(f"  {enemy.get('name', '?')}: {status} — {enemy.get('description', '')}")

    recent = combat_context.get("recent_events", [])
    if recent:
        lines.append("\nRecent combat events:")
        for entry in recent:
            for event_text in entry.get("events", []):
                lines.append(f"  - {event_text}")

    return "\n".join(lines)


def _fmt_outcome(outcome: dict) -> str:
    lines = [f"Result: {outcome.get('result', 'unknown')}"]
    if outcome.get("description"):
        lines.append(outcome["description"])
    if outcome.get("consequences"):
        lines.append(f"Consequences: {outcome['consequences']}")
    return "\n".join(lines)


def _build_instructions(scene_type: str, context: dict) -> str:
    """Build writing instructions based on scene type."""
    base = [
        "Write in second person present tense ('You step into the tavern.').",
        "Show, don't tell. Use sensory details from the location profile.",
        "Keep NPC dialogue in their established voice profiles.",
        "Don't reveal information the player hasn't discovered.",
        "End with a clear prompt for the player's next action.",
    ]

    type_specific = {
        "exploration": [
            "Describe the environment with at least 3 senses.",
            "Mention any NPCs present with brief visual details.",
            "Note obvious exits and points of interest.",
            "Maintain the location's established atmosphere.",
        ],
        "dialogue": [
            "Stay in the NPC's voice profile. Match their vocabulary and rhythm.",
            "The NPC should only share knowledge they actually have.",
            "Include physical beats between dialogue lines (what the NPC does while talking).",
            "Let the NPC's disposition color their tone and willingness to help.",
            "If the NPC has secrets, they may hint but not reveal unless trust is earned.",
        ],
        "combat": [
            "Keep action sequences punchy — short sentences, active verbs.",
            "Describe the physical space and how it affects the fight.",
            "Track injuries and fatigue realistically.",
            "Give enemies distinct fighting styles.",
        ],
        "discovery": [
            "Build the reveal gradually — don't dump information.",
            "Let the player piece things together from details.",
            "Connect discoveries to active quests when relevant.",
            "Make the moment feel earned.",
        ],
        "rest": [
            "Slow the pace. Let the player breathe.",
            "This is where character development happens.",
            "Small, human details matter more than grand statements.",
            "If NPCs are present, let casual conversation happen.",
        ],
    }

    instructions = base + type_specific.get(scene_type, [])
    return "\n".join(f"- {i}" for i in instructions)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from game_state import load_game_data

    if len(sys.argv) < 2:
        print("Usage: python scene_engine.py <game_data_dir> [scene_type]")
        sys.exit(1)

    game_dir = sys.argv[1]
    scene_type = sys.argv[2] if len(sys.argv) > 2 else "exploration"

    data = load_game_data(game_dir)
    context = resolve_scene_context(data, scene_type=scene_type)
    prompt = build_narrative_prompt(context)
    print(prompt)
