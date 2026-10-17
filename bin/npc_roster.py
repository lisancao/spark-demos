#!/usr/bin/env python3
"""Export the sim's NPC roster (npcs.yaml) as JSON lines: the initial state for the cyberpsychosis processor."""
import json
import sys
from pathlib import Path

import yaml

src = Path(sys.argv[1] if len(sys.argv) > 1 else "sim/cyberpunk_sim/game_data/npcs.yaml")
dst = Path(sys.argv[2] if len(sys.argv) > 2 else "data/roster/npcs.jsonl")
dst.parent.mkdir(parents=True, exist_ok=True)
npcs = yaml.safe_load(open(src))["npcs"]
with open(dst, "w") as f:
    for n in npcs:
        f.write(json.dumps({
            "agent_id": n["id"],
            "agent_name": n.get("name", n["id"]),
            "role": n.get("role", ""),
            "faction_id": n.get("faction", ""),
            "chrome_score": int(n.get("chrome_score", 0) or 0),
            "cyberware_count": len(n.get("cyberware") or []),
        }) + "\n")
print(f"{len(npcs)} NPCs -> {dst}", file=sys.stderr)
