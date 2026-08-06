#!/usr/bin/env python3
"""
Measures the local-mode overheads Project Feather (SPARK-56978) targets.

Why a baseline harness rather than a before/after demo: as of Spark 4.2.0 none of
Feather's configs exist yet. They are merged on master for 4.3.0. So this measures
the problem the SPIP describes, on the Spark you actually have, and the same script
will show the improvement once 4.3 ships. Run it before and after upgrading.

The four things measured map to the SPIP's own claims:

  1. Session creation      community feedback in the SPIP: "multiple seconds"
  2. Exchange count        SPIP category 1/3: small queries get shuffles they do
                           not need, so the plan has an Exchange that Feather elides
  3. Small-query latency   SPIP Q3: "queries over less than 100 MB run for three
                           seconds or more"
  4. Cache round trip      SPIP category 2: df.cache is the ad hoc prototyping path

Usage:
    python3 bench/feather_baseline.py              # default: 5 reps
    python3 bench/feather_baseline.py --reps 15    # steadier medians
    python3 bench/feather_baseline.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time

from pyspark.sql import SparkSession

# Configs Feather introduces. Probed, not assumed: absent on 4.2, present on 4.3+.
FEATHER_CONFIGS = [
    "spark.sql.optimizer.singleTaskExecution.enabled",
    "spark.sql.optimizer.singleTaskExecution.sort",
    "spark.sql.optimizer.singleTaskExecution.aggregation",
    "spark.sql.optimizer.singleTaskExecution.limitOffset",
    "spark.sql.optimizer.singleTaskExecution.window",
    "spark.sql.optimizer.singleTaskExecution.expand",
    "spark.sql.optimizer.singleTaskExecution.localTableScan.threshold",
    "spark.sql.execution.arrow.cache.prefetch.enabled",
    "spark.sql.unionOutputPartitioning.enabled",
]

# The Arrow cache is NOT a boolean flag. It ships as an alternative serializer class
# selected through a STATIC conf, so it cannot be toggled on a live session and a
# boolean probe would miss it entirely.
ARROW_SERIALIZER_CONF = "spark.sql.cache.serializer"
ARROW_SERIALIZER_CLASS = "org.apache.spark.sql.execution.columnar.ArrowCachedBatchSerializer"


def timed(fn, reps: int) -> dict:
    """Runs fn reps+1 times, discards the first as warm-up, reports the rest."""
    fn()  # warm-up: JIT and codegen cost lands here, not in the numbers
    samples = []
    for _ in range(reps):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return {
        "median_ms": round(statistics.median(samples), 1),
        "min_ms": round(min(samples), 1),
        "max_ms": round(max(samples), 1),
        "reps": reps,
    }


def exchanges(df) -> int:
    """Counts Exchange nodes in the physical plan: each one is a shuffle."""
    plan = df._jdf.queryExecution().executedPlan().toString()
    return plan.count("Exchange")


def probe_configs(spark) -> dict:
    """Which Feather configs does this Spark actually have?"""
    out = {}
    for key in FEATHER_CONFIGS:
        try:
            out[key] = spark.conf.get(key)
        except Exception:
            out[key] = None
    # Reported separately: which serializer the cache is actually using.
    try:
        out[ARROW_SERIALIZER_CONF] = spark.conf.get(ARROW_SERIALIZER_CONF)
    except Exception:
        out[ARROW_SERIALIZER_CONF] = None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--rows", type=int, default=800)
    ap.add_argument("--json", default="bench/results.json")
    args = ap.parse_args()

    results = {
        "platform": f"{platform.system()} {platform.machine()}",
        "python": platform.python_version(),
        "rows": args.rows,
    }

    # 1. Session creation. Timed around getOrCreate, so this is the real cost a
    # script or an AI agent pays before running its first query.
    t = time.perf_counter()
    spark = (SparkSession.builder
             .master("local[*]")
             .appName("feather-baseline")
             .config("spark.ui.enabled", "false")
             .getOrCreate())
    results["session_create_ms"] = round((time.perf_counter() - t) * 1000, 1)
    spark.sparkContext.setLogLevel("ERROR")
    results["spark_version"] = spark.version

    results["feather_configs"] = probe_configs(spark)
    # Count only the configs Feather ADDS. spark.sql.cache.serializer has existed for
    # years, so counting it would falsely report readiness on a pre-Feather build.
    present = sum(1 for k in FEATHER_CONFIGS
                  if results["feather_configs"].get(k) is not None)
    results["feather_configs_present"] = present
    serializer = results["feather_configs"].get(ARROW_SERIALIZER_CONF) or ""
    results["arrow_cache_active"] = ARROW_SERIALIZER_CLASS in serializer

    df = (spark.range(0, args.rows)
          .selectExpr("id", "id % 7 as g", "cast(id as string) as s"))
    df.createOrReplaceTempView("t")

    # 2. Filter then sort. The SPIP uses this exact shape: a sort over a small
    # single-partition scan gets an Exchange it does not need.
    q_sort = "SELECT s FROM t WHERE g = 3 ORDER BY id"
    results["filter_sort"] = timed(lambda: spark.sql(q_sort).collect(), args.reps)
    results["filter_sort"]["exchanges"] = exchanges(spark.sql(q_sort))

    # 3. Aggregation, the other shuffle-inducing operator Feather marks.
    q_agg = "SELECT g, count(*) AS c FROM t GROUP BY g"
    results["aggregate"] = timed(lambda: spark.sql(q_agg).collect(), args.reps)
    results["aggregate"]["exchanges"] = exchanges(spark.sql(q_agg))

    # 4. Cache round trip: SPIP category 2, the ad hoc prototyping loop.
    cached = df.cache()
    cached.count()  # materialize before timing reads
    results["cached_query"] = timed(
        lambda: cached.filter("g = 3").select("s").collect(), args.reps)

    # 5. Floor: how fast can local mode answer anything at all.
    results["trivial_query"] = timed(
        lambda: spark.sql("SELECT 1").collect(), args.reps * 2)

    spark.stop()

    if args.rows > 1000:
        print(f"\n  NOTE: {args.rows} rows is above the Spark 4.3 default cap of 1000 for")
        print("  spark.sql.optimizer.singleTaskExecution.localTableScan.threshold, so the")
        print("  shuffle-free rule would not apply to this fixture even once enabled.")
    print(f"\nSpark {results['spark_version']} on {results['platform']}")
    print(f"Feather configs present: {present} of {len(FEATHER_CONFIGS)}")
    print(f"Arrow cache serializer active: {results['arrow_cache_active']}")
    if present == 0:
        print("  -> This Spark predates Feather. Numbers below are the baseline it improves on.")
    else:
        print("  -> Feather configs available. Compare against a pre-4.3 baseline run.")

    print(f"\n  session creation      {results['session_create_ms']:>8.1f} ms")
    for key, label in [("filter_sort", "filter + sort"),
                       ("aggregate", "aggregate"),
                       ("cached_query", "cached query"),
                       ("trivial_query", "SELECT 1")]:
        r = results[key]
        ex = f"   exchanges={r['exchanges']}" if "exchanges" in r else ""
        print(f"  {label:<20} {r['median_ms']:>8.1f} ms (median of {r['reps']}){ex}")

    with open(args.json, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
