#!/usr/bin/env python3
"""
Game Registry — Manage multiple game worlds.

Stores game metadata in ~/.rpg_engine/games.yaml. Each game gets its own
directory under ~/.rpg_engine/worlds/ containing the 8 YAML data files.

Supports prefix matching for game IDs — "rpg play hollow" resolves to
"hollow-throne-a3f1" if unambiguous.
"""

import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


RPG_HOME = Path.home() / ".rpg_engine"
WORLDS_DIR = RPG_HOME / "worlds"
REGISTRY_FILE = RPG_HOME / "games.yaml"


class GameRegistry:
    def __init__(self):
        self.home = RPG_HOME
        self.worlds_dir = WORLDS_DIR
        self.registry_file = REGISTRY_FILE
        self._ensure_dirs()
        self.games = self._load()

    def _ensure_dirs(self):
        self.home.mkdir(parents=True, exist_ok=True)
        self.worlds_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if not self.registry_file.exists():
            return []
        try:
            with open(self.registry_file, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, dict) and "games" in data:
                return data["games"]
            return []
        except Exception:
            return []

    def _save(self):
        with open(self.registry_file, "w", encoding="utf-8") as fh:
            yaml.dump({"games": self.games}, fh, default_flow_style=False,
                      allow_unicode=True, sort_keys=False)

    def register(self, name: str, genre: str, game_dir: str = "",
                 player_name: str = "the traveler") -> dict:
        """Register a new game. Returns the game entry."""
        game_id = self._make_id(name)

        if not game_dir:
            game_dir = str(self.worlds_dir / game_id)

        entry = {
            "id": game_id,
            "name": name,
            "genre": genre,
            "game_dir": game_dir,
            "created": _now(),
            "last_played": _now(),
            "turn": 0,
            "player_name": player_name,
        }

        self.games.append(entry)
        self._save()
        return entry

    def find(self, game_id: str) -> Optional[dict]:
        """Find a game by exact ID or unambiguous prefix."""
        # Exact match first.
        for game in self.games:
            if game["id"] == game_id:
                return game

        # Prefix match.
        matches = [g for g in self.games if g["id"].startswith(game_id)]
        if len(matches) == 1:
            return matches[0]

        # Try matching against name slugs.
        if not matches:
            matches = [g for g in self.games
                       if _slugify(g["name"]).startswith(_slugify(game_id))]
            if len(matches) == 1:
                return matches[0]

        return None

    def find_all(self, prefix: str) -> list[dict]:
        """Find all games matching a prefix (for disambiguation)."""
        matches = [g for g in self.games if g["id"].startswith(prefix)]
        if not matches:
            matches = [g for g in self.games
                       if _slugify(g["name"]).startswith(_slugify(prefix))]
        return matches

    def list_all(self) -> list[dict]:
        """All games, sorted by last_played descending."""
        return sorted(self.games,
                      key=lambda g: g.get("last_played", ""), reverse=True)

    def update(self, game_id: str, **fields):
        """Update fields on a game entry."""
        game = self.find(game_id)
        if game:
            game.update(fields)
            self._save()

    def delete(self, game_id: str, delete_files: bool = False) -> bool:
        """Remove a game from the registry."""
        game = self.find(game_id)
        if not game:
            return False

        if delete_files:
            game_dir = Path(game["game_dir"])
            if game_dir.exists() and game_dir.is_dir():
                shutil.rmtree(game_dir)

        self.games = [g for g in self.games if g["id"] != game["id"]]
        self._save()
        return True

    def game_dir_for(self, game_id: str) -> Optional[str]:
        """Get the game_dir path for a game ID."""
        game = self.find(game_id)
        return game["game_dir"] if game else None

    def _make_id(self, name: str) -> str:
        """Generate a slug-hash ID from a name."""
        slug = _slugify(name)[:20]
        hash_part = hashlib.md5(f"{name}{_now()}".encode()).hexdigest()[:4]
        game_id = f"{slug}-{hash_part}" if slug else hash_part

        # Ensure uniqueness.
        existing = {g["id"] for g in self.games}
        while game_id in existing:
            hash_part = hashlib.md5(f"{game_id}{_now()}".encode()).hexdigest()[:4]
            game_id = f"{slug}-{hash_part}"

        return game_id


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    registry = GameRegistry()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "list":
        games = registry.list_all()
        if not games:
            print("No games registered.")
        else:
            for g in games:
                print(f"  {g['id']:30s} {g['genre']:20s} turn {g.get('turn', 0):3d}  {g.get('last_played', '?')}")

    elif cmd == "register":
        name = sys.argv[2] if len(sys.argv) > 2 else "Test Game"
        genre = sys.argv[3] if len(sys.argv) > 3 else "dark-fantasy"
        game_dir = sys.argv[4] if len(sys.argv) > 4 else ""
        entry = registry.register(name, genre, game_dir)
        print(f"Registered: {entry['id']} -> {entry['game_dir']}")

    elif cmd == "find":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        game = registry.find(query)
        if game:
            for k, v in game.items():
                print(f"  {k}: {v}")
        else:
            matches = registry.find_all(query)
            if matches:
                print(f"Ambiguous. Did you mean:")
                for m in matches:
                    print(f"  {m['id']}")
            else:
                print("Not found.")

    elif cmd == "delete":
        game_id = sys.argv[2] if len(sys.argv) > 2 else ""
        force = "--force" in sys.argv
        if registry.delete(game_id, delete_files=force):
            print(f"Deleted: {game_id}")
        else:
            print(f"Not found: {game_id}")
