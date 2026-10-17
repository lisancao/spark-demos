#!/usr/bin/env python3
"""
Combat Engine — Turn-based combat resolution.

Dict-based, functional style matching the rest of the codebase.
Combat resolved as rounds: determine turn order, resolve each actor's action,
apply results. Resource drain: each attack costs 1 stamina.

Combat should feel like a failure state, not a power fantasy.
"""

import random as _random
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Combat initialization
# ---------------------------------------------------------------------------

def start_combat(player_stats: dict, enemies: list[dict],
                 rng: _random.Random = None) -> dict:
    """Initialize combat state.

    player_stats: {"health": int, "stamina": int, "damage": int, ...}
    enemies: [{"name": str, "stats": {"health": int, "damage": int, "speed": str}, "behavior": str}, ...]
    """
    if rng is None:
        rng = _random.Random()

    combat_enemies = []
    for i, enemy in enumerate(enemies):
        stats = enemy.get("stats", {})
        combat_enemies.append({
            "id": f"enemy_{i}",
            "name": enemy.get("name", f"enemy {i}"),
            "description": enemy.get("description", ""),
            "health": stats.get("health", 5),
            "max_health": stats.get("health", 5),
            "damage": stats.get("damage", 2),
            "speed": stats.get("speed", "normal"),
            "behavior": enemy.get("behavior", "aggressive"),
            "defending": False,
            "alive": True,
        })

    # Player combat stats derived from game stats.
    player_damage = player_stats.get("damage", 2)

    return {
        "player": {
            "health": player_stats.get("health", 10),
            "max_health": player_stats.get("health", 10),
            "stamina": player_stats.get("stamina", 8),
            "max_stamina": player_stats.get("stamina", 8),
            "damage": player_damage,
            "defending": False,
        },
        "enemies": combat_enemies,
        "round": 0,
        "status": "active",  # "active", "victory", "defeat", "fled"
        "log": [],
    }


# ---------------------------------------------------------------------------
# Turn order
# ---------------------------------------------------------------------------

SPEED_VALUES = {"fast": 3, "normal": 2, "slow": 1}


def determine_turn_order(player_stats: dict, enemies: list[dict]) -> list[dict]:
    """Speed-based initiative. Returns ordered list of actors."""
    actors = []

    # Player speed derived from stamina.
    player_speed = 2
    stamina = player_stats.get("stamina", 8)
    if stamina >= 6:
        player_speed = 3
    elif stamina <= 2:
        player_speed = 1

    actors.append({"type": "player", "name": "player", "speed": player_speed})

    for enemy in enemies:
        if not enemy.get("alive", True):
            continue
        speed_str = enemy.get("speed", "normal")
        actors.append({
            "type": "enemy",
            "id": enemy.get("id", ""),
            "name": enemy.get("name", "enemy"),
            "speed": SPEED_VALUES.get(speed_str, 2),
        })

    actors.sort(key=lambda a: a["speed"], reverse=True)
    return actors


# ---------------------------------------------------------------------------
# Damage calculation
# ---------------------------------------------------------------------------

def calculate_damage(attacker_damage: int, is_defending: bool,
                     rng: _random.Random = None) -> int:
    """Base damage +/- 1 random variance, halved if defending, min 0."""
    if rng is None:
        rng = _random.Random()

    variance = rng.randint(-1, 1)
    damage = attacker_damage + variance
    if is_defending:
        damage = damage // 2
    return max(0, damage)


# ---------------------------------------------------------------------------
# Enemy AI
# ---------------------------------------------------------------------------

def resolve_enemy_action(enemy: dict, combat: dict,
                         rng: _random.Random = None) -> dict:
    """Simple AI based on behavior string.

    Returns: {"action": str, "target": str, "damage": int}
    """
    if rng is None:
        rng = _random.Random()

    behavior = enemy.get("behavior", "aggressive")
    health_ratio = enemy["health"] / max(1, enemy["max_health"])

    # Defensive behavior: defend more when wounded.
    if "defensive" in behavior and health_ratio < 0.5:
        if rng.random() < 0.6:
            enemy["defending"] = True
            return {"action": "defend", "target": "", "damage": 0}

    # Ambush behavior: higher damage first round.
    if "ambush" in behavior and combat["round"] == 1:
        damage = calculate_damage(enemy["damage"] + 1, combat["player"]["defending"], rng)
        return {"action": "attack", "target": "player", "damage": damage}

    # Default: attack.
    enemy["defending"] = False
    if rng.random() < 0.15:
        # Occasionally defend.
        enemy["defending"] = True
        return {"action": "defend", "target": "", "damage": 0}

    damage = calculate_damage(enemy["damage"], combat["player"]["defending"], rng)
    return {"action": "attack", "target": "player", "damage": damage}


# ---------------------------------------------------------------------------
# Round resolution
# ---------------------------------------------------------------------------

def resolve_combat_round(combat: dict, player_action: str,
                         rng: _random.Random = None) -> dict:
    """Process one combat round.

    player_action: "attack", "defend", "flee", or "use <item>"

    Returns: {"round": int, "events": list[str], "status": str}
    """
    if rng is None:
        rng = _random.Random()

    combat["round"] += 1
    events = []
    player = combat["player"]
    living_enemies = [e for e in combat["enemies"] if e.get("alive", True)]

    if not living_enemies:
        combat["status"] = "victory"
        return {"round": combat["round"], "events": ["No enemies remain."], "status": "victory"}

    # Determine turn order.
    order = determine_turn_order(player, living_enemies)

    # Reset defending.
    player["defending"] = False
    for enemy in living_enemies:
        enemy["defending"] = False

    for actor in order:
        # Check if combat is already over.
        if combat["status"] != "active":
            break

        if actor["type"] == "player":
            result = _resolve_player_action(combat, player_action, living_enemies, rng)
            events.extend(result)
        else:
            enemy = next((e for e in living_enemies if e.get("id") == actor.get("id")), None)
            if enemy and enemy.get("alive", True):
                action = resolve_enemy_action(enemy, combat, rng)
                if action["action"] == "attack":
                    player["health"] -= action["damage"]
                    events.append(f"{enemy['name']} attacks for {action['damage']} damage.")
                    if player["health"] <= 0:
                        player["health"] = 0
                        combat["status"] = "defeat"
                        events.append("You fall.")
                elif action["action"] == "defend":
                    events.append(f"{enemy['name']} takes a defensive stance.")

    # Check victory.
    if all(not e.get("alive", True) for e in combat["enemies"]):
        combat["status"] = "victory"
        events.append("All enemies defeated.")

    combat["log"].append({
        "round": combat["round"],
        "events": events,
        "status": combat["status"],
    })

    return {"round": combat["round"], "events": events, "status": combat["status"]}


def _resolve_player_action(combat: dict, action: str,
                           living_enemies: list[dict],
                           rng: _random.Random) -> list[str]:
    """Resolve the player's chosen action."""
    player = combat["player"]
    events = []

    if action == "defend":
        player["defending"] = True
        events.append("You brace yourself, ready to absorb the next blow.")
        return events

    if action == "flee":
        # Speed check: succeed if player is faster than slowest enemy.
        player_speed = 3 if player["stamina"] >= 6 else (1 if player["stamina"] <= 2 else 2)
        enemy_speeds = [SPEED_VALUES.get(e.get("speed", "normal"), 2) for e in living_enemies]
        min_enemy_speed = min(enemy_speeds) if enemy_speeds else 2

        if player_speed > min_enemy_speed or rng.random() < 0.3:
            combat["status"] = "fled"
            events.append("You break away and run.")
        else:
            events.append("You try to flee but can't break away.")
        return events

    if action.startswith("use "):
        item_name = action[4:].strip()
        events.append(f"You use {item_name}.")
        return events

    # Default: attack the first living enemy.
    if not living_enemies:
        return events

    target = living_enemies[0]

    # Stamina cost.
    if player["stamina"] > 0:
        player["stamina"] -= 1
        damage = calculate_damage(player["damage"], target.get("defending", False), rng)
    else:
        # Exhausted: damage halved.
        damage = calculate_damage(player["damage"] // 2, target.get("defending", False), rng)
        events.append("Exhaustion slows your strike.")

    target["health"] -= damage
    events.append(f"You strike {target['name']} for {damage} damage.")

    if target["health"] <= 0:
        target["health"] = 0
        target["alive"] = False
        events.append(f"{target['name']} falls.")

    return events


# ---------------------------------------------------------------------------
# Combat summary / prompts
# ---------------------------------------------------------------------------

def get_combat_summary(combat: dict) -> str:
    """Formatted status display."""
    player = combat["player"]
    lines = [
        f"--- Round {combat['round']} ---",
        f"  You: {player['health']}/{player['max_health']} HP, {player['stamina']}/{player['max_stamina']} stamina",
    ]
    for enemy in combat["enemies"]:
        status = f"{enemy['health']}/{enemy['max_health']} HP" if enemy["alive"] else "defeated"
        lines.append(f"  {enemy['name']}: {status}")
    lines.append(f"  Actions: attack, defend, flee")
    return "\n".join(lines)


def build_combat_prompt_context(combat: dict) -> dict:
    """Dict for scene_engine injection."""
    return {
        "round": combat["round"],
        "status": combat["status"],
        "player_health": combat["player"]["health"],
        "player_max_health": combat["player"]["max_health"],
        "player_stamina": combat["player"]["stamina"],
        "enemies": [
            {
                "name": e["name"],
                "description": e.get("description", ""),
                "health": e["health"],
                "max_health": e["max_health"],
                "alive": e["alive"],
            }
            for e in combat["enemies"]
        ],
        "recent_events": combat["log"][-3:] if combat["log"] else [],
    }


def get_combat_consequences(combat: dict, encounter: dict) -> list[dict]:
    """Post-combat state updates based on outcome."""
    consequences = []

    if combat["status"] == "victory":
        # Loot.
        for reward in encounter.get("rewards", []):
            consequences.append({"type": "add_item", "item_id": reward.get("id", "")})

        # Quest advancement.
        for c in encounter.get("consequences", []):
            consequences.append(c)

        # Unblock paths.
        for c in encounter.get("consequences", []):
            if c.get("type") == "unblock_path":
                consequences.append(c)

        consequences.append({
            "type": "event",
            "description": f"Defeated {', '.join(e['name'] for e in combat['enemies'])}",
        })

    elif combat["status"] == "defeat":
        consequences.append({
            "type": "event",
            "description": "Fell in combat.",
        })

    elif combat["status"] == "fled":
        consequences.append({
            "type": "event",
            "description": "Fled from combat.",
        })

    return consequences
