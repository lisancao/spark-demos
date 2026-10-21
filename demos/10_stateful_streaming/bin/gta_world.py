#!/usr/bin/env python3
"""Extract the Los Santos world tables from DurtyFree's GTA V data dumps.

    python3 -I bin/gta_world.py <path to gta-v-data-dumps checkout> [sim/losantos/world_data.json]

Reads zones.json (map areas with bounds), vehicles.json (class, type, weapons, speed) and weapons.json
(on-foot weapons) and writes the small subset the simulator uses. Source: https://github.com/DurtyFree/gta-v-data-dumps
"""
import json
import re
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2] if len(sys.argv) > 2 else "sim/losantos/world_data.json")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


zones = {}
for z in json.load(open(src / "zones.json")):
    name = z.get("DisplayName")
    if not name or name in ("Pacific Ocean", "North Yankton", "Island") or name.startswith("Lago"):
        continue
    key = slug(name)
    if key in zones:
        continue
    b = z["Bounds"][0]
    zones[key] = dict(name=name, code=z["Name"], x=round((b["Minimum"]["X"] + b["Maximum"]["X"]) / 2, 1),
                      y=round((b["Minimum"]["Y"] + b["Maximum"]["Y"]) / 2, 1))

WANT_VEHICLES = {
    # pvp / hunting
    "oppressor2": "pvp", "deluxo": "pvp", "toreador": "pvp", "seasparrow2": "pvp", "lazer": "pvp", "nightshark": "pvp",
    "kuruma2": "pvp", "scramjet": "pvp", "vigilante": "pvp", "akula": "pvp", "buzzard": "pvp", "hydra": "pvp", "raiju": "pvp",
    # sell vehicles
    "insurgent2": "sell", "speedo4": "sell", "mule4": "sell", "pounder2": "sell", "cuban800": "sell", "mule": "sell",
    "speedo": "sell", "pounder": "sell", "phantom3": "sell", "brickade": "sell", "tiptruck": "sell", "insurgent": "sell",
    # personal
    "adder": "personal", "zentorno": "personal", "elegy2": "personal", "sultanrs": "personal", "bati": "personal",
    "faggio": "personal", "blista": "personal", "sanchez": "personal", "dominator": "personal", "kuruma": "personal",
}
by = {v["Name"].lower(): v for v in json.load(open(src / "vehicles.json"))}
vehicles = {}
for n, role in WANT_VEHICLES.items():
    v = by[n]
    flying = v["Type"] in ("PLANE", "HELI") or n in ("oppressor2", "deluxo")
    vehicles[n] = dict(name=v["DisplayName"]["English"], role=role, vclass=v["Class"], vtype=v["Type"], flying=flying,
                       weapons=v.get("Weapons") or [], max_speed=round(v["MaxSpeed"], 1), seats=v["Seats"],
                       dlc=v["DlcName"], manufacturer=(v.get("ManufacturerDisplayName") or {}).get("English"))

WANT_WEAPONS = ["WEAPON_CARBINERIFLE_MK2", "WEAPON_HEAVYSNIPER_MK2", "WEAPON_STICKYBOMB", "WEAPON_HOMINGLAUNCHER",
                "WEAPON_RAYPISTOL", "WEAPON_SPECIALCARBINE_MK2", "WEAPON_RPG", "WEAPON_RAILGUN", "WEAPON_PUMPSHOTGUN_MK2",
                "WEAPON_MICROSMG", "WEAPON_PISTOL_MK2", "WEAPON_KNIFE"]
wby = {w["Name"]: w for w in json.load(open(src / "weapons.json"))}
weapons = {}
for n in WANT_WEAPONS:
    w = wby[n]
    weapons[n.removeprefix("WEAPON_").lower()] = dict(id=n, name=w["TranslatedLabel"]["English"], category=w["Category"],
                                                       damage=w.get("DamageType"), dlc=w["DlcName"])

out = dict(source="https://github.com/DurtyFree/gta-v-data-dumps", zones=zones, vehicles=vehicles, weapons=weapons)
dst.parent.mkdir(parents=True, exist_ok=True)
json.dump(out, open(dst, "w"), indent=1)
print(f"{len(zones)} zones, {len(vehicles)} vehicles, {len(weapons)} weapons -> {dst}", file=sys.stderr)
