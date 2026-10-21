#!/usr/bin/env python3
"""
Game State Manager — YAML-driven world state for text-based RPGs.

Loads, queries, and updates all game entities from flat YAML files.
Event-sourced: state changes are tracked as transitions, not overwrites.
Current state = latest transition at or before current game time.

Adapted from Writer's Hand scene_writer.py (load_story_data + resolve logic).
"""

import copy
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml


# ---------------------------------------------------------------------------
# State loading
# ---------------------------------------------------------------------------

def load_game_data(game_dir: str) -> dict[str, Any]:
    """Load all YAML entity files from a game data directory.

    Expects:
        locations.yaml, npcs.yaml, quests.yaml, items.yaml,
        factions.yaml, encounters.yaml, world_rules.yaml, player.yaml

    Returns a dict keyed by entity type. Missing files produce empty
    lists/dicts with a warning — never crash.
    """
    data_dir = Path(game_dir)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Game data directory not found: {game_dir}")

    file_map: dict[str, str] = {
        "locations": "locations",
        "npcs": "npcs",
        "quests": "quests",
        "items": "items",
        "factions": "factions",
        "encounters": "encounters",
        "world_rules": "world_rules",
        "player": "player",
    }

    data: dict[str, Any] = {
        "locations": [],
        "npcs": [],
        "quests": [],
        "items": [],
        "factions": [],
        "encounters": [],
        "world_rules": {},
        "player": {},
    }

    for yaml_file in sorted(data_dir.glob("*.yaml")):
        stem = yaml_file.stem
        canon = file_map.get(stem)
        if canon is None:
            continue
        try:
            with open(yaml_file, "r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
            if raw is None:
                continue
            # Accept wrapped (top-level key matching canon) or unwrapped.
            if isinstance(raw, dict) and canon in raw:
                data[canon] = raw[canon]
            else:
                data[canon] = raw
        except Exception as exc:
            warnings.warn(f"Failed to load {yaml_file}: {exc}")

    return data


def save_entity(game_dir: str, entity_type: str, data: Any) -> None:
    """Save an entity back to its YAML file."""
    out_path = Path(game_dir) / f"{entity_type}.yaml"
    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.dump({entity_type: data}, fh, default_flow_style=False,
                  allow_unicode=True, sort_keys=False)


# ---------------------------------------------------------------------------
# Entity lookups
# ---------------------------------------------------------------------------

def find_entity(entities: list[dict], entity_id: str) -> Optional[dict]:
    """Find an entity by id field."""
    for e in entities:
        if isinstance(e, dict) and e.get("id") == entity_id:
            return e
    return None


def find_entities_by_tag(entities: list[dict], tag: str) -> list[dict]:
    """Find all entities that have a given tag."""
    return [
        e for e in entities
        if isinstance(e, dict) and tag in e.get("tags", [])
    ]


# ---------------------------------------------------------------------------
# Location queries
# ---------------------------------------------------------------------------

def get_location(data: dict, location_id: str) -> Optional[dict]:
    """Get a location by id with full sensory profile."""
    return find_entity(data.get("locations", []), location_id)


def get_connected_locations(data: dict, location_id: str) -> list[dict]:
    """Get all locations connected to the given one."""
    loc = get_location(data, location_id)
    if not loc:
        return []
    connections = loc.get("connections", [])
    result = []
    for conn in connections:
        target_id = conn if isinstance(conn, str) else conn.get("to", "")
        target = get_location(data, target_id)
        if target:
            result.append({
                "location": target,
                "direction": conn.get("direction", "") if isinstance(conn, dict) else "",
                "blocked_by": conn.get("blocked_by", None) if isinstance(conn, dict) else None,
            })
    return result


# ---------------------------------------------------------------------------
# NPC queries
# ---------------------------------------------------------------------------

def get_npc(data: dict, npc_id: str) -> Optional[dict]:
    """Get an NPC by id."""
    return find_entity(data.get("npcs", []), npc_id)


def get_npcs_at_location(data: dict, location_id: str) -> list[dict]:
    """Get all NPCs currently at a location."""
    return [
        npc for npc in data.get("npcs", [])
        if isinstance(npc, dict) and npc.get("location") == location_id
    ]


def get_npc_disposition(npc: dict, toward: str = "player") -> dict:
    """Get an NPC's current disposition (latest transition)."""
    dispositions = npc.get("dispositions", [])
    relevant = [
        d for d in dispositions
        if isinstance(d, dict) and d.get("toward", "player") == toward
    ]
    if not relevant:
        return {"state": npc.get("default_disposition", "neutral")}
    return relevant[-1]


# ---------------------------------------------------------------------------
# Quest queries
# ---------------------------------------------------------------------------

def get_quest(data: dict, quest_id: str) -> Optional[dict]:
    """Get a quest by id."""
    return find_entity(data.get("quests", []), quest_id)


def get_active_quests(data: dict) -> list[dict]:
    """Get all quests in an active (non-completed, non-failed) state."""
    return [
        q for q in data.get("quests", [])
        if isinstance(q, dict) and q.get("status", "inactive") == "active"
    ]


def get_quest_stage(quest: dict) -> dict:
    """Get the current stage of a quest."""
    stages = quest.get("stages", [])
    current_idx = quest.get("current_stage", 0)
    if 0 <= current_idx < len(stages):
        return stages[current_idx]
    return {}


# ---------------------------------------------------------------------------
# Player queries
# ---------------------------------------------------------------------------

def get_player(data: dict) -> dict:
    """Get the player state."""
    return data.get("player", {})


def get_player_inventory(data: dict) -> list[dict]:
    """Get the player's current inventory."""
    player = get_player(data)
    return player.get("inventory", [])


def player_has_item(data: dict, item_id: str) -> bool:
    """Check if the player has a specific item."""
    return any(
        i.get("id") == item_id or i.get("item_id") == item_id
        for i in get_player_inventory(data)
    )


def get_player_knowledge(data: dict) -> list[dict]:
    """Get everything the player has learned."""
    player = get_player(data)
    return player.get("knowledge", [])


def player_knows(data: dict, fact_id: str) -> bool:
    """Check if the player knows a specific fact."""
    return any(
        k.get("id") == fact_id or k.get("fact_id") == fact_id
        for k in get_player_knowledge(data)
    )


# ---------------------------------------------------------------------------
# Faction queries
# ---------------------------------------------------------------------------

def get_faction(data: dict, faction_id: str) -> Optional[dict]:
    """Get a faction by id."""
    return find_entity(data.get("factions", []), faction_id)


def get_faction_reputation(data: dict, faction_id: str) -> dict:
    """Get the player's current reputation with a faction."""
    faction = get_faction(data, faction_id)
    if not faction:
        return {"level": "unknown", "value": 0}
    rep_history = faction.get("player_reputation", [])
    if not rep_history:
        return {"level": faction.get("default_reputation", "neutral"), "value": 0}
    return rep_history[-1]


# ---------------------------------------------------------------------------
# State mutations
# ---------------------------------------------------------------------------

def update_player_location(data: dict, new_location_id: str) -> None:
    """Move the player to a new location."""
    player = data.setdefault("player", {})
    # Record the move in history.
    history = player.setdefault("location_history", [])
    if player.get("location"):
        history.append({
            "from": player["location"],
            "to": new_location_id,
            "timestamp": _now(),
        })
    player["location"] = new_location_id


def add_to_inventory(data: dict, item: dict) -> None:
    """Add an item to the player's inventory."""
    player = data.setdefault("player", {})
    inventory = player.setdefault("inventory", [])
    item_entry = copy.deepcopy(item)
    item_entry["acquired"] = _now()
    inventory.append(item_entry)


def remove_from_inventory(data: dict, item_id: str) -> Optional[dict]:
    """Remove an item from the player's inventory. Returns the removed item."""
    player = data.get("player", {})
    inventory = player.get("inventory", [])
    for i, item in enumerate(inventory):
        if item.get("id") == item_id or item.get("item_id") == item_id:
            return inventory.pop(i)
    return None


def add_player_knowledge(data: dict, fact: dict) -> None:
    """Record that the player learned something."""
    player = data.setdefault("player", {})
    knowledge = player.setdefault("knowledge", [])
    fact_entry = copy.deepcopy(fact)
    fact_entry["learned"] = _now()
    knowledge.append(fact_entry)


def update_npc_disposition(data: dict, npc_id: str, new_state: str,
                           reason: str = "", toward: str = "player") -> None:
    """Add a disposition transition for an NPC."""
    npc = get_npc(data, npc_id)
    if not npc:
        warnings.warn(f"NPC '{npc_id}' not found.")
        return
    dispositions = npc.setdefault("dispositions", [])
    dispositions.append({
        "toward": toward,
        "state": new_state,
        "reason": reason,
        "timestamp": _now(),
    })


def advance_quest(data: dict, quest_id: str) -> dict:
    """Advance a quest to its next stage. Returns the new stage."""
    quest = get_quest(data, quest_id)
    if not quest:
        warnings.warn(f"Quest '{quest_id}' not found.")
        return {}
    stages = quest.get("stages", [])
    current = quest.get("current_stage", 0)
    if current + 1 < len(stages):
        quest["current_stage"] = current + 1
        quest["status"] = "active"
        return stages[current + 1]
    else:
        quest["status"] = "completed"
        return {"status": "completed"}


def update_faction_reputation(data: dict, faction_id: str,
                               delta: int, reason: str = "") -> None:
    """Modify the player's reputation with a faction."""
    faction = get_faction(data, faction_id)
    if not faction:
        warnings.warn(f"Faction '{faction_id}' not found.")
        return
    rep_history = faction.setdefault("player_reputation", [])
    current_value = rep_history[-1].get("value", 0) if rep_history else 0
    new_value = current_value + delta
    # Map value to level.
    if new_value >= 50:
        level = "allied"
    elif new_value >= 20:
        level = "friendly"
    elif new_value >= -10:
        level = "neutral"
    elif new_value >= -30:
        level = "unfriendly"
    else:
        level = "hostile"
    rep_history.append({
        "value": new_value,
        "level": level,
        "delta": delta,
        "reason": reason,
        "timestamp": _now(),
    })


def record_event(data: dict, event: dict) -> None:
    """Record a world event in the global event log."""
    player = data.setdefault("player", {})
    event_log = player.setdefault("event_log", [])
    event_entry = copy.deepcopy(event)
    event_entry.setdefault("timestamp", _now())
    event_log.append(event_entry)


# ---------------------------------------------------------------------------
# Stat mutations
# ---------------------------------------------------------------------------

def get_player_stat(data: dict, stat_name: str) -> int:
    """Read any player stat."""
    player = get_player(data)
    return player.get("stats", {}).get(stat_name, 0)


def get_player_max_stat(data: dict, stat_name: str) -> int:
    """Read the max value for a stat (from max_stats or initial value)."""
    player = get_player(data)
    max_stats = player.get("max_stats", {})
    if stat_name in max_stats:
        return max_stats[stat_name]
    return player.get("stats", {}).get(stat_name, 10)


def update_player_stat(data: dict, stat_name: str, delta: int,
                       reason: str = "", cap: int = None) -> int:
    """Modify a stat with floor at 0 and optional cap. Returns new value."""
    player = data.setdefault("player", {})
    stats = player.setdefault("stats", {})
    current = stats.get(stat_name, 0)
    new_value = current + delta
    new_value = max(0, new_value)
    if cap is not None:
        new_value = min(cap, new_value)
    stats[stat_name] = new_value
    record_event(data, {
        "type": "stat_change",
        "stat": stat_name,
        "from": current,
        "to": new_value,
        "delta": delta,
        "reason": reason,
    })
    return new_value


# ---------------------------------------------------------------------------
# Condition tracking
# ---------------------------------------------------------------------------

def add_player_condition(data: dict, condition: str) -> None:
    """Add a condition (wounded, incapacitated, etc.) to the player."""
    player = data.setdefault("player", {})
    conditions = player.setdefault("conditions", [])
    if condition not in conditions:
        conditions.append(condition)


def remove_player_condition(data: dict, condition: str) -> None:
    """Remove a condition from the player."""
    player = data.setdefault("player", {})
    conditions = player.get("conditions", [])
    if condition in conditions:
        conditions.remove(condition)


# ---------------------------------------------------------------------------
# Equipment system
# ---------------------------------------------------------------------------

def get_equipped_item(data: dict, slot: str) -> Optional[dict]:
    """Get the item equipped in a slot."""
    player = get_player(data)
    equipped = player.get("equipped", {})
    item_id = equipped.get(slot)
    if not item_id:
        return None
    return get_item_definition(data, item_id)


def equip_item(data: dict, item_id: str, slot: str) -> None:
    """Equip an item to a slot."""
    player = data.setdefault("player", {})
    equipped = player.setdefault("equipped", {})
    equipped[slot] = item_id


def unequip_item(data: dict, slot: str) -> Optional[str]:
    """Unequip an item from a slot. Returns removed item_id."""
    player = data.setdefault("player", {})
    equipped = player.setdefault("equipped", {})
    return equipped.pop(slot, None)


# ---------------------------------------------------------------------------
# Item definitions
# ---------------------------------------------------------------------------

def get_item_definition(data: dict, item_id: str) -> Optional[dict]:
    """Look up a canonical item definition from items list or inventory."""
    item = find_entity(data.get("items", []), item_id)
    if item:
        return item
    # Also check inventory.
    for inv_item in get_player_inventory(data):
        if inv_item.get("id") == item_id:
            return inv_item
    return None


# ---------------------------------------------------------------------------
# Location item management
# ---------------------------------------------------------------------------

def get_items_at_location(data: dict, location_id: str) -> list[dict]:
    """Get all items at a location."""
    loc = get_location(data, location_id)
    if not loc:
        return []
    return loc.get("items", [])


def add_item_to_location(data: dict, location_id: str, item: dict) -> None:
    """Add an item to a location."""
    loc = get_location(data, location_id)
    if not loc:
        return
    items = loc.setdefault("items", [])
    items.append(copy.deepcopy(item))


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

def unblock_connection(data: dict, location_id: str,
                       target_location_id: str, reason: str = "") -> bool:
    """Remove blocked_by from a connection. Returns True if unblocked."""
    loc = get_location(data, location_id)
    if not loc:
        return False
    for conn in loc.get("connections", []):
        if isinstance(conn, dict) and conn.get("to") == target_location_id:
            if "blocked_by" in conn:
                del conn["blocked_by"]
                record_event(data, {
                    "type": "path_unblocked",
                    "from": location_id,
                    "to": target_location_id,
                    "reason": reason,
                })
                return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_location_state(data: dict, location_id: str) -> str:
    """Get a location's current state (normal, changed, destroyed, etc.)."""
    loc = get_location(data, location_id)
    if not loc:
        return "unknown"
    return loc.get("state", "normal")


def set_location_state(data: dict, location_id: str, new_state: str,
                       reason: str = "") -> None:
    """Set a location's state with history tracking."""
    loc = get_location(data, location_id)
    if not loc:
        warnings.warn(f"Location '{location_id}' not found.")
        return
    history = loc.setdefault("state_history", [])
    history.append({
        "from": loc.get("state", "normal"),
        "to": new_state,
        "reason": reason,
        "timestamp": _now(),
    })
    loc["state"] = new_state


def get_entity_state(data: dict, entity_type: str, entity_id: str) -> dict:
    """Get the full state of any entity by type and id.

    Returns a dict with the entity data plus any tracked state transitions.
    Designed for procedural generation — any entity type works.
    """
    entities = data.get(entity_type, [])
    if isinstance(entities, list):
        entity = find_entity(entities, entity_id)
    elif isinstance(entities, dict) and entities.get("id") == entity_id:
        entity = entities
    else:
        entity = None

    if not entity:
        return {"id": entity_id, "exists": False}

    return {
        "id": entity_id,
        "exists": True,
        "data": entity,
        "state": entity.get("state", "normal"),
        "state_history": entity.get("state_history", []),
    }


def set_entity_state(data: dict, entity_type: str, entity_id: str,
                     key: str, value: Any, reason: str = "") -> None:
    """Set an arbitrary state key on any entity. Tracks changes.

    This is the generic state mutation function for procedural worlds —
    you can set any key on any entity and it gets tracked.
    """
    entities = data.get(entity_type, [])
    entity = find_entity(entities, entity_id) if isinstance(entities, list) else None

    if not entity:
        warnings.warn(f"Entity '{entity_id}' not found in '{entity_type}'.")
        return

    # Track the change.
    changes = entity.setdefault("state_changes", [])
    changes.append({
        "key": key,
        "from": entity.get(key),
        "to": value,
        "reason": reason,
        "timestamp": _now(),
    })
    entity[key] = value


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def save_full_state(game_dir: str, data: dict) -> None:
    """Save all entity types back to their YAML files."""
    for entity_type in ["locations", "npcs", "quests", "items",
                        "factions", "encounters", "world_rules", "player"]:
        if entity_type in data:
            save_entity(game_dir, entity_type, data[entity_type])


def get_world_summary(data: dict) -> dict[str, Any]:
    """Get a summary of the entire world state.

    Useful for procedural generation — gives you the state of every
    region, NPC, and significant item at a glance.
    """
    player = get_player(data)

    # Location states.
    location_states = {}
    for loc in data.get("locations", []):
        if isinstance(loc, dict):
            location_states[loc.get("id", "?")] = {
                "name": loc.get("name", "?"),
                "state": loc.get("state", "normal"),
                "items": len(loc.get("items", [])),
            }

    # NPC states.
    npc_states = {}
    for npc in data.get("npcs", []):
        if isinstance(npc, dict):
            disp = get_npc_disposition(npc)
            npc_states[npc.get("id", "?")] = {
                "name": npc.get("name", "?"),
                "location": npc.get("location", "?"),
                "disposition": disp.get("state", "neutral"),
            }

    # Quest states.
    quest_states = {}
    for quest in data.get("quests", []):
        if isinstance(quest, dict):
            quest_states[quest.get("id", "?")] = {
                "name": quest.get("name", "?"),
                "status": quest.get("status", "inactive"),
                "stage": quest.get("current_stage", 0),
            }

    # Faction states.
    faction_states = {}
    for faction in data.get("factions", []):
        if isinstance(faction, dict):
            rep = get_faction_reputation(data, faction.get("id", ""))
            faction_states[faction.get("id", "?")] = {
                "name": faction.get("name", "?"),
                "reputation": rep.get("level", "unknown"),
                "value": rep.get("value", 0),
            }

    return {
        "player": {
            "name": player.get("name", "?"),
            "location": player.get("location", "?"),
            "health": player.get("stats", {}).get("health", 0),
            "inventory_count": len(player.get("inventory", [])),
            "knowledge_count": len(player.get("knowledge", [])),
            "events_count": len(player.get("event_log", [])),
        },
        "locations": location_states,
        "npcs": npc_states,
        "quests": quest_states,
        "factions": faction_states,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    """Current timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# CLI (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python game_state.py <game_data_dir> [entity_type] [entity_id]")
        sys.exit(1)

    game_dir = sys.argv[1]
    data = load_game_data(game_dir)

    if len(sys.argv) >= 3:
        entity_type = sys.argv[2]
        entities = data.get(entity_type, [])
        if len(sys.argv) >= 4:
            entity_id = sys.argv[3]
            entity = find_entity(entities, entity_id) if isinstance(entities, list) else entities
            print(yaml.dump(entity, default_flow_style=False, allow_unicode=True))
        else:
            if isinstance(entities, list):
                for e in entities:
                    if isinstance(e, dict):
                        print(f"  {e.get('id', '?'):20s} {e.get('name', '')}")
            else:
                print(yaml.dump(entities, default_flow_style=False, allow_unicode=True))
    else:
        print("Loaded entities:")
        for key, val in data.items():
            count = len(val) if isinstance(val, list) else ("loaded" if val else "empty")
            print(f"  {key:15s} {count}")
