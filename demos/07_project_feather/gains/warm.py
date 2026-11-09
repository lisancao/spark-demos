"""Warm medians per query, flag off and on, in one session.

"rebuilt" builds the DataFrame again before every collect (a notebook cell, a test, an agent);
"reused" collects the same DataFrame object again. Off and on alternate rep by rep so they share
any drift.
"""
import json, statistics as st, sys, time
from pyspark.sql import SparkSession
sys.path.insert(0, "gains"); from queries import queries, exchanges, make_data

spark = SparkSession.builder.getOrCreate()
make_data(spark)
FLAG = "spark.sql.optimizer.singleTaskExecution.enabled"
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 60
OUT = sys.argv[2] if len(sys.argv) > 2 else "gains/results-warm.json"

def timed(f):
    t = time.perf_counter(); f(); return (time.perf_counter() - t) * 1000

out = {}
for name, build in queries(spark).items():
    t = {(v, m): [] for v in ("false", "true") for m in ("rebuilt", "reused")}
    kept, ex = {}, {}
    for v in ("false", "true"):
        spark.conf.set(FLAG, v)
        kept[v] = build()
        for _ in range(3): kept[v].collect(); build().collect()
        ex[v] = exchanges(kept[v])
    for _ in range(REPS):
        for v in ("false", "true"):
            spark.conf.set(FLAG, v)
            t[(v, "rebuilt")].append(timed(lambda: build().collect()))
            t[(v, "reused")].append(timed(lambda: kept[v].collect()))
    quart = lambda xs: [round(x, 1) for x in st.quantiles(xs, n=4)]
    out[name] = {v: {"exchanges": ex[v], **{m: {"median": round(st.median(t[(v, m)]), 1),
                                                  "quartiles": quart(t[(v, m)])}
                                              for m in ("rebuilt", "reused")}}
                 for v in ("false", "true")}
    o, n = out[name]["false"], out[name]["true"]
    print(f"{name:24} exch {o['exchanges']}->{n['exchanges']}  rebuilt {o['rebuilt']['median']:6.1f} -> {n['rebuilt']['median']:6.1f}"
          f"   reused {o['reused']['median']:6.1f} -> {n['reused']['median']:6.1f}", flush=True)
out["SELECT 1"] = round(st.median([timed(lambda: spark.sql("SELECT 1").collect()) for _ in range(REPS)]), 1)
print("SELECT 1", out["SELECT 1"])
json.dump(out, open(OUT, "w"), indent=1)
