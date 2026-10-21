#!/usr/bin/env python3
"""Grade the lobby board against the sim's own verdict.

Every `lobby.snapshot` the sim emits carries `sim_safety`, computed from facts the stream never sees (the hidden
archetypes). The board passes snapshots through, so each one yields a verdict row with the board's score and the
sim's side by side. This prints the agreement.

    python3 bin/losantos_grade.py [data/losantos/board]
"""
import glob
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

root = Path(sys.argv[1] if len(sys.argv) > 1 else "data/losantos/board")
rows = pq.ParquetDataset(glob.glob(str(root / "out" / "*.parquet"))).read().to_pylist()
pairs = [(r["score"], r["sim_safety"], r["verdict"], r["lobby_id"], r["population"], r["sim_population"]) for r in rows if r["sim_safety"] is not None]
if not pairs:
    sys.exit("no snapshot-triggered rows")


def verdict(s):
    return "sell" if s >= 70 else "risky" if s >= 40 else "hop"


n = len(pairs)
mx = sum(p[0] for p in pairs) / n
my = sum(p[1] for p in pairs) / n
cov = sum((p[0] - mx) * (p[1] - my) for p in pairs)
vx = sum((p[0] - mx) ** 2 for p in pairs) ** 0.5
vy = sum((p[1] - my) ** 2 for p in pairs) ** 0.5
r = cov / (vx * vy) if vx and vy else float("nan")
agree = sum(1 for p in pairs if p[2] == verdict(p[1]))
grid = Counter((verdict(p[1]), p[2]) for p in pairs)
popdiff = Counter(abs(p[4] - p[5]) for p in pairs)
print(f"snapshots graded: {n}")
print(f"pearson r (board score vs sim_safety): {r:.3f}")
print(f"verdict agreement: {agree}/{n} = {agree / n:.1%}")
print("sim verdict (rows) x board verdict (cols):")
for sv in ("sell", "risky", "hop"):
    print(f"  {sv:6s} " + "  ".join(f"{bv}={grid[(sv, bv)]:4d}" for bv in ("sell", "risky", "hop")))
print("population |board - sim|:", dict(sorted(popdiff.items())))
# the cases that matter most: sim says hop, board says sell (you sold into a griefed lobby)
bad = [p for p in pairs if verdict(p[1]) == "hop" and p[2] == "sell"]
print(f"sold into a lobby the sim calls hop: {len(bad)}")
