#!/usr/bin/env python3
"""Summarise processor outputs under data/processors/<name>: rows, outcome mix, engine metrics."""
import json
import sys
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.dataset as ds

root = Path("data/processors")
names = sys.argv[1:] or ["presence", "combat", "ncpd"]


def engine(name):
    data = empty = dropped = state = 0
    durations = []
    with open(root / name / "progress.jsonl") as f:
        for line in f:
            p = json.loads(line)
            if p.get("numInputRows", 0) == 0:
                empty += 1
                continue
            data += 1
            durations.append(p["durationMs"].get("triggerExecution", 0))
            for op in p.get("stateOperators", []):
                dropped += op.get("numRowsDroppedByWatermark", 0)
                state = op.get("numRowsTotal", state)
    med = sorted(durations)[len(durations) // 2] if durations else 0
    return f"data batches {data} (median {med} ms), empty batches {empty}, dropped by watermark {dropped}, state rows at end {state}"


for name in names:
    try:
        t = ds.dataset(str(root / name / "out"), format="parquet").to_table()
    except Exception as e:  # noqa: BLE001
        print(f"== {name}: no output ({e})")
        continue
    print(f"== {name}: {t.num_rows} rows")
    if name == "presence":
        first = pc.sum(t["first_seen"]).as_py()
        print(f"   first sightings {first}, moves {t.num_rows - first}, distinct agents {pc.count_distinct(t['agent_id']).as_py()}")
    elif name == "combat":
        print("   closed_by:", dict(zip(*t.group_by("closed_by").aggregate([("attacker_id", "count")]).to_pydict().values())))
        ended = t.filter(pc.equal(t["closed_by"], "ended"))
        agree = pc.sum(pc.equal(ended["rounds_seen"], ended["rounds_reported"])).as_py()
        print(f"   rounds seen == rounds reported by the sim: {agree} of {ended.num_rows} ended sessions")
    elif name == "ncpd":
        print("   outcome:", dict(zip(*t.group_by("outcome").aggregate([("crime_key", "count")]).to_pydict().values())))
        ans = t.filter(pc.equal(t["outcome"], "answered"))
        if ans.num_rows:
            print(f"   answered: waited p50 {pc.quantile(ans['waited_ms'], q=0.5).to_pylist()[0]:.0f} ms, max {pc.max(ans['waited_ms']).as_py()} ms")
    print("  ", engine(name))
