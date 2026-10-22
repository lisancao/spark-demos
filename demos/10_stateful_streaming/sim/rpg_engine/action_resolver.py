#!/usr/bin/env python3
"""
Action Resolver — Parse player actions and determine outcomes.

Takes free-text player input, classifies the intent, checks it against
world rules and current game state, and produces a structured outcome
that the scene engine can narrate.

STATE-AWARE: The classifier knows about NPCs, items, and locations
in the current game state. It matches entity names before extracting
generic targets, so "talk to maren about drinks" correctly splits
into target=maren, topic=drinks.

Supports compound actions: "sit down and order food" becomes a primary
action (social/rest) with secondary intents preserved.
"""

import re
from typing import Any, Optional

from game_state import (
    get_player, get_location, get_npc, get_npcs_at_location,
    get_connected_locations, get_location_state,
)


# ---------------------------------------------------------------------------
# Action classification
# ---------------------------------------------------------------------------

ACTION_PATTERNS: dict[str, list[str]] = {
    "move": [
        r"\b(?:go|walk|move|travel|head|run|leave|exit|enter|climb|descend)\b",
        r"\b(?:north|south|east|west|up|down|left|right|forward|back)\b",
    ],
    "look": [
        r"\b(?:look|examine|inspect|search|investigate|check|observe|study|read)\b",
    ],
    "talk": [
        r"\b(?:talk|speak|ask|tell|greet|chat|converse|say|call|hail|approach|inquire|request|order)\b",
    ],
    "take": [
        r"\b(?:take|grab|pick up|collect|loot|gather|acquire|steal)\b",
    ],
    "use": [
        r"\b(?:use|apply|activate|open|close|unlock|light|equip|wear)\b",
    ],
    "consume": [
        r"\b(?:drink|eat|consume|sip|taste|swallow)\b",
    ],
    "give": [
        r"\b(?:give|hand|offer|trade|sell|buy|barter|show)\b",
    ],
    "attack": [
        r"\b(?:attack|fight|strike|hit|punch|kick|slash|stab|shoot|cast|throw)\b",
    ],
    "rest": [
        r"\b(?:rest|sleep|wait|camp|meditate|heal)\b",
    ],
    "social": [
        r"\b(?:sit|stand|lean|wave|nod|bow|smile|laugh|shrug|gesture)\b",
    ],
    "inventory": [
        r"\b(?:inventory|items|bag|pack|pouch|what do i have|my stuff)\b",
    ],
    "help": [
        r"\b(?:help|hint|what can i do|options|commands)\b",
    ],
}

# Priority: when multiple action types match, prefer this order.
# talk > social > look > move > take > use > consume > give > attack > rest
ACTION_PRIORITY = {
    "talk": 10, "social": 9, "look": 8, "consume": 7,
    "take": 6, "use": 5, "give": 4, "move": 3,
    "attack": 2, "rest": 1, "inventory": 0, "help": 0,
}

DIRECTIONS = {"north", "south", "east", "west", "up", "down",
              "left", "right", "forward", "back"}

NOISE_WORDS = {"the", "a", "an", "at", "to", "with", "on", "in", "from",
               "around", "into", "through", "some", "for", "then", "and",
               "i", "my", "me", "am", "ill", "i'll", "im", "i'm"}

TOPIC_PREPOSITIONS = {"about", "regarding", "concerning", "on"}


# ---------------------------------------------------------------------------
# State-aware classification
# ---------------------------------------------------------------------------

def classify_action(player_input: str, data: dict = None) -> dict[str, Any]:
    """Classify player input into action(s) with state-aware target extraction.

    When data is provided, matches NPC names, item names, and location names
    from the current game state before falling back to generic extraction.

    Returns:
        {
            "raw_input": str,
            "action_type": str,        # primary action
            "target": str,             # resolved entity name or extracted noun
            "target_id": str,          # resolved entity id (if matched)
            "target_type": str,        # "npc", "item", "location", "direction", ""
            "topic": str,              # conversation topic (for talk actions)
            "direction": str,          # for move actions
            "secondary_actions": [],   # compound action parts
            "confidence": float,
            "social_disposition": str, # "friendly", "hostile", "neutral", etc.
        }
    """
    text = player_input.strip()
    text_lower = text.lower()

    if not text:
        return _empty_action(player_input)

    # --- Extract social disposition cues ---
    disposition = _detect_disposition(text_lower)

    # --- Split compound actions on "and", "then", commas ---
    parts = _split_compound(text_lower)
    primary_text = parts[0]
    secondary_texts = parts[1:]

    # --- Score action types for the primary part ---
    scores: dict[str, float] = {}
    for action_type, patterns in ACTION_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, primary_text, re.IGNORECASE)
            score += len(matches)
        if score > 0:
            # Weight by priority so "talk" wins over "social" when both match.
            scores[action_type] = score + ACTION_PRIORITY.get(action_type, 0) * 0.1

    if not scores:
        # No verb match — check if the whole input is a direction.
        if text_lower.strip() in DIRECTIONS:
            return {
                **_empty_action(player_input),
                "action_type": "move",
                "direction": text_lower.strip(),
                "confidence": 0.8,
            }
        # Check if it's just a topic (player continuing a conversation).
        return {
            **_empty_action(player_input),
            "action_type": "talk",
            "topic": text_lower.strip(),
            "confidence": 0.3,
            "social_disposition": disposition,
        }

    best_type = max(scores, key=lambda k: scores[k])
    confidence = min(1.0, scores[best_type] / 3.0)

    # --- Extract direction ---
    direction = ""
    dir_match = re.search(
        r"\b(north|south|east|west|up|down|left|right|forward|back)\b",
        primary_text, re.IGNORECASE,
    )
    if dir_match:
        direction = dir_match.group(1).lower()

    # --- State-aware target extraction ---
    target = ""
    target_id = ""
    target_type = ""
    topic = ""

    if data:
        target, target_id, target_type, topic = _extract_target_stateful(
            primary_text, best_type, data
        )
    else:
        target = _extract_target_simple(primary_text, best_type)

    # For move actions, if we got a direction but no target, that's fine.
    if best_type == "move" and direction and not target:
        target = direction
        target_type = "direction"

    # --- Process secondary actions ---
    secondary_actions = []
    for sec_text in secondary_texts:
        sec_scores = {}
        for action_type, patterns in ACTION_PATTERNS.items():
            score = sum(len(re.findall(p, sec_text, re.IGNORECASE)) for p in patterns)
            if score > 0:
                sec_scores[action_type] = score
        if sec_scores:
            sec_type = max(sec_scores, key=lambda k: sec_scores[k])
            sec_target = ""
            if data:
                sec_target, _, _, _ = _extract_target_stateful(sec_text, sec_type, data)
            else:
                sec_target = _extract_target_simple(sec_text, sec_type)
            secondary_actions.append({
                "action_type": sec_type,
                "target": sec_target,
                "raw": sec_text,
            })

    return {
        "raw_input": player_input,
        "action_type": best_type,
        "target": target,
        "target_id": target_id,
        "target_type": target_type,
        "topic": topic,
        "direction": direction,
        "secondary_actions": secondary_actions,
        "confidence": confidence,
        "social_disposition": disposition,
    }


def _empty_action(raw: str) -> dict:
    return {
        "raw_input": raw,
        "action_type": "unknown",
        "target": "",
        "target_id": "",
        "target_type": "",
        "topic": "",
        "direction": "",
        "secondary_actions": [],
        "confidence": 0.0,
        "social_disposition": "neutral",
    }


def _detect_disposition(text: str) -> str:
    """Detect the player's social disposition from their phrasing."""
    friendly_cues = ["friendly", "warmly", "kindly", "politely", "gently",
                     "smile", "grin", "cheerful", "pleasant", "nice"]
    hostile_cues = ["threaten", "demand", "angrily", "hostile", "aggressive",
                    "coldly", "snarl", "glare", "menacing", "intimidate"]
    cautious_cues = ["carefully", "cautiously", "quietly", "warily",
                     "suspicious", "guarded"]

    for cue in hostile_cues:
        if cue in text:
            return "hostile"
    for cue in cautious_cues:
        if cue in text:
            return "cautious"
    for cue in friendly_cues:
        if cue in text:
            return "friendly"
    return "neutral"


def _split_compound(text: str) -> list[str]:
    """Split compound actions. 'sit down and order food' -> ['sit down', 'order food']."""
    # Split on ", then ", " and then ", " then ", ". ", and bare " and " when
    # followed by a verb-like word.
    parts = re.split(
        r'(?:,\s*then\s+|,\s*and\s+then\s+|\.\s+|\bthen\s+)',
        text,
    )

    # Also split on " and " but only if the second part starts with a verb.
    expanded = []
    for part in parts:
        # Try splitting on " and " only if what follows looks like an action.
        and_parts = re.split(r'\band\b', part, maxsplit=1)
        if len(and_parts) == 2:
            after = and_parts[1].strip()
            # Check if the part after "and" starts with a verb-like word.
            first_word = after.split()[0] if after.split() else ""
            verb_starts = {
                "go", "walk", "move", "talk", "speak", "ask", "tell", "take",
                "grab", "look", "examine", "use", "give", "attack", "rest",
                "sit", "stand", "order", "drink", "eat", "read", "open",
                "close", "light", "equip", "search", "inspect", "approach",
                "inquire", "greet", "buy", "sell", "trade",
            }
            if first_word in verb_starts:
                expanded.append(and_parts[0].strip())
                expanded.append(after)
            else:
                expanded.append(part.strip())
        else:
            expanded.append(part.strip())

    return [p for p in expanded if p]


def _extract_target_stateful(text: str, action_type: str,
                              data: dict) -> tuple[str, str, str, str]:
    """Extract target by matching against known entities in game state.

    Returns: (target_name, target_id, target_type, topic)
    """
    player = get_player(data)
    location_id = player.get("location", "")

    # --- Try matching NPC names (highest priority for talk/give/attack) ---
    npcs = get_npcs_at_location(data, location_id)
    all_npcs = data.get("npcs", [])  # Also check NPCs not at location for references.
    npc_match = _match_entity_name(text, npcs + all_npcs)

    if npc_match:
        # Extract topic: everything after the NPC name + topic prepositions.
        topic = _extract_topic_after_entity(text, npc_match["name"])
        return npc_match["name"], npc_match["id"], "npc", topic

    # --- Try matching item names (for take/use/give/look) ---
    if action_type in ("take", "use", "look", "give", "consume"):
        # Check location items.
        loc = get_location(data, location_id)
        loc_items = loc.get("items", []) if loc else []
        # Check inventory.
        inv_items = player.get("inventory", [])
        # Check global items.
        global_items = data.get("items", [])
        all_items = loc_items + inv_items + global_items
        item_match = _match_entity_name(text, all_items)
        if item_match:
            topic = _extract_topic_after_entity(text, item_match["name"])
            return item_match["name"], item_match["id"], "item", topic

    # --- Try matching location names (for move/look) ---
    if action_type in ("move", "look"):
        connections = get_connected_locations(data, location_id)
        conn_locs = [c["location"] for c in connections]
        loc_match = _match_entity_name(text, conn_locs)
        if loc_match:
            return loc_match["name"], loc_match["id"], "location", ""

    # --- If talk action but no NPC matched, the whole thing might be a topic ---
    if action_type == "talk":
        topic = _extract_topic_from_text(text)
        # Auto-target: if only one NPC present, target them.
        if len(npcs) == 1:
            npc = npcs[0]
            return npc.get("name", ""), npc.get("id", ""), "npc", topic
        return "", "", "", topic

    # --- Fallback: generic extraction ---
    target = _extract_target_simple(text, action_type)
    return target, "", "", ""


def _match_entity_name(text: str, entities: list[dict]) -> Optional[dict]:
    """Find the best entity name match in the text.

    Tries exact match first, then word-boundary match, then substring.
    Returns the matched entity dict or None.
    """
    text_lower = text.lower()
    best_match = None
    best_score = 0

    seen_ids = set()
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        eid = entity.get("id", "")
        if eid in seen_ids:
            continue
        seen_ids.add(eid)

        name = entity.get("name", "").lower()
        entity_id = eid.lower()

        if not name and not entity_id:
            continue

        # Score by match quality and name length (longer = more specific = better).
        score = 0

        # Check name.
        if name:
            # Word-boundary match on name.
            if re.search(r'\b' + re.escape(name) + r'\b', text_lower):
                score = 100 + len(name)
            # Check individual words of multi-word names (e.g. "sister vale" -> "vale").
            elif " " in name:
                for word in name.split():
                    if len(word) > 2 and re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                        score = max(score, 50 + len(word))
            # Substring match.
            elif name in text_lower:
                score = 30 + len(name)

        # Check id.
        if entity_id and not score:
            if re.search(r'\b' + re.escape(entity_id) + r'\b', text_lower):
                score = 40 + len(entity_id)

        if score > best_score:
            best_score = score
            best_match = entity

    return best_match if best_match else None


def _extract_topic_after_entity(text: str, entity_name: str) -> str:
    """Extract the conversation topic from text after the entity name."""
    text_lower = text.lower()
    name_lower = entity_name.lower()

    # Find where the entity name ends in the text.
    idx = text_lower.find(name_lower)
    if idx < 0:
        # Try individual words.
        for word in name_lower.split():
            if len(word) > 2:
                idx = text_lower.find(word)
                if idx >= 0:
                    idx += len(word)
                    break
        if idx < 0:
            return _extract_topic_from_text(text)
    else:
        idx += len(name_lower)

    remainder = text_lower[idx:].strip()

    # Strip topic prepositions.
    for prep in TOPIC_PREPOSITIONS:
        if remainder.startswith(prep + " "):
            remainder = remainder[len(prep):].strip()
            break
        if remainder.startswith(prep):
            remainder = remainder[len(prep):].strip()
            break

    # Clean up noise words at the start.
    words = remainder.split()
    while words and words[0] in NOISE_WORDS:
        words.pop(0)

    topic = " ".join(words)

    # Remove trailing action fragments that leaked in.
    topic = re.sub(r'\b(?:and|then|also)\s*$', '', topic).strip()

    return topic


def _extract_topic_from_text(text: str) -> str:
    """Extract topic when no entity name was found."""
    text_lower = text.lower()

    # Look for "about X", "regarding X".
    for prep in TOPIC_PREPOSITIONS:
        match = re.search(r'\b' + prep + r'\s+(.+)', text_lower)
        if match:
            topic = match.group(1).strip()
            # Clean noise.
            words = topic.split()
            while words and words[0] in NOISE_WORDS:
                words.pop(0)
            return " ".join(words)

    return ""


def _extract_target_simple(text: str, action_type: str) -> str:
    """Fallback: extract target without state awareness."""
    patterns = ACTION_PATTERNS.get(action_type, [])

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            remainder = text[match.end():].strip()
            words = remainder.split()
            while words and words[0] in NOISE_WORDS:
                words.pop(0)
            # Take up to 4 words as the target (prevents runaway).
            if words:
                return " ".join(words[:4])

    return ""


# ---------------------------------------------------------------------------
# Action validation
# ---------------------------------------------------------------------------

def validate_action(action: dict, data: dict) -> dict[str, Any]:
    """Check if an action is valid given the current game state.

    Returns:
        {
            "valid": bool,
            "reason": str,
            "resolved_target": str,     # matched entity id
            "resolved_target_name": str, # human-readable name
            "resolved_topic": str,
            "action": dict,
        }
    """
    action_type = action.get("action_type", "unknown")
    target = action.get("target", "")
    target_id = action.get("target_id", "")
    target_type = action.get("target_type", "")
    topic = action.get("topic", "")
    direction = action.get("direction", "")
    player = get_player(data)
    location_id = player.get("location", "")

    if action_type == "unknown":
        return _invalid(action, "I don't understand what you're trying to do.")

    if action_type == "move":
        return _validate_move(action, data, location_id, direction, target, target_id)

    if action_type == "talk":
        return _validate_talk(action, data, location_id, target, target_id, topic)

    if action_type == "take":
        return _validate_take(action, data, location_id, target, target_id)

    if action_type in ("use", "consume"):
        return _validate_use(action, data, target, target_id)

    if action_type == "give":
        return _validate_give(action, data, location_id, target, target_id, topic)

    if action_type == "attack":
        return _validate_attack(action, data, location_id, target, target_id)

    if action_type == "social":
        # Social actions (sit, stand, wave, etc.) are always valid.
        return _valid(action, target_id or target, target, topic)

    # look, rest, inventory, help — always valid.
    return _valid(action, target_id or target, target, topic)


def _validate_move(action: dict, data: dict, location_id: str,
                   direction: str, target: str, target_id: str) -> dict:
    connections = get_connected_locations(data, location_id)

    if not connections:
        return _invalid(action, "There's nowhere to go from here.")

    # If we already resolved a target location.
    if target_id:
        for conn in connections:
            if conn["location"].get("id", "") == target_id:
                if conn.get("blocked_by"):
                    return _invalid(
                        action,
                        f"The way to {conn['location'].get('name', '?')} is blocked: {conn['blocked_by']}",
                    )
                return _valid(action, target_id, conn["location"].get("name", ""))

    # Try direction.
    if direction:
        for conn in connections:
            conn_dir = conn.get("direction", "").lower()
            if conn_dir == direction:
                if conn.get("blocked_by"):
                    return _invalid(
                        action,
                        f"The way {direction} is blocked: {conn['blocked_by']}",
                    )
                loc = conn["location"]
                return _valid(action, loc.get("id", ""), loc.get("name", ""))

    # Try name substring match.
    if target:
        target_lower = target.lower()
        for conn in connections:
            loc_name = conn["location"].get("name", "").lower()
            loc_id = conn["location"].get("id", "").lower()
            if target_lower in loc_name or target_lower in loc_id:
                if conn.get("blocked_by"):
                    return _invalid(
                        action,
                        f"The way to {conn['location'].get('name', '?')} is blocked: {conn['blocked_by']}",
                    )
                loc = conn["location"]
                return _valid(action, loc.get("id", ""), loc.get("name", ""))

    available = [
        f"{conn.get('direction', '?')} -> {conn['location'].get('name', '?')}"
        for conn in connections
    ]
    return _invalid(action, f"You can't go that way. Available exits: {', '.join(available)}")


def _validate_talk(action: dict, data: dict, location_id: str,
                   target: str, target_id: str, topic: str) -> dict:
    npcs = get_npcs_at_location(data, location_id)
    if not npcs:
        return _invalid(action, "There's nobody here to talk to.")

    # If we already resolved an NPC.
    if target_id:
        for npc in npcs:
            if npc.get("id") == target_id:
                return _valid(action, target_id, npc.get("name", ""), topic)
        # NPC exists but not at this location.
        return _invalid(action, f"That person isn't here right now.")

    # If we have a target name but no id, try matching.
    if target:
        target_lower = target.lower()
        for npc in npcs:
            if (target_lower in npc.get("name", "").lower()
                    or target_lower in npc.get("id", "").lower()):
                return _valid(action, npc.get("id", ""), npc.get("name", ""), topic)

    # No target — auto-select if only one NPC.
    if len(npcs) == 1:
        npc = npcs[0]
        return _valid(action, npc.get("id", ""), npc.get("name", ""), topic)

    names = [npc.get("name", "?") for npc in npcs]
    return _invalid(action, f"Who do you want to talk to? Present: {', '.join(names)}")


def _validate_take(action: dict, data: dict, location_id: str,
                   target: str, target_id: str) -> dict:
    loc = get_location(data, location_id)
    if not loc:
        return _invalid(action, "You can't take anything here.")

    available_items = loc.get("items", [])
    if not available_items:
        return _invalid(action, "There's nothing here to take.")

    # If resolved.
    if target_id:
        for item in available_items:
            if isinstance(item, dict) and item.get("id") == target_id:
                return _valid(action, target_id, item.get("name", target_id))
        return _invalid(action, f"That isn't here to take.")

    if not target:
        names = [i.get("name", i.get("id", "?")) for i in available_items if isinstance(i, dict)]
        return _invalid(action, f"What do you want to take? Available: {', '.join(names)}")

    target_lower = target.lower()
    for item in available_items:
        if isinstance(item, dict):
            if (target_lower in item.get("name", "").lower()
                    or target_lower in item.get("id", "").lower()):
                return _valid(action, item.get("id", ""), item.get("name", ""))

    return _invalid(action, f"There's nothing called '{target}' here to take.")


def _validate_use(action: dict, data: dict, target: str, target_id: str) -> dict:
    if not target and not target_id:
        return _invalid(action, "What do you want to use?")

    inventory = get_player(data).get("inventory", [])
    if target_id:
        for item in inventory:
            if item.get("id") == target_id:
                return _valid(action, target_id, item.get("name", target_id))

    if target:
        target_lower = target.lower()
        for item in inventory:
            if (target_lower in item.get("name", "").lower()
                    or target_lower in item.get("id", "").lower()):
                return _valid(action, item.get("id", ""), item.get("name", ""))

    return _invalid(action, f"You don't have anything called '{target}'.")


def _validate_give(action: dict, data: dict, location_id: str,
                   target: str, target_id: str, topic: str) -> dict:
    npcs = get_npcs_at_location(data, location_id)
    if not npcs:
        return _invalid(action, "There's nobody here to give things to.")

    # For give, target is typically the recipient NPC. Topic might be the item.
    if target_id:
        return _valid(action, target_id, target, topic)
    if target:
        return _valid(action, target, target, topic)

    if len(npcs) == 1:
        npc = npcs[0]
        return _valid(action, npc.get("id", ""), npc.get("name", ""), topic)

    return _invalid(action, "Who do you want to give it to?")


def _validate_attack(action: dict, data: dict, location_id: str,
                     target: str, target_id: str) -> dict:
    npcs = get_npcs_at_location(data, location_id)
    if not npcs and not target:
        return _invalid(action, "There's nothing here to attack.")
    return _valid(action, target_id or target, target)


def _valid(action: dict, resolved_target: str,
           resolved_name: str = "", topic: str = "") -> dict:
    return {
        "valid": True,
        "reason": "",
        "resolved_target": resolved_target,
        "resolved_target_name": resolved_name or resolved_target,
        "resolved_topic": topic,
        "action": action,
    }


def _invalid(action: dict, reason: str) -> dict:
    return {
        "valid": False,
        "reason": reason,
        "resolved_target": "",
        "resolved_target_name": "",
        "resolved_topic": "",
        "action": action,
    }


# ---------------------------------------------------------------------------
# Outcome resolution
# ---------------------------------------------------------------------------

def resolve_outcome(validated: dict, data: dict) -> dict[str, Any]:
    """Determine the outcome of a validated action."""
    if not validated.get("valid"):
        return {
            "result": "blocked",
            "description": validated.get("reason", "That's not possible right now."),
            "consequences": [],
            "narrative_hints": ["Describe why the action fails in a way that feels natural."],
        }

    action = validated.get("action", {})
    action_type = action.get("action_type", "unknown")
    target = validated.get("resolved_target", "")
    target_name = validated.get("resolved_target_name", target)
    topic = validated.get("resolved_topic", action.get("topic", ""))

    resolver = {
        "move": _resolve_move,
        "look": _resolve_look,
        "talk": _resolve_talk,
        "take": _resolve_take,
        "use": _resolve_use,
        "consume": _resolve_use,
        "give": _resolve_give,
        "attack": _resolve_attack,
        "rest": _resolve_rest,
        "social": _resolve_social,
        "inventory": _resolve_inventory,
        "help": _resolve_help,
    }

    fn = resolver.get(action_type, _resolve_generic)
    outcome = fn(action, target, target_name, topic, data)

    # Attach secondary actions as narrative hints.
    secondary = action.get("secondary_actions", [])
    if secondary:
        for sec in secondary:
            outcome["narrative_hints"].append(
                f"The player also wants to: {sec['raw']}"
            )

    # Attach social disposition as a hint.
    disposition = action.get("social_disposition", "neutral")
    if disposition != "neutral":
        outcome["narrative_hints"].insert(
            0, f"Player's demeanor: {disposition}."
        )

    return outcome


def _resolve_move(action, target, target_name, topic, data):
    return {
        "result": "success",
        "description": f"Moving to {target_name}.",
        "consequences": [
            {"type": "move_player", "location": target},
            {"type": "event", "description": f"Traveled to {target_name}"},
        ],
        "narrative_hints": [
            "Describe the journey briefly — what the player sees/hears as they move.",
            "Then describe arriving at the new location using its sensory profile.",
        ],
    }


def _resolve_look(action, target, target_name, topic, data):
    from game_state import get_items_at_location, get_location_state

    player = get_player(data)
    location_id = player.get("location", "")
    hints = [
        "Use all available senses from the location/object profile.",
        "Reveal details proportional to how closely the player looks.",
        "If there are hidden things, hint at them without revealing.",
    ]

    # List items at location.
    loc_items = get_items_at_location(data, location_id)
    if loc_items:
        item_names = [i.get("name", i.get("id", "?")) for i in loc_items if isinstance(i, dict)]
        if item_names:
            hints.append(f"Items visible here: {', '.join(item_names)}.")

    # List NPCs present.
    npcs = get_npcs_at_location(data, location_id)
    if npcs:
        npc_descs = [f"{n.get('name', '?')} ({n.get('current_activity', n.get('role', ''))})" for n in npcs]
        hints.append(f"People here: {', '.join(npc_descs)}.")

    # List exits.
    connections = get_connected_locations(data, location_id)
    if connections:
        exit_descs = []
        for conn in connections:
            direction = conn.get("direction", "?")
            dest = conn["location"].get("name", "?")
            blocked = conn.get("blocked_by")
            if blocked:
                exit_descs.append(f"{direction} -> {dest} [BLOCKED: {blocked}]")
            else:
                exit_descs.append(f"{direction} -> {dest}")
        hints.append(f"Exits: {'; '.join(exit_descs)}.")

    # Location state.
    loc_state = get_location_state(data, location_id)
    if loc_state != "normal":
        hints.append(f"This area appears {loc_state}. Reflect this in the description.")

    return {
        "result": "success",
        "description": f"Examining {target_name or 'surroundings'}.",
        "consequences": [],
        "narrative_hints": hints,
    }


def _resolve_talk(action, target, target_name, topic, data):
    from game_state import get_npc_disposition
    npc = get_npc(data, target)
    disposition = "neutral"
    if npc:
        disp = get_npc_disposition(npc)
        disposition = disp.get("state", "neutral")

    hints = [
        f"NPC disposition: {disposition}. Color their response accordingly.",
        "Stay in the NPC's voice profile.",
        "Don't reveal secrets unless disposition warrants it.",
    ]
    if topic:
        hints.insert(0, f"Conversation topic: {topic}.")

    return {
        "result": "success",
        "description": f"Speaking with {target_name}" + (f" about {topic}" if topic else "") + ".",
        "consequences": [
            {"type": "event", "description": f"Spoke with {target_name}" + (f" about {topic}" if topic else "")},
        ],
        "narrative_hints": hints,
    }


def _resolve_take(action, target, target_name, topic, data):
    return {
        "result": "success",
        "description": f"Taking {target_name}.",
        "consequences": [
            {"type": "add_item", "item_id": target},
            {"type": "remove_location_item", "item_id": target},
            {"type": "event", "description": f"Picked up {target_name}"},
        ],
        "narrative_hints": [
            "Describe the physical act of picking up the item.",
            "Mention its weight, texture, or any notable properties.",
        ],
    }


def _resolve_use(action, target, target_name, topic, data):
    from game_state import get_item_definition

    consequences = [
        {"type": "event", "description": f"Used {target_name}"},
    ]
    hints = [
        "Describe the effect of using the item based on its properties.",
    ]

    item_def = get_item_definition(data, target)
    props = item_def.get("properties", {}) if item_def else {}

    if props.get("heals"):
        amount = props["heals"]
        stat = props.get("heals_stat", "health")
        consequences.append({"type": "heal", "amount": amount, "stat": stat})
        hints.append(f"The item restores {amount} {stat}. Show the relief physically.")

    if props.get("consumable"):
        consequences.append({"type": "remove_item", "item_id": target})
        hints.append("The item is consumed — note that it's used up.")

    if props.get("light_source"):
        consequences.append({"type": "set_flag", "flag": "has_light", "value": True})
        consequences.append({"type": "equip_item", "item_id": target, "slot": "light"})
        hints.append("Light spills into the darkness. Describe what it reveals.")

    if props.get("quest_trigger"):
        consequences.append({"type": "advance_quest", "quest_id": props["quest_trigger"]})
        hints.append("This item triggers a quest advancement.")

    if props.get("readable"):
        desc = item_def.get("description", "") if item_def else ""
        consequences.append({
            "type": "learn",
            "fact": {"id": f"read_{target}", "content": desc},
        })
        hints.append("Show the player reading and absorbing the content.")

    if any(tag in (item_def or {}).get("tags", []) for tag in ["weapon", "melee", "ranged"]):
        consequences.append({"type": "equip_item", "item_id": target, "slot": "weapon"})
        hints.append("The player equips the weapon. Describe the heft and feel.")

    return {
        "result": "success",
        "description": f"Using {target_name}.",
        "consequences": consequences,
        "narrative_hints": hints,
    }


def _resolve_give(action, target, target_name, topic, data):
    return {
        "result": "success",
        "description": f"Giving item to {target_name}.",
        "consequences": [
            {"type": "event", "description": f"Gave item to {target_name}"},
        ],
        "narrative_hints": [
            "Describe the NPC's reaction to receiving the item.",
            "If the item is quest-relevant, reflect that in the response.",
        ],
    }


def _resolve_attack(action, target, target_name, topic, data):
    return {
        "result": "success",
        "description": f"Initiating combat with {target_name}.",
        "consequences": [
            {"type": "event", "description": f"Attacked {target_name}"},
            {"type": "enter_combat", "target": target},
        ],
        "narrative_hints": [
            "Describe the opening of combat — who strikes first, the environment.",
            "Combat should feel physical and consequential.",
        ],
    }


def _resolve_rest(action, target, target_name, topic, data):
    return {
        "result": "success",
        "description": "Resting.",
        "consequences": [
            {"type": "heal", "amount": "partial"},
            {"type": "event", "description": "Rested"},
        ],
        "narrative_hints": [
            "Describe the passage of time.",
            "Small details: sounds, shifting light, dreams if sleeping.",
        ],
    }


def _resolve_social(action, target, target_name, topic, data):
    return {
        "result": "success",
        "description": f"Social action: {action.get('raw_input', '?')}",
        "consequences": [
            {"type": "event", "description": action.get("raw_input", "social action")},
        ],
        "narrative_hints": [
            "Describe the physical action naturally.",
            "Let nearby NPCs react if appropriate.",
        ],
    }


def _resolve_inventory(action, target, target_name, topic, data):
    player = get_player(data)
    items = player.get("inventory", [])
    item_list = ", ".join(i.get("name", i.get("id", "?")) for i in items) if items else "nothing"
    return {
        "result": "success",
        "description": f"Inventory: {item_list}",
        "consequences": [],
        "narrative_hints": ["List the inventory naturally, as if the player is checking their pack."],
    }


def _resolve_help(action, target, target_name, topic, data):
    return {
        "result": "success",
        "description": "Available actions: look, move, talk, take, use, give, attack, rest, inventory.",
        "consequences": [],
        "narrative_hints": [],
    }


def _resolve_generic(action, target, target_name, topic, data):
    return {
        "result": "partial",
        "description": f"Attempting: {action.get('raw_input', '?')}",
        "consequences": [],
        "narrative_hints": ["Interpret the player's intent and describe a reasonable outcome."],
    }


# ---------------------------------------------------------------------------
# Consequence application
# ---------------------------------------------------------------------------

def apply_consequences(consequences: list[dict], data: dict,
                       session: dict = None) -> list[str]:
    """Apply outcome consequences to game state. Returns log of changes."""
    from game_state import (
        update_player_location, add_to_inventory, remove_from_inventory,
        add_player_knowledge, update_npc_disposition, advance_quest,
        update_faction_reputation, record_event, update_player_stat,
        get_player_max_stat, equip_item as gs_equip_item,
        unblock_connection,
    )

    log = []

    for c in consequences:
        ctype = c.get("type", "")

        if ctype == "move_player":
            update_player_location(data, c["location"])
            log.append(f"Moved to {c['location']}")

        elif ctype == "add_item":
            item_id = c.get("item_id", "")
            item_def = None
            for item in data.get("items", []):
                if isinstance(item, dict) and item.get("id") == item_id:
                    item_def = item
                    break
            if item_def:
                add_to_inventory(data, item_def)
                log.append(f"Added {item_def.get('name', item_id)} to inventory")
            else:
                add_to_inventory(data, {"id": item_id, "name": item_id})
                log.append(f"Added {item_id} to inventory")

        elif ctype == "remove_item":
            removed = remove_from_inventory(data, c.get("item_id", ""))
            if removed:
                log.append(f"Removed {removed.get('name', '?')} from inventory")

        elif ctype == "remove_location_item":
            location_id = get_player(data).get("location", "")
            loc = get_location(data, location_id)
            if loc:
                items = loc.get("items", [])
                loc["items"] = [
                    i for i in items
                    if not (isinstance(i, dict) and i.get("id") == c.get("item_id"))
                ]

        elif ctype == "learn":
            add_player_knowledge(data, c.get("fact", {}))
            log.append(f"Learned: {c.get('fact', {}).get('id', '?')}")

        elif ctype == "npc_disposition":
            update_npc_disposition(
                data, c.get("npc_id", ""),
                c.get("new_state", "neutral"),
                c.get("reason", ""),
            )
            log.append(f"NPC {c.get('npc_id', '?')} disposition -> {c.get('new_state', '?')}")

        elif ctype == "advance_quest":
            advance_quest(data, c.get("quest_id", ""))
            log.append(f"Quest {c.get('quest_id', '?')} advanced")

        elif ctype == "faction_reputation":
            update_faction_reputation(
                data, c.get("faction_id", ""),
                c.get("delta", 0), c.get("reason", ""),
            )
            log.append(f"Faction {c.get('faction_id', '?')} rep changed by {c.get('delta', 0)}")

        elif ctype == "event":
            record_event(data, {"description": c.get("description", "")})
            log.append(f"Event: {c.get('description', '?')}")

        elif ctype == "heal":
            amount = c.get("amount", 0)
            stat = c.get("stat", "health")
            if amount == "partial":
                max_val = get_player_max_stat(data, stat)
                amount = max(1, max_val // 4)
            cap = get_player_max_stat(data, stat)
            new_val = update_player_stat(data, stat, amount, "healing", cap=cap)
            log.append(f"Healed {amount} {stat} (now {new_val})")

        elif ctype == "set_flag":
            if session is not None:
                session.setdefault("flags", {})[c.get("flag", "")] = c.get("value", True)
                log.append(f"Flag set: {c.get('flag', '?')}")

        elif ctype == "equip_item":
            gs_equip_item(data, c.get("item_id", ""), c.get("slot", "weapon"))
            log.append(f"Equipped {c.get('item_id', '?')} to {c.get('slot', 'weapon')}")

        elif ctype == "unblock_path":
            unblocked = unblock_connection(
                data, c.get("location_id", ""),
                c.get("target_location_id", ""),
                c.get("reason", "Path cleared"),
            )
            if unblocked:
                log.append(f"Path unblocked: {c.get('location_id', '?')} -> {c.get('target_location_id', '?')}")

        elif ctype == "enter_combat":
            log.append(f"Combat initiated with {c.get('target', '?')}")

    return log


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from game_state import load_game_data

    if len(sys.argv) < 3:
        print("Usage: python action_resolver.py <game_data_dir> '<player input>'")
        sys.exit(1)

    game_dir = sys.argv[1]
    player_input = " ".join(sys.argv[2:])
    data = load_game_data(game_dir)

    print(f"Input: {player_input}\n")

    action = classify_action(player_input, data)
    print(f"Action: {action['action_type']} (confidence: {action['confidence']:.1f})")
    print(f"Target: {action['target']} (id={action['target_id']}, type={action['target_type']})")
    print(f"Topic: {action['topic']}")
    print(f"Direction: {action['direction']}")
    print(f"Disposition: {action['social_disposition']}")
    if action["secondary_actions"]:
        print(f"Secondary actions:")
        for s in action["secondary_actions"]:
            print(f"  - {s['action_type']}: {s['raw']}")
    print()

    validated = validate_action(action, data)
    print(f"Valid: {validated['valid']}")
    if not validated["valid"]:
        print(f"Reason: {validated['reason']}")
    else:
        print(f"Resolved: {validated['resolved_target']} ({validated['resolved_target_name']})")
        print(f"Topic: {validated['resolved_topic']}")
    print()

    outcome = resolve_outcome(validated, data)
    print(f"Result: {outcome['result']}")
    print(f"Description: {outcome['description']}")
    if outcome["narrative_hints"]:
        print(f"Hints:")
        for h in outcome["narrative_hints"]:
            print(f"  - {h}")
