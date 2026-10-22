#!/usr/bin/env python3
"""
Simulation Engine — Dwarf Fortress-style world simulation between turns.

Manages:
  - NPC schedules (location changes by time of day)
  - NPC relationship web (opinions, alliances, grudges)
  - Faction dynamics (territory, power, inter-faction relations)
  - World events (raids, weather, festivals, arrivals, deaths)

All functions are pure — operate on the game data dict, return changes.
The game master calls `advance_simulation(data, turn, rng)` each turn.
"""

import random
from typing import Any


# ---------------------------------------------------------------------------
# Time system
# ---------------------------------------------------------------------------

PHASES = ["dawn", "morning", "afternoon", "evening", "night", "late_night"]


def get_time_phase(turn: int) -> str:
    """Map turn number to time-of-day phase."""
    return PHASES[turn % len(PHASES)]


# ---------------------------------------------------------------------------
# NPC Schedules
# ---------------------------------------------------------------------------

def generate_npc_schedules(npcs: list[dict], locations: list[dict],
                           rng: random.Random) -> dict[str, dict]:
    """Generate daily schedules for all NPCs.

    Returns a dict mapping npc_id -> schedule dict.
    Each schedule maps time phase -> location_id.
    """
    loc_ids = [loc["id"] for loc in locations]
    loc_by_tag = {}
    for loc in locations:
        for tag in loc.get("tags", []):
            loc_by_tag.setdefault(tag, []).append(loc["id"])

    schedules = {}
    for npc in npcs:
        npc_id = npc["id"]
        home_loc = npc.get("location", loc_ids[0])
        schedule = {}
        for phase in PHASES:
            if phase in ("late_night", "dawn"):
                # Most NPCs stay at their home location at night.
                schedule[phase] = home_loc
            elif phase == "morning":
                # NPCs go to work.
                schedule[phase] = home_loc
            elif phase in ("afternoon", "evening"):
                # Some NPCs wander.
                if rng.random() < 0.4 and len(loc_ids) > 1:
                    # Pick a connected or nearby social location.
                    social = loc_by_tag.get("social", [])
                    if social:
                        schedule[phase] = rng.choice(social)
                    else:
                        schedule[phase] = rng.choice(loc_ids)
                else:
                    schedule[phase] = home_loc
            else:
                schedule[phase] = home_loc

        schedules[npc_id] = schedule

    return schedules


def apply_npc_schedules(data: dict, schedules: dict, turn: int) -> list[dict]:
    """Move NPCs according to their schedules. Returns list of moves."""
    phase = get_time_phase(turn)
    moves = []

    for npc in data.get("npcs", []):
        npc_id = npc.get("id", "")
        schedule = schedules.get(npc_id, {})
        target_loc = schedule.get(phase)

        if target_loc and target_loc != npc.get("location"):
            old_loc = npc.get("location", "")
            npc["location"] = target_loc
            moves.append({
                "npc_id": npc_id,
                "npc_name": npc.get("name", npc_id),
                "from": old_loc,
                "to": target_loc,
                "phase": phase,
            })

    return moves


# ---------------------------------------------------------------------------
# NPC Relationship Web
# ---------------------------------------------------------------------------

def generate_npc_relationships(npcs: list[dict],
                                rng: random.Random) -> list[dict]:
    """Generate a relationship web between NPCs.

    Returns a list of relationship dicts.
    Each relationship has: from_npc, to_npc, type, strength, reason.
    """
    if len(npcs) < 2:
        return []

    RELATIONSHIP_TYPES = [
        ("ally", "trusts", 1, 3),
        ("rival", "distrusts", -3, -1),
        ("friend", "likes", 2, 4),
        ("enemy", "hates", -4, -2),
        ("indifferent", "barely notices", -1, 1),
        ("mentor", "guides", 2, 4),
        ("debtor", "owes", -1, 2),
        ("informant", "feeds information to", 0, 2),
        ("suspicious_of", "watches carefully", -2, 0),
        ("protective_of", "would fight for", 2, 5),
    ]

    relationships = []
    npc_ids = [n["id"] for n in npcs]

    # Each NPC gets 1-3 relationships.
    for npc in npcs:
        num_rels = rng.randint(1, min(3, len(npcs) - 1))
        others = [oid for oid in npc_ids if oid != npc["id"]]
        targets = rng.sample(others, min(num_rels, len(others)))

        for target_id in targets:
            target = next((n for n in npcs if n["id"] == target_id), None)
            if not target:
                continue

            rel_type, verb, min_str, max_str = rng.choice(RELATIONSHIP_TYPES)
            strength = rng.randint(min_str, max_str)

            # Generate a reason based on roles.
            reasons = [
                f"Old history between {npc['name']} and {target['name']}.",
                f"Something happened at {npc.get('location', 'somewhere')}.",
                f"{npc['name']} {verb} {target['name']} — everyone knows.",
                f"It started over a deal gone sideways.",
                f"They worked together once. It ended badly. Or well. Depends who you ask.",
            ]

            relationships.append({
                "from_npc": npc["id"],
                "to_npc": target_id,
                "type": rel_type,
                "verb": verb,
                "strength": strength,
                "reason": rng.choice(reasons),
                "public": rng.random() < 0.6,  # 60% of relationships are known.
            })

    return relationships


def get_npc_relationships(relationships: list[dict],
                           npc_id: str) -> list[dict]:
    """Get all relationships involving an NPC."""
    return [
        r for r in relationships
        if r.get("from_npc") == npc_id or r.get("to_npc") == npc_id
    ]


def get_relationship_between(relationships: list[dict],
                              npc_a: str, npc_b: str) -> list[dict]:
    """Get direct relationships between two NPCs."""
    return [
        r for r in relationships
        if (r.get("from_npc") == npc_a and r.get("to_npc") == npc_b)
        or (r.get("from_npc") == npc_b and r.get("to_npc") == npc_a)
    ]


def shift_relationship(relationships: list[dict], from_npc: str,
                        to_npc: str, delta: int,
                        reason: str = "") -> None:
    """Shift the strength of a relationship. Creates one if none exists."""
    for rel in relationships:
        if rel.get("from_npc") == from_npc and rel.get("to_npc") == to_npc:
            rel["strength"] = max(-5, min(5, rel["strength"] + delta))
            if reason:
                rel["reason"] = reason
            # Update type based on strength.
            if rel["strength"] >= 3:
                rel["type"] = "ally"
            elif rel["strength"] >= 1:
                rel["type"] = "friend"
            elif rel["strength"] >= -1:
                rel["type"] = "indifferent"
            elif rel["strength"] >= -3:
                rel["type"] = "rival"
            else:
                rel["type"] = "enemy"
            return

    # Create new relationship.
    relationships.append({
        "from_npc": from_npc,
        "to_npc": to_npc,
        "type": "indifferent",
        "verb": "regards",
        "strength": delta,
        "reason": reason or "New acquaintance.",
        "public": False,
    })


# ---------------------------------------------------------------------------
# Faction Dynamics
# ---------------------------------------------------------------------------

def generate_faction_territories(factions: list[dict],
                                  locations: list[dict],
                                  rng: random.Random) -> dict[str, list[str]]:
    """Assign territories to factions. Returns faction_id -> [location_ids]."""
    if not factions or not locations:
        return {}

    territories = {f["id"]: [] for f in factions}
    loc_ids = [loc["id"] for loc in locations]

    # Each location is claimed by at most one faction.
    rng.shuffle(loc_ids)
    for i, loc_id in enumerate(loc_ids):
        # Some locations are unclaimed.
        if rng.random() < 0.3:
            continue
        faction = factions[i % len(factions)]
        territories[faction["id"]].append(loc_id)

    return territories


def generate_faction_relations(factions: list[dict],
                                rng: random.Random) -> list[dict]:
    """Generate inter-faction relationships.

    Returns a list of faction-to-faction relation dicts.
    """
    if len(factions) < 2:
        return []

    RELATION_TYPES = [
        ("hostile", -3, -1),
        ("tense", -2, 0),
        ("neutral", -1, 1),
        ("cooperative", 1, 3),
        ("allied", 2, 4),
    ]

    relations = []
    for i, faction_a in enumerate(factions):
        for faction_b in factions[i + 1:]:
            rel_type, min_str, max_str = rng.choice(RELATION_TYPES)
            strength = rng.randint(min_str, max_str)

            relations.append({
                "faction_a": faction_a["id"],
                "faction_b": faction_b["id"],
                "type": rel_type,
                "strength": strength,
                "history": [f"Initial stance: {rel_type}."],
            })

    return relations


def advance_faction_dynamics(data: dict, faction_territories: dict,
                              faction_relations: list[dict],
                              turn: int, rng: random.Random) -> list[dict]:
    """Advance faction dynamics for one turn. Returns list of events."""
    events = []
    factions = data.get("factions", [])

    if len(factions) < 2 or rng.random() < 0.6:
        # 40% chance something happens per turn.
        return events

    # Pick a random faction relation to evolve.
    if not faction_relations:
        return events

    rel = rng.choice(faction_relations)
    faction_a_id = rel["faction_a"]
    faction_b_id = rel["faction_b"]

    faction_a = next((f for f in factions if f["id"] == faction_a_id), None)
    faction_b = next((f for f in factions if f["id"] == faction_b_id), None)

    if not faction_a or not faction_b:
        return events

    faction_a_name = faction_a.get("name", faction_a_id)
    faction_b_name = faction_b.get("name", faction_b_id)

    # Evolve the relationship.
    roll = rng.random()
    if roll < 0.3:
        # Tension increases.
        rel["strength"] = max(-5, rel["strength"] - 1)
        event_text = f"Tensions rise between {faction_a_name} and {faction_b_name}."
        if rel["strength"] <= -3:
            rel["type"] = "hostile"
        elif rel["strength"] <= -1:
            rel["type"] = "tense"
    elif roll < 0.5:
        # Relations improve.
        rel["strength"] = min(5, rel["strength"] + 1)
        event_text = f"Relations improve between {faction_a_name} and {faction_b_name}."
        if rel["strength"] >= 3:
            rel["type"] = "allied"
        elif rel["strength"] >= 1:
            rel["type"] = "cooperative"
    elif roll < 0.7 and rel["strength"] <= -2:
        # Territory skirmish.
        terr_a = faction_territories.get(faction_a_id, [])
        terr_b = faction_territories.get(faction_b_id, [])
        if terr_a and terr_b:
            contested = rng.choice(terr_b)
            event_text = f"{faction_a_name} raids {faction_b_name} territory near {contested}."
            # 50% chance the raid succeeds.
            if rng.random() < 0.5:
                terr_b.remove(contested)
                terr_a.append(contested)
                event_text += f" They seize control."
            else:
                event_text += f" The raid is repelled."
        else:
            event_text = f"Skirmishes between {faction_a_name} and {faction_b_name}."
    else:
        # Trade or diplomacy.
        event_text = f"{faction_a_name} and {faction_b_name} conduct {rng.choice(['trade negotiations', 'border talks', 'a prisoner exchange', 'a summit'])}."

    rel.setdefault("history", []).append(f"Turn {turn}: {event_text}")
    events.append({
        "type": "faction_event",
        "text": event_text,
        "factions": [faction_a_id, faction_b_id],
        "turn": turn,
    })

    return events


# ---------------------------------------------------------------------------
# World Events
# ---------------------------------------------------------------------------

# Event templates by genre feel. The world_generator adds genre-specific
# events; these are universal fallbacks.
WORLD_EVENT_TEMPLATES = [
    {
        "type": "weather",
        "templates": [
            "A storm rolls in. Travel between locations is harder.",
            "Clear skies. Visibility is good. So is visibility of you.",
            "Fog. Dense. Sound carries strangely.",
            "Rain. Steady, cold. Everyone's indoors who can be.",
        ],
        "weight": 3,
        "effects": [],
    },
    {
        "type": "arrival",
        "templates": [
            "A stranger arrives at {location}. Nobody knows them.",
            "A caravan reaches {location}. New goods, new rumors.",
            "Refugees from somewhere. They don't want to talk about it.",
        ],
        "weight": 2,
        "effects": [],
    },
    {
        "type": "rumor",
        "templates": [
            "Word spreads: something happened at {location}. Details vary.",
            "A rumor about {npc} circulates. May or may not be true.",
            "Someone heard something. Something about {faction}. Ask around.",
        ],
        "weight": 3,
        "effects": [],
    },
    {
        "type": "disturbance",
        "templates": [
            "Something happened at {location} during the night. Nobody saw anything.",
            "An argument between {npc} and someone escalated. It's been handled. Probably.",
            "A scream from {location}. When people arrived, nothing was there.",
        ],
        "weight": 2,
        "effects": [],
    },
    {
        "type": "opportunity",
        "templates": [
            "{npc} is looking for someone to help with something. Might be worth asking.",
            "A notice posted at {location}: work available. Details unclear.",
            "Something was left unguarded at {location}. Coincidence or trap.",
        ],
        "weight": 1,
        "effects": [],
    },
]


def generate_world_event(data: dict, turn: int,
                          rng: random.Random) -> dict | None:
    """Maybe generate a world event for this turn.

    Returns an event dict or None.
    40% chance per turn of a non-faction world event.
    """
    if rng.random() < 0.6:
        return None

    # Pick event type by weight.
    templates = WORLD_EVENT_TEMPLATES
    weights = [t.get("weight", 1) for t in templates]
    total = sum(weights)
    r = rng.uniform(0, total)
    cumulative = 0
    chosen = templates[0]
    for t, w in zip(templates, weights):
        cumulative += w
        if r <= cumulative:
            chosen = t
            break

    # Pick a template and fill variables.
    text = rng.choice(chosen["templates"])

    locations = data.get("locations", [])
    npcs = data.get("npcs", [])
    factions = data.get("factions", [])

    if "{location}" in text and locations:
        loc = rng.choice(locations)
        text = text.replace("{location}", loc.get("name", "somewhere"))
    if "{npc}" in text and npcs:
        npc = rng.choice(npcs)
        text = text.replace("{npc}", npc.get("name", "someone"))
    if "{faction}" in text and factions:
        faction = rng.choice(factions)
        text = text.replace("{faction}", faction.get("name", "a faction"))

    return {
        "type": chosen["type"],
        "text": text,
        "turn": turn,
        "effects": list(chosen.get("effects", [])),
    }


# ---------------------------------------------------------------------------
# Master simulation advance
# ---------------------------------------------------------------------------

def advance_simulation(data: dict, turn: int,
                        schedules: dict = None,
                        relationships: list[dict] = None,
                        faction_territories: dict = None,
                        faction_relations: list[dict] = None,
                        rng: random.Random = None) -> dict[str, Any]:
    """Advance the full simulation by one turn.

    Returns a dict with:
      - npc_moves: list of NPC location changes
      - faction_events: list of faction dynamic events
      - world_event: a world event dict or None
      - time_phase: current time of day
      - relationship_changes: list of relationship shifts (if any)
    """
    if rng is None:
        rng = random.Random()

    result = {
        "time_phase": get_time_phase(turn),
        "npc_moves": [],
        "faction_events": [],
        "world_event": None,
        "relationship_changes": [],
    }

    # NPC schedules.
    if schedules:
        result["npc_moves"] = apply_npc_schedules(data, schedules, turn)

    # Faction dynamics.
    if faction_territories and faction_relations:
        result["faction_events"] = advance_faction_dynamics(
            data, faction_territories, faction_relations, turn, rng
        )

    # World events.
    event = generate_world_event(data, turn, rng)
    if event:
        result["world_event"] = event
        # Apply world event effects to game state.
        apply_world_event(event, data, rng)

    # Dynamic quest generation.
    if faction_relations and relationships:
        quest_seed = check_quest_seeds(data, faction_relations, relationships, rng)
        if quest_seed:
            data.setdefault("quests", []).append(quest_seed)
            result["quest_seed"] = quest_seed

    # NPC relationship drift (small random changes).
    if relationships and rng.random() < 0.2:  # 20% chance per turn.
        rel = rng.choice(relationships)
        drift = rng.choice([-1, 1])
        rel["strength"] = max(-5, min(5, rel["strength"] + drift))
        # Update type.
        if rel["strength"] >= 3:
            rel["type"] = "ally"
        elif rel["strength"] >= 1:
            rel["type"] = "friend"
        elif rel["strength"] >= -1:
            rel["type"] = "indifferent"
        elif rel["strength"] >= -3:
            rel["type"] = "rival"
        else:
            rel["type"] = "enemy"

        from_npc = next((n for n in data.get("npcs", [])
                         if n["id"] == rel["from_npc"]), None)
        to_npc = next((n for n in data.get("npcs", [])
                       if n["id"] == rel["to_npc"]), None)
        if from_npc and to_npc:
            result["relationship_changes"].append({
                "from": from_npc.get("name", rel["from_npc"]),
                "to": to_npc.get("name", rel["to_npc"]),
                "type": rel["type"],
                "strength": rel["strength"],
            })

    return result


def format_simulation_events(sim_result: dict,
                              player_location: str = "") -> str:
    """Format simulation results into narrative text for the game master prompt.

    Only includes events the player would notice (same location or widely known).
    """
    lines = []

    # Time of day.
    phase = sim_result.get("time_phase", "")
    if phase:
        phase_desc = {
            "dawn": "Dawn breaks.",
            "morning": "Morning. The day is young.",
            "afternoon": "Afternoon. The day wears on.",
            "evening": "Evening falls.",
            "night": "Night. Darkness settles.",
            "late_night": "Late night. The world sleeps.",
        }
        lines.append(phase_desc.get(phase, f"It is {phase}."))

    # NPC movements the player can see.
    for move in sim_result.get("npc_moves", []):
        if move.get("to") == player_location:
            lines.append(f"{move['npc_name']} arrives.")
        elif move.get("from") == player_location:
            lines.append(f"{move['npc_name']} leaves.")

    # Faction events (always reportable as rumors).
    for event in sim_result.get("faction_events", []):
        lines.append(event.get("text", ""))

    # World events.
    world_event = sim_result.get("world_event")
    if world_event:
        lines.append(world_event.get("text", ""))

    return "\n".join(lines) if lines else ""


# ---------------------------------------------------------------------------
# Faction → NPC disposition propagation
# ---------------------------------------------------------------------------

DISPOSITION_LADDER = [
    "hostile", "unfriendly", "cautious", "neutral",
    "open", "interested", "friendly", "trusting", "allied",
]


def _disposition_index(state: str) -> int:
    """Get index on the disposition ladder."""
    try:
        return DISPOSITION_LADDER.index(state)
    except ValueError:
        return 3  # default: neutral


def propagate_faction_action(data: dict, relationships: list[dict],
                              faction_id: str, delta: int,
                              reason: str = "") -> list[dict]:
    """When faction reputation changes, shift dispositions of NPCs in that faction.

    Positive delta: NPCs in same faction become friendlier.
    Negative delta: NPCs in same faction become less friendly.
    NPCs in rival factions shift the opposite direction.

    Returns list of changes made.
    """
    from game_state import get_npc_disposition, update_npc_disposition

    changes = []
    npcs = data.get("npcs", [])

    for npc in npcs:
        npc_faction = npc.get("faction", "")
        if not npc_faction:
            continue

        shift = 0
        if npc_faction == faction_id:
            shift = 1 if delta > 0 else -1
        else:
            # Check if this NPC's faction is rival to the changed faction.
            for rel in relationships:
                factions = {rel.get("from_npc", ""), rel.get("to_npc", "")}
                if npc_faction in factions and faction_id in factions:
                    if rel.get("type") in ("rival", "enemy"):
                        shift = -1 if delta > 0 else 1
                    break

        if shift == 0:
            continue

        disp = get_npc_disposition(npc)
        current_state = disp.get("state", "neutral")
        current_idx = _disposition_index(current_state)
        new_idx = max(0, min(len(DISPOSITION_LADDER) - 1, current_idx + shift))
        new_state = DISPOSITION_LADDER[new_idx]

        if new_state != current_state:
            update_npc_disposition(
                data, npc.get("id", ""), new_state,
                reason=reason or f"Faction reputation change ({faction_id})",
            )
            changes.append({
                "npc_id": npc.get("id", ""),
                "npc_name": npc.get("name", ""),
                "from": current_state,
                "to": new_state,
                "faction": npc_faction,
            })

    return changes


# ---------------------------------------------------------------------------
# World event application
# ---------------------------------------------------------------------------

def apply_world_event(event: dict, data: dict,
                      rng: random.Random = None) -> list[dict]:
    """Apply event effects to game state.

    Returns list of applied effects.
    """
    if rng is None:
        rng = random.Random()
    if not event:
        return []

    effects = []
    event_type = event.get("type", "")

    if event_type == "weather":
        effects.append({"type": "session_flag", "flag": "weather", "value": event.get("text", "")})

    elif event_type == "arrival":
        locations = data.get("locations", [])
        if locations:
            loc = rng.choice(locations)
            from game_state import add_item_to_location
            add_item_to_location(data, loc.get("id", ""), {
                "id": f"arrival_goods_{event.get('turn', 0)}",
                "name": "newly arrived goods",
                "description": "Fresh supplies from a recent arrival.",
            })
            effects.append({"type": "item_added", "location": loc.get("id", "")})

    elif event_type == "disturbance":
        locations = data.get("locations", [])
        if locations:
            loc = rng.choice(locations)
            from game_state import set_location_state
            set_location_state(data, loc.get("id", ""), "disturbed", "world event disturbance")
            effects.append({"type": "location_state_changed", "location": loc.get("id", ""), "state": "disturbed"})

    elif event_type == "opportunity":
        effects.append({"type": "quest_seed", "text": event.get("text", "")})

    return effects


# ---------------------------------------------------------------------------
# Dynamic quest generation
# ---------------------------------------------------------------------------

QUEST_SEED_TEMPLATES = [
    {
        "type": "faction_conflict",
        "name": "Mediating {faction_a} and {faction_b}",
        "description": "Two factions are at odds. Someone needs to intervene before it escalates.",
        "stages": [
            {"objective": "Learn about the conflict.", "location": "any"},
            {"objective": "Speak to both sides.", "location": "any"},
            {"objective": "Propose a resolution.", "location": "any"},
        ],
    },
    {
        "type": "relationship_breakdown",
        "name": "Trouble between {npc_a} and {npc_b}",
        "description": "A relationship between two people has soured. There may be consequences.",
        "stages": [
            {"objective": "Discover what happened.", "location": "any"},
            {"objective": "Decide who to help.", "location": "any"},
        ],
    },
]


def check_quest_seeds(data: dict, faction_relations: list[dict],
                      relationships: list[dict],
                      rng: random.Random = None) -> dict | None:
    """Check if conditions exist for generating a new quest.

    Only generates if < 3 active quests (prevents quest flood).
    """
    if rng is None:
        rng = random.Random()

    from game_state import get_active_quests
    active = get_active_quests(data)
    if len(active) >= 3:
        return None

    # Check for hostile faction relations.
    hostile_relations = [r for r in faction_relations if r.get("type") == "hostile"]
    if hostile_relations and rng.random() < 0.3:
        rel = rng.choice(hostile_relations)
        factions = data.get("factions", [])
        fa = next((f for f in factions if f["id"] == rel["faction_a"]), None)
        fb = next((f for f in factions if f["id"] == rel["faction_b"]), None)
        if fa and fb:
            template = QUEST_SEED_TEMPLATES[0]
            return {
                "id": f"mediation_{rel['faction_a']}_{rel['faction_b']}",
                "name": template["name"].format(
                    faction_a=fa.get("name", rel["faction_a"]),
                    faction_b=fb.get("name", rel["faction_b"]),
                ),
                "description": template["description"],
                "status": "inactive",
                "current_stage": 0,
                "stages": template["stages"],
            }

    # Check for broken NPC relationships.
    enemy_rels = [r for r in relationships if r.get("type") == "enemy"]
    if enemy_rels and rng.random() < 0.3:
        rel = rng.choice(enemy_rels)
        npcs = data.get("npcs", [])
        na = next((n for n in npcs if n["id"] == rel["from_npc"]), None)
        nb = next((n for n in npcs if n["id"] == rel["to_npc"]), None)
        if na and nb:
            template = QUEST_SEED_TEMPLATES[1]
            return {
                "id": f"trouble_{rel['from_npc']}_{rel['to_npc']}",
                "name": template["name"].format(
                    npc_a=na.get("name", rel["from_npc"]),
                    npc_b=nb.get("name", rel["to_npc"]),
                ),
                "description": template["description"],
                "status": "inactive",
                "current_stage": 0,
                "stages": template["stages"],
            }

    return None


# ---------------------------------------------------------------------------
# Simulation state persistence
# ---------------------------------------------------------------------------

def save_simulation_state(game_dir: str, schedules: dict,
                           relationships: list[dict],
                           faction_territories: dict,
                           faction_relations: list[dict]) -> None:
    """Save simulation state to YAML files in the game directory."""
    from pathlib import Path
    import yaml

    sim_dir = Path(game_dir)

    sim_data = {
        "schedules": schedules,
        "relationships": relationships,
        "faction_territories": faction_territories,
        "faction_relations": faction_relations,
    }

    with open(sim_dir / "simulation.yaml", "w", encoding="utf-8") as fh:
        yaml.dump(sim_data, fh, default_flow_style=False,
                  allow_unicode=True, sort_keys=False)


def load_simulation_state(game_dir: str) -> dict | None:
    """Load simulation state from YAML. Returns None if not found."""
    from pathlib import Path
    import yaml

    sim_file = Path(game_dir) / "simulation.yaml"
    if not sim_file.exists():
        return None

    with open(sim_file, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
