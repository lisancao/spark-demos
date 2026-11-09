"""Grade the recommender against the shoppers' hidden favourite aisles.

hit rate = share of recommended books that sit in one of the shopper's favourite aisles,
grouped by how many clicks the shopper had made when the picks were emitted. The baseline
is what picking books at random from the catalog would score for the same shoppers.

Nudges (idle-timer output) are reported with their delay: broker append time minus the
time the timer was due.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bin.latency import pct, read_all  # noqa: E402
from bookshop.common import CATALOG, DATA, RECS  # noqa: E402

BUCKETS = [(1, 1), (2, 4), (5, 9), (10, 19), (20, 10**9)]


def main() -> None:
    favs = json.loads((DATA / "shoppers.json").read_text())
    aisles = pq.read_table(CATALOG, columns=["aisle"]).column("aisle").to_pylist()
    share = {a: aisles.count(a) / len(aisles) for a in set(aisles)}
    rows = read_all(RECS)
    picks = [(t, r) for t, r in rows if r["kind"] == "picks"]
    nudges = [(t, r) for t, r in rows if r["kind"] == "nudge"]

    hits, total, base = defaultdict(int), defaultdict(int), defaultdict(float)
    for _, r in picks:
        fav = set(favs[r["user_id"]])
        b = next(b for b in BUCKETS if b[0] <= r["clicks"] <= b[1])
        for p in r["picks"]:
            total[b] += 1
            hits[b] += p["aisle"] in fav
            base[b] += sum(share[a] for a in fav)
    print(f"{'clicks so far':>14}  {'picks':>6}  {'in a favourite aisle':>20}  {'random picks would be':>21}")
    for b in BUCKETS:
        if total[b]:
            label = f"{b[0]}" if b[0] == b[1] else (f"{b[0]}+" if b[1] > 10**8 else f"{b[0]}-{b[1]}")
            print(f"{label:>14}  {total[b]:>6}  {hits[b] / total[b]:>19.0%}  {base[b] / total[b]:>20.0%}")
    if nudges:
        d = [t - r["ts"] for t, r in nudges]
        print(f"nudges: {len(nudges)} (idle timers fired)  delay after due time: "
              f"p50 {pct(d, .5) / 1000:.1f} s  max {max(d) / 1000:.1f} s")


if __name__ == "__main__":
    main()
