"""Static tables: the map, businesses, vehicles and weapons the lobby sim draws from."""

# Freemode areas. Flat list; distance is "same area or not", which is all the sim needs.
AREAS = [
    "vinewood", "rockford_hills", "del_perro", "vespucci", "los_santos_intl", "downtown", "mirror_park",
    "la_mesa", "cypress_flats", "elysian_island", "terminal", "davis", "strawberry", "chumash",
    "vinewood_hills", "sandy_shores", "grapeseed", "paleto_bay", "mount_chiliad", "fort_zancudo",
]
CITY = AREAS[:13]
COUNTY = AREAS[13:]

# Business types a grinder can own: where the product accrues, how fast, what it sells for,
# and what the sell mission looks like (vehicle, number of drops, mission clock in ticks).
BUSINESSES = {
    "bunker":            dict(areas=COUNTY, cap=1_050_000, accrual=12_000, product="weapons",       vehicle="insurgent",     drops=(1, 3), clock=48),
    "nightclub":         dict(areas=CITY,   cap=1_690_000, accrual=9_000,  product="nightclub_goods", vehicle="speedo_custom", drops=(1, 2), clock=40),
    "acid_lab":          dict(areas=COUNTY, cap=335_000,   accrual=6_000,  product="acid",          vehicle="mule",          drops=(1, 1), clock=30),
    "coke_lockup":       dict(areas=CITY,   cap=420_000,   accrual=7_000,  product="coke",          vehicle="post_op_van",   drops=(2, 4), clock=44),
    "meth_lab":          dict(areas=COUNTY, cap=357_000,   accrual=6_000,  product="meth",          vehicle="post_op_van",   drops=(2, 4), clock=44),
    "counterfeit_cash":  dict(areas=CITY,   cap=294_000,   accrual=5_000,  product="cash",          vehicle="post_op_van",   drops=(2, 4), clock=44),
    "hangar":            dict(areas=COUNTY, cap=1_200_000, accrual=8_000,  product="air_cargo",     vehicle="cuban_800",     drops=(1, 2), clock=40),
    "crate_warehouse":   dict(areas=CITY,   cap=2_220_000, accrual=10_000, product="special_cargo", vehicle="pounder",       drops=(2, 5), clock=50),
    "vehicle_warehouse": dict(areas=CITY,   cap=800_000,   accrual=8_000,  product="export_cars",   vehicle="export_car",    drops=(1, 1), clock=36),
}

# How hard a sell vehicle is to kill, as the per-tick chance a griefer on top of it finishes the job.
VEHICLE_KILL_CHANCE = {
    "insurgent": 0.18, "speedo_custom": 0.30, "mule": 0.35, "post_op_van": 0.45, "cuban_800": 0.40,
    "pounder": 0.33, "export_car": 0.50,
}

# What a griefer or tryhard shows up in. Flying means it closes distance in one tick.
PVP_VEHICLES = {
    "oppressor_mk2": dict(flying=True,  menace=3, chance=0.55),
    "deluxo":        dict(flying=True,  menace=2, chance=0.30),
    "toreador":      dict(flying=False, menace=2, chance=0.25),
    "sparrow":       dict(flying=True,  menace=1, chance=0.10),
    "lazer":         dict(flying=True,  menace=3, chance=0.35),
    "nightshark":    dict(flying=False, menace=1, chance=0.08),
    "kuruma":        dict(flying=False, menace=0, chance=0.04),
}

WEAPONS = {
    "oppressor_mk2": "mk2_missiles", "deluxo": "deluxo_missiles", "toreador": "toreador_missiles",
    "sparrow": "sparrow_missiles", "lazer": "explosive_cannon", "nightshark": "carbine_mk2", "kuruma": "carbine_mk2",
}
ON_FOOT_WEAPONS = ["carbine_mk2", "heavy_sniper_mk2", "sticky_bomb", "homing_launcher", "up_n_atomizer"]

WANTED_REASONS = ["shot_cops", "stole_vehicle", "killed_npcs", "destroyed_vehicles", "robbed_store"]

ORG_NAMES = ["Chumash Imports", "Vespucci Holdings", "Paleto Logistics", "Mirror Park MC", "Lost Cause MC",
             "Grapeseed Growers", "Elysian Freight", "Del Perro Capital", "Zancudo Exports", "Davis Street MC",
             "Rockford Equity", "Strawberry Syndicate", "Chiliad Movers", "LSIA Cargo", "La Mesa Metalworks"]

# Gamertag parts. Combined deterministically per player.
TAG_LEFT = ["xX", "Lester", "Ghost", "Trevor", "Sniper", "Nova", "Big", "Lil", "Dark", "Pink", "Loud", "Quiet",
            "Shark", "Chop", "Vinewood", "Paleto", "Sandy", "Cayo", "Griefed", "Passive", "Turbo", "Salty", "Humble",
            "Cargo", "Bunker", "Nightclub", "Oppressor", "Kosatka", "Zancudo", "Casino"]
TAG_RIGHT = ["Slayer", "Fan2013", "Rider", "Mom", "Dad", "Enjoyer", "Hater", "King", "Queen", "Gremlin", "Wizard",
             "Pilot", "Mechanic", "Grinder", "Hopper", "Menace", "Civilian", "Tourist", "Lord", "Andy", "Chad",
             "Raccoon", "Pigeon", "Seagull", "Duck", "Goose", "Otter", "Bear"]
TAG_SUFFIX = ["", "", "", "_", "Xx", "420", "69", "1999", "2004", "_TTV", "_YT", "ok", "sr", "jr"]
