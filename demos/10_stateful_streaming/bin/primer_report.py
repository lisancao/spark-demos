#!/usr/bin/env python3
"""Summarise a Primer run: lateness distribution, dedup effect, and what the watermark dropped (from engine metrics)."""
import json
import sys
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.dataset as ds

root = Path(sys.argv[1] if len(sys.argv) > 1 else "data/primer/30_seconds")


def load(name):
    return ds.dataset(str(root / name), format="parquet").to_table()


def progress(name):
    """Sum per-query stateful operator metrics across all batches."""
    tot = {"numRowsTotal": 0, "numRowsDroppedByWatermark": 0, "numRowsUpdated": 0, "numRowsRemoved": 0, "batches": 0}
    with open(root / "progress.jsonl") as f:
        for line in f:
            p = json.loads(line)
            if p.get("name") != name or p.get("numInputRows", 0) == 0:
                continue
            tot["batches"] += 1
            for op in p.get("stateOperators", []):
                for k in ("numRowsDroppedByWatermark", "numRowsUpdated", "numRowsRemoved"):
                    tot[k] += op.get(k, 0)
                tot["numRowsTotal"] = op.get("numRowsTotal", tot["numRowsTotal"])
    return tot


late = load("lateness")
n = late.num_rows
distinct = pc.count_distinct(late["event_id"]).as_py()
delay_s = pc.divide(late["delay_ms"], 1000.0)
print(f"== {root}")
print(f"events read                 {n}  (distinct event_id {distinct}, duplicates {n - distinct})")
for q in (0.5, 0.9, 0.95, 0.99, 1.0):
    v = pc.quantile(delay_s, q=q).to_pylist()[0]
    print(f"delivery delay p{int(q*100):<3}        {v:8.2f} s")
for t in (1, 5, 10, 15, 20, 30):
    frac = pc.sum(pc.greater(delay_s, t)).as_py() / n
    print(f"share later than {t:>2}s        {frac:7.2%}")

dedup = load("dedup")
pd = progress("dedup")
print(f"dedup output                {dedup.num_rows} rows; engine dropped {pd['numRowsDroppedByWatermark']} as late, "
      f"removed {pd['numRowsRemoved']} expired keys, {pd['batches']} batches")
print(f"  distinct ids never output {distinct - pc.count_distinct(dedup['event_id']).as_py()}  (late events lost to the watermark)")

win = load("windows")
pw = progress("windows")
streamed = pc.sum(win["events"]).as_py() or 0
print(f"windows emitted             {win.num_rows}; events counted {streamed} of {n} ({streamed / n:.2%}); "
      f"engine dropped {pw['numRowsDroppedByWatermark']} as late; {pw['numRowsTotal']} windows still open at end")
