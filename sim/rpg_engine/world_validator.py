#!/usr/bin/env python3
"""
World Validator — Setting register enforcement for text-based RPGs.

Scans generated narrative text for vocabulary that breaks the world's register.
A medieval fantasy game shouldn't reference "databases." A cyberpunk game
shouldn't mention "chainmail."

Adapted from Writer's Hand register_validator.py.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Built-in setting presets
# ---------------------------------------------------------------------------

DARK_FANTASY = {
    "name": "Dark Fantasy",
    "description": "Medieval dark fantasy. Grim, low-magic. No modern technology, no cheerful tone in dangerous situations.",
    "forbidden": {
        # Modern technology
        "computer": "[avoid — no electronics]",
        "phone": "[avoid]",
        "email": "[avoid]",
        "screenshot": "[avoid]",
        "download": "[avoid]",
        "upload": "[avoid]",
        "online": "[avoid]",
        "database": "records, archives, ledgers",
        "algorithm": "method, pattern, system",
        "software": "[avoid]",
        "hardware": "ironmongery, fittings, equipment",
        # Corporate/bureaucratic
        "stakeholder": "interested party, those with a claim",
        "leverage": "advantage, hold (noun); use, exploit (verb)",
        "optimize": "sharpen, hone, improve",
        "synergy": "[avoid]",
        "bandwidth": "capacity, attention",
        "paradigm": "[avoid]",
        # Modern casual
        "okay": "very well, agreed",
        "OK": "very well, agreed",
        "cool": "good, well (unless literal temperature)",
        "awesome": "use only in original sense (inspiring awe)",
        "literally": "truly, in truth (or cut)",
        "basically": "in essence, simply (or cut)",
        "gonna": "going to",
        "wanna": "want to",
        "dude": "[avoid]",
        "guys": "men, folk, people",
        # Out-of-setting
        "gun": "crossbow, bow, siege weapon (unless gunpowder exists in setting)",
        "electricity": "[avoid unless setting-specific]",
        "plastic": "[avoid]",
        "rubber": "[avoid]",
    },
    "flagged": {
        "machine": "Fine for siege engines, traps. Flag if it reads as modern machinery.",
        "system": "Fine for political systems. Flag if it reads as IT.",
        "network": "Fine for spy networks, trade routes. Flag if it reads as computer networks.",
        "trigger": "Fine for traps, crossbows. Flag if used psychologically.",
        "process": "Fine as verb. Flag if it reads as bureaucratic noun.",
        "protocol": "Borderline. 'Procedure' or 'custom' may fit better.",
    },
    "preferred": {
        "categories": [
            "stone, iron, steel, bronze, leather, bone",
            "torch, candle, lantern, hearth, brazier",
            "sword, axe, mace, spear, bow, dagger, shield",
            "horse, mule, cart, wagon",
            "tavern, inn, smithy, chapel, keep, dungeon",
            "bread, stew, ale, mead, wine, dried meat",
            "lord, lady, knight, squire, priest, merchant, thief",
        ],
    },
}

CYBERPUNK = {
    "name": "Cyberpunk",
    "description": "Near-future dystopian. High tech, low life. Corporate control, street culture, augmentation.",
    "forbidden": {
        # Medieval/fantasy
        "sword": "blade, monofilament, vibroblade",
        "castle": "megastructure, arcology, corporate tower",
        "magic": "tech, augmentation, hack",
        "wizard": "[not in this setting]",
        "dragon": "[not in this setting]",
        "thou": "you",
        "thee": "you",
        "thy": "your",
        "knight": "operative, enforcer, agent",
        "peasant": "citizen, wage-slave, prole",
        "chainmail": "[not in this setting — use body armor, smart weave]",
        "goblin": "[not in this setting]",
        "potion": "stim, chems, pharma",
    },
    "flagged": {
        "organic": "Fine for food/biological. Flag if used as tech term incorrectly.",
        "natural": "In cyberpunk, 'natural' vs augmented is politically loaded.",
        "human": "Context-dependent — augmentation blurs the line.",
    },
    "preferred": {
        "categories": [
            "neon, chrome, concrete, polymer, glass, circuitry",
            "pistol, rifle, SMG, shotgun, taser, EMP",
            "augmentation, cyberware, neural link, optics",
            "corp, megacorp, subsidiary, black site",
            "netrunner, fixer, solo, techie, medic",
            "cred, eddies, scrip, crypto",
            "drone, AV, spinner, bike",
        ],
    },
}

SPACE_OPERA = {
    "name": "Space Opera",
    "description": "Interstellar sci-fi. Multiple species, FTL travel, energy weapons, galactic politics.",
    "forbidden": {
        "sword": "energy blade, vibroblade (or justify culturally)",
        "castle": "station, citadel, orbital, flagship",
        "magic": "psionic abilities, anomalous energy, dark tech",
        "horse": "ground transport, speeder, mount (alien equivalent)",
        "tavern": "cantina, bar, lounge, mess hall",
        "chainmail": "[not in this setting — use armor plating, kinetic barriers]",
    },
    "flagged": {
        "alien": "Fine in human POV. In mixed-species contexts, consider perspective.",
        "human": "Neutral. But non-human POV characters wouldn't center humanity.",
    },
    "preferred": {
        "categories": [
            "hull, bulkhead, airlock, viewport, corridor, deck",
            "pistol, rifle, plasma, laser, mass driver",
            "FTL, hyperdrive, relay, slip-space, warp",
            "station, dreadnought, frigate, shuttle, dropship",
            "captain, commander, admiral, operative, diplomat",
            "credits, standard galactic, trade units",
        ],
    },
}

POST_APOCALYPTIC = {
    "name": "Post-Apocalyptic",
    "description": "After civilization fell. Scarcity, ruins, improvisation, danger. No functioning high technology unless found/hoarded.",
    "forbidden": {
        "download": "[no functioning internet]",
        "upload": "[no functioning internet]",
        "email": "[no functioning email]",
        "app": "[no functioning smartphones]",
        "wifi": "[no functioning wifi]",
        "uber": "[avoid brand names]",
    },
    "flagged": {
        "electricity": "Rare. If used, note it as exceptional — generator, solar, pre-war.",
        "car": "Fine if fuel exists. Most vehicles are broken or jury-rigged.",
        "gun": "Fine. But ammo is scarce — note it.",
        "phone": "Pre-war relic. Note if it somehow works.",
        "computer": "Pre-war tech. Mostly broken. Treat as rare artifact.",
    },
    "preferred": {
        "categories": [
            "ruin, rubble, wreckage, overgrowth, dust, rust",
            "machete, pipe, bat, crossbow, sling, improvised weapon",
            "canned food, jerky, clean water, salvage, scrap",
            "settlement, camp, bunker, safe house, outpost",
            "scavenger, trader, raider, elder, scout, healer",
            "barter, trade, favor, debt",
        ],
    },
}

PRESETS = {
    "dark-fantasy": DARK_FANTASY,
    "cyberpunk": CYBERPUNK,
    "space-opera": SPACE_OPERA,
    "post-apocalyptic": POST_APOCALYPTIC,
}


# ---------------------------------------------------------------------------
# Validation logic (from register_validator.py)
# ---------------------------------------------------------------------------

def load_preset(name: str) -> dict:
    """Load a setting preset by name."""
    if name in PRESETS:
        return PRESETS[name]
    # Try loading from file.
    config_path = Path(__file__).parent / "setting_configs" / f"{name}.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    raise ValueError(f"Unknown setting preset: {name}. Available: {', '.join(PRESETS.keys())}")


def validate_text(text: str, preset: dict) -> dict[str, Any]:
    """Scan text against a setting preset. Returns structured findings."""
    lines = text.split("\n")
    findings = {
        "forbidden": [],
        "flagged": [],
        "stats": {
            "total_lines": len(lines),
            "forbidden_count": 0,
            "flagged_count": 0,
        },
    }

    forbidden = preset.get("forbidden", {})
    flagged = preset.get("flagged", {})

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        for word, suggestion in forbidden.items():
            pattern = r'\b' + re.escape(word) + r'\b'
            for match in re.finditer(pattern, line, re.IGNORECASE):
                context = _get_context(line, match)
                findings["forbidden"].append({
                    "line": line_num,
                    "word": word,
                    "matched": match.group(),
                    "suggestion": suggestion,
                    "context": context,
                })
                findings["stats"]["forbidden_count"] += 1

        for word, note in flagged.items():
            pattern = r'\b' + re.escape(word) + r'\b'
            for match in re.finditer(pattern, line, re.IGNORECASE):
                context = _get_context(line, match)
                findings["flagged"].append({
                    "line": line_num,
                    "word": word,
                    "matched": match.group(),
                    "note": note,
                    "context": context,
                })
                findings["stats"]["flagged_count"] += 1

    # Dedup: remove flagged entries for words also found in forbidden on same line.
    forbidden_keys = set((f["line"], f["word"]) for f in findings["forbidden"])
    findings["flagged"] = [
        f for f in findings["flagged"]
        if (f["line"], f["word"]) not in forbidden_keys
    ]
    findings["stats"]["flagged_count"] = len(findings["flagged"])

    return findings


def _get_context(line: str, match: re.Match, window: int = 40) -> str:
    """Extract context window around a match."""
    start = max(0, match.start() - window)
    end = min(len(line), match.end() + window)
    context = line[start:end].strip()
    if start > 0:
        context = "..." + context
    if end < len(line):
        context = context + "..."
    return context


def format_validation_report(findings: dict, preset: dict) -> str:
    """Format validation findings as readable text."""
    lines = []
    lines.append(f"## World Register Validation: {preset.get('name', '?')}")
    lines.append(f"Setting: {preset.get('description', '')}")
    lines.append("")

    stats = findings["stats"]
    lines.append(f"Lines scanned: {stats['total_lines']}")
    lines.append(f"Forbidden: {stats['forbidden_count']} | Flagged: {stats['flagged_count']}")
    lines.append("")

    if findings["forbidden"]:
        lines.append("### FORBIDDEN (must fix)")
        lines.append("")
        by_word = defaultdict(list)
        for f in findings["forbidden"]:
            by_word[f["word"]].append(f)
        for word, instances in sorted(by_word.items(), key=lambda x: -len(x[1])):
            lines.append(f'**"{word}"** - {len(instances)} occurrence(s)')
            lines.append(f"  Replace with: {instances[0]['suggestion']}")
            for inst in instances[:3]:
                lines.append(f"  - Line {inst['line']}: `{inst['context']}`")
            lines.append("")

    if findings["flagged"]:
        lines.append("### FLAGGED (review)")
        lines.append("")
        by_word = defaultdict(list)
        for f in findings["flagged"]:
            by_word[f["word"]].append(f)
        for word, instances in sorted(by_word.items(), key=lambda x: -len(x[1])):
            lines.append(f'**"{word}"** - {len(instances)} occurrence(s)')
            lines.append(f"  Note: {instances[0]['note']}")
            for inst in instances[:3]:
                lines.append(f"  - Line {inst['line']}: `{inst['context']}`")
            lines.append("")

    if not findings["forbidden"] and not findings["flagged"]:
        lines.append("**Clean pass.** No register violations found.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate RPG narrative text against a world setting."
    )
    sub = parser.add_subparsers(dest="command")

    scan_p = sub.add_parser("scan", help="Scan a text file")
    scan_p.add_argument("file", help="Text file to scan")
    scan_p.add_argument("--preset", "-p", default="dark-fantasy", help="Setting preset")

    list_p = sub.add_parser("list", help="List available presets")

    show_p = sub.add_parser("show", help="Show a preset's word lists")
    show_p.add_argument("preset", help="Preset name")

    args = parser.parse_args()

    if args.command == "list":
        print("Available setting presets:")
        for name, config in PRESETS.items():
            fc = len(config.get("forbidden", {}))
            fl = len(config.get("flagged", {}))
            print(f"  {name:20s} - {config['description'][:60]}... ({fc} forbidden, {fl} flagged)")

    elif args.command == "show":
        preset = load_preset(args.preset)
        print(f"## {preset['name']}")
        print(f"{preset.get('description', '')}\n")
        if preset.get("forbidden"):
            print(f"### Forbidden ({len(preset['forbidden'])})")
            for word, suggestion in sorted(preset["forbidden"].items()):
                print(f"  {word:25s} -> {suggestion}")
        if preset.get("flagged"):
            print(f"\n### Flagged ({len(preset['flagged'])})")
            for word, note in sorted(preset["flagged"].items()):
                print(f"  {word:25s} - {note[:80]}")
        if preset.get("preferred"):
            print(f"\n### Preferred vocabulary")
            for cat in preset["preferred"].get("categories", []):
                print(f"  - {cat}")

    elif args.command == "scan":
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"Error: File not found: {filepath}")
            sys.exit(1)
        text = filepath.read_text()
        preset = load_preset(args.preset)
        findings = validate_text(text, preset)
        print(format_validation_report(findings, preset))

    else:
        parser.print_help()
