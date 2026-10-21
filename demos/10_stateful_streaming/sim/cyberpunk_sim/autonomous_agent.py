"""Goal-driven NPC AI — selects actions as natural-language text.

Each NPC has a list of goals (from their YAML data). The agent system:
1. Assesses the NPC's current situation (location, nearby entities, health, inventory)
2. Scores each goal by priority × urgency × feasibility + noise
3. Converts the best goal into a natural-language action string
4. That string feeds directly into classify_action() from the rpg_engine

No LLM needed — pure heuristic decision-making with weighted randomness.
"""

import random
from typing import Any


# ---------------------------------------------------------------------------
# Goal scoring weights (base priority per goal type)
# ---------------------------------------------------------------------------

GOAL_BASE_PRIORITY = {
    "territory_control": 0.7,
    "resource_acquisition": 0.6,
    "relationship_building": 0.4,
    "conflict": 0.8,
    "survival": 0.9,
    "mission": 0.5,
    "trade": 0.5,
    "patrol": 0.6,
}


def select_action(npc: dict, data: dict, sim_state: dict,
                   rng: random.Random) -> tuple[str, str | None]:
    """Select an action for an NPC based on their goals and current situation.

    Returns (action_text, goal_change_or_none).
    action_text: natural-language string like "attack Razor" or "move to Kabuki Market"
    goal_change: the new active goal if it changed from last tick, else None
    """
    situation = assess_situation(npc, data, sim_state)
    scores = {}
    for goal in npc.get("goals", ["survival"]):
        scores[goal] = score_goal(goal, situation, npc, rng)

    best_goal = max(scores, key=scores.get)

    # Track goal changes
    prev_goal = npc.get("_active_goal")
    goal_change = None
    if prev_goal and prev_goal != best_goal:
        goal_change = best_goal
    npc["_active_goal"] = best_goal

    return goal_to_action_text(best_goal, situation, npc, data, rng), goal_change


def assess_situation(npc: dict, data: dict, sim_state: dict) -> dict[str, Any]:
    """Build a situation assessment for an NPC."""
    location_id = npc.get("location", "")
    location = _find_location(data, location_id)

    # NPCs at same location (excluding self)
    nearby_npcs = [
        n for n in data.get("npcs", [])
        if n.get("location") == location_id and n["id"] != npc["id"]
    ]

    # Nearby enemies (different faction, hostile disposition)
    npc_faction = _get_npc_faction(npc, data)
    enemies = []
    allies = []
    neutrals = []
    for other in nearby_npcs:
        other_faction = _get_npc_faction(other, data)
        if other_faction and npc_faction and other_faction != npc_faction:
            rel = _get_faction_relation(npc_faction, other_faction, sim_state)
            if rel in ("hostile", "war", "tense"):
                enemies.append(other)
            elif rel in ("allied", "friendly", "cooperative"):
                allies.append(other)
            else:
                neutrals.append(other)
        else:
            neutrals.append(other)

    # Location items
    items_here = location.get("items", []) if location else []

    # Connected locations
    connections = []
    if location:
        for conn in location.get("connections", []):
            target_id = conn if isinstance(conn, str) else conn.get("target", "")
            target_loc = _find_location(data, target_id)
            if target_loc:
                connections.append(target_loc)

    # Health assessment
    health = npc.get("stats", {}).get("health", 10)
    max_health = npc.get("stats", {}).get("max_health", 10)
    health_pct = health / max_health if max_health > 0 else 1.0

    # Inventory
    inventory = npc.get("inventory", [])

    # Chrome score (cyberpsychosis risk)
    chrome_score = npc.get("chrome_score", 0)

    return {
        "location": location,
        "location_id": location_id,
        "nearby_npcs": nearby_npcs,
        "enemies": enemies,
        "allies": allies,
        "neutrals": neutrals,
        "items_here": items_here,
        "connections": connections,
        "health_pct": health_pct,
        "inventory": inventory,
        "chrome_score": chrome_score,
        "time_phase": sim_state.get("time_phase", "afternoon"),
        "npc_faction": npc_faction,
    }


def score_goal(goal: str, situation: dict, npc: dict,
               rng: random.Random) -> float:
    """Score a goal based on situation. Higher = more urgent/desirable."""
    base = GOAL_BASE_PRIORITY.get(goal, 0.5)

    urgency = 1.0
    feasibility = 1.0

    if goal == "survival":
        # Urgent when low health
        urgency = 2.0 - situation["health_pct"]
        feasibility = 1.0  # always feasible

    elif goal == "conflict":
        if situation["enemies"]:
            urgency = 1.5
            feasibility = 1.0 if situation["health_pct"] > 0.3 else 0.2
        else:
            urgency = 0.3
            feasibility = 0.5

    elif goal == "territory_control":
        if situation["enemies"]:
            urgency = 1.3
        feasibility = 0.8 if situation["health_pct"] > 0.4 else 0.3

    elif goal == "resource_acquisition":
        if situation["items_here"]:
            urgency = 1.2
            feasibility = 1.0
        else:
            urgency = 0.8
            feasibility = 0.6

    elif goal == "trade":
        # Better in commerce locations
        loc_tags = situation["location"].get("tags", []) if situation["location"] else []
        if "commerce" in loc_tags:
            urgency = 1.3
            feasibility = 1.0 if situation["nearby_npcs"] else 0.3
        else:
            urgency = 0.6
            feasibility = 0.4

    elif goal == "relationship_building":
        if situation["allies"] or situation["neutrals"]:
            urgency = 0.9
            feasibility = 1.0
        else:
            urgency = 0.4
            feasibility = 0.2

    elif goal == "patrol":
        urgency = 0.8
        feasibility = 1.0 if situation["connections"] else 0.1

    elif goal == "mission":
        urgency = 1.0
        feasibility = 0.7

    # Personality modifier — aggressive roles score conflict higher
    role = npc.get("role", "civilian")
    if goal == "conflict" and role in ("solo_merc", "gang_lieutenant", "street_soldier"):
        urgency *= 1.3
    if goal == "trade" and role in ("fixer", "ripperdoc"):
        urgency *= 1.4
    if goal == "patrol" and role == "ncpd_officer":
        urgency *= 1.5

    # Time phase modifiers
    phase = situation["time_phase"]
    if goal == "conflict" and phase in ("night", "late_night"):
        urgency *= 1.2
    if goal == "trade" and phase in ("morning", "afternoon"):
        urgency *= 1.1
    if goal == "rest" and phase == "late_night":
        urgency *= 1.5

    # Noise for variety
    noise = rng.uniform(0.8, 1.2)

    return base * urgency * feasibility * noise


def goal_to_action_text(goal: str, situation: dict, npc: dict,
                         data: dict, rng: random.Random) -> str:
    """Convert a goal + situation into a natural-language action string."""
    if goal == "conflict":
        return _action_conflict(situation, npc, rng)
    elif goal == "territory_control":
        return _action_territory(situation, npc, data, rng)
    elif goal == "resource_acquisition":
        return _action_acquire(situation, npc, rng)
    elif goal == "trade":
        return _action_trade(situation, npc, rng)
    elif goal == "relationship_building":
        return _action_relationship(situation, npc, rng)
    elif goal == "survival":
        return _action_survival(situation, npc, rng)
    elif goal == "patrol":
        return _action_patrol(situation, npc, rng)
    elif goal == "mission":
        return _action_mission(situation, npc, data, rng)
    else:
        return "look around"


# ---------------------------------------------------------------------------
# Goal → action text converters
# ---------------------------------------------------------------------------

def _action_conflict(situation: dict, npc: dict, rng: random.Random) -> str:
    if situation["enemies"]:
        target = rng.choice(situation["enemies"])
        return f"attack {target['name']}"
    # No enemies here — move toward hostile territory
    if situation["connections"]:
        dest = rng.choice(situation["connections"])
        return f"move to {dest['name']}"
    return "look around"


def _action_territory(situation: dict, npc: dict, data: dict,
                       rng: random.Random) -> str:
    if situation["enemies"]:
        target = rng.choice(situation["enemies"])
        return f"attack {target['name']}"
    # Move to expand territory
    if situation["connections"]:
        dest = rng.choice(situation["connections"])
        return f"move to {dest['name']}"
    return "look around"


def _action_acquire(situation: dict, npc: dict, rng: random.Random) -> str:
    if situation["items_here"]:
        item = rng.choice(situation["items_here"])
        item_name = item if isinstance(item, str) else item.get("name", "item")
        return f"take {item_name}"
    # Talk to someone about opportunities
    if situation["nearby_npcs"]:
        target = rng.choice(situation["nearby_npcs"])
        return f"talk to {target['name']} about work"
    # Move to find resources
    if situation["connections"]:
        dest = rng.choice(situation["connections"])
        return f"move to {dest['name']}"
    return "look around"


def _action_trade(situation: dict, npc: dict, rng: random.Random) -> str:
    if situation["nearby_npcs"]:
        target = rng.choice(situation["nearby_npcs"])
        if situation["inventory"]:
            item = rng.choice(situation["inventory"])
            item_name = item if isinstance(item, str) else item.get("name", "item")
            return f"give {item_name} to {target['name']}"
        return f"talk to {target['name']} about trade"
    if situation["connections"]:
        # Move to a commerce location
        commerce = [c for c in situation["connections"]
                    if "commerce" in c.get("tags", [])]
        if commerce:
            return f"move to {rng.choice(commerce)['name']}"
        return f"move to {rng.choice(situation['connections'])['name']}"
    return "look around"


def _action_relationship(situation: dict, npc: dict, rng: random.Random) -> str:
    targets = situation["allies"] + situation["neutrals"]
    if targets:
        target = rng.choice(targets)
        topics = ["the neighborhood", "business", "the news", "their day",
                  "the weather", "work", "the situation"]
        return f"talk to {target['name']} about {rng.choice(topics)}"
    if situation["connections"]:
        dest = rng.choice(situation["connections"])
        return f"move to {dest['name']}"
    return "look around"


def _action_survival(situation: dict, npc: dict, rng: random.Random) -> str:
    if situation["health_pct"] < 0.7:
        # Try to use a healing item from inventory
        healing = [i for i in situation["inventory"]
                   if isinstance(i, dict) and
                   ("consumable" in i.get("tags", []) or "medical" in i.get("tags", []))]
        if healing:
            return f"use {healing[0]['name']}"
        # Try any item in inventory
        if situation["inventory"]:
            item = situation["inventory"][0]
            item_name = item if isinstance(item, str) else item.get("name", "item")
            return f"use {item_name}"
        return "rest"
    # If enemies nearby and low health, flee
    if situation["enemies"] and situation["health_pct"] < 0.6:
        if situation["connections"]:
            dest = rng.choice(situation["connections"])
            return f"move to {dest['name']}"
    return "rest"


def _action_patrol(situation: dict, npc: dict, rng: random.Random) -> str:
    if situation["connections"]:
        dest = rng.choice(situation["connections"])
        return f"move to {dest['name']}"
    return "look around"


def _action_mission(situation: dict, npc: dict, data: dict,
                     rng: random.Random) -> str:
    # Check for active quests
    quests = data.get("quests", [])
    active = [q for q in quests if q.get("status") == "active"]
    if active:
        quest = rng.choice(active)
        stages = quest.get("stages", [])
        current = quest.get("current_stage", 0)
        if current < len(stages):
            stage = stages[current]
            loc_type = stage.get("location_type", "")
            # Try to move to quest location
            for conn in situation["connections"]:
                if conn.get("type") == loc_type:
                    return f"move to {conn['name']}"
    # Fallback: talk to someone or explore
    if situation["nearby_npcs"]:
        target = rng.choice(situation["nearby_npcs"])
        return f"talk to {target['name']} about work"
    if situation["connections"]:
        return f"move to {rng.choice(situation['connections'])['name']}"
    return "look around"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_location(data: dict, location_id: str) -> dict | None:
    for loc in data.get("locations", []):
        if loc["id"] == location_id:
            return loc
    return None


def _get_npc_faction(npc: dict, data: dict) -> str | None:
    """Get the faction an NPC belongs to, based on their role and location."""
    # Check if NPC has an explicit faction
    if "faction" in npc:
        return npc["faction"]
    # Infer from tags
    npc_tags = set(npc.get("tags", []))
    for faction in data.get("factions", []):
        fid = faction["id"]
        if fid in npc_tags:
            return fid
    # Infer from role
    role = npc.get("role", "")
    if role == "ncpd_officer":
        for f in data.get("factions", []):
            if "law_enforcement" in f.get("description", "").lower():
                return f["id"]
    return None


def _get_faction_relation(faction_a: str, faction_b: str,
                          sim_state: dict) -> str:
    """Get the relation between two factions from simulation state."""
    relations = sim_state.get("faction_relations", [])
    for rel in relations:
        if ((rel.get("faction_a") == faction_a and rel.get("faction_b") == faction_b) or
            (rel.get("faction_a") == faction_b and rel.get("faction_b") == faction_a)):
            return rel.get("type", "neutral")
    return "neutral"
