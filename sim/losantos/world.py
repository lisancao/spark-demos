"""Static tables for the lobby sim, built from GTA V's own data where the game has it.

`world_data.json` is extracted by `bin/gta_world.py` from DurtyFree's GTA V data dumps
(https://github.com/DurtyFree/gta-v-data-dumps): the map's named zones with their centroids, the vehicles
with class, type, mounted weapons and top speed, and the on-foot weapons. The business table and the behaviour
numbers below are the sim's own; the game does not publish those.
"""

import json
import math
from pathlib import Path

_DATA = json.load(open(Path(__file__).with_name("world_data.json")))

ZONES = _DATA["zones"]                  # key -> {name, code, x, y}
VEHICLES = _DATA["vehicles"]            # key -> {name, role, vclass, vtype, flying, weapons, max_speed, ...}
WEAPONS = _DATA["weapons"]              # key -> {id, name, category, damage}

AREAS = sorted(ZONES)
# The city is everything south of the Vinewood Hills; the county is the rest. Split on the map's y axis.
CITY = [a for a in AREAS if ZONES[a]["y"] < 600]
COUNTY = [a for a in AREAS if ZONES[a]["y"] >= 600]


def distance(a: str, b: str) -> float:
    za, zb = ZONES[a], ZONES[b]
    return math.hypot(za["x"] - zb["x"], za["y"] - zb["y"])


# A ground vehicle covers max_speed * SECONDS_PER_TICK metres per tick (the dump's MaxSpeed is m/s). Flying
# vehicles close any distance in a tick.
SECONDS_PER_TICK = 60.0   # a tick is a minute of game time


def reach(vehicle: str | None) -> float:
    if vehicle is None:
        return 25.0 * SECONDS_PER_TICK      # on foot, or a taxi
    v = VEHICLES.get(vehicle)
    if v is None:
        return 40.0 * SECONDS_PER_TICK      # "personal_vehicle" and anything not in the dump
    return math.inf if v["flying"] else v["max_speed"] * SECONDS_PER_TICK


def step_toward(src: str, dst: str, vehicle: str | None) -> str:
    """The zone a player gets to this tick heading from src to dst: dst if within reach, else the zone within
    reach that is closest to dst."""
    if src == dst or distance(src, dst) <= reach(vehicle):
        return dst
    r = reach(vehicle)
    candidates = [a for a in AREAS if a != src and distance(src, a) <= r]
    if not candidates:
        return src
    return min(candidates, key=lambda a: distance(a, dst))


def is_flying(vehicle: str | None) -> bool:
    return bool(vehicle and VEHICLES.get(vehicle, {}).get("flying"))


PVP_VEHICLES = {k for k, v in VEHICLES.items() if v["role"] == "pvp"}
SELL_VEHICLES = {k for k, v in VEHICLES.items() if v["role"] == "sell"}

# How dangerous a hunter on this vehicle is to a sell: the dump gives mounted weapons and whether it flies.
def menace(vehicle: str) -> int:
    v = VEHICLES[vehicle]
    missiles = any("MISSILE" in w or "ROCKET" in w or "CANNON" in w for w in v["weapons"])
    return (2 if v["flying"] else 0) + (1 if missiles else 0)

PVP_KILL_CHANCE = {k: {3: 0.55, 2: 0.30, 1: 0.25, 0: 0.08}[menace(k)] for k in PVP_VEHICLES}

# Business types a grinder can own: where the product accrues, how fast, what it sells for, and what the sell mission
# looks like (vehicle, number of drops, mission clock in ticks). The sim's own numbers.
BUSINESSES = {
    "bunker":            dict(areas=COUNTY, cap=1_050_000, accrual=12_000, product="weapons",         vehicle="insurgent2", drops=(1, 3), clock=48),
    "nightclub":         dict(areas=CITY,   cap=1_690_000, accrual=9_000,  product="nightclub_goods", vehicle="speedo4",    drops=(1, 2), clock=40),
    "acid_lab":          dict(areas=COUNTY, cap=335_000,   accrual=6_000,  product="acid",            vehicle="mule4",      drops=(1, 1), clock=30),
    "coke_lockup":       dict(areas=CITY,   cap=420_000,   accrual=7_000,  product="coke",            vehicle="mule",       drops=(2, 4), clock=44),
    "meth_lab":          dict(areas=COUNTY, cap=357_000,   accrual=6_000,  product="meth",            vehicle="speedo",     drops=(2, 4), clock=44),
    "counterfeit_cash":  dict(areas=CITY,   cap=294_000,   accrual=5_000,  product="cash",            vehicle="brickade",   drops=(2, 4), clock=44),
    "hangar":            dict(areas=COUNTY, cap=1_200_000, accrual=8_000,  product="air_cargo",       vehicle="cuban800",   drops=(1, 2), clock=40),
    "crate_warehouse":   dict(areas=CITY,   cap=2_220_000, accrual=10_000, product="special_cargo",   vehicle="pounder2",   drops=(2, 5), clock=50),
    "vehicle_warehouse": dict(areas=CITY,   cap=800_000,   accrual=8_000,  product="export_cars",     vehicle="adder",      drops=(1, 1), clock=36),
}

# How hard a sell vehicle is to kill: the per-tick chance a hunter on top of it finishes the job. Armoured and
# weaponised sell vehicles (the dump lists their turrets) are harder.
def _sell_toughness(k: str) -> float:
    v = VEHICLES[k]
    return 0.18 if v["weapons"] and v["vclass"] == "OFF_ROAD" else 0.30 if v["weapons"] else 0.45

VEHICLE_KILL_CHANCE = {k: _sell_toughness(k) for k in SELL_VEHICLES} | {"adder": 0.50}

# What a hunter's kill is logged with: the vehicle's first missile-class weapon, else its gun, else on foot.
def vehicle_weapon(vehicle: str | None) -> str | None:
    v = VEHICLES.get(vehicle or "")
    if not v or not v["weapons"]:
        return None
    heavy = [w for w in v["weapons"] if "MISSILE" in w or "ROCKET" in w or "CANNON" in w]
    return (heavy or v["weapons"])[0]

ON_FOOT_WEAPONS = [k for k in WEAPONS if k != "knife"]

WANTED_REASONS = ["shot_cops", "stole_vehicle", "killed_npcs", "destroyed_vehicles", "robbed_store"]

ORG_NAMES = ["Chumash Imports", "Vespucci Holdings", "Paleto Logistics", "Mirror Park MC", "Lost Cause MC",
             "Grapeseed Growers", "Elysian Freight", "Del Perro Capital", "Zancudo Exports", "Davis Street MC",
             "Rockford Equity", "Strawberry Syndicate", "Chiliad Movers", "LSIA Cargo", "La Mesa Metalworks"]

TAG_LEFT = ["xX", "Lester", "Ghost", "Trevor", "Sniper", "Nova", "Big", "Lil", "Dark", "Pink", "Loud", "Quiet",
            "Shark", "Chop", "Vinewood", "Paleto", "Sandy", "Cayo", "Griefed", "Passive", "Turbo", "Salty", "Humble",
            "Cargo", "Bunker", "Nightclub", "Oppressor", "Kosatka", "Zancudo", "Casino"]
TAG_RIGHT = ["Slayer", "Fan2013", "Rider", "Mom", "Dad", "Enjoyer", "Hater", "King", "Queen", "Gremlin", "Wizard",
             "Pilot", "Mechanic", "Grinder", "Hopper", "Menace", "Civilian", "Tourist", "Lord", "Andy", "Chad",
             "Raccoon", "Pigeon", "Seagull", "Duck", "Goose", "Otter", "Bear"]
TAG_SUFFIX = ["", "", "", "_", "Xx", "420", "69", "1999", "2004", "_TTV", "_YT", "ok", "sr", "jr"]
