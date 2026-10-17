#!/usr/bin/env python3
"""
The Game Master — Main orchestrator for the text-based RPG engine.

Full game loop with session persistence, trigger evaluation,
conversation history, and narrative prompt assembly.

Commands:
  play <game_dir>           Start an interactive game session
  resume <game_dir>         Resume a saved session
  test <game_dir>           Run a test action through the full pipeline
  scene <game_dir>          Generate a scene prompt from current state
  validate <file> --preset  Check narrative text against a world setting
  npc <archetype>           Show an NPC voice profile
  status <game_dir>         Show game state summary
  analyze <file>            Analyze narrative quality of a text file

Usage:
  python3 game_master.py play game_data/
  python3 game_master.py resume game_data/
  python3 game_master.py test game_data/ "talk to maren about thornwood"
  python3 game_master.py scene game_data/ --type exploration
  python3 game_master.py validate output.md --preset dark-fantasy
  python3 game_master.py status game_data/
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent to path for imports.
sys.path.insert(0, str(Path(__file__).parent))

from game_state import (
    load_game_data, save_full_state, get_player, get_location,
    get_npcs_at_location, get_active_quests, get_quest_stage, get_npc,
    record_event, get_world_summary,
)
from scene_engine import (
    resolve_scene_context, resolve_dialogue_context, resolve_combat_context,
    build_narrative_prompt,
)
from action_resolver import (
    classify_action, validate_action, resolve_outcome, apply_consequences,
)
from session import (
    new_session, start_turn, record_turn, save_session, load_session,
    list_saves, create_snapshot, get_conversation_context, get_action_summary,
    set_flag, get_flag, has_flag, set_active_scene, get_active_scene,
)
from trigger_engine import (
    evaluate_all, apply_all_triggers, apply_encounter_effects, apply_quest_trigger,
)
from npc_voice import (
    VOICE_ARCHETYPES, build_voice_instructions, format_voice_report,
)
from world_validator import (
    PRESETS as WORLD_PRESETS, load_preset, validate_text,
    format_validation_report,
)
from narrative_analyzer import (
    analyze_narrative, score_narrative, format_report as format_quality_report,
)
from simulation import (
    advance_simulation, format_simulation_events,
    load_simulation_state, save_simulation_state,
    propagate_faction_action,
)
from llm_client import create_client, generate_narrative, build_system_message, get_usage_summary
from combat_engine import (
    start_combat, resolve_combat_round, get_combat_summary,
    build_combat_prompt_context, get_combat_consequences,
)

ENGINE_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

def run_play(args):
    """Interactive game loop with full integration."""
    import random as _random

    game_dir = args.game_dir
    no_llm = getattr(args, "no_llm", False)
    data = load_game_data(game_dir)
    player = get_player(data)

    if not player:
        print("Error: No player.yaml found in game data.")
        sys.exit(1)

    # Parse multiplayer roster.
    roster = None
    game_id = getattr(args, "game_id_resolved", "")
    players_spec = getattr(args, "players", None)
    if players_spec:
        from multiplayer import parse_players
        roster = parse_players(players_spec)

    # Initialize LLM.
    llm_config = create_client() if not no_llm else {"available": False, "client": None, "total_calls": 0, "total_input_tokens": 0, "total_output_tokens": 0}
    system_msg = build_system_message(data) if llm_config.get("available") else ""
    if llm_config.get("available"):
        print(f"  LLM: connected ({llm_config.get('model', '?')})")
    else:
        print("  LLM: prompt-only mode")

    # Load simulation state.
    sim_state = load_simulation_state(game_dir) or {}
    sim_rng = _random.Random()

    # Create new session.
    session = new_session(game_dir, player_name=player.get("name", "unknown"))
    _print_banner(player, data, session)

    # Generate and display opening scene.
    _narrate_opening(data, session, llm_config, system_msg)

    # Main game loop.
    _game_loop(data, session, game_dir, sim_state, sim_rng, llm_config, system_msg,
               roster=roster, game_id=game_id)


def run_resume(args):
    """Resume a saved session."""
    import random as _random

    game_dir = args.game_dir
    no_llm = getattr(args, "no_llm", False)
    saves = list_saves(game_dir)

    if not saves:
        print("No saved sessions found. Starting new game...")
        args.command = "play"
        run_play(args)
        return

    print("Saved sessions:")
    for i, save in enumerate(saves):
        print(f"  [{i + 1}] Turn {save['turn']:3d} — {save['last_played']} (id: {save['session_id']})")

    print(f"  [n] New game")

    try:
        choice = input("\nSelect session: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice.lower() == 'n':
        args.command = "play"
        run_play(args)
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(saves):
            session = load_session(saves[idx]["file"])
            data = load_game_data(game_dir)
            player = get_player(data)

            # Initialize LLM.
            llm_config = create_client() if not no_llm else {"available": False, "client": None, "total_calls": 0, "total_input_tokens": 0, "total_output_tokens": 0}
            system_msg = build_system_message(data) if llm_config.get("available") else ""

            # Load simulation state.
            sim_state = load_simulation_state(game_dir) or {}
            sim_rng = _random.Random()

            print(f"\nResuming session {session['session_id']} at turn {session['turn']}.")
            _print_banner(player, data, session)

            # Show recent conversation context.
            ctx = get_conversation_context(session, max_turns=3)
            if ctx:
                print("\n  Previously...")
                for line in ctx.split('\n')[1:]:  # Skip header.
                    print(f"  {line}")
                print()

            # Parse multiplayer roster.
            roster = None
            game_id = getattr(args, "game_id_resolved", "")
            players_spec = getattr(args, "players", None)
            if players_spec:
                from multiplayer import parse_players
                roster = parse_players(players_spec)

            _game_loop(data, session, game_dir, sim_state, sim_rng, llm_config, system_msg,
                       roster=roster, game_id=game_id)
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid selection.")


def _game_loop(data: dict, session: dict, game_dir: str,
               sim_state: dict | None = None, sim_rng=None,
               llm_config: dict | None = None, system_msg: str = "",
               roster: list | None = None, game_id: str = ""):
    """The core game loop. Supports multiplayer with remote players."""
    if sim_state is None:
        sim_state = {}
    if llm_config is None:
        llm_config = {"available": False}

    # Multiplayer support.
    from multiplayer import (
        get_current_player, write_context, wait_for_action,
        append_adventure_log, clear_live_dir,
    )
    multiplayer = roster and len(roster) > 0
    if multiplayer and game_id:
        clear_live_dir(game_id)
        print(f"\n  Multiplayer: {', '.join(p['name'] + (' (remote)' if p['type'] == 'remote' else '') for p in roster)}")
        print()

    # Track last narrative for context files.
    last_narrative = ""

    while True:
        # Determine whose turn it is.
        current = None
        if multiplayer:
            current = get_current_player(roster, session.get("turn", 0))
            print(f"\n  --- {current['name']}'s turn ---")

        if current and current["type"] == "remote":
            # Remote player: write context, wait for action file.
            if game_id:
                ctx_path = write_context(game_id, current["name"], data, session, last_narrative)
                print(f"  Waiting for {current['name']}...")
                print(f"  (rpg turn {game_id} --player \"{current['name']}\" \"<action>\")")

                player_input = wait_for_action(game_id, current["name"])
                if player_input is None:
                    print(f"  {current['name']} timed out. Skipping.")
                    start_turn(session)
                    continue
                print(f"  {current['name']}: {player_input}")
            else:
                # Fallback: no game_id means no file protocol, skip.
                start_turn(session)
                continue
        else:
            # Human player: prompt at stdin.
            prompt_name = current["name"] if current else ""
            prompt_str = f"{prompt_name}> " if prompt_name else "> "
            try:
                player_input = input(prompt_str).strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGame ended.")
                if llm_config.get("total_calls"):
                    print(f"  {get_usage_summary(llm_config)}")
                break

            if not player_input:
                continue

            # Meta commands (human only).
            if player_input.lower() in ("quit", "exit", "q"):
                print("\nGame ended.")
                if llm_config.get("total_calls"):
                    print(f"  {get_usage_summary(llm_config)}")
                break

            if player_input.lower() == "save":
                _do_save(session, data, game_dir, sim_state)
                continue

            if player_input.lower() == "status":
                _show_status(data, session)
                continue

            if player_input.lower() in ("help", "?"):
                _show_help()
                continue

            if player_input.lower() == "history":
                ctx = get_conversation_context(session, max_turns=10)
                print(ctx if ctx else "  No conversation history yet.")
                print()
                continue

            if player_input.lower() == "inventory":
                _show_inventory(data)
                continue

            if player_input.lower() == "map":
                from map_renderer import render_ascii_map
                player = get_player(data)
                print()
                print(render_ascii_map(data, player_location=player.get("location", "")))
                print()
                continue

            if player_input.lower() == "quests":
                _show_quests(data)
                continue

        # --- Process game action ---
        player_name = current["name"] if current else "Player"
        narrative = _process_turn(player_input, data, session, game_dir,
                      sim_state, sim_rng, llm_config, system_msg)

        # Update last narrative and append to adventure log.
        if narrative:
            last_narrative = narrative
        if multiplayer and game_id and narrative:
            append_adventure_log(game_id, session.get("turn", 0),
                                player_name, player_input, narrative)


def _process_turn(player_input: str, data: dict, session: dict, game_dir: str,
                   sim_state: dict | None = None, sim_rng=None,
                   llm_config: dict | None = None, system_msg: str = ""):
    """Process a single player turn through the full pipeline.

    New flow: LLM narrates FIRST from raw player input, then the action
    resolver runs silently in the background to update state. The player
    never sees validation errors or mechanical parse failures.

    Returns the narrative text (for multiplayer adventure log).
    """
    import logging
    t0 = time.time()
    if llm_config is None:
        llm_config = {"available": False}

    # 1. Start the turn.
    turn = start_turn(session)

    player = get_player(data)
    location_id = player.get("location", "")

    # 2. Advance simulation (NPC schedules, faction dynamics, world events).
    sim_events_text = ""
    if sim_state:
        import random as _random
        sim_result = advance_simulation(
            data, turn,
            schedules=sim_state.get("schedules") or {},
            relationships=sim_state.get("relationships") or [],
            faction_territories=sim_state.get("faction_territories") or {},
            faction_relations=sim_state.get("faction_relations") or [],
            rng=sim_rng or _random.Random(),
        )
        sim_events_text = format_simulation_events(sim_result, location_id)
        if sim_events_text:
            print(f"\n  {sim_events_text.replace(chr(10), chr(10) + '  ')}")

    # 3. Build scene context with raw player input — no classification needed yet.
    #    We use a neutral "exploration" type as the base; the LLM has full context
    #    to decide what actually happens in the scene.
    context = resolve_scene_context(data, scene_type="exploration", session=session)
    if sim_events_text:
        context["simulation_events"] = sim_events_text

    # 4. Build narrative prompt with raw player input.
    prompt = build_narrative_prompt(context, action=player_input)

    # 5. LLM narrates FIRST (or show minimal fallback). Display narrative NOW.
    narrative_text = ""
    if llm_config.get("available"):
        fallback = location_id and get_location(data, location_id) or {}
        fallback_desc = fallback.get("description", f"You attempt: {player_input}") if fallback else f"You attempt: {player_input}"
        response = generate_narrative(llm_config, prompt, system_msg, fallback_desc)
        narrative_text = response.get("text", fallback_desc)
        print(f"\n{narrative_text}\n")
        if response.get("source") == "llm":
            print(f"    [{response.get('input_tokens', 0)} in / {response.get('output_tokens', 0)} out tokens]")
    else:
        # No-LLM fallback: show a simple, clean message — not a raw prompt dump.
        narrative_text = f"You attempt: {player_input}"
        print(f"\n  {narrative_text}\n")

    # 6-9. Classify, validate, resolve, apply state — ALL SILENT.
    #      Failures are logged but never shown to the player.
    action = {"action_type": "unknown", "raw": player_input}
    outcome = {"result": "unknown", "description": narrative_text, "consequences": []}
    consequence_log = []
    trigger_log = []
    fired = {"encounters": [], "quest_triggers": []}
    validated = None

    try:
        # 6. Classify the action (state-aware).
        action = classify_action(player_input, data)

        # 7. Validate against current state (silent — no error display).
        validated = validate_action(action, data)
        if not validated["valid"]:
            logging.debug(f"[turn {turn}] Validation blocked: {validated.get('reason', '')}")
            # Validation failed: state won't be updated this turn, but narrative already shown.
            validated = None

        if validated:
            # 8. Resolve outcome.
            outcome = resolve_outcome(validated, data)

            # 9. Apply consequences to game state.
            if outcome.get("consequences"):
                consequence_log = apply_consequences(outcome["consequences"], data, session=session)

            # 9b. Faction propagation.
            for c in outcome.get("consequences", []):
                if c.get("type") == "faction_reputation" and sim_state:
                    relationships = sim_state.get("relationships", [])
                    propagate_faction_action(data, relationships, c.get("faction_id", ""), c.get("delta", 0))

            # 9c. Evaluate triggers (encounters, quest advancement).
            fired = evaluate_all(data, action, session)
            trigger_log = apply_all_triggers(fired, data, session)

            # 9d. Check for combat encounters.
            for enc in fired.get("encounters", []):
                if enc.get("type") == "combat" and enc.get("enemies"):
                    combat_result = _run_combat(enc, data, session, llm_config, system_msg)
                    if combat_result:
                        combat_consequences = get_combat_consequences(combat_result, enc)
                        combat_log = apply_consequences(combat_consequences, data, session=session)
                        consequence_log.extend(combat_log)
                        trigger_log.append(f"Combat result: {combat_result['status']}")

    except Exception as exc:
        logging.warning(f"[turn {turn}] Silent action resolution failed: {exc}")

    # 10. Track the scene (use classified action type if available, else exploration).
    scene_type = _determine_scene_type(action, fired)
    set_active_scene(session, scene_type, {
        "location": player.get("location", location_id),
        "action_type": action.get("action_type", ""),
    })

    # 11. Show mechanical debug info AFTER narrative.
    elapsed = time.time() - t0
    _display_turn_result(action, outcome, consequence_log, trigger_log, elapsed, len(prompt))

    # 12. Record the turn with narrative.
    record_turn(session, {
        "player_input": player_input,
        "action": action,
        "outcome": outcome,
        "narrative": narrative_text,
        "location": player.get("location", location_id),
        "prompt_size": len(prompt),
        "triggered": {
            "encounters": [e.get("id") for e in fired.get("encounters", [])],
            "quests": [qt["quest"].get("id") for qt in fired.get("quest_triggers", [])],
        },
    })

    # 13. Auto-save every 10 turns.
    if session["turn"] % 10 == 0:
        save_session(session)

    return narrative_text


def _display_turn_result(action, outcome, consequence_log, trigger_log,
                         elapsed, prompt_size):
    """Display the mechanical results of a turn."""
    action_type = action.get("action_type", "?")
    target = action.get("target", "")
    topic = action.get("topic", "")
    result = outcome.get("result", "?")

    # Action summary.
    parts = [f"  [{action_type}]"]
    if target:
        parts.append(target)
    if topic:
        parts.append(f"(about: {topic})")
    parts.append(f"-> {result}")
    print("\n" + " ".join(parts))

    # Consequences.
    for entry in consequence_log:
        print(f"    * {entry}")

    # Triggered events.
    for entry in trigger_log:
        print(f"    ! {entry}")

    # Performance.
    print(f"    [{elapsed:.2f}s, prompt: {prompt_size} chars]")


def _build_triggered_events(fired: dict, data: dict) -> list[dict]:
    """Build triggered event descriptions for the narrative prompt."""
    events = []

    for encounter in fired.get("encounters", []):
        event = {
            "type": "encounter",
            "id": encounter.get("id", ""),
            "name": encounter.get("name", ""),
            "description": encounter.get("description", ""),
            "tone_direction": encounter.get("tone_direction", ""),
            "enemies": encounter.get("enemies", []),
        }
        events.append(event)

    for qt in fired.get("quest_triggers", []):
        quest = qt["quest"]
        stage_idx = qt["stage_idx"]
        stages = quest.get("stages", [])
        current_stage = stages[stage_idx] if stage_idx < len(stages) else {}

        if quest.get("status") == "inactive":
            events.append({
                "type": "quest_activated",
                "id": quest.get("id", ""),
                "name": quest.get("name", ""),
                "objective": current_stage.get("objective", ""),
            })
        else:
            # Get the NEW stage (one after current).
            next_idx = stage_idx + 1
            next_stage = stages[next_idx] if next_idx < len(stages) else {}
            events.append({
                "type": "quest_advanced",
                "id": quest.get("id", ""),
                "name": quest.get("name", ""),
                "objective": next_stage.get("objective", "Quest completed."),
            })

    return events


def _determine_scene_type(action: dict, fired: dict) -> str:
    """Determine the scene type based on action and triggered events."""
    # If a combat encounter fired, it's combat.
    for enc in fired.get("encounters", []):
        if enc.get("type") == "combat":
            return "combat"

    # If a discovery encounter fired, it's discovery.
    for enc in fired.get("encounters", []):
        if enc.get("type") == "discovery":
            return "discovery"

    # Otherwise, derive from action type.
    action_type = action.get("action_type", "")
    type_map = {
        "talk": "dialogue",
        "attack": "combat",
        "look": "discovery",
        "rest": "rest",
    }
    return type_map.get(action_type, "exploration")


def _narrate_opening(data: dict, session: dict,
                     llm_config: dict | None = None, system_msg: str = ""):
    """Generate and display the opening scene."""
    if llm_config is None:
        llm_config = {"available": False}

    player = get_player(data)
    location_id = player.get("location", "")
    location = get_location(data, location_id)

    context = resolve_scene_context(data, scene_type="exploration", session=session)
    prompt = build_narrative_prompt(context)

    # Try LLM narration first.
    if llm_config.get("available"):
        fallback = location.get("description", "").strip() if location else ""
        response = generate_narrative(llm_config, prompt, system_msg, fallback)
        if response.get("source") == "llm":
            print(f"\n{response['text']}\n")
            return

    # Fallback: show location as clean prose narration — no raw prompt, no tags.
    if location:
        loc_name = location.get("name", "")
        loc_desc = location.get("description", "").strip()

        if loc_name:
            print(f"\n{loc_name}")
        if loc_desc:
            print(f"\n{loc_desc}")

        # Sensory details as flowing prose paragraphs — no [sight]/[sound] labels.
        sensory = location.get("sensory", {})
        if sensory:
            print()
            for detail in sensory.values():
                if detail and detail.strip():
                    print(detail.strip())

        # NPC activities as natural sentences.
        npcs = get_npcs_at_location(data, location_id)
        if npcs:
            print()
            for npc in npcs:
                activity = npc.get("current_activity", "")
                npc_name = npc.get("name", "Someone")
                if activity:
                    print(f"{npc_name} {activity}")
                else:
                    role = npc.get("role", "")
                    print(f"{npc_name} is here{f', {role}' if role else ''}.")

        # Atmosphere from encounter YAML if available.
        encounters = data.get("encounters", [])
        for enc in encounters:
            if enc.get("location") == location_id and enc.get("atmosphere"):
                print(f"\n{enc['atmosphere'].strip()}")
                break

    print()


def _run_combat(encounter: dict, data: dict, session: dict,
                llm_config: dict | None = None, system_msg: str = "") -> dict:
    """Run a combat sub-loop. Returns the final combat state."""
    import random as _random

    if llm_config is None:
        llm_config = {"available": False}

    player = get_player(data)
    player_stats = player.get("stats", {})

    # Get equipped weapon bonus.
    from game_state import get_equipped_item
    weapon = get_equipped_item(data, "weapon")
    base_damage = 2
    if weapon:
        base_damage = weapon.get("properties", {}).get("damage", 3)
    player_stats["damage"] = base_damage

    enemies = encounter.get("enemies", [])
    rng = _random.Random()
    combat = start_combat(player_stats, enemies, rng)

    print(f"\n  === COMBAT: {encounter.get('name', 'Battle')} ===")
    if encounter.get("description"):
        print(f"  {encounter['description'].strip()}")
    print()

    while combat["status"] == "active":
        print(get_combat_summary(combat))
        try:
            action = input("Combat> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            combat["status"] = "fled"
            print("  You flee from combat.")
            break

        if not action:
            action = "attack"

        if action not in ("attack", "defend", "flee") and not action.startswith("use "):
            print("  Actions: attack, defend, flee, use <item>")
            continue

        result = resolve_combat_round(combat, action, rng)

        # Display round events.
        for event_text in result.get("events", []):
            print(f"    {event_text}")

        # Optionally narrate with LLM.
        if llm_config.get("available") and result.get("events"):
            combat_ctx = build_combat_prompt_context(combat)
            context = resolve_scene_context(data, scene_type="combat", session=session)
            context["combat_state"] = combat_ctx
            combat_prompt = build_narrative_prompt(context, action=action)
            response = generate_narrative(llm_config, combat_prompt, system_msg, "")
            if response.get("source") == "llm" and response.get("text"):
                print(f"\n{response['text']}\n")

        print()

    # Display result.
    if combat["status"] == "victory":
        print("  === VICTORY ===")
        # Sync health/stamina back.
        from game_state import update_player_stat, get_player_max_stat
        current_health = player_stats.get("health", 10)
        combat_health = combat["player"]["health"]
        if combat_health < current_health:
            update_player_stat(data, "health", combat_health - current_health, "combat damage")
        current_stamina = player_stats.get("stamina", 8)
        combat_stamina = combat["player"]["stamina"]
        if combat_stamina < current_stamina:
            update_player_stat(data, "stamina", combat_stamina - current_stamina, "combat exertion")
    elif combat["status"] == "defeat":
        print("  === DEFEAT ===")
        from game_state import update_player_stat, add_player_condition
        update_player_stat(data, "health", -player_stats.get("health", 10), "combat defeat")
        add_player_condition(data, "incapacitated")
    elif combat["status"] == "fled":
        print("  You escaped.")

    print()
    return combat


def _print_prompt_summary(prompt: str):
    """Print a summary of the narrative prompt sections."""
    sections = prompt.split("\n\n")
    for section in sections[:3]:  # Show first 3 sections.
        lines = section.strip().split("\n")
        if lines:
            # Print section header.
            for line in lines[:2]:
                if line.strip("=").strip():
                    print(f"    {line.strip('=').strip()}")
                    break


# ---------------------------------------------------------------------------
# Meta commands
# ---------------------------------------------------------------------------

def _do_save(session: dict, data: dict, game_dir: str, sim_state: dict | None = None):
    """Save the current game."""
    session_path = save_session(session)
    snapshot_path = create_snapshot(session, data)
    save_full_state(game_dir, data)
    if sim_state:
        save_simulation_state(
            game_dir,
            sim_state.get("schedules", {}),
            sim_state.get("relationships", []),
            sim_state.get("faction_territories", {}),
            sim_state.get("faction_relations", []),
        )
    print(f"\n  Saved. (session: {session_path})")
    print(f"  Snapshot: {snapshot_path}\n")


def _show_status(data: dict, session: dict):
    """Show current game status."""
    summary = get_world_summary(data)
    player = summary["player"]

    print(f"\n  Turn {session.get('turn', 0)}")
    print(f"  {player['name']} at {player['location']}")
    print(f"  Health: {player['health']}  Items: {player['inventory_count']}  Knowledge: {player['knowledge_count']}")

    # Active quests.
    active = get_active_quests(data)
    if active:
        print(f"\n  Active quests:")
        for q in active:
            stage = get_quest_stage(q)
            print(f"    - {q.get('name', '?')}: {stage.get('objective', '?')}")

    # Session stats.
    stats = session.get("stats", {})
    if stats.get("total_actions"):
        print(f"\n  Actions: {stats['total_actions']}  Locations: {len(stats.get('locations_visited', []))}")

    print()


def _show_help():
    """Show available commands."""
    print("""
  Commands:
    <action>    Describe what you want to do (e.g., "talk to maren about thornwood")
    save        Save your game
    status      Show game status
    inventory   Check your pack
    quests      Show active quests
    map         Show ASCII map
    history     Review recent conversation
    help / ?    Show this help
    quit        End the game
""")


def _show_inventory(data: dict):
    """Show player inventory."""
    player = get_player(data)
    inventory = player.get("inventory", [])
    if not inventory:
        print("\n  You're carrying nothing.\n")
        return

    print(f"\n  Inventory ({len(inventory)} items):")
    for item in inventory:
        name = item.get("name", item.get("id", "?"))
        desc = item.get("description", "")
        print(f"    - {name}")
        if desc:
            print(f"      {desc.strip()[:80]}")
    print()


def _show_quests(data: dict):
    """Show quest information."""
    quests = data.get("quests", [])

    active = [q for q in quests if q.get("status") == "active"]
    completed = [q for q in quests if q.get("status") == "completed"]

    if not active and not completed:
        print("\n  No quests yet. Explore and talk to people.\n")
        return

    if active:
        print(f"\n  Active quests:")
        for q in active:
            stage = get_quest_stage(q)
            print(f"    [{q.get('id', '?')}] {q.get('name', '?')}")
            print(f"      Objective: {stage.get('objective', '?')}")
            for hint in stage.get("hints", [])[:2]:
                print(f"      Hint: {hint}")

    if completed:
        print(f"\n  Completed:")
        for q in completed:
            print(f"    [{q.get('id', '?')}] {q.get('name', '?')}")

    print()


def _print_banner(player: dict, data: dict, session: dict):
    """Print the game banner."""
    location_id = player.get("location", "")
    location = get_location(data, location_id)
    active_quests = get_active_quests(data)

    print("=" * 60)
    print("  THE GAME MASTER")
    print("=" * 60)
    print(f"\n  Player: {player.get('name', 'Unknown')}")
    print(f"  Location: {location.get('name', location_id) if location else 'Unknown'}")
    print(f"  Turn: {session.get('turn', 0)}")
    if active_quests:
        print(f"  Active quests: {len(active_quests)}")
    print(f"\n  Type 'help' for commands, 'quit' to exit.\n")
    print("-" * 60)


# ---------------------------------------------------------------------------
# Non-interactive commands
# ---------------------------------------------------------------------------

def run_test(args):
    """Test a single action through the full pipeline."""
    game_dir = args.game_dir
    player_input = args.action
    data = load_game_data(game_dir)

    # Create a mock session for trigger evaluation.
    mock_session = {"turn": 5, "flags": {}, "conversation": [], "history": []}

    print(f"Input: {player_input}\n")

    # 1. Classify.
    action = classify_action(player_input, data)
    print(f"Action: {action['action_type']} (confidence: {action['confidence']:.1f})")
    print(f"Target: {action['target']} (id={action['target_id']}, type={action['target_type']})")
    if action['topic']:
        print(f"Topic: {action['topic']}")
    if action['direction']:
        print(f"Direction: {action['direction']}")
    if action['social_disposition'] != 'neutral':
        print(f"Disposition: {action['social_disposition']}")
    if action['secondary_actions']:
        print(f"Secondary actions:")
        for s in action['secondary_actions']:
            print(f"  + {s['action_type']}: {s['raw']}")
    print()

    # 2. Validate.
    validated = validate_action(action, data)
    print(f"Valid: {validated['valid']}")
    if not validated["valid"]:
        print(f"Reason: {validated['reason']}")
        return
    print(f"Resolved: {validated['resolved_target']} ({validated['resolved_target_name']})")
    if validated['resolved_topic']:
        print(f"Topic: {validated['resolved_topic']}")
    print()

    # 3. Resolve outcome.
    outcome = resolve_outcome(validated, data)
    print(f"Result: {outcome['result']}")
    print(f"Description: {outcome['description']}")
    if outcome["narrative_hints"]:
        print("Narrative hints:")
        for h in outcome["narrative_hints"]:
            print(f"  - {h}")
    print()

    # 4. Check triggers.
    fired = evaluate_all(data, action, mock_session)
    if fired["encounters"] or fired["quest_triggers"]:
        print("Triggers fired:")
        for enc in fired["encounters"]:
            print(f"  ! Encounter: {enc.get('name', '?')}")
        for qt in fired["quest_triggers"]:
            print(f"  ! Quest: {qt['quest'].get('name', '?')} (stage {qt['stage_idx']})")
        print()

    # 5. Generate scene prompt.
    scene_type = _determine_scene_type(action, fired)
    context = resolve_scene_context(data, scene_type=scene_type, session=mock_session)
    triggered_events = _build_triggered_events(fired, data)
    context["triggered_events"] = triggered_events
    prompt = build_narrative_prompt(context, action=player_input, outcome=outcome)
    print(f"Scene type: {scene_type}")
    print(f"Prompt: {len(prompt)} characters")

    if args.show_prompt:
        print("\n" + "=" * 60)
        print(prompt)
        print("=" * 60)


def run_scene(args):
    """Generate a scene prompt from current game state."""
    game_dir = args.game_dir
    scene_type = args.type or "exploration"
    data = load_game_data(game_dir)

    context = resolve_scene_context(data, scene_type=scene_type)
    prompt = build_narrative_prompt(context)
    print(prompt)


def run_validate(args):
    """Validate narrative text against a world setting."""
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    text = filepath.read_text()
    preset = load_preset(args.preset)
    findings = validate_text(text, preset)
    print(format_validation_report(findings, preset))


def run_npc(args):
    """Show an NPC voice profile."""
    archetype = args.archetype

    if archetype == "list":
        print("Available voice archetypes:")
        for name in VOICE_ARCHETYPES:
            print(f"  - {name}")
        return

    if archetype not in VOICE_ARCHETYPES:
        print(f"Unknown archetype: {archetype}")
        print(f"Available: {', '.join(VOICE_ARCHETYPES.keys())}")
        return

    npc = {"name": archetype.capitalize(), "voice_profile": VOICE_ARCHETYPES[archetype]}
    print(build_voice_instructions(npc))


def run_status(args):
    """Show full game state summary."""
    game_dir = args.game_dir
    data = load_game_data(game_dir)

    print("=" * 60)
    print("  GAME STATE SUMMARY")
    print("=" * 60)

    summary = get_world_summary(data)

    print("\nPlayer:")
    for k, v in summary["player"].items():
        print(f"  {k}: {v}")

    print("\nLocations:")
    for loc_id, loc_info in summary["locations"].items():
        print(f"  {loc_id:25s} state={loc_info['state']:10s} items={loc_info['items']}")

    print("\nNPCs:")
    for npc_id, npc_info in summary["npcs"].items():
        print(f"  {npc_id:15s} at {npc_info['location']:20s} disposition={npc_info['disposition']}")

    print("\nQuests:")
    for q_id, q_info in summary["quests"].items():
        print(f"  {q_id:25s} status={q_info['status']:10s} stage={q_info['stage']}")

    print("\nFactions:")
    for f_id, f_info in summary["factions"].items():
        print(f"  {f_id:25s} reputation={f_info['reputation']:10s} value={f_info['value']}")

    # Saves.
    saves = list_saves(game_dir)
    if saves:
        print(f"\nSaves ({len(saves)}):")
        for s in saves[:5]:
            print(f"  [{s['session_id']}] Turn {s['turn']} — {s['last_played']}")

    # Modules.
    modules = [
        "game_state.py", "scene_engine.py", "action_resolver.py",
        "npc_voice.py", "world_validator.py", "narrative_analyzer.py",
        "session.py", "trigger_engine.py", "game_master.py",
    ]
    print("\nModules:")
    for filename in modules:
        path = ENGINE_DIR / filename
        status = "ok" if path.exists() else "MISSING"
        print(f"  [{status:7s}] {filename}")

    print()


def run_analyze(args):
    """Analyze narrative quality of a text file."""
    filepath = Path(args.file)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    text = filepath.read_text()
    profile = analyze_narrative(text, name=filepath.stem)
    score = score_narrative(profile)
    print(format_quality_report(profile, score))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="The Game Master — Text-based RPG engine orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command")

    # play
    play_p = subparsers.add_parser("play", help="Start interactive game")
    play_p.add_argument("game_dir", help="Path to game data directory")
    play_p.add_argument("--no-llm", action="store_true", help="Prompt-display-only mode (no API calls)")

    # resume
    resume_p = subparsers.add_parser("resume", help="Resume a saved session")
    resume_p.add_argument("game_dir", help="Path to game data directory")
    resume_p.add_argument("--no-llm", action="store_true", help="Prompt-display-only mode (no API calls)")

    # test
    test_p = subparsers.add_parser("test", help="Test a single action")
    test_p.add_argument("game_dir", help="Path to game data directory")
    test_p.add_argument("action", help="Player action text")
    test_p.add_argument("--show-prompt", action="store_true", help="Show full generated prompt")

    # scene
    scene_p = subparsers.add_parser("scene", help="Generate scene prompt")
    scene_p.add_argument("game_dir", help="Path to game data directory")
    scene_p.add_argument("--type", "-t", default="exploration",
                         choices=["exploration", "dialogue", "combat", "discovery", "rest"])

    # validate
    val_p = subparsers.add_parser("validate", help="Validate narrative text")
    val_p.add_argument("file", help="Text file to validate")
    val_p.add_argument("--preset", "-p", default="dark-fantasy", help="World setting preset")

    # npc
    npc_p = subparsers.add_parser("npc", help="Show NPC voice profile")
    npc_p.add_argument("archetype", help="Voice archetype name (or 'list')")

    # status
    stat_p = subparsers.add_parser("status", help="Show game state summary")
    stat_p.add_argument("game_dir", help="Path to game data directory")

    # analyze
    ana_p = subparsers.add_parser("analyze", help="Analyze narrative quality")
    ana_p.add_argument("file", help="Text file to analyze")

    args = parser.parse_args()

    commands = {
        "play": run_play,
        "resume": run_resume,
        "test": run_test,
        "scene": run_scene,
        "validate": run_validate,
        "npc": run_npc,
        "status": run_status,
        "analyze": run_analyze,
    }

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
