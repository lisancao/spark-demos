"""Invariant checker: rebuild the lobby world from the event log alone and fail on anything inconsistent.

    python -m losantos.check sim/output_losantos/events_*.ndjson

This is what "airtight" means for the sim: every kill is between two players who are in the same
lobby and neither of whom is passive; every sell, bounty, wanted level and organisation opens
before it closes and closes exactly once; nobody acts while out of session; snapshots agree with
the membership the events imply.
"""

import glob
import json
import sys
from collections import Counter, defaultdict


def load(paths):
    for pattern in paths:
        for path in sorted(glob.glob(pattern)):
            with open(path) as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)


def main():
    errors = Counter()
    examples = {}
    counts = Counter()

    def fail(rule, ev):
        errors[rule] += 1
        examples.setdefault(rule, ev)

    lobby_of = {}          # player -> lobby
    passive = set()
    sells = {}             # mission_id -> dict(seller, lobby, value, drops, delivered, drop)
    bounties = {}          # target -> amount
    wanted = {}            # player -> stars
    orgs = {}              # org_id -> dict(leader, lobby, members)
    org_of = {}            # player -> org
    stock = {}             # business -> value
    members_at_tick = defaultdict(set)
    seen_ids = set()
    last_tick = -1
    last_ts = ""
    terminal_sell = {"sell.completed", "sell.destroyed", "sell.expired", "sell.abandoned"}

    for ev in load(sys.argv[1:]):
        t = ev["event_type"]
        counts[t] += 1
        tick = ev["sim_tick"]
        if ev["event_id"] in seen_ids:
            fail("event_id unique", ev)
        seen_ids.add(ev["event_id"])
        if tick < last_tick:
            fail("sim_tick monotonic", ev)
        if ev["timestamp"] < last_ts:
            fail("timestamp monotonic", ev)
        last_tick, last_ts = tick, ev["timestamp"]
        a = ev.get("agent_id")
        lobby = ev.get("lobby_id")

        if t == "session.join":
            if a in lobby_of:
                fail("join while in session", ev)
            lobby_of[a] = lobby
            continue
        if a is not None:
            if lobby_of.get(a) != lobby:
                fail("actor in stated lobby", ev)
        if t == "session.leave":
            if a not in lobby_of:
                fail("leave while out of session", ev)
            if a in passive or a in bounties or a in wanted or a in org_of or any(s["seller"] == a for s in sells.values()):
                fail("leave with open state", ev)
            lobby_of.pop(a, None)
        elif t == "session.passive_on":
            if a in passive or any(s["seller"] == a for s in sells.values()):
                fail("passive_on twice or while selling", ev)
            passive.add(a)
        elif t == "session.passive_off":
            if a not in passive:
                fail("passive_off without passive_on", ev)
            passive.discard(a)
        elif t == "combat.kill":
            v = ev["target_id"]
            if lobby_of.get(v) != lobby or v == a:
                fail("kill: victim in same lobby", ev)
            if v in passive or a in passive:
                fail("kill: nobody passive", ev)
            if a in passive:
                fail("kill: attacker passive", ev)
        elif t == "player.bounty_placed":
            v = ev["target_id"]
            if lobby_of.get(v) != lobby or v in bounties:
                fail("bounty: target in lobby and unbountied", ev)
            bounties[v] = ev["amount"]
        elif t == "player.bounty_claimed":
            v = ev["target_id"]
            if bounties.get(v) != ev["amount"]:
                fail("bounty claimed matches placed", ev)
            bounties.pop(v, None)
        elif t == "player.bounty_expired":
            if bounties.get(a) != ev["amount"]:
                fail("bounty expired matches placed", ev)
            bounties.pop(a, None)
        elif t == "wanted.gained":
            if a in wanted:
                fail("wanted gained while wanted", ev)
            wanted[a] = ev["stars"]
        elif t == "wanted.escalated":
            if wanted.get(a) != ev["from_stars"] or ev["stars"] != ev["from_stars"] + 1:
                fail("wanted escalates by one from current", ev)
            wanted[a] = ev["stars"]
        elif t == "wanted.cleared":
            if wanted.get(a) != ev["stars"]:
                fail("wanted cleared matches current stars", ev)
            wanted.pop(a, None)
        elif t == "org.registered":
            if a in org_of:
                fail("org registered while in an org", ev)
            orgs[ev["faction_id"]] = dict(leader=a, lobby=lobby, members=set())
            org_of[a] = ev["faction_id"]
            for b in ev["businesses"]:
                if b["business"] in stock and stock[b["business"]] != b["stock_value"]:
                    fail("registration restates the stock the log implies", ev)
                stock[b["business"]] = b["stock_value"]
        elif t == "org.member_joined":
            o = orgs.get(ev["faction_id"])
            if o is None or o["lobby"] != lobby or a in org_of:
                fail("member joins an open org in its lobby", ev)
            else:
                o["members"].add(a)
                org_of[a] = ev["faction_id"]
        elif t == "org.member_left":
            o = orgs.get(ev["faction_id"])
            if o is None or a not in o["members"]:
                fail("member leaves an org it is in", ev)
            else:
                o["members"].discard(a)
            org_of.pop(a, None)
        elif t == "org.disbanded":
            o = orgs.get(ev["faction_id"])
            if o is None or o["leader"] != a or o["members"]:
                fail("disband by leader with no members left", ev)
            orgs.pop(ev["faction_id"], None)
            org_of.pop(a, None)
        elif t in ("org.business_stocked", "org.supply_run"):
            if org_of.get(a) != ev["faction_id"]:
                fail("stock event by org leader", ev)
            prev = stock.get(ev["business"], 0)
            if ev["stock_value"] != prev + ev["stock_added"]:
                fail("stock accounting", ev)
            stock[ev["business"]] = ev["stock_value"]
        elif t == "sell.started":
            if org_of.get(a) != ev["faction_id"] or any(s["seller"] == a for s in sells.values()):
                fail("sell by org leader with no sell in flight", ev)
            if ev["value"] != stock.get(ev["business"], None):
                fail("sell value equals stock", ev)
            stock[ev["business"]] = 0
            if a in passive:
                fail("sell started while passive", ev)
            sells[ev["mission_id"]] = dict(seller=a, lobby=lobby, value=ev["value"], drops=ev["drops"], delivered=0, drop=0)
        elif t == "sell.delivery":
            s = sells.get(ev["mission_id"])
            if s is None or s["seller"] != a or ev["drop"] != s["drop"] + 1 or ev["drop"] > s["drops"]:
                fail("delivery in order on an open sell", ev)
            else:
                s["drop"] = ev["drop"]
                s["delivered"] = ev["value_delivered"]
        elif t in terminal_sell:
            s = sells.pop(ev["mission_id"], None)
            if s is None or s["seller"] != a:
                fail("sell closes once, by its seller", ev)
            elif t == "sell.completed" and (s["drop"] != s["drops"] or ev["value_delivered"] != s["value"]):
                fail("completed sell delivered everything", ev)
            elif t != "sell.completed" and ev["value_lost"] + ev["value_delivered"] != s["value"]:
                fail("lost + delivered = value", ev)
            elif t == "sell.destroyed" and lobby_of.get(ev["destroyed_by"]) != lobby:
                fail("destroyed by a player in the lobby", ev)
        elif t == "lobby.snapshot":
            pop = sum(1 for p, l in lobby_of.items() if l == lobby)
            if pop != ev["population"]:
                fail("snapshot population matches membership", ev)
            if ev["active_sells"] != sum(1 for s in sells.values() if s["lobby"] == lobby):
                fail("snapshot active sells", ev)
            if ev["passive_players"] != sum(1 for p in passive if lobby_of.get(p) == lobby):
                fail("snapshot passive count", ev)

    if lobby_of or sells or bounties or wanted or orgs:
        errors["everything closed at end"] += 1
    print(f"events: {sum(counts.values())}")
    for t, n in sorted(counts.items()):
        print(f"  {t:28s} {n}")
    if errors:
        print("VIOLATIONS")
        for rule, n in errors.most_common():
            print(f"  {rule}: {n}  e.g. {json.dumps(examples.get(rule))[:300]}")
        sys.exit(1)
    print("all invariants hold")


if __name__ == "__main__":
    main()
