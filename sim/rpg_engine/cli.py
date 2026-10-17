#!/usr/bin/env python3
"""
RPG Engine CLI — Multi-game management, world generation, and multiplayer.

Commands:
  rpg new <genre> [--name NAME] [--seed SEED]   Generate a new world
  rpg list                                       List all games
  rpg play <game_id> [-p PLAYERS]                Start or resume a game
  rpg map <game_id>                              Show ASCII map
  rpg status <game_id>                           World state summary
  rpg turn <game_id> --player NAME "action"      Submit a remote player's turn
  rpg context <game_id> --player NAME            Show context for a remote player
  rpg watch <game_id>                            Tail the adventure log
  rpg delete <game_id> [--force]                 Remove a game
  rpg genres                                     List available genres

Multiplayer:
  rpg play ithilien --players "Lisa:human,Boromir:remote"

  Then from a Claude Code session:
    rpg context ithilien --player Boromir    # read what's happening (~300 words)
    rpg turn ithilien --player Boromir "I draw my sword"  # submit action
"""

import argparse
import sys
from pathlib import Path

# Add engine dir to path.
sys.path.insert(0, str(Path(__file__).parent))

from game_registry import GameRegistry
from game_state import load_game_data, get_player, get_world_summary
from map_renderer import render_ascii_map


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_new(args):
    """Generate a new world."""
    from world_generator import generate_world
    from genre_templates import GENRES

    genre = args.genre
    if genre not in GENRES:
        print(f"Unknown genre: {genre}")
        print(f"Available: {', '.join(GENRES.keys())}")
        sys.exit(1)

    name = args.name or GENRES[genre].get("default_name", f"New {genre} world")
    seed = args.seed

    registry = GameRegistry()

    # Create game directory.
    entry = registry.register(name, genre)
    game_dir = entry["game_dir"]

    print(f"\n  Generating: {name} ({genre})")
    print(f"  ID: {entry['id']}")
    print(f"  Directory: {game_dir}")
    print()

    # Generate the world.
    result = generate_world(genre, name=name, seed=seed, output_dir=game_dir)

    print(f"  Locations: {result['location_count']}")
    print(f"  NPCs: {result['npc_count']}")
    print(f"  Quests: {result['quest_count']}")
    print(f"  Items: {result['item_count']}")
    print(f"  Factions: {result['faction_count']}")
    print(f"  Encounters: {result['encounter_count']}")
    print()
    print(f"  Run: python3 cli.py play {entry['id']}")
    print()

    # Show the map.
    data = load_game_data(game_dir)
    player = get_player(data)
    print(render_ascii_map(data, player_location=player.get("location", "")))


def cmd_list(args):
    """List all registered games."""
    registry = GameRegistry()
    games = registry.list_all()

    if not games:
        print("\n  No games. Create one: python3 cli.py new <genre>")
        from genre_templates import GENRES
        print(f"  Genres: {', '.join(GENRES.keys())}")
        print()
        return

    print()
    print(f"  {'ID':<30s} {'GENRE':<20s} {'TURN':>5s}  {'LAST PLAYED'}")
    print(f"  {'-'*30} {'-'*20} {'-'*5}  {'-'*19}")
    for g in games:
        print(f"  {g['id']:<30s} {g['genre']:<20s} {g.get('turn', 0):>5d}  {g.get('last_played', '?')}")
    print()


def cmd_play(args):
    """Start or resume a game."""
    registry = GameRegistry()
    game = registry.find(args.game_id)

    if not game:
        matches = registry.find_all(args.game_id)
        if matches:
            print(f"\n  Ambiguous. Did you mean:")
            for m in matches:
                print(f"    {m['id']}  ({m['genre']})")
        else:
            print(f"\n  Game not found: {args.game_id}")
            print(f"  Run: python3 cli.py list")
        print()
        return

    game_dir = game["game_dir"]
    if not Path(game_dir).exists():
        print(f"\n  Game directory missing: {game_dir}")
        print(f"  The game files may have been deleted.\n")
        return

    # Import game_master functions.
    from game_master import run_play as _run_play, run_resume as _run_resume
    from session import list_saves

    # Update last played.
    registry.update(game["id"], last_played=__import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Check for existing saves.
    saves = list_saves(game_dir)

    # Build a fake args namespace for game_master.
    class GMArgs:
        pass
    gm_args = GMArgs()
    gm_args.game_dir = game_dir
    gm_args.game_id_resolved = game["id"]
    gm_args.players = getattr(args, "players", None)

    if saves:
        _run_resume(gm_args)
    else:
        _run_play(gm_args)

    # Update turn count after play.
    data = load_game_data(game_dir)
    player = get_player(data)
    saves_after = list_saves(game_dir)
    if saves_after:
        latest = saves_after[0]
        registry.update(game["id"],
                        turn=latest.get("turn", 0),
                        last_played=__import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def cmd_map(args):
    """Show ASCII map for a game."""
    registry = GameRegistry()
    game = registry.find(args.game_id)

    if not game:
        print(f"\n  Game not found: {args.game_id}\n")
        return

    data = load_game_data(game["game_dir"])
    player = get_player(data)
    player_loc = player.get("location", "")

    print()
    print(f"  {game['name']} ({game['genre']})")
    print()
    print(render_ascii_map(data, player_location=player_loc))
    print()


def cmd_status(args):
    """Show world state summary."""
    registry = GameRegistry()
    game = registry.find(args.game_id)

    if not game:
        print(f"\n  Game not found: {args.game_id}\n")
        return

    data = load_game_data(game["game_dir"])
    summary = get_world_summary(data)

    print()
    print(f"  {game['name']} ({game['genre']})")
    print(f"  ID: {game['id']}")
    print(f"  Created: {game.get('created', '?')}")
    print()

    # Player.
    p = summary["player"]
    print(f"  Player: {p['name']} at {p['location']}")
    print(f"  Health: {p['health']}  Items: {p['inventory_count']}  Knowledge: {p['knowledge_count']}")
    print()

    # Locations.
    print(f"  Locations ({len(summary['locations'])}):")
    for loc_id, info in summary["locations"].items():
        state_tag = f" [{info['state']}]" if info['state'] != 'normal' else ""
        print(f"    {info['name']}{state_tag}")
    print()

    # NPCs.
    print(f"  NPCs ({len(summary['npcs'])}):")
    for npc_id, info in summary["npcs"].items():
        print(f"    {info['name']:20s} at {info['location']:20s} ({info['disposition']})")
    print()

    # Quests.
    print(f"  Quests ({len(summary['quests'])}):")
    for q_id, info in summary["quests"].items():
        print(f"    {info['name']:30s} {info['status']:10s} stage {info['stage']}")
    print()

    # Factions.
    if summary.get("factions"):
        print(f"  Factions ({len(summary['factions'])}):")
        for f_id, info in summary["factions"].items():
            print(f"    {info['name']:25s} reputation: {info['reputation']}")
        print()


def cmd_delete(args):
    """Delete a game."""
    registry = GameRegistry()
    game = registry.find(args.game_id)

    if not game:
        print(f"\n  Game not found: {args.game_id}\n")
        return

    if not args.force:
        print(f"\n  Delete '{game['name']}' ({game['id']})?")
        print(f"  This will remove the game directory: {game['game_dir']}")
        try:
            confirm = input("  Type 'yes' to confirm: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.\n")
            return
        if confirm != "yes":
            print("  Cancelled.\n")
            return

    registry.delete(game["id"], delete_files=True)
    print(f"\n  Deleted: {game['name']} ({game['id']})\n")


def cmd_turn(args):
    """Submit a turn for a remote player."""
    from multiplayer import write_action

    registry = GameRegistry()
    game = registry.find(args.game_id)

    if not game:
        print(f"\n  Game not found: {args.game_id}\n")
        return

    player_name = args.player
    action = args.action

    write_action(game["id"], player_name, action)
    print(f"\n  {player_name}: {action}")
    print(f"  (action submitted)\n")


def cmd_context(args):
    """Show the current context for a remote player."""
    from multiplayer import read_context

    registry = GameRegistry()
    game = registry.find(args.game_id)

    if not game:
        print(f"\n  Game not found: {args.game_id}\n")
        return

    text = read_context(game["id"], args.player)
    if text:
        print(text)
    else:
        print(f"\n  No context available for {args.player}.")
        print(f"  (the game must be running with --players for context to appear)\n")


def cmd_watch(args):
    """Tail the adventure log for a game."""
    import subprocess

    registry = GameRegistry()
    game = registry.find(args.game_id)

    if not game:
        print(f"\n  Game not found: {args.game_id}\n")
        return

    log_path = Path.home() / ".rpg_engine" / "live" / game["id"] / "adventure.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    print(f"  Watching: {log_path}")
    print(f"  (Ctrl+C to stop)\n")

    try:
        subprocess.run(["tail", "-f", str(log_path)])
    except KeyboardInterrupt:
        print("\n  Stopped watching.")


def cmd_genres(args):
    """List available genres."""
    from genre_templates import GENRES

    print("\n  Available genres:\n")
    for genre_id, template in GENRES.items():
        name = template.get("display_name", genre_id)
        desc = template.get("description", "")
        topology = template.get("topology", "?")
        locs = template.get("location_count", {})
        npcs = template.get("npc_count", {})
        print(f"  {genre_id:<22s} {name}")
        if desc:
            print(f"    {desc[:80]}")
        print(f"    Topology: {topology}  Locations: {locs.get('min', '?')}-{locs.get('max', '?')}  NPCs: {npcs.get('min', '?')}-{npcs.get('max', '?')}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="rpg",
        description="RPG Engine — Multi-game management and world generation",
    )
    subparsers = parser.add_subparsers(dest="command")

    # new
    new_p = subparsers.add_parser("new", help="Generate a new world")
    new_p.add_argument("genre", help="Genre (use 'rpg genres' to list)")
    new_p.add_argument("--name", "-n", help="World name")
    new_p.add_argument("--seed", "-s", type=int, help="RNG seed for reproducibility")

    # list
    subparsers.add_parser("list", help="List all games")

    # play
    play_p = subparsers.add_parser("play", help="Start or resume a game")
    play_p.add_argument("game_id", help="Game ID (or prefix)")
    play_p.add_argument("--players", "-p", help="Player roster: 'Name:human,Name:remote,...'")

    # map
    map_p = subparsers.add_parser("map", help="Show ASCII map")
    map_p.add_argument("game_id", help="Game ID (or prefix)")
    map_p.add_argument("--full", action="store_true", help="Show full detail")

    # status
    stat_p = subparsers.add_parser("status", help="World state summary")
    stat_p.add_argument("game_id", help="Game ID (or prefix)")

    # delete
    del_p = subparsers.add_parser("delete", help="Remove a game")
    del_p.add_argument("game_id", help="Game ID (or prefix)")
    del_p.add_argument("--force", "-f", action="store_true", help="Skip confirmation")

    # turn (remote player action)
    turn_p = subparsers.add_parser("turn", help="Submit a turn for a remote player")
    turn_p.add_argument("game_id", help="Game ID (or prefix)")
    turn_p.add_argument("action", help="The action to take")
    turn_p.add_argument("--player", required=True, help="Player name")

    # context (read remote player context)
    ctx_p = subparsers.add_parser("context", help="Show context for a remote player")
    ctx_p.add_argument("game_id", help="Game ID (or prefix)")
    ctx_p.add_argument("--player", required=True, help="Player name")

    # watch (tail adventure log)
    watch_p = subparsers.add_parser("watch", help="Watch the adventure log")
    watch_p.add_argument("game_id", help="Game ID (or prefix)")

    # genres
    subparsers.add_parser("genres", help="List available genres")

    args = parser.parse_args()

    commands = {
        "new": cmd_new,
        "list": cmd_list,
        "play": cmd_play,
        "map": cmd_map,
        "status": cmd_status,
        "delete": cmd_delete,
        "turn": cmd_turn,
        "context": cmd_context,
        "watch": cmd_watch,
        "genres": cmd_genres,
    }

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
