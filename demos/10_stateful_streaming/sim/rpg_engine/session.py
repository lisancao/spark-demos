#!/usr/bin/env python3
"""
Session Manager — Turn tracking, conversation history, and session persistence.

Tracks the full state of a play session: turn counter, conversation history
(player inputs + narrative outputs), recent actions, and session metadata.
Persists to disk as YAML so sessions can be resumed.

Designed for procedural scaling: each session snapshot captures enough context
to reconstruct the narrative state without replaying the full history.
"""

import copy
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml


# ---------------------------------------------------------------------------
# Session data structure
# ---------------------------------------------------------------------------

def new_session(game_dir: str, player_name: str = "") -> dict[str, Any]:
    """Create a fresh session."""
    return {
        "session_id": _generate_id(),
        "game_dir": game_dir,
        "player_name": player_name,
        "created": _now(),
        "last_played": _now(),
        "turn": 0,
        "history": [],          # Full turn-by-turn log.
        "conversation": [],     # Recent narrative exchanges for LLM context.
        "active_scene": None,   # Current scene type/context.
        "flags": {},            # Arbitrary session flags (e.g. "visited_inn": True).
        "stats": {              # Session-level analytics.
            "total_actions": 0,
            "actions_by_type": {},
            "locations_visited": [],
            "npcs_spoken_to": [],
            "items_acquired": [],
            "quests_advanced": [],
            "combat_encounters": 0,
        },
    }


# ---------------------------------------------------------------------------
# Turn management
# ---------------------------------------------------------------------------

def start_turn(session: dict) -> int:
    """Increment the turn counter and return the new turn number."""
    session["turn"] += 1
    session["last_played"] = _now()
    return session["turn"]


def record_turn(session: dict, turn_data: dict) -> None:
    """Record a complete turn in session history.

    turn_data should include:
        turn: int
        player_input: str
        action: dict           # classified action
        outcome: dict          # resolved outcome
        narrative: str         # LLM-generated narrative text
        location: str          # location_id at time of action
        timestamp: str
    """
    entry = {
        "turn": session["turn"],
        "timestamp": _now(),
        **turn_data,
    }
    session["history"].append(entry)

    # Update conversation window (keep last N exchanges for LLM context).
    _update_conversation(session, entry)

    # Update session stats.
    _update_stats(session, entry)


def _update_conversation(session: dict, entry: dict, max_exchanges: int = 10) -> None:
    """Maintain a sliding window of recent narrative exchanges."""
    exchange = {
        "turn": entry.get("turn", 0),
        "player": entry.get("player_input", ""),
        "narrative": entry.get("narrative", ""),
        "action_type": entry.get("action", {}).get("action_type", ""),
        "location": entry.get("location", ""),
    }
    session["conversation"].append(exchange)

    # Trim to window size.
    if len(session["conversation"]) > max_exchanges:
        session["conversation"] = session["conversation"][-max_exchanges:]


def _update_stats(session: dict, entry: dict) -> None:
    """Update session analytics from a turn entry."""
    stats = session["stats"]
    stats["total_actions"] += 1

    action = entry.get("action", {})
    action_type = action.get("action_type", "unknown")
    stats["actions_by_type"][action_type] = stats["actions_by_type"].get(action_type, 0) + 1

    # Track unique locations visited.
    location = entry.get("location", "")
    if location and location not in stats["locations_visited"]:
        stats["locations_visited"].append(location)

    # Track NPCs spoken to.
    if action_type == "talk":
        target_id = action.get("target_id", "")
        if target_id and target_id not in stats["npcs_spoken_to"]:
            stats["npcs_spoken_to"].append(target_id)

    # Track items acquired.
    outcome = entry.get("outcome", {})
    for c in outcome.get("consequences", []):
        if c.get("type") == "add_item":
            item_id = c.get("item_id", "")
            if item_id and item_id not in stats["items_acquired"]:
                stats["items_acquired"].append(item_id)
        if c.get("type") == "advance_quest":
            quest_id = c.get("quest_id", "")
            if quest_id:
                stats["quests_advanced"].append(quest_id)
        if c.get("type") == "enter_combat":
            stats["combat_encounters"] += 1


# ---------------------------------------------------------------------------
# Conversation context (for LLM prompts)
# ---------------------------------------------------------------------------

def get_conversation_context(session: dict, max_turns: int = 5) -> str:
    """Build a conversation summary for LLM prompt injection.

    Returns a formatted string of recent player/narrative exchanges that
    gives the LLM continuity without dumping the full history.
    """
    recent = session.get("conversation", [])[-max_turns:]
    if not recent:
        return ""

    lines = ["RECENT CONVERSATION:"]
    for ex in recent:
        turn_num = ex.get("turn", "?")
        player_said = ex.get("player", "")
        narrative = ex.get("narrative", "")
        loc = ex.get("location", "")

        lines.append(f"\n[Turn {turn_num}] (at {loc})")
        if player_said:
            lines.append(f"  Player: {player_said}")
        if narrative:
            # Truncate long narratives for context.
            truncated = narrative[:500] + "..." if len(narrative) > 500 else narrative
            lines.append(f"  Narrator: {truncated}")

    return "\n".join(lines)


def get_action_summary(session: dict, last_n: int = 3) -> list[str]:
    """Get a brief summary of recent actions (for trigger evaluation)."""
    recent = session.get("history", [])[-last_n:]
    summaries = []
    for entry in recent:
        action = entry.get("action", {})
        outcome = entry.get("outcome", {})
        summary = (
            f"{action.get('action_type', '?')}"
            f" target={action.get('target', '')}"
            f" topic={action.get('topic', '')}"
            f" result={outcome.get('result', '?')}"
            f" at={entry.get('location', '?')}"
        )
        summaries.append(summary)
    return summaries


# ---------------------------------------------------------------------------
# Session flags
# ---------------------------------------------------------------------------

def set_flag(session: dict, flag: str, value: Any = True) -> None:
    """Set a session flag."""
    session["flags"][flag] = value


def get_flag(session: dict, flag: str, default: Any = None) -> Any:
    """Get a session flag."""
    return session["flags"].get(flag, default)


def has_flag(session: dict, flag: str) -> bool:
    """Check if a session flag is set and truthy."""
    return bool(session["flags"].get(flag))


# ---------------------------------------------------------------------------
# Scene tracking
# ---------------------------------------------------------------------------

def set_active_scene(session: dict, scene_type: str,
                     context: Optional[dict] = None) -> None:
    """Track the current active scene."""
    session["active_scene"] = {
        "type": scene_type,
        "started_turn": session["turn"],
        "context": context or {},
    }


def get_active_scene(session: dict) -> Optional[dict]:
    """Get the current active scene."""
    return session.get("active_scene")


def clear_active_scene(session: dict) -> None:
    """Clear the active scene (scene ended)."""
    session["active_scene"] = None


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_session(session: dict, save_dir: Optional[str] = None) -> str:
    """Save session to YAML. Returns the save file path."""
    if save_dir:
        out_dir = Path(save_dir)
    else:
        out_dir = Path(session.get("game_dir", ".")) / "saves"

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"session_{session['session_id']}.yaml"
    out_path = out_dir / filename

    # Deep copy to avoid mutating the live session.
    save_data = copy.deepcopy(session)
    save_data["saved_at"] = _now()

    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.dump(save_data, fh, default_flow_style=False,
                  allow_unicode=True, sort_keys=False)

    return str(out_path)


def load_session(filepath: str) -> dict[str, Any]:
    """Load a session from a YAML file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Session file not found: {filepath}")

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "session_id" not in data:
        raise ValueError(f"Invalid session file: {filepath}")

    return data


def list_saves(game_dir: str) -> list[dict]:
    """List available save files for a game directory."""
    save_dir = Path(game_dir) / "saves"
    if not save_dir.is_dir():
        return []

    saves = []
    for f in sorted(save_dir.glob("session_*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            saves.append({
                "file": str(f),
                "session_id": data.get("session_id", "?"),
                "player_name": data.get("player_name", "?"),
                "turn": data.get("turn", 0),
                "last_played": data.get("last_played", "?"),
                "saved_at": data.get("saved_at", "?"),
            })
        except Exception:
            continue

    return saves


def create_snapshot(session: dict, game_data: dict,
                    save_dir: Optional[str] = None) -> str:
    """Create a full snapshot: session + game state together.

    This captures everything needed to restore a game exactly as it was.
    """
    if save_dir:
        out_dir = Path(save_dir)
    else:
        out_dir = Path(session.get("game_dir", ".")) / "saves"

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"snapshot_t{session['turn']}_{session['session_id']}.yaml"
    out_path = out_dir / filename

    snapshot = {
        "snapshot_at": _now(),
        "turn": session["turn"],
        "session": copy.deepcopy(session),
        "game_state": copy.deepcopy(game_data),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        yaml.dump(snapshot, fh, default_flow_style=False,
                  allow_unicode=True, sort_keys=False)

    return str(out_path)


def load_snapshot(filepath: str) -> tuple[dict, dict]:
    """Load a snapshot. Returns (session, game_data)."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Snapshot not found: {filepath}")

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "session" not in data:
        raise ValueError(f"Invalid snapshot file: {filepath}")

    return data["session"], data["game_state"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _generate_id() -> str:
    """Generate a short session id."""
    import hashlib
    return hashlib.md5(_now().encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python session.py <game_dir> [list|new|load <file>]")
        sys.exit(1)

    game_dir = sys.argv[1]
    cmd = sys.argv[2] if len(sys.argv) > 2 else "new"

    if cmd == "list":
        saves = list_saves(game_dir)
        if not saves:
            print("No saves found.")
        else:
            for s in saves:
                print(f"  [{s['session_id']}] Turn {s['turn']} — {s['last_played']}")

    elif cmd == "new":
        session = new_session(game_dir, player_name="test player")
        print(f"New session: {session['session_id']}")
        print(f"Turn: {session['turn']}")

        # Simulate a turn.
        turn = start_turn(session)
        print(f"Started turn {turn}")
        record_turn(session, {
            "player_input": "look around",
            "action": {"action_type": "look", "target": "", "topic": ""},
            "outcome": {"result": "success", "consequences": []},
            "narrative": "You take in your surroundings...",
            "location": "crossroads_inn",
        })
        print(f"Recorded turn. History: {len(session['history'])} entries")
        print(f"Conversation context:\n{get_conversation_context(session)}")

        path = save_session(session)
        print(f"Saved to: {path}")

    elif cmd == "load":
        if len(sys.argv) < 4:
            print("Usage: python session.py <game_dir> load <file>")
            sys.exit(1)
        session = load_session(sys.argv[3])
        print(f"Loaded session {session['session_id']} at turn {session['turn']}")
        print(f"History: {len(session['history'])} entries")
