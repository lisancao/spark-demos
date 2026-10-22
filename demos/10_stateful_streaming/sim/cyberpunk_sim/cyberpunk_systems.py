"""Night City systems — economy, crime, territory, cyberpsychosis.

These run every tick alongside the base simulation engine, generating
cyberpunk-specific events for the event stream.
"""

import random
from typing import Any

from cyberpunk_sim.event_schema import (
    build_economy_event,
    build_crime_event,
    build_faction_event,
    build_world_event,
    build_agent_event,
    sim_time,
)


# ---------------------------------------------------------------------------
# Economy system
# ---------------------------------------------------------------------------

class EconomyState:
    """Tracks supply/demand, prices, and transaction flows."""

    def __init__(self, economy_data: dict, rng: random.Random):
        self.rng = rng
        self.config = economy_data
        self.base_prices = economy_data.get("base_prices", {})
        self.district_mods = economy_data.get("district_price_modifiers", {})
        self.supply = {}  # category → current_supply
        self.faction_wallets = {}  # faction_id → eddies

        # Initialize supply levels
        for cat, cfg in economy_data.get("supply_categories", {}).items():
            self.supply[cat] = cfg.get("base_supply", 100)

        # Initialize faction wallets
        for faction_type, income in economy_data.get("faction_income", {}).items():
            self.faction_wallets[faction_type] = income * 10  # start with 10 days

    def tick(self, tick: int, data: dict) -> list[dict[str, Any]]:
        """Advance economy by one tick. Returns list of economy events."""
        events = []
        time_info = sim_time(tick)

        # Supply restock — once per day (at tick 0 of each day)
        if tick > 0 and time_info["sim_phase_tick"] == 0 and time_info["sim_time_phase"] == "dawn":
            events.extend(self._restock_supplies(tick))

        # Price fluctuations — every 10 ticks
        if tick % 10 == 0:
            events.extend(self._price_fluctuation(tick))

        # Trade route shipments — random chance per tick
        if self.rng.random() < 0.02:  # ~2% per tick
            events.extend(self._supply_shipment(tick, data))

        return events

    def process_transaction(self, tick: int, buyer_id: str, seller_id: str,
                            item_name: str, price: float,
                            location_id: str) -> dict[str, Any]:
        """Record a transaction event."""
        return build_economy_event(
            "economy.transaction", tick, location_id,
            buyer_id=buyer_id, seller_id=seller_id,
            item=item_name, price=price, currency="eddies",
        )

    def get_price(self, item_category: str, item_key: str,
                  location_type: str = "") -> float:
        """Get current price with location modifier."""
        cat_prices = self.base_prices.get(item_category, {})
        base = cat_prices.get(item_key, 100)
        mod = self.district_mods.get(location_type, 1.0)
        return round(base * mod, 2)

    def _restock_supplies(self, tick: int) -> list[dict]:
        events = []
        for cat, cfg in self.config.get("supply_categories", {}).items():
            restock = cfg.get("restock_rate", 10)
            self.supply[cat] = min(
                self.supply[cat] + restock,
                cfg.get("base_supply", 100) * 2,
            )
        return events

    def _price_fluctuation(self, tick: int) -> list[dict]:
        events = []
        for cat, cfg in self.config.get("supply_categories", {}).items():
            volatility = cfg.get("volatility", 0.1)
            delta = self.rng.uniform(-volatility, volatility)
            if abs(delta) > volatility * 0.5:
                events.append(build_economy_event(
                    "economy.price_change", tick, "",
                    category=cat, delta=round(delta, 4),
                    new_supply=self.supply.get(cat, 0),
                ))
        return events

    def _supply_shipment(self, tick: int, data: dict) -> list[dict]:
        events = []
        routes = self.config.get("trade_routes", [])
        if not routes:
            return events
        route = self.rng.choice(routes)
        if self.rng.random() < route.get("reliability", 0.5):
            goods = route.get("goods", [])
            if goods:
                good = self.rng.choice(goods)
                events.append(build_economy_event(
                    "economy.supply_shipment", tick,
                    route.get("to", ""),
                    from_location=route.get("from", ""),
                    goods_type=good,
                    reliability=route.get("reliability", 0.5),
                ))
        return events


# ---------------------------------------------------------------------------
# Crime system
# ---------------------------------------------------------------------------

# Crime probability by time phase
CRIME_PHASE_WEIGHTS = {
    "dawn": 0.3,
    "morning": 0.2,
    "afternoon": 0.3,
    "evening": 0.6,
    "night": 0.9,
    "late_night": 1.0,
}

# NCPD response time by location type (lower = faster)
NCPD_RESPONSE = {
    "corpo_tower": 2,
    "ncpd_precinct": 1,
    "megabuilding": 5,
    "nightclub": 6,
    "food_stall": 7,
    "gang_hideout": 10,
    "black_market": 12,
    "combat_zone": 20,
    "shanty_market": 15,
    "nomad_camp": 30,  # effectively never
    "netrunner_den": 25,
    "chop_shop": 18,
}

CRIME_TYPES = [
    {"type": "robbery", "severity": 2, "tags": ["commerce", "criminal"]},
    {"type": "assault", "severity": 3, "tags": ["dangerous"]},
    {"type": "data_theft", "severity": 4, "tags": ["criminal"]},
    {"type": "murder", "severity": 5, "tags": ["dangerous", "criminal"]},
    {"type": "cyberware_theft", "severity": 3, "tags": ["commerce", "criminal"]},
    {"type": "drug_deal", "severity": 1, "tags": ["criminal"]},
    {"type": "extortion", "severity": 2, "tags": ["criminal", "social"]},
    {"type": "illegal_braindance", "severity": 1, "tags": ["social"]},
    {"type": "vehicle_theft", "severity": 2, "tags": []},
    {"type": "corp_espionage", "severity": 4, "tags": ["authority"]},
]


def generate_crimes(tick: int, data: dict, rng: random.Random) -> list[dict[str, Any]]:
    """Generate crime events based on district + time phase."""
    events = []
    time_info = sim_time(tick)
    phase = time_info["sim_time_phase"]
    crime_chance = CRIME_PHASE_WEIGHTS.get(phase, 0.3)

    # Check each location with dangerous/criminal tags
    for loc in data.get("locations", []):
        loc_tags = set(loc.get("tags", []))
        if not (loc_tags & {"dangerous", "criminal"}):
            continue

        # Base chance scaled by tag count
        loc_chance = crime_chance * 0.03 * len(loc_tags & {"dangerous", "criminal"})
        if rng.random() > loc_chance:
            continue

        # Pick a crime type that matches location tags
        matching = [c for c in CRIME_TYPES
                    if not c["tags"] or (set(c["tags"]) & loc_tags)]
        if not matching:
            matching = CRIME_TYPES
        crime = rng.choice(matching)

        # Extract district from location ID prefix (e.g., "gang_hideout_28" → "gang_hideout")
        district = "_".join(loc["id"].rsplit("_", 1)[:-1]) or loc["id"]
        events.append(build_crime_event(
            "crime.committed", tick, loc["id"], district,
            crime_type=crime["type"],
            severity=crime["severity"],
        ))

        # NCPD response
        response_time = NCPD_RESPONSE.get(district, 15)
        if crime["severity"] >= 3 or rng.random() < 0.5:
            events.append(build_crime_event(
                "crime.ncpd_response", tick, loc["id"], district,
                crime_type=crime["type"],
                response_ticks=response_time,
                dispatched=response_time < 20,
            ))

    return events


# ---------------------------------------------------------------------------
# Territory system
# ---------------------------------------------------------------------------

def advance_territory(tick: int, data: dict, sim_state: dict,
                      rng: random.Random) -> list[dict[str, Any]]:
    """Update faction influence scores per location. Returns territory events."""
    events = []
    territories = sim_state.get("faction_territories", {})

    # Influence decay and drift — every 20 ticks
    if tick % 20 != 0:
        return events

    factions = data.get("factions", [])
    locations = data.get("locations", [])

    for loc in locations:
        loc_id = loc["id"]
        if loc_id not in territories:
            territories[loc_id] = {}

        loc_control = territories[loc_id]

        # Each faction with presence drifts
        for faction in factions:
            fid = faction["id"]
            current = loc_control.get(fid, 0.0)

            # Count faction NPCs at this location
            npc_count = sum(
                1 for npc in data.get("npcs", [])
                if npc.get("location") == loc_id and npc.get("faction") == fid
            )

            # Drift: more NPCs = more influence
            if npc_count > 0:
                gain = min(0.05 * npc_count, 0.2)
                new_val = min(current + gain, 1.0)
            else:
                # Slow decay without presence
                new_val = max(current - 0.02, 0.0)

            if abs(new_val - current) > 0.01:
                loc_control[fid] = round(new_val, 3)

                # Emit territory events on significant changes
                if new_val >= 0.6 and current < 0.6:
                    events.append(build_faction_event(
                        "faction.territory_gained", tick, fid,
                        location_id=loc_id,
                        influence=new_val,
                    ))
                elif new_val < 0.3 and current >= 0.3:
                    events.append(build_faction_event(
                        "faction.territory_lost", tick, fid,
                        location_id=loc_id,
                        influence=new_val,
                    ))

    return events


# ---------------------------------------------------------------------------
# Cyberpsychosis system
# ---------------------------------------------------------------------------

PSYCHOSIS_THRESHOLD = 60  # chrome_score above which risk begins
PSYCHOSIS_CRISIS_THRESHOLD = 80


def advance_cyberpsychosis(tick: int, data: dict,
                            rng: random.Random) -> list[dict[str, Any]]:
    """Check for cyberpsychosis degradation and crisis events."""
    events = []

    # Check every 25 ticks
    if tick % 25 != 0:
        return events

    for npc in data.get("npcs", []):
        chrome = npc.get("chrome_score", 0)
        if chrome < PSYCHOSIS_THRESHOLD:
            continue

        # Degradation: chrome score slowly increases from use
        if rng.random() < 0.1:
            npc["chrome_score"] = chrome + 1

        # Crisis check
        if chrome >= PSYCHOSIS_CRISIS_THRESHOLD and rng.random() < 0.05:
            events.append(build_world_event(
                "world.cyberpsychosis", tick,
                agent_id=npc["id"],
                agent_name=npc["name"],
                location_id=npc.get("location", ""),
                chrome_score=chrome,
                severity="crisis",
            ))
            # Mark NPC as hostile to everyone
            npc["default_disposition"] = "hostile"
            if "cyberpsycho" not in npc.get("tags", []):
                npc.setdefault("tags", []).append("cyberpsycho")

        elif chrome >= PSYCHOSIS_THRESHOLD and rng.random() < 0.15:
            events.append(build_world_event(
                "world.cyberpsychosis", tick,
                agent_id=npc["id"],
                agent_name=npc["name"],
                location_id=npc.get("location", ""),
                chrome_score=chrome,
                severity="warning",
            ))

    return events


# ---------------------------------------------------------------------------
# Weather system
# ---------------------------------------------------------------------------

WEATHER_TYPES = [
    {"type": "acid_rain", "weight": 3, "effects": {"outdoor_danger": 1}},
    {"type": "smog_heavy", "weight": 4, "effects": {"visibility": -1}},
    {"type": "clear", "weight": 5, "effects": {}},
    {"type": "sandstorm", "weight": 1, "effects": {"outdoor_danger": 2, "visibility": -2}},
    {"type": "neon_fog", "weight": 3, "effects": {"visibility": -1}},
    {"type": "heatwave", "weight": 2, "effects": {"fatigue": 1}},
]


def generate_weather(tick: int, rng: random.Random) -> dict[str, Any] | None:
    """Generate weather event — changes once per day phase."""
    time_info = sim_time(tick)
    if time_info["sim_phase_tick"] != 0:
        return None

    total_weight = sum(w["weight"] for w in WEATHER_TYPES)
    r = rng.uniform(0, total_weight)
    cumulative = 0
    for weather in WEATHER_TYPES:
        cumulative += weather["weight"]
        if r <= cumulative:
            return build_world_event(
                "world.weather", tick,
                weather_type=weather["type"],
                effects=weather["effects"],
            )
    return None


# ---------------------------------------------------------------------------
# Combined system tick
# ---------------------------------------------------------------------------

class CyberpunkSystems:
    """Aggregator for all cyberpunk-specific subsystems."""

    def __init__(self, economy_data: dict, rng: random.Random):
        self.economy = EconomyState(economy_data, rng)
        self.rng = rng

    def tick(self, tick: int, data: dict,
             sim_state: dict) -> list[dict[str, Any]]:
        """Run all cyberpunk systems for one tick. Returns all events."""
        events = []
        events.extend(self.economy.tick(tick, data))
        events.extend(generate_crimes(tick, data, self.rng))
        events.extend(advance_territory(tick, data, sim_state, self.rng))
        events.extend(advance_cyberpsychosis(tick, data, self.rng))

        weather = generate_weather(tick, self.rng)
        if weather:
            events.append(weather)

        return events
