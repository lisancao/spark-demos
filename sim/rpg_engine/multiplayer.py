#!/usr/bin/env python3
"""
Multiplayer — Player roster, turn rotation, and file-based remote player I/O.

Remote players (Claude Code sessions) interact through small context files
and action files. The context file contains ONLY what's needed for the next
decision — no full history.

File protocol:
  ~/.rpg_engine/live/<game_id>/context_<player>.md   — engine writes before remote turn
  ~/.rpg_engine/live/<game_id>/action_<player>.txt   — remote player writes their action
  ~/.rpg_engine/live/<game_id>/adventure.md          — append-only narrative log (all turns)
"""

import time
from pathlib import Path
from typing import Any


LIVE_DIR = Path.home() / ".rpg_engine" / "live"
POLL_INTERVAL = 1.0  # seconds


# ---------------------------------------------------------------------------
# Player roster
# ---------------------------------------------------------------------------

def parse_players(spec: str) -> list[dict]:
    """Parse player spec string into roster.

    Format: "Name:type,Name:type" where type is 'human' or 'remote'.
    Example: "Lisa:human,Boromir:remote,Eowyn:remote"
    """
    players = []
    for entry in spec.split(","):
        entry = entry.strip()
        if ":" in entry:
            name, ptype = entry.rsplit(":", 1)
            ptype = ptype.strip().lower()
        else:
            name = entry
            ptype = "human"

        if ptype not in ("human", "remote"):
            ptype = "human"

        players.append({
            "name": name.strip(),
            "type": ptype,
        })

    return players


def get_current_player(roster: list[dict], turn: int) -> dict:
    """Get the player whose turn it is (round-robin)."""
    if not roster:
        return {"name": "unknown", "type": "human"}
    return roster[turn % len(roster)]


# ---------------------------------------------------------------------------
# Live directory management
# ---------------------------------------------------------------------------

def get_live_dir(game_id: str) -> Path:
    """Get/create the live directory for a game."""
    d = LIVE_DIR / game_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def clear_live_dir(game_id: str):
    """Remove stale action files on session start."""
    d = get_live_dir(game_id)
    for f in d.glob("action_*.txt"):
        f.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Context writing — SMALL, focused, no history dump
# ---------------------------------------------------------------------------

def write_context(game_id: str, player_name: str, data: dict,
                  session: dict, last_narrative: str = "") -> Path:
    """Write a minimal context file for a remote player.

    Contains ONLY:
    - Whose turn it is
    - Current location + sensory
    - NPCs present
    - Player stats/inventory (brief)
    - Active quests (brief)
    - Last turn's narrative (what just happened)

    Typically ~300-500 words. The engine owns the full state.
    """
    from game_state import (
        get_player, get_location, get_npcs_at_location,
        get_active_quests, get_quest_stage,
    )

    player = get_player(data)
    location_id = player.get("location", "")
    location = get_location(data, location_id) if location_id else {}

    lines = []
    lines.append(f"# {player_name}'s Turn")
    lines.append(f"Turn {session.get('turn', 0) + 1}")
    lines.append("")

    # What just happened.
    if last_narrative:
        lines.append("## Last Turn")
        lines.append(last_narrative.strip())
        lines.append("")

    # Where you are.
    if location:
        loc_name = location.get("name", location_id)
        lines.append(f"## Location: {loc_name}")
        if location.get("description"):
            lines.append(location["description"].strip())
        sensory = location.get("sensory", {})
        if sensory:
            details = [v.strip() for v in sensory.values() if v and v.strip()]
            if details:
                lines.append(" ".join(details))
        lines.append("")

    # Who's here.
    npcs = get_npcs_at_location(data, location_id) if location_id else []
    if npcs:
        lines.append("## NPCs Present")
        for npc in npcs:
            name = npc.get("name", "Someone")
            role = npc.get("role", "")
            activity = npc.get("current_activity", "")
            disposition = npc.get("disposition", "neutral")
            line = f"- **{name}**"
            if role:
                line += f" ({role})"
            if disposition != "neutral":
                line += f" [{disposition}]"
            if activity:
                line += f" — {activity}"
            lines.append(line)
        lines.append("")

    # Your state (brief).
    stats = player.get("stats", {})
    health = stats.get("health", "?")
    stamina = stats.get("stamina", "?")
    inventory = player.get("inventory", [])
    inv_names = [i.get("name", i.get("id", "?")) for i in inventory[:10]]

    lines.append("## Your State")
    lines.append(f"Health: {health} | Stamina: {stamina}")
    if inv_names:
        lines.append(f"Carrying: {', '.join(inv_names)}")
    conditions = player.get("conditions", [])
    if conditions:
        lines.append(f"Conditions: {', '.join(conditions)}")
    lines.append("")

    # Active quests (brief).
    quests = get_active_quests(data)
    if quests:
        lines.append("## Active Quests")
        for q in quests[:5]:
            stage = get_quest_stage(q)
            lines.append(f"- {q.get('name', '?')}: {stage.get('objective', '?')}")
        lines.append("")

    # Connections (where can you go).
    if location:
        connections = location.get("connections", [])
        if connections:
            lines.append("## Exits")
            for conn in connections:
                if isinstance(conn, dict):
                    lines.append(f"- {conn.get('direction', '?')} → {conn.get('destination', conn.get('location', '?'))}")
                else:
                    lines.append(f"- {conn}")
            lines.append("")

    # Write it.
    live_dir = get_live_dir(game_id)
    context_file = live_dir / f"context_{_sanitize(player_name)}.md"
    context_file.write_text("\n".join(lines), encoding="utf-8")
    return context_file


def read_context(game_id: str, player_name: str) -> str:
    """Read the context file for a player (used by `rpg context`)."""
    live_dir = get_live_dir(game_id)
    context_file = live_dir / f"context_{_sanitize(player_name)}.md"
    if context_file.exists():
        return context_file.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Action file I/O
# ---------------------------------------------------------------------------

def write_action(game_id: str, player_name: str, action: str) -> Path:
    """Write an action file (called by `rpg turn`)."""
    live_dir = get_live_dir(game_id)
    action_file = live_dir / f"action_{_sanitize(player_name)}.txt"
    action_file.write_text(action.strip(), encoding="utf-8")
    return action_file


def wait_for_action(game_id: str, player_name: str,
                    timeout: float = 600.0) -> str | None:
    """Poll for an action file from a remote player.

    Returns the action text, or None on timeout.
    Deletes the action file after reading.
    """
    live_dir = get_live_dir(game_id)
    action_file = live_dir / f"action_{_sanitize(player_name)}.txt"

    # Clear any stale action file.
    action_file.unlink(missing_ok=True)

    elapsed = 0.0
    while elapsed < timeout:
        if action_file.exists():
            text = action_file.read_text(encoding="utf-8").strip()
            action_file.unlink(missing_ok=True)
            if text:
                return text
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    return None


# ---------------------------------------------------------------------------
# Adventure log — append-only narrative record
# ---------------------------------------------------------------------------

def append_adventure_log(game_id: str, turn: int, player_name: str,
                         action: str, narrative: str):
    """Append a turn to the shared adventure log."""
    live_dir = get_live_dir(game_id)
    log_file = live_dir / "adventure.md"

    entry = []
    entry.append(f"\n---\n**Turn {turn}** — *{player_name}*")
    entry.append(f"> {action}")
    entry.append("")
    entry.append(narrative.strip())
    entry.append("")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write("\n".join(entry))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize(name: str) -> str:
    """Sanitize a player name for use in filenames."""
    return name.lower().replace(" ", "_").replace("/", "_")
