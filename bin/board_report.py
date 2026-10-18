#!/usr/bin/env python3
"""Read the Los Santos board out of Redis: the serving path, the latency distribution, and the grade.

    docker compose run --rm tools /app/bin/board_report.py --redis redis [board|sell <lobby>|latency|grade|config] [--skip-first-s 15]

board:   every lobby by safety, with the verdict and what drove it (ZREVRANGE lobbies:safety + HGETALL lobby:<id>)
sell:    the one-line answer a seller wants for one lobby
latency: written_at minus source_kafka_ts over the verdicts stream, percentiles
grade:   verdicts triggered by a sim snapshot, board score vs sim_safety
config:  verdict mix before and after the first config row
"""
import argparse
import math
import sys
from collections import Counter

import redis

ap = argparse.ArgumentParser()
ap.add_argument("what", nargs="?", default="board")
ap.add_argument("lobby", nargs="?")
ap.add_argument("--redis", default="localhost")
ap.add_argument("--port", type=int, default=6379)
ap.add_argument("--skip-first-s", type=float, default=15.0)
args = ap.parse_args()
r = redis.Redis(host=args.redis, port=args.port, decode_responses=True)


def verdict(s):
    return "sell" if s >= 70 else "risky" if s >= 40 else "hop"


def stream():
    rows = [dict(f) for _, f in r.xrange("verdicts", "-", "+")]
    for x in rows:
        for k in ("score", "written_at", "source_kafka_ts", "at", "population", "menaces", "pvp_vehicles", "sells_destroyed_recent"):
            x[k] = float(x[k]) if k == "score" else int(x[k])
        x["sim_safety"] = int(x["sim_safety"]) if x["sim_safety"] else None
    return rows


if args.what == "board":
    for lobby, score in r.zrevrange("lobbies:safety", 0, -1, withscores=True):
        h = r.hgetall(f"lobby:{lobby}")
        print(f"{lobby:14s} {score:5.1f} {h['verdict']:5s}  pop {h['population']:>2}  menaces {h['menaces']}  hostiles {h['hostiles']}  "
              f"bikes {h['pvp_vehicles']}  destroyed {h['sells_destroyed_recent']}/{h['sells_recent']}  last: {h['trigger']}")
elif args.what == "sell":
    h = r.hgetall(f"lobby:{args.lobby}")
    if not h:
        sys.exit(f"no verdict for {args.lobby}")
    why = []
    if int(h["menaces"]):
        why.append(f"{h['menaces']} known griefer{'s' if h['menaces'] != '1' else ''} in session")
    if int(h["pvp_vehicles"]):
        why.append(f"{h['pvp_vehicles']} armed vehicle{'s' if h['pvp_vehicles'] != '1' else ''} out")
    if int(h["sells_destroyed_recent"]):
        why.append(f"{h['sells_destroyed_recent']} sell{'s' if h['sells_destroyed_recent'] != '1' else ''} destroyed just now")
    print(f"{args.lobby}: {h['verdict'].upper()} (safety {float(h['score']):.0f}). " + ("; ".join(why) if why else "nothing on the radar") + ".")
elif args.what == "latency":
    rows = [x for x in stream() if x["source_kafka_ts"] > 0]
    if not rows:
        sys.exit("no rows with a source timestamp")
    t0 = min(x["written_at"] for x in rows) + args.skip_first_s * 1000
    lat = sorted(x["written_at"] - x["source_kafka_ts"] for x in rows if x["written_at"] >= t0)
    q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))]
    print(f"verdicts {len(lat)} (after skipping the first {args.skip_first_s:.0f} s): p50 {q(0.5)} ms  p90 {q(0.9)} ms  p99 {q(0.99)} ms  max {lat[-1]} ms  mean {sum(lat) / len(lat):.0f} ms")
elif args.what == "grade":
    rows = [x for x in stream() if x["sim_safety"] is not None]
    n = len(rows)
    if not n:
        sys.exit("no snapshot-triggered verdicts")
    mx = sum(x["score"] for x in rows) / n
    my = sum(x["sim_safety"] for x in rows) / n
    cov = sum((x["score"] - mx) * (x["sim_safety"] - my) for x in rows)
    vx = math.sqrt(sum((x["score"] - mx) ** 2 for x in rows))
    vy = math.sqrt(sum((x["sim_safety"] - my) ** 2 for x in rows))
    agree = sum(1 for x in rows if x["verdict"] == verdict(x["sim_safety"]))
    bad = sum(1 for x in rows if verdict(x["sim_safety"]) == "hop" and x["verdict"] == "sell")
    grid = Counter((verdict(x["sim_safety"]), x["verdict"]) for x in rows)
    print(f"snapshots graded: {n}  pearson r {cov / vx / vy:.3f}  agreement {agree}/{n} = {agree / n:.1%}  sold into a hop lobby {bad}")
    for sv in ("sell", "risky", "hop"):
        print(f"  sim {sv:6s} " + "  ".join(f"board {bv}={grid[(sv, bv)]:4d}" for bv in ("sell", "risky", "hop")))
elif args.what == "config":
    rows = stream()
    cfg = [x for x in rows if x["trigger"].startswith("config")]
    if not cfg:
        sys.exit("no config-triggered verdicts")
    t0 = min(x["at"] for x in cfg)
    before = [x for x in rows if x["at"] < t0]
    after = [x for x in rows if x["at"] >= t0]
    print(f"config rows {len(cfg)}, first at {t0}; weights now {cfg[0]['weights']}")
    for name, part in (("before", before), ("after", after)):
        print(f"  {name}: {len(part)} verdicts {dict(Counter(x['verdict'] for x in part))} mean safety {sum(x['score'] for x in part) / max(1, len(part)):.1f}")
    last_before = {}
    for x in before:
        last_before[x["lobby_id"]] = x
    first_after = {}
    for x in sorted(after, key=lambda x: x["at"]):
        first_after.setdefault(x["lobby_id"], x)
    for l in sorted(last_before):
        a, b = last_before[l], first_after.get(l)
        if b:
            print(f"  {l}: menaces {a['menaces']} bikes {a['pvp_vehicles']} destroyed {a['sells_destroyed_recent']}: {a['score']:.0f} {a['verdict']} -> {b['score']:.0f} {b['verdict']}")
