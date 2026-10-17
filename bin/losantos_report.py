#!/usr/bin/env python3
"""Summarise the Los Santos processor outputs and grade them against the sim's hidden truth.

    python3 bin/losantos_report.py [data/losantos] [sim/output_losantos]
"""
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

root = Path(sys.argv[1] if len(sys.argv) > 1 else "data/losantos")
sim = Path(sys.argv[2] if len(sys.argv) > 2 else "sim/output_losantos")


def table(name):
    files = glob.glob(str(root / name / "out" / "*.parquet"))
    return pq.ParquetDataset(files).read().to_pylist() if files else []


def progress(name):
    p = root / name / "progress.jsonl"
    if not p.exists():
        return {}
    rows = [json.loads(l) for l in open(p) if l.strip()]
    data = [r for r in rows if r.get("numInputRows", 0) > 0]
    durs = sorted(r.get("durationMs", {}).get("triggerExecution", 0) for r in data)
    ops = rows[-1].get("stateOperators", [{}]) if rows else [{}]
    late = sum(op.get("numRowsDroppedByWatermark", 0) for r in rows for op in r.get("stateOperators", []))
    return dict(batches=len(data), median_ms=durs[len(durs) // 2] if durs else 0,
                state_rows=[op.get("numRowsTotal") for op in ops], dropped_late=late)


truth = {json.loads(l)["agent_id"]: json.loads(l)["archetype"] for l in open(sim / "players_truth.jsonl")} if (sim / "players_truth.jsonl").exists() else {}

for name in ("presence", "streaks", "sells", "orgs", "menace", "board"):
    rows = table(name)
    if not rows:
        continue
    print(f"\n## {name}: {len(rows)} rows, engine {progress(name)}")
    if name == "presence":
        print("  changes:", dict(Counter(r["change"] for r in rows)))
    elif name == "streaks":
        print("  closed_by:", dict(Counter(r["closed_by"] for r in rows)))
        print("  kills per streak:", dict(sorted(Counter(min(r["kills"], 10) for r in rows).items())))
        print("  streaks with a seller kill:", sum(1 for r in rows if r["sellers_killed"]), "flying:", sum(1 for r in rows if r["flying"]))
        by = defaultdict(lambda: [0, 0])
        for r in rows:
            a = truth.get(r["attacker_id"], "?")
            by[a][0] += 1
            by[a][1] += r["sellers_killed"]
        print("  by hidden archetype (streaks, seller kills):", dict(by))
    elif name == "sells":
        print("  outcomes:", dict(Counter(r["outcome"] for r in rows)))
        lost = sum(r["value"] - r["value_delivered"] for r in rows if r["outcome"] == "destroyed")
        print(f"  value destroyed: ${lost:,}")
        bylobby = defaultdict(Counter)
        for r in rows:
            bylobby[r["lobby_id"]][r["outcome"]] += 1
        for l in sorted(bylobby):
            print(f"  {l}: {dict(bylobby[l])}")
    elif name == "orgs":
        last = {}
        for r in sorted(rows, key=lambda r: r["at"]):
            last[r["org_id"]] = r
        print("  orgs seen:", len(last), " event types:", dict(Counter(r["event_type"] for r in rows)))
        print("  stock held at end (sum over orgs): $%s" % f"{sum(r['stock_total'] for r in last.values()):,}")
    elif name == "menace":
        last = {}
        for r in sorted(rows, key=lambda r: r["at"]):
            last[r["agent_id"]] = r
        peak = defaultdict(str)
        order = {"civilian": 0, "hostile": 1, "menace": 2}
        for r in rows:
            if order[r["level"]] > order.get(peak[r["agent_id"]], -1):
                peak[r["agent_id"]] = r["level"]
        print("  players scored:", len(last), " levels at end:", dict(Counter(r["level"] for r in last.values())))
        grid = defaultdict(Counter)
        for pid, lvl in peak.items():
            grid[truth.get(pid, "?")][lvl] += 1
        print("  peak level reached vs hidden archetype:")
        for a in ("griefer", "tryhard", "grinder", "tourist"):
            print(f"    {a:8s} {dict(grid[a])}")
        top = sorted(last.values(), key=lambda r: -r["score"])[:5]
        for r in top:
            print(f"    top: {r['agent_name']:22s} {truth.get(r['agent_id'], '?'):8s} score {r['score']:.0f} sellers {r['sellers_killed']} pvp {r['pvp_kills']} bikes {r['flying_spawns']}")
    elif name == "board":
        print("  verdicts emitted:", dict(Counter(r["verdict"] for r in rows)))
        print("  triggers:", dict(Counter(r["trigger"].split(":")[0] for r in rows)))
        # latest verdict per lobby
        last = {}
        for r in sorted(rows, key=lambda r: r["at"]):
            last[r["lobby_id"]] = r
        for l in sorted(last):
            r = last[l]
            print(f"  {l}: pop {r['population']:2d} menaces {r['menaces']} hostiles {r['hostiles']} bikes {r['pvp_vehicles']} destroyed {r['sells_destroyed_recent']}/{r['sells_recent']} -> {r['score']:5.1f} {r['verdict']}")
        # compare with the sim's own verdict: for each snapshot, the board's latest score before it
        snaps = [json.loads(l) for f in sorted(glob.glob(str(sim / "events_*.ndjson"))) for l in open(f) if '"lobby.snapshot"' in l]
        if snaps:
            import bisect
            series = defaultdict(list)
            for r in sorted(rows, key=lambda r: r["at"]):
                series[r["lobby_id"]].append((r["at"], r["score"]))
            pairs = []
            for s in snaps:
                ts = series.get(s["lobby_id"])
                if not ts:
                    continue
                # match by sim_tick order: the board rows carry event time of replay; use rank position instead
                pairs.append((s["lobby_id"], s["sim_tick"], s["sim_safety"]))
            print("  (snapshot comparison needs the board run on the live topic; see losantos_grade.py)")
