"""Night City Autonomous Simulator — headless orchestrator.

Runs the full simulation loop without any interactive input.
NPC agents select actions through the autonomous_agent system,
which feeds into the rpg_engine's action resolver pipeline.

Usage:
    python -m cyberpunk_sim.city_sim
    python -m cyberpunk_sim.city_sim --max-ticks 100
"""

import argparse
import logging
import random
import sys
import time
from pathlib import Path
from typing import Any

# Add rpg_engine to path for imports
_project_root = Path(__file__).resolve().parent.parent
_rpg_engine_dir = _project_root / "rpg_engine"
if str(_rpg_engine_dir) not in sys.path:
    sys.path.insert(0, str(_rpg_engine_dir))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import yaml

from cyberpunk_sim.config import SimConfig
from cyberpunk_sim.event_schema import (
    build_agent_event,
    build_event,
    build_faction_event,
    build_relationship_event,
    build_world_event,
    build_mission_event,
    build_combat_event,
    sim_time,
)
from cyberpunk_sim.event_emitter import EventEmitter
from cyberpunk_sim.autonomous_agent import select_action
from cyberpunk_sim.cyberpunk_systems import CyberpunkSystems

# rpg_engine imports
from game_state import load_game_data
from action_resolver import classify_action, validate_action, resolve_outcome, apply_consequences
from trigger_engine import evaluate_all, apply_all_triggers
from simulation import advance_simulation, load_simulation_state
from session import new_session, start_turn, record_turn
from combat_engine import start_combat, resolve_combat_round, get_combat_consequences

logger = logging.getLogger("nightcity")


def main():
    parser = argparse.ArgumentParser(description="Night City Autonomous Simulator")
    parser.add_argument("--max-ticks", type=int, default=None,
                        help="Override SIM_MAX_TICKS (0 = infinite)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Override SIM_SEED")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Override SIM_OUTPUT_DIR")
    args = parser.parse_args()

    config = SimConfig.from_env()
    if args.max_ticks is not None:
        config.max_ticks = args.max_ticks
    if args.seed is not None:
        config.seed = args.seed
    if args.output_dir is not None:
        config.output_dir = args.output_dir

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    run_simulation(config)


def run_simulation(config: SimConfig):
    """Main simulation loop."""
    rng = random.Random(config.seed)
    game_dir = str(Path(__file__).resolve().parent / "game_data")

    # Load game data
    logger.info("Loading game data from %s", game_dir)
    data = load_game_data(game_dir)

    # Load economy data
    economy_path = Path(game_dir) / "economy.yaml"
    with open(economy_path) as f:
        economy_data = yaml.safe_load(f).get("economy", {})

    # Load simulation state (schedules, relationships, territories, relations)
    sim_state = load_simulation_state(game_dir) or {}
    schedules = sim_state.get("schedules", {})
    relationships = sim_state.get("relationships", [])
    faction_territories = sim_state.get("faction_territories", {})
    faction_relations = sim_state.get("faction_relations", [])

    # Initialize session (lightweight — used for trigger engine context)
    session = new_session(game_dir, "nightcity_observer")

    # Initialize event emitter
    emitter = EventEmitter(config)
    emitter.start()

    # Initialize cyberpunk systems
    systems = CyberpunkSystems(economy_data, rng)

    # Assign factions to NPCs that don't have them
    _assign_factions(data, rng)

    # Ensure NPCs have basic stats
    _ensure_npc_stats(data, rng)

    logger.info("Simulation starting: seed=%d, max_ticks=%d, agents_per_tick=%d",
                config.seed, config.max_ticks, config.agents_per_tick)

    # Emit start event
    emitter.emit(build_event("world.disturbance", 0,
                             description="Night City simulation started",
                             config={"seed": config.seed,
                                     "agents_per_tick": config.agents_per_tick,
                                     "max_ticks": config.max_ticks}))

    tick = 0
    tick_interval = config.tick_ms / 1000.0
    npc_roster = list(data.get("npcs", []))
    roster_index = 0

    try:
        while config.max_ticks == 0 or tick < config.max_ticks:
            tick_start = time.monotonic()

            # 1. Advance base simulation (NPC schedules, faction dynamics, world events)
            turn = start_turn(session)
            sim_result = advance_simulation(
                data, turn,
                schedules=schedules,
                relationships=relationships,
                faction_territories=faction_territories,
                faction_relations=faction_relations,
                rng=rng,
            )

            # Track quest count for mission.generated detection
            quest_count_before = len(data.get("quests", []))

            # Emit simulation events
            _emit_simulation_events(emitter, tick, sim_result, data)

            # Check for newly generated quests
            quests_now = data.get("quests", [])
            if len(quests_now) > quest_count_before:
                for q in quests_now[quest_count_before:]:
                    emitter.emit(build_mission_event(
                        "mission.generated", tick,
                        mission_id=q.get("id", ""),
                        name=q.get("name", ""),
                        faction_id=q.get("faction", ""),
                    ))

            # 2. Advance cyberpunk-specific systems
            system_events = systems.tick(tick, data, sim_state)
            for evt in system_events:
                emitter.emit(evt)

            # 3. Select active agents (round-robin subset)
            active_npcs = _select_active_agents(
                npc_roster, roster_index, config.agents_per_tick,
            )
            roster_index = (roster_index + config.agents_per_tick) % max(len(npc_roster), 1)

            # 4. Process each agent's action
            for npc in active_npcs:
                _process_agent_turn(npc, data, session, sim_state,
                                    emitter, tick, rng, systems)

            tick += 1

            # Pace the simulation
            elapsed = time.monotonic() - tick_start
            sleep_time = tick_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

            if tick % 100 == 0:
                logger.info("Tick %d completed (day %d, %s)",
                            tick, sim_time(tick)["sim_day"],
                            sim_time(tick)["sim_time_phase"])

    except KeyboardInterrupt:
        logger.info("Simulation stopped by user at tick %d", tick)
    finally:
        emitter.stop()
        logger.info("Emitter stopped. Total ticks: %d", tick)


def _process_agent_turn(npc: dict, data: dict, session: dict,
                         sim_state: dict, emitter: EventEmitter,
                         tick: int, rng: random.Random,
                         systems: CyberpunkSystems):
    """Run one NPC through the full action pipeline."""
    npc_id = npc["id"]
    npc_name = npc.get("name", npc_id)
    location_id = npc.get("location", "")

    # Temporarily set player location to this NPC's location
    # so the action resolver's validation works for NPC actions
    player = data.get("player", {})
    original_player_loc = player.get("location", "")
    player["location"] = location_id

    try:
        _do_agent_turn(npc, npc_id, npc_name, location_id,
                        data, session, sim_state, emitter, tick, rng, systems)
    finally:
        player["location"] = original_player_loc


def _do_agent_turn(npc: dict, npc_id: str, npc_name: str, location_id: str,
                    data: dict, session: dict, sim_state: dict,
                    emitter: EventEmitter, tick: int, rng: random.Random,
                    systems: CyberpunkSystems):
    """Inner agent turn logic (player location already set)."""
    # Agent selects action
    action_text, goal_change = select_action(npc, data, sim_state, rng)

    # Emit goal change event if applicable
    if goal_change:
        emitter.emit(build_agent_event(
            "agent.goal_change", tick, npc_id, npc_name, location_id,
            new_goal=goal_change,
            previous_goal=npc.get("_prev_goal", ""),
        ))
        npc["_prev_goal"] = goal_change

    # Classify action (state-aware)
    action = classify_action(action_text, data)

    # Emit the agent action event
    emitter.emit(build_agent_event(
        f"agent.{action.get('action_type', 'look')}", tick,
        npc_id, npc_name, location_id,
        raw_input=action_text,
        action_type=action.get("action_type", "look"),
        target=action.get("target", ""),
        target_id=action.get("target_id", ""),
        confidence=action.get("confidence", 0),
    ))

    # Validate action
    validated = validate_action(action, data)
    if not validated.get("valid"):
        return

    # Resolve outcome
    outcome = resolve_outcome(validated, data)

    # Apply consequences
    consequences = outcome.get("consequences", [])
    if consequences:
        change_log = apply_consequences(consequences, data, session)
        _emit_consequence_events(emitter, tick, npc_id, npc_name,
                                 location_id, consequences, change_log)

    # Update NPC location if moved
    for c in consequences:
        if c.get("type") == "move_player":
            # For NPCs, "move_player" means move this NPC
            new_loc = c.get("location", "")
            if new_loc:
                npc["location"] = new_loc

    # Evaluate triggers
    fired = evaluate_all(data, action, session)
    if fired.get("encounters") or fired.get("quests"):
        trigger_log = apply_all_triggers(fired, data, session)

        # Emit trigger events
        for enc in fired.get("encounters", []):
            emitter.emit(build_event(
                "world.disturbance", tick,
                encounter_id=enc.get("id", ""),
                encounter_type=enc.get("type", ""),
                location_id=location_id,
                triggered_by=npc_id,
            ))

        for quest_info in fired.get("quests", []):
            quest_id = quest_info.get("quest_id", "")
            # Check if quest is now completed
            quest = next((q for q in data.get("quests", [])
                          if q.get("id") == quest_id), None)
            if quest and quest.get("completed"):
                emitter.emit(build_mission_event(
                    "mission.completed", tick,
                    mission_id=quest_id,
                    triggered_by=npc_id,
                ))
            else:
                emitter.emit(build_mission_event(
                    "mission.stage_advanced", tick,
                    mission_id=quest_id,
                    stage=quest_info.get("new_stage", 0),
                    triggered_by=npc_id,
                ))

    # Headless combat resolution for attack actions
    if action.get("action_type") == "attack" and validated.get("valid"):
        _resolve_headless_combat(npc, data, emitter, tick, rng, location_id)

    # Generate economy transaction events for trade/give actions
    if action.get("action_type") in ("give", "trade"):
        target_id = action.get("target_id", "")
        if target_id:
            price = rng.randint(50, 500)
            evt = systems.economy.process_transaction(
                tick, npc_id, target_id,
                action.get("target", "item"), price, location_id,
            )
            emitter.emit(evt)

    # Also emit transaction for talk-about-trade interactions
    if (action.get("action_type") == "talk"
        and action.get("topic", "") in ("trade", "business", "work")
        and action.get("target_id")):
        if rng.random() < 0.3:  # 30% of trade talks result in a deal
            price = rng.randint(100, 1000)
            emitter.emit(systems.economy.process_transaction(
                tick, npc_id, action["target_id"],
                "services", price, location_id,
            ))


def _emit_simulation_events(emitter: EventEmitter, tick: int,
                             sim_result: dict, data: dict):
    """Convert base simulation results to structured events."""
    # NPC moves
    for move in sim_result.get("npc_moves", []):
        emitter.emit(build_agent_event(
            "agent.move", tick,
            move.get("npc_id", ""),
            move.get("npc_name", ""),
            move.get("to", ""),
            from_location=move.get("from", ""),
            source="schedule",
        ))

    # Faction events
    for fevt in sim_result.get("faction_events", []):
        factions = fevt.get("factions", [])
        fid = factions[0] if factions else ""
        emitter.emit(build_faction_event(
            "faction.relation_change", tick, fid,
            description=fevt.get("text", ""),
            involved_factions=factions,
        ))

    # World event
    world_evt = sim_result.get("world_event")
    if world_evt:
        emitter.emit(build_world_event(
            "world.disturbance", tick,
            world_event_type=world_evt.get("type", ""),
            description=world_evt.get("text", ""),
            effects=world_evt.get("effects", {}),
        ))

    # Relationship changes
    for rel in sim_result.get("relationship_changes", []):
        emitter.emit(build_relationship_event(
            tick,
            source_id=rel.get("npc_a", ""),
            target_id=rel.get("npc_b", ""),
            old_strength=rel.get("old_strength", 0),
            new_strength=rel.get("new_strength", 0),
            relationship_type=rel.get("type", "neutral"),
        ))


def _emit_consequence_events(emitter: EventEmitter, tick: int,
                              npc_id: str, npc_name: str,
                              location_id: str,
                              consequences: list[dict],
                              change_log: list[str]):
    """Emit events for action consequences."""
    for c in consequences:
        ctype = c.get("type", "")
        if ctype == "enter_combat":
            emitter.emit(build_combat_event(
                "combat.started", tick, location_id,
                attacker_id=npc_id,
                attacker_name=npc_name,
                target=c.get("target", ""),
            ))
        elif ctype == "faction_reputation":
            emitter.emit(build_faction_event(
                "faction.relation_change", tick,
                c.get("faction_id", ""),
                delta=c.get("delta", 0),
                reason=c.get("reason", ""),
                caused_by=npc_id,
            ))
        elif ctype == "npc_disposition":
            emitter.emit(build_relationship_event(
                tick,
                source_id=npc_id,
                target_id=c.get("npc_id", ""),
                new_state=c.get("new_state", ""),
                reason=c.get("reason", ""),
            ))
        elif ctype == "advance_quest":
            emitter.emit(build_mission_event(
                "mission.stage_advanced", tick,
                mission_id=c.get("quest_id", ""),
                caused_by=npc_id,
            ))


def _select_active_agents(npc_roster: list[dict], start: int,
                           count: int) -> list[dict]:
    """Round-robin select a subset of NPCs for this tick."""
    n = len(npc_roster)
    if n == 0:
        return []
    if count >= n:
        return list(npc_roster)
    indices = [(start + i) % n for i in range(count)]
    return [npc_roster[i] for i in indices]


def _assign_factions(data: dict, rng: random.Random):
    """Assign factions to NPCs that don't have one, based on role heuristics."""
    factions = data.get("factions", [])
    if not factions:
        return

    # Build role → faction mapping from faction descriptions
    faction_by_type = {}
    for f in factions:
        desc = f.get("description", "").lower()
        for ftype in ("megacorp", "gang", "netrunner", "nomad", "law_enforcement", "underground"):
            if ftype in desc:
                faction_by_type[ftype] = f["id"]

    role_to_ftype = {
        "corpo_exec": "megacorp",
        "gang_lieutenant": "gang",
        "street_soldier": "gang",
        "ncpd_officer": "law_enforcement",
        "netrunner": "netrunner",
        "nomad": "nomad",
        "fixer": "underground",
    }

    for npc in data.get("npcs", []):
        if "faction" in npc:
            continue
        role = npc.get("role", "")
        ftype = role_to_ftype.get(role, "")
        if ftype and ftype in faction_by_type:
            npc["faction"] = faction_by_type[ftype]


def _ensure_npc_stats(data: dict, rng: random.Random):
    """Ensure all NPCs have basic stats for the action resolver."""
    role_stats = {
        "corpo_exec": {"health": 8, "max_health": 8, "damage": 2, "speed": "medium"},
        "gang_lieutenant": {"health": 12, "max_health": 12, "damage": 5, "speed": "fast"},
        "street_soldier": {"health": 8, "max_health": 8, "damage": 4, "speed": "fast"},
        "fixer": {"health": 7, "max_health": 7, "damage": 2, "speed": "medium"},
        "netrunner": {"health": 6, "max_health": 6, "damage": 3, "speed": "medium"},
        "ripperdoc": {"health": 7, "max_health": 7, "damage": 2, "speed": "slow"},
        "ncpd_officer": {"health": 10, "max_health": 10, "damage": 4, "speed": "medium"},
        "nomad": {"health": 9, "max_health": 9, "damage": 3, "speed": "medium"},
        "civilian": {"health": 5, "max_health": 5, "damage": 1, "speed": "slow"},
        "solo_merc": {"health": 14, "max_health": 14, "damage": 6, "speed": "fast"},
    }
    for npc in data.get("npcs", []):
        if "stats" not in npc:
            role = npc.get("role", "civilian")
            npc["stats"] = dict(role_stats.get(role, role_stats["civilian"]))


def _resolve_headless_combat(npc: dict, data: dict, emitter: EventEmitter,
                              tick: int, rng: random.Random, location_id: str):
    """Resolve combat headlessly — run rounds until one side drops."""
    npc_id = npc["id"]
    npc_name = npc.get("name", npc_id)
    npc_stats = npc.get("stats", {})

    # Find any other NPC at the same location to fight
    others_here = [
        n for n in data.get("npcs", [])
        if n.get("location") == location_id and n["id"] != npc_id
    ]
    if not others_here:
        return

    target = others_here[0]
    target_stats = target.get("stats", {})

    # Build enemy for combat engine
    enemy = {
        "name": target.get("name", target["id"]),
        "stats": {
            "health": target_stats.get("health", 5),
            "damage": target_stats.get("damage", 2),
            "speed": target_stats.get("speed", "medium"),
        },
        "behavior": "aggressive",
    }

    player_stats = {
        "health": npc_stats.get("health", 10),
        "stamina": 8,
        "damage": npc_stats.get("damage", 3),
    }

    combat = start_combat(player_stats, [enemy], rng)
    round_num = 0
    max_rounds = 5

    while not combat.get("finished") and round_num < max_rounds:
        round_num += 1
        actions = ["attack", "attack", "attack", "defend"]
        player_action = rng.choice(actions)
        result = resolve_combat_round(combat, player_action, rng)

        emitter.emit(build_combat_event(
            "combat.round", tick, location_id,
            attacker_id=npc_id,
            attacker_name=npc_name,
            target_id=target["id"],
            target_name=target.get("name", ""),
            round=round_num,
            player_action=player_action,
            player_health=result.get("player", {}).get("health", 0),
            enemies_remaining=len([e for e in result.get("enemies", [])
                                   if e.get("health", 0) > 0]),
        ))

        if result.get("finished"):
            combat["finished"] = True

    # Emit combat ended
    victory = combat.get("player", {}).get("health", 0) > 0
    emitter.emit(build_combat_event(
        "combat.ended", tick, location_id,
        attacker_id=npc_id,
        attacker_name=npc_name,
        target_id=target["id"],
        target_name=target.get("name", ""),
        rounds=round_num,
        result="victory" if victory else "defeat",
    ))

    # Apply health changes back to NPCs
    final_player_hp = combat.get("player", {}).get("health", npc_stats.get("health", 10))
    npc_stats["health"] = max(final_player_hp, 1)

    for enemy_state in combat.get("enemies", []):
        if enemy_state.get("health", 0) <= 0:
            target_stats["health"] = 0
            target["default_disposition"] = "unconscious"


if __name__ == "__main__":
    main()
