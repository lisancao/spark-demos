#!/usr/bin/env python3
"""
World Generator — Procedural world creation from genre templates.

Takes a genre template (TEMPLATE dict from genre_templates/) and generates
a complete set of 8 YAML files: locations, npcs, quests, items, factions,
encounters, world_rules, player.

Supports 4 topology algorithms for location graphs:
  branching_paths  — main road with side branches (dark fantasy, post-apocalyptic)
  urban_grid       — rectangular grid of districts (modern crime)
  hub_and_spoke    — central hub with radiating paths (high fantasy)
  star_cluster     — multiple hub systems connected by corridors (space opera)
"""

import copy
import random
import re
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_world(genre: str, name: str = "", seed: int = None,
                   output_dir: str = None) -> dict[str, Any]:
    """Generate a complete world and write all 8 YAML files.

    Returns a summary dict with counts.
    """
    from genre_templates import GENRES

    template = GENRES.get(genre)
    if not template:
        raise ValueError(f"Unknown genre: {genre}. Available: {list(GENRES.keys())}")

    # Seed RNG.
    rng = random.Random(seed)

    # Create output directory.
    out_dir = Path(output_dir) if output_dir else Path(f"generated_{genre}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate all entities.
    locations = _generate_locations(template, rng)
    start_location = _find_start_location(locations)

    npcs = _generate_npcs(template, locations, rng)
    quests = _generate_quests(template, locations, npcs, rng)
    items = _generate_items(template, rng)
    factions = _generate_factions(template, rng)
    encounters = _generate_encounters(template, locations, npcs, quests, rng)
    world_rules = _generate_world_rules(template, name)
    player = _generate_player(template, start_location, rng)

    # Distribute some items to locations.
    _place_items_in_locations(locations, items, rng)

    # Generate simulation data (schedules, relationships, faction dynamics).
    from simulation import (
        generate_npc_schedules, generate_npc_relationships,
        generate_faction_territories, generate_faction_relations,
        save_simulation_state,
    )
    schedules = generate_npc_schedules(npcs, locations, rng)
    relationships = generate_npc_relationships(npcs, rng)
    faction_territories = generate_faction_territories(factions, locations, rng)
    faction_relations = generate_faction_relations(factions, rng)

    # Write all YAML files.
    _write_yaml(out_dir / "locations.yaml", {"locations": locations})
    _write_yaml(out_dir / "npcs.yaml", {"npcs": npcs})
    _write_yaml(out_dir / "quests.yaml", {"quests": quests})
    _write_yaml(out_dir / "items.yaml", {"items": items})
    _write_yaml(out_dir / "factions.yaml", {"factions": factions})
    _write_yaml(out_dir / "encounters.yaml", {"encounters": encounters})
    _write_yaml(out_dir / "world_rules.yaml", {"world_rules": world_rules})
    _write_yaml(out_dir / "player.yaml", {"player": player})

    # Write simulation state.
    save_simulation_state(str(out_dir), schedules, relationships,
                          faction_territories, faction_relations)

    return {
        "game_dir": str(out_dir),
        "location_count": len(locations),
        "npc_count": len(npcs),
        "quest_count": len(quests),
        "item_count": len(items),
        "faction_count": len(factions),
        "encounter_count": len(encounters),
        "relationship_count": len(relationships),
    }


# ---------------------------------------------------------------------------
# Location generation
# ---------------------------------------------------------------------------

def _generate_locations(template: dict, rng: random.Random) -> list[dict]:
    """Generate the location graph using the template's topology."""
    topology = template.get("topology", "branching_paths")
    loc_range = template.get("location_count", {"min": 8, "max": 12})
    count = rng.randint(loc_range["min"], loc_range["max"])

    loc_types = template.get("location_types", [])
    name_pools = template.get("name_pools", {})

    # Generate the type sequence.
    type_sequence = _pick_location_types(loc_types, count, rng)

    # Generate names.
    used_names = set()
    locations = []
    for i, loc_type in enumerate(type_sequence):
        loc_id = _make_id(loc_type["type"], i, used_names)
        loc_name = _generate_location_name(loc_type, name_pools, used_names, rng)
        used_names.add(loc_name.lower())

        sensory = _pick_sensory(loc_type.get("sensory", {}), rng)
        atmosphere = rng.choice(loc_type.get("atmosphere", [""])) if loc_type.get("atmosphere") else ""

        state = "normal"
        if "magical" in loc_type.get("tags", []):
            state = "dormant"

        locations.append({
            "id": loc_id,
            "name": loc_name,
            "description": "",  # Will be filled by _generate_description.
            "sensory": sensory,
            "atmosphere": atmosphere,
            "connections": [],  # Filled by topology.
            "items": [],
            "tags": list(loc_type.get("tags", [])),
            "state": state,
            "_type": loc_type["type"],  # Internal, for NPC placement.
        })

    # Generate descriptions from sensory data.
    for loc in locations:
        loc["description"] = _generate_location_description(loc, rng)

    # Apply topology to create connections.
    topology_fn = TOPOLOGIES.get(topology, _topology_branching_paths)
    topology_fn(locations, rng)

    # Remove internal fields.
    for loc in locations:
        loc.pop("_type", None)

    return locations


def _pick_location_types(loc_types: list[dict], count: int,
                         rng: random.Random) -> list[dict]:
    """Pick location types using weighted random selection."""
    # Ensure we have at least one start location.
    start_types = [lt for lt in loc_types if lt.get("is_start")]
    other_types = [lt for lt in loc_types if not lt.get("is_start")]

    sequence = []
    if start_types:
        sequence.append(rng.choice(start_types))
        count -= 1

    # Weighted selection for the rest.
    weights = [lt.get("weight", 1) for lt in loc_types]
    total_weight = sum(weights)
    for _ in range(count):
        r = rng.uniform(0, total_weight)
        cumulative = 0
        for lt, w in zip(loc_types, weights):
            cumulative += w
            if r <= cumulative:
                sequence.append(lt)
                break

    return sequence


def _make_id(type_name: str, index: int, used: set) -> str:
    """Generate a unique location ID."""
    base = f"{type_name}_{index}"
    if base not in used:
        used.add(base)
        return base
    i = 2
    while f"{base}_{i}" in used:
        i += 1
    used.add(f"{base}_{i}")
    return f"{base}_{i}"


def _generate_location_name(loc_type: dict, name_pools: dict,
                             used_names: set, rng: random.Random) -> str:
    """Generate a location name from patterns and name pools."""
    patterns = loc_type.get("name_patterns", ["{adj} {noun}"])
    pattern = rng.choice(patterns)

    # Fill template fields.
    max_attempts = 20
    for _ in range(max_attempts):
        name = pattern
        for field in re.findall(r'\{(\w+)\}', pattern):
            pool = name_pools.get(field, ["Unknown"])
            name = name.replace(f"{{{field}}}", rng.choice(pool), 1)

        if name.lower() not in used_names:
            return name

    return f"Place {len(used_names) + 1}"


def _pick_sensory(sensory_template: dict, rng: random.Random) -> dict:
    """Pick one sensory detail per sense from the template pools."""
    result = {}
    for sense, options in sensory_template.items():
        if isinstance(options, list) and options:
            result[sense] = rng.choice(options)
        elif isinstance(options, str):
            result[sense] = options
    return result


def _generate_location_description(loc: dict, rng: random.Random) -> str:
    """Generate a description from the location's sensory data and atmosphere."""
    parts = []
    sensory = loc.get("sensory", {})
    if sensory.get("sight"):
        parts.append(sensory["sight"])
    atmosphere = loc.get("atmosphere", "")
    if atmosphere:
        parts.append(atmosphere)
    return " ".join(parts) if parts else loc.get("name", "A place.")


def _place_items_in_locations(locations: list[dict], items: list[dict],
                               rng: random.Random):
    """Place clue and quest items at appropriate locations."""
    clue_items = [i for i in items if "clue" in i.get("tags", [])]
    non_safe = [l for l in locations if "safe" not in l.get("tags", [])]
    safe_locs = [l for l in locations if "safe" in l.get("tags", [])]
    all_locs = safe_locs + non_safe if safe_locs else locations

    for item in clue_items[:3]:  # Place up to 3 clue items.
        loc = rng.choice(all_locs) if all_locs else locations[0]
        loc.setdefault("items", []).append({
            "id": item["id"],
            "name": item["name"],
            "description": item.get("description", ""),
        })


# ---------------------------------------------------------------------------
# Topology algorithms
# ---------------------------------------------------------------------------

def _topology_branching_paths(locations: list[dict], rng: random.Random):
    """Main road with side branches. Dead ends at dangerous/mystery locations."""
    if len(locations) < 2:
        return

    # Shuffle non-start locations.
    start = locations[0]
    rest = locations[1:]
    rng.shuffle(rest)

    # Main path: start → first half of locations.
    main_count = max(3, len(rest) // 2)
    main_path = [start] + rest[:main_count]
    branches = rest[main_count:]

    # Connect main path linearly.
    directions = ["north", "east", "north", "west", "north", "east"]
    for i in range(len(main_path) - 1):
        d = directions[i % len(directions)]
        _connect(main_path[i], main_path[i + 1], d)

    # Attach branches to main path nodes.
    branch_dirs = ["west", "east", "south", "north"]
    for i, branch in enumerate(branches):
        parent_idx = rng.randint(0, len(main_path) - 1)
        parent = main_path[parent_idx]
        d = branch_dirs[i % len(branch_dirs)]

        # Avoid duplicate directions.
        existing_dirs = {c.get("direction") for c in parent.get("connections", [])}
        while d in existing_dirs:
            d = rng.choice(branch_dirs)

        blocked = None
        if "dangerous" in branch.get("tags", []) and rng.random() < 0.3:
            blocked = _random_blockage(rng)

        _connect(parent, branch, d, blocked_by=blocked)


def _topology_urban_grid(locations: list[dict], rng: random.Random):
    """Rectangular grid of city blocks."""
    if len(locations) < 2:
        return

    # Determine grid size.
    n = len(locations)
    cols = max(2, int(n ** 0.5))
    rows = (n + cols - 1) // cols

    # Place locations in grid cells.
    grid = {}
    for i, loc in enumerate(locations):
        row = i // cols
        col = i % cols
        grid[(row, col)] = loc

    # Connect adjacent cells.
    for (row, col), loc in grid.items():
        # East.
        if (row, col + 1) in grid:
            _connect(loc, grid[(row, col + 1)], "east")
        # South.
        if (row + 1, col) in grid:
            _connect(loc, grid[(row + 1, col)], "south")

    # Randomly block 1-2 connections.
    all_conns = []
    for loc in locations:
        for conn in loc.get("connections", []):
            all_conns.append((loc, conn))
    if all_conns:
        for _ in range(min(2, len(all_conns))):
            loc, conn = rng.choice(all_conns)
            if not conn.get("blocked_by"):
                conn["blocked_by"] = _random_blockage_urban(rng)
                break


def _topology_hub_and_spoke(locations: list[dict], rng: random.Random):
    """Central hub with radiating paths to destinations."""
    if len(locations) < 2:
        return

    hub = locations[0]
    rest = locations[1:]
    rng.shuffle(rest)

    # Create hub connections — inner ring.
    inner_count = min(4, len(rest))
    inner = rest[:inner_count]
    outer = rest[inner_count:]

    directions = ["north", "east", "south", "west"]
    for i, loc in enumerate(inner):
        d = directions[i % len(directions)]
        _connect(hub, loc, d)

    # Outer locations connect to inner ring nodes.
    for i, loc in enumerate(outer):
        parent = inner[i % len(inner)]
        # Pick direction away from hub.
        parent_dir = ""
        for conn in parent.get("connections", []):
            if conn.get("to") == hub["id"]:
                parent_dir = REVERSE_DIR.get(conn.get("direction", ""), "")
                break
        if not parent_dir:
            parent_dir = rng.choice(directions)

        blocked = None
        if "dangerous" in loc.get("tags", []) and rng.random() < 0.4:
            blocked = _random_blockage(rng)

        _connect(parent, loc, parent_dir, blocked_by=blocked)


def _topology_star_cluster(locations: list[dict], rng: random.Random):
    """Multiple hub systems connected by corridors."""
    if len(locations) < 2:
        return

    # Determine number of clusters.
    n = len(locations)
    num_clusters = max(2, min(4, n // 3))

    # Split locations into clusters.
    rng.shuffle(locations)
    clusters = [[] for _ in range(num_clusters)]
    for i, loc in enumerate(locations):
        clusters[i % num_clusters].append(loc)

    # Connect within each cluster (star pattern).
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        hub = cluster[0]
        directions = ["north", "east", "south", "west"]
        for i, loc in enumerate(cluster[1:]):
            d = directions[i % len(directions)]
            _connect(hub, loc, d)

    # Connect clusters to each other via their hubs.
    for i in range(len(clusters) - 1):
        hub_a = clusters[i][0]
        hub_b = clusters[i + 1][0]
        _connect(hub_a, hub_b, "east")


REVERSE_DIR = {"north": "south", "south": "north", "east": "west", "west": "east"}

TOPOLOGIES = {
    "branching_paths": _topology_branching_paths,
    "urban_grid": _topology_urban_grid,
    "hub_and_spoke": _topology_hub_and_spoke,
    "star_cluster": _topology_star_cluster,
}


def _connect(loc_a: dict, loc_b: dict, direction: str,
             blocked_by: str = None):
    """Create a bidirectional connection between two locations."""
    conn_a = {"to": loc_b["id"], "direction": direction}
    if blocked_by:
        conn_a["blocked_by"] = blocked_by
    loc_a.setdefault("connections", []).append(conn_a)

    reverse = REVERSE_DIR.get(direction, direction)
    conn_b = {"to": loc_a["id"], "direction": reverse}
    if blocked_by:
        conn_b["blocked_by"] = blocked_by
    loc_b.setdefault("connections", []).append(conn_b)


def _random_blockage(rng: random.Random) -> str:
    options = [
        "The path is overgrown and something has blocked it.",
        "A rockfall blocks the way. It might be passable with effort.",
        "Thick webbing covers the entrance. Something lives here.",
        "The bridge is collapsed. You'd need to find another way.",
    ]
    return rng.choice(options)


def _random_blockage_urban(rng: random.Random) -> str:
    options = [
        "Police checkpoint. They're not letting anyone through.",
        "Gang territory. Wrong colors to be walking here.",
        "Road construction. Or that's what the signs say.",
        "Barricade. Someone doesn't want visitors.",
    ]
    return rng.choice(options)


# ---------------------------------------------------------------------------
# NPC generation
# ---------------------------------------------------------------------------

def _generate_npcs(template: dict, locations: list[dict],
                   rng: random.Random) -> list[dict]:
    """Generate NPCs and place them in locations."""
    npc_range = template.get("npc_count", {"min": 5, "max": 10})
    count = rng.randint(npc_range["min"], npc_range["max"])
    archetypes = template.get("npc_archetypes", [])

    if not archetypes:
        return []

    # Build location type lookup.
    loc_by_type = {}
    for loc in locations:
        lt = loc.get("_type", loc.get("tags", ["unknown"])[0] if loc.get("tags") else "unknown")
        loc_by_type.setdefault(lt, []).append(loc)

    used_names = set()
    npcs = []

    for i in range(count):
        archetype = _pick_weighted(archetypes, rng)
        name = _pick_unique(archetype.get("names", [f"NPC_{i}"]), used_names, rng)
        used_names.add(name.lower())

        # Place in appropriate location.
        pref_type = archetype.get("location_type", "")
        if pref_type and pref_type in loc_by_type:
            location = rng.choice(loc_by_type[pref_type])
        else:
            location = rng.choice(locations)

        personality = rng.choice(archetype.get("personalities", ["Reserved."]))
        npc_id = _slugify(name)

        # Generate knowledge.
        knowledge = []
        for topic in archetype.get("knowledge_topics", [])[:3]:
            knowledge.append({
                "id": f"{npc_id}_knows_{_slugify(topic)}",
                "content": f"{name} knows about {topic}.",
                "willingness": rng.choice([
                    "shares if asked directly",
                    "trades for information",
                    "won't share easily — needs trust",
                    "mentions casually if prompted",
                ]),
            })

        # Generate secret.
        secrets = []
        secret_types = archetype.get("secret_types", [])
        if secret_types:
            secret_type = rng.choice(secret_types)
            secrets.append({
                "id": f"{npc_id}_secret",
                "hint": f"Something about {name} seems off when you mention {secret_type}.",
                "content": f"{name}'s secret involves {secret_type}.",
            })

        # Voice profile from archetype.
        from npc_voice import VOICE_ARCHETYPES
        voice_key = archetype.get("voice", "innkeeper")
        voice_profile = copy.deepcopy(VOICE_ARCHETYPES.get(voice_key, {}))

        # Generate dialogue hooks.
        hooks = []
        for topic in archetype.get("knowledge_topics", [])[:2]:
            hooks.append({
                "topic": topic,
                "response_style": rng.choice([
                    "Cautious, partial answers. Watches your reaction.",
                    "In their element. Warm, expert.",
                    "Deflects first, then cautious partial answers.",
                    "Interested but guarded. Values what you share.",
                ]),
            })

        # Activity.
        activities = {
            "innkeeper": ["Wiping down the bar.", "Serving a table.", "Watching the door."],
            "merchant": ["Arranging goods.", "Counting coins.", "Eyeing passersby."],
            "chapel keeper": ["Standing very still.", "Tending candles.", "Watching the flames."],
            "guard": ["Leaning on a wall.", "Scanning the crowd.", "Sharpening a blade."],
            "herbalist": ["Sorting dried herbs.", "Grinding something in a mortar.", "Sniffing a jar."],
            "crime_boss": ["Sitting in the back booth.", "Smoking.", "Making someone wait."],
            "detective": ["Taking notes.", "Watching everyone.", "Nursing a cold coffee."],
            "street_dealer": ["Leaning on a corner.", "Checking their phone.", "Watching for cops."],
            "bartender": ["Polishing a glass.", "Pouring drinks.", "Watching the room."],
            "fixer": ["On the phone.", "Reading something.", "Waiting for you."],
            "informant": ["Fidgeting.", "Looking over their shoulder.", "Talking too fast."],
            "king": ["Seated on the throne.", "Consulting advisors.", "Studying a map."],
            "wizard": ["Reading a tome.", "Stirring something.", "Staring into middle distance."],
            "ranger": ["Checking gear.", "Watching the horizon.", "Carving something."],
            "bard": ["Tuning an instrument.", "Telling a story.", "Listening intently."],
            "admiral": ["Reviewing reports.", "Standing at parade rest.", "Monitoring displays."],
            "pilot": ["Running pre-flight checks.", "Leaning on their ship.", "Arguing with maintenance."],
            "engineer": ["Welding something.", "Muttering about specs.", "Buried in a panel."],
            "warlord": ["Sharpening a weapon.", "Giving orders.", "Eating without looking up."],
            "scavenger": ["Sorting through scrap.", "Repairing something.", "Keeping one eye on you."],
        }
        role = archetype.get("role", "")
        activity = rng.choice(activities.get(role, ["Going about their business."]))

        npcs.append({
            "id": npc_id,
            "name": name,
            "role": role,
            "location": location["id"],
            "appearance": f"A {rng.choice(['lean', 'broad', 'wiry', 'tall', 'short', 'weathered'])} figure.",
            "appearance_brief": f"{name}, the {role}.",
            "personality": personality,
            "default_disposition": archetype.get("default_disposition", "neutral"),
            "dispositions": [{
                "toward": "player",
                "state": archetype.get("default_disposition", "neutral"),
                "reason": "First impression.",
            }],
            "voice_archetype": voice_key,
            "voice_profile": voice_profile,
            "knowledge": knowledge,
            "secrets": secrets,
            "dialogue_hooks": hooks,
            "current_activity": activity,
            "tags": [role, "information"] if knowledge else [role],
        })

    return npcs


# ---------------------------------------------------------------------------
# Quest generation
# ---------------------------------------------------------------------------

def _generate_quests(template: dict, locations: list[dict],
                     npcs: list[dict], rng: random.Random) -> list[dict]:
    """Generate quest chains referencing real location/NPC IDs."""
    patterns = template.get("quest_patterns", [])
    if not patterns:
        return []

    name_pools = template.get("name_pools", {})
    quest_count = min(len(patterns), 3)

    loc_by_type = {}
    for loc in locations:
        lt = loc.get("_type", "")
        if lt:
            loc_by_type.setdefault(lt, []).append(loc)

    # Index NPCs by location for quest-giver assignment.
    npcs_by_loc = {}
    for npc in npcs:
        npcs_by_loc.setdefault(npc.get("location", ""), []).append(npc)

    # Location id → name lookup.
    loc_names = {loc["id"]: loc["name"] for loc in locations}

    quests = []
    used_names = set()

    for i in range(quest_count):
        pattern = patterns[i % len(patterns)]
        quest_name = _generate_name_from_patterns(
            pattern.get("name_templates", ["A Quest"]),
            name_pools, used_names, rng
        )
        used_names.add(quest_name.lower())

        quest_id = _slugify(quest_name)

        # Generate stages.
        stages = []
        stage_templates = pattern.get("stage_templates", [])
        num_stages = len(stage_templates)

        for stage_idx, st in enumerate(stage_templates):
            loc_type = st.get("location_type", "any")
            # Find a matching location.
            if loc_type in loc_by_type:
                stage_loc = rng.choice(loc_by_type[loc_type])
                location_id = stage_loc["id"]
            elif loc_type == "any":
                location_id = "any"
            else:
                stage_loc = rng.choice(locations)
                location_id = stage_loc["id"]

            # Fill template variables — track substituted NPC.
            objective = st.get("objective", "Do something.")
            stage_npc = None
            if "{npc}" in objective and npcs:
                # Prefer an NPC at this stage's location.
                local_npcs = npcs_by_loc.get(location_id, [])
                stage_npc = rng.choice(local_npcs) if local_npcs else rng.choice(npcs)
                objective = objective.replace("{npc}", stage_npc["name"])
            if "{location}" in objective:
                loc = rng.choice(locations)
                objective = objective.replace("{location}", loc["name"])
            for field in re.findall(r'\{(\w+)\}', objective):
                pool = name_pools.get(field, ["something"])
                objective = objective.replace(f"{{{field}}}", rng.choice(pool), 1)

            # --- Build conditions and triggers based on stage role ---
            conditions = []
            triggers = []
            loc_display = loc_names.get(location_id, location_id.replace("_", " ")) if location_id != "any" else "anywhere"

            if location_id != "any":
                conditions.append({"type": "at_location", "location": location_id})

            if stage_idx == 0:
                # Stage 0: activation requires talking to an NPC.
                if stage_npc is None and npcs:
                    local_npcs = npcs_by_loc.get(location_id, [])
                    stage_npc = rng.choice(local_npcs) if local_npcs else rng.choice(npcs)
                if stage_npc:
                    conditions.append({"type": "action_type", "action_type": "talk"})
                    triggers.append(f"Talk to {stage_npc['name']} at {loc_display}")
                    # Store quest hook on the NPC so narrative prompts can mention it.
                    stage_npc.setdefault("quest_hooks", []).append({
                        "quest_id": quest_id,
                        "quest_name": quest_name,
                        "role": "quest_giver",
                    })
                else:
                    triggers.append(f"Visit {loc_display}")

            elif stage_idx == num_stages - 1 and pattern.get("type", "") in ("fetch", "escort", "delivery"):
                # Final stage of return-type quests: arriving is enough.
                triggers.append(f"Return to {loc_display}")

            else:
                # Middle stages: detect action from objective verb.
                action_type = _action_type_from_objective(objective)
                if action_type:
                    conditions.append({"type": "action_type", "action_type": action_type})
                npc_name = stage_npc["name"] if stage_npc else None
                triggers.append(_build_trigger_text(action_type, npc_name, loc_display, objective))

            stages.append({
                "objective": objective,
                "location": location_id,
                "triggers": triggers,
                "conditions": conditions,
                "hints": [f"Look around {loc_display} for clues."] if location_id != "any" else [f"This can happen anywhere."],
                "completion": f"Stage completed: {objective}",
            })

        quests.append({
            "id": quest_id,
            "name": quest_name,
            "description": f"A {pattern.get('type', 'quest')} quest: {quest_name}.",
            "status": "inactive",
            "current_stage": 0,
            "stages": stages,
        })

    return quests


# Verb → action_type mapping for quest stage conditions.
_VERB_ACTION_MAP = [
    ({"learn", "ask", "hear", "speak", "talk", "tell", "return", "report", "meet"}, "talk"),
    ({"investigate", "explore", "search", "reach", "scout", "survey"}, "look"),
    ({"find", "take", "retrieve", "collect", "gather", "pick", "grab", "steal"}, "take"),
    ({"decide", "understand", "reflect", "consider", "choose"}, None),  # at_location only
]


def _action_type_from_objective(objective: str) -> str | None:
    """Detect the required action_type from a stage objective's leading verb."""
    first_word = objective.lstrip().split()[0].lower().rstrip(".,!") if objective.strip() else ""
    for verbs, action in _VERB_ACTION_MAP:
        if first_word in verbs:
            return action
    # Default: if the objective mentions making a choice or stand, talk.
    lower = objective.lower()
    if "make your" in lower or "confront" in lower:
        return "talk"
    return None


def _build_trigger_text(action_type: str | None, npc_name: str | None,
                        loc_display: str, objective: str) -> str:
    """Build a human-readable trigger string for a quest stage."""
    if action_type == "talk" and npc_name:
        return f"Talk to {npc_name}" + (f" at {loc_display}" if loc_display != "anywhere" else "")
    if action_type == "talk":
        return f"Speak with someone" + (f" at {loc_display}" if loc_display != "anywhere" else "")
    if action_type == "look":
        return f"Investigate {loc_display}"
    if action_type == "take":
        return f"Search {loc_display} for what you need"
    if loc_display == "anywhere":
        return objective
    return f"Go to {loc_display}"


# ---------------------------------------------------------------------------
# Item generation
# ---------------------------------------------------------------------------

def _generate_items(template: dict, rng: random.Random) -> list[dict]:
    """Generate world items from template item types."""
    item_types = template.get("item_types", [])
    items = []
    used_ids = set()

    for itype in item_types:
        category = itype.get("category", "misc")
        tags = list(itype.get("tags", [category]))
        item_pool = itype.get("items", [])

        # Pick 2-4 items per category.
        count = min(len(item_pool), rng.randint(2, 4))
        selected = rng.sample(item_pool, count) if len(item_pool) >= count else item_pool

        for item_data in selected:
            item_name = item_data.get("name", f"a {category}")
            item_id = _slugify(item_name)
            while item_id in used_ids:
                item_id += f"_{rng.randint(0, 99)}"
            used_ids.add(item_id)

            item = {
                "id": item_id,
                "name": item_name,
                "description": item_data.get("desc", ""),
                "properties": {},
                "tags": tags,
            }

            # Set properties by category.
            if category == "weapon":
                item["properties"]["damage"] = rng.randint(2, 5)
            elif category == "consumable":
                item["properties"]["consumable"] = True
                item["properties"]["heals"] = rng.randint(2, 4)
            elif category == "tool":
                item["properties"]["reusable"] = True
            elif category == "clue":
                item["properties"]["readable"] = True

            items.append(item)

    return items


# ---------------------------------------------------------------------------
# Faction generation
# ---------------------------------------------------------------------------

def _generate_factions(template: dict, rng: random.Random) -> list[dict]:
    """Generate factions from template faction types."""
    faction_types = template.get("faction_types", [])
    name_pools = template.get("name_pools", {})
    factions = []
    used_names = set()

    for ftype in faction_types:
        name = _generate_name_from_patterns(
            ftype.get("name_templates", ["A Faction"]),
            name_pools, used_names, rng
        )
        used_names.add(name.lower())
        faction_id = _slugify(name)

        factions.append({
            "id": faction_id,
            "name": name,
            "description": f"A {ftype.get('type', 'faction')} faction.",
            "goals": list(ftype.get("goals", ["Survive."])),
            "default_reputation": ftype.get("default_reputation", "neutral"),
            "player_reputation": [],
        })

    return factions


# ---------------------------------------------------------------------------
# Encounter generation
# ---------------------------------------------------------------------------

def _generate_encounters(template: dict, locations: list[dict],
                          npcs: list[dict], quests: list[dict],
                          rng: random.Random) -> list[dict]:
    """Generate encounters bound to locations, wired to quest progression."""
    enc_types = template.get("encounter_types", [])
    encounters = []
    used_ids = set()

    # Build quest location maps for wiring encounters → quest advancement.
    # stage0_locs: location_id → quest_id  (dialogue encounters activate quests)
    # investigate_locs: location_id → quest_id  (discovery encounters advance quests)
    stage0_locs = {}
    investigate_locs = {}
    for quest in quests:
        quest_id = quest["id"]
        stages = quest.get("stages", [])
        if stages:
            loc0 = stages[0].get("location", "")
            if loc0 and loc0 != "any":
                stage0_locs[loc0] = quest_id
        # Middle stages with look/take actions map to discovery advancement.
        for stage in stages[1:]:
            for cond in stage.get("conditions", []):
                if cond.get("type") == "action_type" and cond.get("action_type") in ("look", "take"):
                    sloc = stage.get("location", "")
                    if sloc and sloc != "any":
                        investigate_locs[sloc] = quest_id

    for etype in enc_types:
        enc_type = etype.get("type", "combat")
        location_tags = set(etype.get("location_tags", []))

        # Find matching locations.
        matching_locs = [
            loc for loc in locations
            if location_tags.intersection(set(loc.get("tags", [])))
        ]
        if not matching_locs:
            matching_locs = locations[:3]

        # Generate 1-2 encounters per type.
        count = min(len(matching_locs), rng.randint(1, 2))

        for i in range(count):
            loc = matching_locs[i % len(matching_locs)]
            enc_id = f"{enc_type}_{loc['id']}"
            while enc_id in used_ids:
                enc_id += f"_{rng.randint(0, 99)}"
            used_ids.add(enc_id)

            tone = rng.choice(etype.get("tone_templates", [""])) if etype.get("tone_templates") else ""

            encounter = {
                "id": enc_id,
                "name": f"Event at {loc['name']}",
                "type": enc_type,
                "location": loc["id"],
                "trigger": f"Player explores {loc['name']}.",
                "conditions": [
                    {"type": "at_location", "location": loc["id"]},
                    {"type": "not_session_flag", "flag": f"encounter_fired_{enc_id}"},
                ],
                "description": f"Something happens at {loc['name']}.",
                "consequences": [],
                "tone_direction": tone,
            }

            # Add enemies for combat encounters.
            if enc_type == "combat" and etype.get("enemy_templates"):
                enemy = rng.choice(etype["enemy_templates"])
                encounter["enemies"] = [copy.deepcopy(enemy)]

            # Discovery encounters learn facts.
            if enc_type == "discovery":
                encounter["consequences"].append({
                    "type": "learn",
                    "fact": {
                        "id": f"discovered_{loc['id']}",
                        "content": f"You discovered something significant at {loc['name']}.",
                    },
                })

            # Wire dialogue encounters to quest activation (stage 0).
            if enc_type == "dialogue" and loc["id"] in stage0_locs:
                encounter["consequences"].append({
                    "type": "advance_quest",
                    "quest_id": stage0_locs[loc["id"]],
                })

            # Wire discovery encounters to quest advancement (investigation stages).
            if enc_type == "discovery" and loc["id"] in investigate_locs:
                encounter["consequences"].append({
                    "type": "advance_quest",
                    "quest_id": investigate_locs[loc["id"]],
                })

            encounters.append(encounter)

    return encounters


# ---------------------------------------------------------------------------
# World rules + player generation
# ---------------------------------------------------------------------------

def _generate_world_rules(template: dict, world_name: str) -> dict:
    """Build world_rules from template."""
    rules = copy.deepcopy(template.get("world_rules_template", {}))
    rules["register"] = template.get("register_preset", "dark-fantasy")
    return rules


def _generate_player(template: dict, start_location: str,
                     rng: random.Random) -> dict:
    """Generate starting player state."""
    defaults = template.get("player_defaults", {})
    return {
        "name": defaults.get("name", "the traveler"),
        "class": "",
        "level": 1,
        "location": start_location,
        "stats": copy.deepcopy(defaults.get("stats", {"health": 10})),
        "conditions": [],
        "inventory": copy.deepcopy(defaults.get("starting_items", [])),
        "knowledge": [],
        "event_log": [],
        "location_history": [],
    }


def _find_start_location(locations: list[dict]) -> str:
    """Find the starting location ID."""
    for loc in locations:
        if "safe" in loc.get("tags", []):
            return loc["id"]
    return locations[0]["id"] if locations else ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_weighted(items: list[dict], rng: random.Random) -> dict:
    """Pick an item using weight field."""
    weights = [i.get("weight", 1) for i in items]
    total = sum(weights)
    r = rng.uniform(0, total)
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def _pick_unique(pool: list[str], used: set, rng: random.Random) -> str:
    """Pick a unique name from a pool."""
    available = [n for n in pool if n.lower() not in used]
    if available:
        return rng.choice(available)
    # All used — add a suffix.
    base = rng.choice(pool)
    suffix = rng.randint(2, 99)
    return f"{base} the {suffix}th"


def _generate_name_from_patterns(patterns: list[str], name_pools: dict,
                                  used: set, rng: random.Random) -> str:
    """Generate a name from pattern templates."""
    for _ in range(20):
        pattern = rng.choice(patterns)
        name = pattern
        for field in re.findall(r'\{(\w+)\}', pattern):
            pool = name_pools.get(field, ["Unknown"])
            name = name.replace(f"{{{field}}}", rng.choice(pool), 1)
        if name.lower() not in used:
            return name
    return f"Untitled {len(used) + 1}"


def _slugify(text: str) -> str:
    """Convert text to a safe ID."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s_-]', '', text)
    text = re.sub(r'[\s]+', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')[:40]


def _write_yaml(filepath: Path, data: dict):
    """Write data to a YAML file."""
    with open(filepath, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False,
                  allow_unicode=True, sort_keys=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python world_generator.py <genre> [--name NAME] [--seed SEED] [--output DIR]")
        print("Genres: dark-fantasy, modern-crime, high-fantasy, space-opera, post-apocalyptic")
        sys.exit(1)

    genre = sys.argv[1]
    name = ""
    seed = None
    output = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--name" and i + 1 < len(args):
            name = args[i + 1]
            i += 2
        elif args[i] == "--seed" and i + 1 < len(args):
            seed = int(args[i + 1])
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output = args[i + 1]
            i += 2
        else:
            i += 1

    result = generate_world(genre, name=name, seed=seed, output_dir=output)
    print(f"Generated {genre} world:")
    for k, v in result.items():
        print(f"  {k}: {v}")
