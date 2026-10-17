"""The lobby engine: public sessions full of players who grind, grief, hunt and wander.

Every tick each player in a session acts according to its hidden archetype. The engine keeps the
world consistent (who is in which lobby, who is passive, which sell is in flight, who is wanted,
who has a bounty) and emits one event per thing that happens. `check.py` re-derives that world
from the events alone and fails if anything does not line up.
"""

import math
import random
from dataclasses import dataclass, field

from cyberpunk_sim.event_schema import build_event
from losantos import world
from losantos.players import Player, make_roster

SNAPSHOT_EVERY = 25
ACCRUAL_EVERY = 25
PASSIVE_TICKS = 30
RECENT_WINDOW = 40


@dataclass
class Org:
    org_id: str
    name: str
    kind: str          # ceo | mc
    leader: str
    lobby: str
    members: set = field(default_factory=set)


@dataclass
class Sell:
    mission_id: str
    seller: str
    org: str
    business: str
    product: str
    value: int
    drops: int
    route: list
    vehicle: str
    started: int
    deadline: int
    drop_idx: int = 0
    delivered: int = 0

    @property
    def per_drop(self) -> int:
        return self.value // self.drops


@dataclass
class Lobby:
    lobby_id: str
    players: set = field(default_factory=set)
    sells: dict = field(default_factory=dict)      # mission_id -> Sell
    orgs: dict = field(default_factory=dict)       # org_id -> Org
    kills: list = field(default_factory=list)      # (tick, victim_activity)
    destroyed: list = field(default_factory=list)  # ticks


class LobbySim:
    def __init__(self, seed: int, n_players: int, n_lobbies: int, capacity: int, emit, join_rate: float = 0.08):
        self.rng = random.Random(seed)
        self.players: dict[str, Player] = {p.player_id: p for p in make_roster(self.rng, n_players)}
        self.lobbies: dict[str, Lobby] = {f"ls_public_{i + 1:02d}": Lobby(f"ls_public_{i + 1:02d}") for i in range(n_lobbies)}
        self.capacity = capacity
        self.emit = emit
        self.join_rate = join_rate
        self.tick = 0
        self._seq = 0

    # ---- helpers -------------------------------------------------------------------------------

    def _id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq:06d}"

    def ev(self, event_type: str, p: Player | None = None, **fields):
        base = {}
        if p is not None:
            base = dict(agent_id=p.player_id, agent_name=p.gamertag, lobby_id=p.lobby, location_id=p.area)
        base.update(fields)
        self.emit(build_event(event_type, self.tick, **base))

    def lobby_of(self, p: Player) -> Lobby:
        return self.lobbies[p.lobby]

    def in_lobby(self, lobby: Lobby):
        return [self.players[pid] for pid in lobby.players]

    def flying(self, p: Player) -> bool:
        return world.is_flying(p.vehicle)

    # ---- session membership --------------------------------------------------------------------

    def join(self, p: Player, prefer_quiet: bool = False):
        open_lobbies = [l for l in self.lobbies.values() if len(l.players) < self.capacity]
        if not open_lobbies:
            p.rejoin_at = self.tick + self.rng.randint(5, 15)
            return
        if prefer_quiet:
            lobby = min(open_lobbies, key=lambda l: (len(l.players), self.rng.random()))
        else:
            lobby = self.rng.choice(open_lobbies)
        p.lobby = lobby.lobby_id
        p.area = self.rng.choice(world.CITY if self.rng.random() < 0.8 else world.COUNTY)
        p.vehicle = None
        p.passive = False
        p.passive_until = -1
        p.wanted_stars = 0
        p.streak = 0
        p.bounty = 0
        p.bounty_placer = None
        p.org = None
        p.sell = None
        p.rejoin_at = -1
        p.griefed_ticks = []
        p.deaths_recent = []
        p.idle_hunt_ticks = 0
        p.busy_until = -1
        p.joined_at = self.tick
        lobby.players.add(p.player_id)
        self.ev("session.join", p, rank=p.rank, population=len(lobby.players))

    def leave(self, p: Player, reason: str):
        lobby = self.lobby_of(p)
        if p.sell is not None:
            s = p.sell
            self.ev("sell.abandoned", p, mission_id=s.mission_id, faction_id=s.org, value_lost=s.value - s.delivered,
                    value_delivered=s.delivered, elapsed_ticks=self.tick - s.started)
            del lobby.sells[s.mission_id]
            p.sell = None
        if p.bounty:
            self.ev("player.bounty_expired", p, amount=p.bounty, placed_by=p.bounty_placer)
            p.bounty = 0
            p.bounty_placer = None
        if p.wanted_stars:
            self.ev("wanted.cleared", p, stars=p.wanted_stars, how="left_session", ticks_wanted=self.tick - p.wanted_since)
            p.wanted_stars = 0
        if p.org:
            org = lobby.orgs[p.org]
            if org.leader == p.player_id:
                for mid in list(org.members):
                    m = self.players[mid]
                    self.ev("org.member_left", m, faction_id=org.org_id, reason="disbanded")
                    m.org = None
                org.members.clear()
                self.ev("org.disbanded", p, faction_id=org.org_id, org_name=org.name, reason=reason)
                del lobby.orgs[org.org_id]
            else:
                org.members.discard(p.player_id)
                self.ev("org.member_left", p, faction_id=org.org_id, reason=reason)
            p.org = None
        if p.passive:
            self.ev("session.passive_off", p, reason="left_session")
            p.passive = False
        self.ev("session.leave", p, reason=reason, session_ticks=self.tick - p.joined_at, population=len(lobby.players) - 1)
        lobby.players.discard(p.player_id)
        p.lobby = None
        p.area = None
        p.vehicle = None
        if reason == "lobby_hop":
            p.rejoin_at = self.tick + self.rng.randint(3, 8)
        elif reason == "rage_quit":
            p.rejoin_at = self.tick + self.rng.randint(60, 200)
        else:
            p.rejoin_at = self.tick + self.rng.randint(20, 120)
        p.last_hop = reason

    # ---- passive mode ----------------------------------------------------------------------------

    def passive_on(self, p: Player, reason: str):
        if p.passive or p.sell is not None:
            return
        p.passive = True
        p.passive_until = self.tick + PASSIVE_TICKS
        self.ev("session.passive_on", p, reason=reason)

    def passive_off(self, p: Player, reason: str):
        if not p.passive:
            return
        p.passive = False
        p.passive_until = -1
        self.ev("session.passive_off", p, reason=reason)

    # ---- violence --------------------------------------------------------------------------------

    def move(self, p: Player, area: str, vehicle: str | None = None):
        """Head for `area`: flying vehicles get there this tick, ground vehicles get as far as their top speed allows."""
        if area == p.area:
            return
        v = vehicle or p.vehicle
        nxt = world.step_toward(p.area, area, v)
        if nxt == p.area:
            return
        prev = p.area
        p.area = nxt
        self.ev("player.move", p, from_location=prev, vehicle=v, heading=area,
                distance_m=round(world.distance(prev, nxt)))

    def spawn_vehicle(self, p: Player, vehicle: str):
        p.vehicle = vehicle
        self.ev("player.vehicle_spawned", p, vehicle=vehicle)

    def kill(self, attacker: Player, victim: Player, activity: str):
        assert attacker.lobby == victim.lobby and not victim.passive and attacker is not victim
        lobby = self.lobby_of(attacker)
        attacker.streak += 1
        weapon = world.vehicle_weapon(attacker.vehicle) or self.rng.choice(world.ON_FOOT_WEAPONS)
        self.ev("combat.kill", attacker, target_id=victim.player_id, target_name=victim.gamertag, weapon=weapon,
                attacker_vehicle=attacker.vehicle, victim_activity=activity, victim_vehicle=victim.vehicle,
                kill_streak=attacker.streak, location_id=victim.area)
        lobby.kills.append((self.tick, activity))
        attacker.career_kills += 1
        victim.career_deaths += 1
        victim.streak = 0
        victim.deaths_recent.append(self.tick)
        if victim.bounty:
            self.ev("player.bounty_claimed", attacker, target_id=victim.player_id, amount=victim.bounty, placed_by=victim.bounty_placer)
            victim.bounty = 0
            victim.bounty_placer = None
        if victim.wanted_stars:
            self.ev("wanted.cleared", victim, stars=victim.wanted_stars, how="died", ticks_wanted=self.tick - victim.wanted_since)
            victim.wanted_stars = 0
        if victim.sell is not None:
            s = victim.sell
            self.ev("sell.destroyed", victim, mission_id=s.mission_id, faction_id=s.org, business=s.business,
                    value_lost=s.value - s.delivered, value_delivered=s.delivered, destroyed_by=attacker.player_id,
                    elapsed_ticks=self.tick - s.started)
            del lobby.sells[s.mission_id]
            victim.sell = None
            victim.griefed_ticks.append(self.tick)
            lobby.destroyed.append(self.tick)
        victim.vehicle = None if victim.archetype in ("grinder", "tourist") else victim.vehicle
        # the law notices some of it
        if not attacker.wanted_stars and self.rng.random() < 0.25:
            self.wanted_gain(attacker, self.rng.randint(2, 3), self.rng.choice(["shot_cops", "killed_npcs", "destroyed_vehicles"]))
        self.after_death(victim, attacker, activity)

    def after_death(self, victim: Player, attacker: Player, activity: str):
        r = self.rng.random()
        if victim.archetype == "grinder":
            if activity == "selling":
                if not attacker.bounty and r < 0.6:
                    self.place_bounty(victim, attacker)
                if self.rng.random() < 0.5:
                    victim.busy_until = self.tick + 1   # leaves next tick
                    victim.pending_leave = "lobby_hop"
                else:
                    self.passive_on(victim, "griefed")
            elif r < 0.3:
                self.passive_on(victim, "killed")
        elif victim.archetype == "tourist":
            recent = [t for t in victim.deaths_recent if self.tick - t <= RECENT_WINDOW]
            if len(recent) >= 2 and r < 0.7:
                victim.pending_leave = "rage_quit"
                victim.busy_until = self.tick + 1
            elif r < 0.5:
                self.passive_on(victim, "killed")
            elif not attacker.bounty and r < 0.65:
                self.place_bounty(victim, attacker)
        elif victim.archetype in ("tryhard", "griefer"):
            if not attacker.bounty and r < 0.15:
                self.place_bounty(victim, attacker)

    def place_bounty(self, placer: Player, target: Player):
        amount = self.rng.choice([1000, 2000, 5000, 7500, 9000, 10000])
        target.bounty = amount
        target.bounty_placer = placer.player_id
        self.ev("player.bounty_placed", placer, target_id=target.player_id, target_name=target.gamertag, amount=amount)

    def wanted_gain(self, p: Player, stars: int, reason: str):
        p.wanted_stars = stars
        p.wanted_since = self.tick
        self.ev("wanted.gained", p, stars=stars, reason=reason)

    def resolve_wanted(self, p: Player):
        r = self.rng.random()
        esc = 0.2 if p.archetype in ("griefer", "tryhard") else 0.1
        if p.wanted_stars < 5 and r < esc:
            prev = p.wanted_stars
            p.wanted_stars += 1
            self.ev("wanted.escalated", p, stars=p.wanted_stars, from_stars=prev)
            return
        evade = 0.3 if self.flying(p) else 0.15
        if r < esc + evade:
            how = "evaded"
        elif p.rank >= 40 and r < esc + evade + 0.08:
            how = "lester"
        elif p.archetype == "tourist" and r < esc + evade + 0.08 + 0.03 * p.wanted_stars:
            how = "arrested"
        else:
            return
        self.ev("wanted.cleared", p, stars=p.wanted_stars, how=how, ticks_wanted=self.tick - p.wanted_since)
        p.wanted_stars = 0

    # ---- business ----------------------------------------------------------------------------------

    def register_org(self, p: Player):
        lobby = self.lobby_of(p)
        kinds = {b.kind for b in p.businesses}
        kind = "ceo" if kinds & {"crate_warehouse", "vehicle_warehouse", "hangar", "bunker", "nightclub"} else "mc"
        org = Org(self._id(f"org_{p.player_id}"), self.rng.choice(world.ORG_NAMES), kind, p.player_id, p.lobby)
        lobby.orgs[org.org_id] = org
        p.org = org.org_id
        # restate the stock on every registration: product persists across sessions, and a consumer that
        # starts mid-stream needs a baseline before it can account for sells and supply runs
        self.ev("org.registered", p, faction_id=org.org_id, org_name=org.name, org_type=kind,
                businesses=[dict(business=b.name, business_type=b.kind, stock_value=b.stock, location_id=b.area) for b in p.businesses])

    def start_sell(self, p: Player, b):
        spec = b.spec
        lobby = self.lobby_of(p)
        self.passive_off(p, "sell_started")
        drops = self.rng.randint(*spec["drops"])
        # drops are elsewhere on the map; a sell mission does not send you next door
        route = self.rng.sample([a for a in world.AREAS if 1500 < world.distance(a, p.area) < 6000], k=drops)
        # the mission clock is the sim's: enough ticks to drive the route at the sell vehicle's top speed, plus slack
        legs = [p.area] + route
        travel = sum(math.ceil(world.distance(a, b) / world.reach(spec["vehicle"])) for a, b in zip(legs, legs[1:]))
        s = Sell(self._id(f"sell_{p.player_id}"), p.player_id, p.org, b.name, spec["product"], b.stock, drops, route,
                 spec["vehicle"], self.tick, self.tick + 2 * travel + spec["clock"] // 2 + 2 * drops)
        p.sell = s
        lobby.sells[s.mission_id] = s
        b.stock = 0
        p.vehicle = s.vehicle
        self.ev("sell.started", p, mission_id=s.mission_id, faction_id=s.org, business=b.name, business_type=b.kind,
                product=s.product, value=s.value, drops=drops, sell_vehicle=s.vehicle, mission_clock=s.deadline - self.tick,
                population=len(lobby.players))

    def progress_sell(self, p: Player):
        s = p.sell
        lobby = self.lobby_of(p)
        if self.tick > s.deadline:
            self.ev("sell.expired", p, mission_id=s.mission_id, faction_id=s.org, business=s.business,
                    value_lost=s.value - s.delivered, value_delivered=s.delivered, elapsed_ticks=self.tick - s.started)
            del lobby.sells[s.mission_id]
            p.sell = None
            p.vehicle = None
            return
        hunters = [q for q in self.in_lobby(lobby) if q is not p and q.area == p.area and not q.passive
                   and q.archetype in ("griefer", "tryhard") and q.vehicle in world.PVP_VEHICLES]
        if hunters and self.rng.random() < 0.25:
            return   # hiding under a bridge; the clock keeps running
        target = s.route[s.drop_idx]
        if p.area != target:
            self.move(p, target, s.vehicle)
            return
        s.drop_idx += 1
        s.delivered += s.per_drop if s.drop_idx < s.drops else s.value - s.delivered
        self.ev("sell.delivery", p, mission_id=s.mission_id, faction_id=s.org, drop=s.drop_idx, drops=s.drops,
                value_delivered=s.delivered)
        if s.drop_idx >= s.drops:
            pop = len(lobby.players)
            bonus = int(s.value * min(0.5, 0.025 * max(0, pop - 1)))
            self.ev("sell.completed", p, mission_id=s.mission_id, faction_id=s.org, business=s.business, value=s.value,
                    value_delivered=s.delivered, bonus=bonus, population=pop, elapsed_ticks=self.tick - s.started)
            del lobby.sells[s.mission_id]
            p.sell = None
            p.vehicle = None

    def accrue(self, p: Player):
        for b in p.businesses:
            spec = b.spec
            added = min(spec["accrual"] * ACCRUAL_EVERY // 5, spec["cap"] - b.stock)
            if added <= 0:
                continue
            b.stock += added
            self.ev("org.business_stocked", p, faction_id=p.org, business=b.name, business_type=b.kind,
                    stock_value=b.stock, stock_added=added, location_id=b.area)

    # ---- archetype turns ---------------------------------------------------------------------------

    def act_grinder(self, p: Player):
        if p.org is None:
            self.register_org(p)
            return
        if p.sell is not None:
            self.progress_sell(p)
            return
        if p.busy_until > self.tick:
            return
        if p.passive:
            return
        ready = [b for b in p.businesses if b.stock >= 0.6 * b.spec["cap"]]
        low = [b for b in p.businesses if b.stock < 0.3 * b.spec["cap"]]
        r = self.rng.random()
        if ready and r < 0.15:
            self.start_sell(p, max(ready, key=lambda b: b.stock))
        elif low and r < 0.35:
            b = self.rng.choice(low)
            added = min(b.spec["accrual"] * 6, b.spec["cap"] - b.stock)
            b.stock += added
            self.move(p, b.area, p.personal_vehicle)
            self.ev("org.supply_run", p, faction_id=p.org, business=b.name, business_type=b.kind, stock_value=b.stock, stock_added=added)
            p.busy_until = self.tick + 2
        elif r < 0.55:
            self.move(p, self.rng.choice(world.AREAS), p.personal_vehicle)

    def act_griefer(self, p: Player):
        lobby = self.lobby_of(p)
        if p.vehicle not in world.PVP_VEHICLES:
            if self.rng.random() < 0.7:
                self.spawn_vehicle(p, p.preferred_vehicle)
            return
        # a sell blip is visible to the lobby after a few ticks; griefers go for the nearest one
        sells = [s for s in lobby.sells.values() if not self.players[s.seller].passive and self.tick - s.started >= 3]
        if sells:
            p.idle_hunt_ticks = 0
            s = min(sells, key=lambda s: (world.distance(p.area, self.players[s.seller].area), self.rng.random()))
            seller = self.players[s.seller]
            if seller.area != p.area:
                self.move(p, seller.area)
                return
            chance = world.VEHICLE_KILL_CHANCE[s.vehicle] * (0.3 if self.flying(p) else 0.18)
            if self.rng.random() < chance:
                self.kill(p, seller, "selling")
            return
        p.idle_hunt_ticks += 1
        prey = [q for q in self.in_lobby(lobby) if q is not p and q.area == p.area and not q.passive
                and q.archetype in ("tourist", "grinder")]
        r = self.rng.random()
        if prey and r < 0.1:
            q = self.rng.choice(prey)
            self.kill(p, q, "supply" if q.busy_until > self.tick else "freemode")
        elif r < 0.6:
            self.move(p, self.rng.choice(world.AREAS))
        elif p.idle_hunt_ticks > 40 and r < 0.7:
            self.leave(p, "lobby_hop")

    def act_tryhard(self, p: Player):
        lobby = self.lobby_of(p)
        if p.vehicle not in world.PVP_VEHICLES:
            if self.rng.random() < 0.6:
                self.spawn_vehicle(p, p.preferred_vehicle)
            return
        marks = [q for q in self.in_lobby(lobby) if q is not p and not q.passive and q.archetype in ("griefer", "tryhard")]
        if marks:
            q = max(marks, key=lambda m: (m.bounty > 0, m.streak, self.rng.random()))
            if q.area != p.area:
                self.move(p, q.area)
                return
            if self.rng.random() < 0.15:
                mine = world.PVP_KILL_CHANCE.get(p.vehicle, 0.05)
                theirs = world.PVP_KILL_CHANCE.get(q.vehicle, 0.05)
                win = (p.kd * (1 + mine)) / (p.kd * (1 + mine) + q.kd * (1 + theirs))
                if self.rng.random() < win:
                    self.kill(p, q, "pvp")
                else:
                    self.kill(q, p, "pvp")
            return
        prey = [q for q in self.in_lobby(lobby) if q is not p and q.area == p.area and not q.passive and q.archetype == "tourist"]
        r = self.rng.random()
        if prey and r < 0.08:
            self.kill(p, self.rng.choice(prey), "freemode")
        elif r < 0.5:
            self.move(p, self.rng.choice(world.AREAS))

    def act_tourist(self, p: Player):
        lobby = self.lobby_of(p)
        r = self.rng.random()
        if r < 0.35:
            self.move(p, self.rng.choice(world.AREAS), p.personal_vehicle if self.rng.random() < 0.7 else None)
        elif r < 0.38 and not p.wanted_stars and not p.passive:
            self.wanted_gain(p, 1, "stole_vehicle" if self.rng.random() < 0.8 else "robbed_store")
        elif r < 0.39:
            self.leave(p, "quit")
        elif r < 0.42 and p.org is None:
            open_orgs = [o for o in lobby.orgs.values() if len(o.members) < 3]
            if open_orgs:
                o = self.rng.choice(open_orgs)
                o.members.add(p.player_id)
                p.org = o.org_id
                self.ev("org.member_joined", p, faction_id=o.org_id, org_name=o.name)

    # ---- the tick ----------------------------------------------------------------------------------

    def snapshot(self, lobby: Lobby):
        ps = self.in_lobby(lobby)
        counts = {a: sum(1 for q in ps if q.archetype == a) for a in ("grinder", "griefer", "tryhard", "tourist")}
        flying = sum(1 for q in ps if self.flying(q))
        recent = [(t, act) for t, act in lobby.kills if self.tick - t < SNAPSHOT_EVERY]
        kills = len(recent)
        civilian_kills = sum(1 for _, act in recent if act != "pvp")
        destroyed = sum(1 for t in lobby.destroyed if self.tick - t < SNAPSHOT_EVERY)
        hunting = sum(1 for q in ps if q.archetype == "griefer" and q.vehicle in world.PVP_VEHICLES)
        # the sim's own verdict for a seller, from facts the stream never sees directly (archetypes). Duels between
        # tryhards and griefers are their problem; what matters is griefers on bikes, and what they did to sellers.
        safety = max(0, 100 - 20 * hunting - 8 * (counts["griefer"] - hunting) - 3 * counts["tryhard"]
                     - 4 * civilian_kills - 10 * destroyed)
        self.emit(build_event("lobby.snapshot", self.tick, lobby_id=lobby.lobby_id, population=len(ps), **counts,
                              pvp_vehicles=sum(1 for q in ps if q.vehicle in world.PVP_VEHICLES), flying=flying,
                              passive_players=sum(1 for q in ps if q.passive), active_sells=len(lobby.sells),
                              kills_window=kills, civilian_kills_window=civilian_kills, sells_destroyed_window=destroyed,
                              sim_safety=safety, window_ticks=SNAPSHOT_EVERY))

    def step(self):
        t = self.tick
        # joins and rejoins
        for p in self.players.values():
            if p.in_session:
                continue
            if p.rejoin_at == -1 and self.rng.random() < self.join_rate:
                self.join(p)
            elif 0 <= p.rejoin_at <= t:
                self.join(p, prefer_quiet=(p.last_hop == "lobby_hop" and p.archetype == "grinder"))
        # passive expiry, scheduled leaves
        for p in list(self.players.values()):
            if not p.in_session:
                continue
            if p.passive and p.passive_until <= t:
                self.passive_off(p, "expired")
            if p.pending_leave and p.busy_until <= t:
                reason = p.pending_leave
                p.pending_leave = None
                self.leave(p, reason)
        # turns
        order = [p for p in self.players.values() if p.in_session]
        self.rng.shuffle(order)
        for p in order:
            if not p.in_session:
                continue
            getattr(self, f"act_{p.archetype}")(p)
        # the law
        for p in self.players.values():
            if p.in_session and p.wanted_stars:
                self.resolve_wanted(p)
        # product accrues while the owner is in a session
        if t % ACCRUAL_EVERY == 0 and t > 0:
            for p in self.players.values():
                if p.in_session and p.archetype == "grinder" and p.org:
                    self.accrue(p)
        if t % SNAPSHOT_EVERY == 0:
            for lobby in self.lobbies.values():
                self.snapshot(lobby)
        self.tick += 1

    def drain(self):
        """End of run: everyone leaves, so every open thing gets its closing event."""
        for p in list(self.players.values()):
            if p.in_session:
                self.leave(p, "shutdown")
