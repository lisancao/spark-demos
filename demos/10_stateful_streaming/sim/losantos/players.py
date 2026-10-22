"""Player roster: a pool of players with a public profile and a hidden archetype.

The public profile (rank, career K/D, hours, kills, deaths) is what a studio holds before a session
and what the streaming side gets as initial state. The archetype drives behaviour inside the sim and
is never emitted; it is exported separately as ground truth so the streaming scores can be graded.
"""

import random
from dataclasses import dataclass, field

from losantos import world

ARCHETYPES = ["grinder", "griefer", "tryhard", "tourist"]
ARCHETYPE_MIX = {"grinder": 0.40, "griefer": 0.08, "tryhard": 0.12, "tourist": 0.40}

# Profile ranges per archetype. Deliberately overlapping: the point of the streaming score is that
# the profile alone does not tell you who is going to ruin your sell.
PROFILE = {
    "grinder": dict(rank=(60, 420),  kd=(0.5, 1.4), hours=(300, 2500)),
    "griefer": dict(rank=(90, 650),  kd=(1.2, 4.5), hours=(400, 4000)),
    "tryhard": dict(rank=(180, 1100), kd=(1.8, 6.0), hours=(900, 6000)),
    "tourist": dict(rank=(1, 60),    kd=(0.2, 1.0), hours=(2, 200)),
}


@dataclass
class Business:
    name: str          # "<owner>_bunker"
    kind: str
    area: str
    stock: int = 0

    @property
    def spec(self) -> dict:
        return world.BUSINESSES[self.kind]


@dataclass
class Player:
    player_id: str
    gamertag: str
    archetype: str
    rank: int
    kd: float
    hours: int
    career_kills: int
    career_deaths: int
    businesses: list[Business] = field(default_factory=list)
    preferred_vehicle: str | None = None   # griefers and tryhards
    personal_vehicle: str = "blista"

    # session state (reset on join)
    lobby: str | None = None
    area: str | None = None
    vehicle: str | None = None
    passive: bool = False
    passive_until: int = -1
    wanted_stars: int = 0
    wanted_since: int = -1
    streak: int = 0
    bounty: int = 0                  # amount on this player's head
    bounty_placer: str | None = None
    org: str | None = None            # org id this player belongs to
    sell: object = None               # active Sell (grinders)
    rejoin_at: int = -1
    griefed_ticks: list[int] = field(default_factory=list)
    deaths_recent: list[int] = field(default_factory=list)
    idle_hunt_ticks: int = 0
    busy_until: int = -1
    joined_at: int = -1
    pending_leave: str | None = None
    last_hop: str = ""

    @property
    def in_session(self) -> bool:
        return self.lobby is not None

    def public_profile(self) -> dict:
        return dict(agent_id=self.player_id, agent_name=self.gamertag, rank=self.rank, kd=self.kd, hours=self.hours,
                    career_kills=self.career_kills, career_deaths=self.career_deaths,
                    businesses=len(self.businesses))

    def truth(self) -> dict:
        return dict(agent_id=self.player_id, archetype=self.archetype, preferred_vehicle=self.preferred_vehicle)


def make_roster(rng: random.Random, n: int) -> list[Player]:
    players = []
    used = set()
    for i in range(n):
        archetype = rng.choices(ARCHETYPES, weights=[ARCHETYPE_MIX[a] for a in ARCHETYPES])[0]
        spec = PROFILE[archetype]
        rank = rng.randint(*spec["rank"])
        kd = round(rng.uniform(*spec["kd"]), 2)
        hours = rng.randint(*spec["hours"])
        deaths = max(1, int(hours * rng.uniform(1.5, 4.0)))
        kills = int(deaths * kd)
        while True:
            tag = f"{rng.choice(world.TAG_LEFT)}{rng.choice(world.TAG_RIGHT)}{rng.choice(world.TAG_SUFFIX)}"
            if tag not in used:
                used.add(tag)
                break
        pid = f"p{i:03d}"
        p = Player(pid, tag, archetype, rank, kd, hours, kills, deaths)
        if archetype == "grinder":
            kinds = rng.sample(list(world.BUSINESSES), k=rng.randint(1, 3))
            for kind in kinds:
                spec_b = world.BUSINESSES[kind]
                area = rng.choice(spec_b["areas"])
                p.businesses.append(Business(f"{pid}_{kind}", kind, area, stock=int(spec_b["cap"] * rng.uniform(0.2, 0.7))))
        elif archetype == "griefer":
            p.preferred_vehicle = rng.choices(["oppressor2", "deluxo", "lazer", "toreador", "seasparrow2"], weights=[0.6, 0.12, 0.08, 0.1, 0.1])[0]
        elif archetype == "tryhard":
            p.preferred_vehicle = rng.choices(["oppressor2", "toreador", "seasparrow2", "nightshark", "kuruma2", "vigilante"], weights=[0.3, 0.25, 0.15, 0.12, 0.08, 0.1])[0]
        p.personal_vehicle = rng.choice([k for k, v in world.VEHICLES.items() if v["role"] == "personal"])
        players.append(p)
    return players
