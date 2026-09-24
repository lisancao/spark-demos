#!/usr/bin/env python3
"""Project Feather demo: watch Spark plan a needless shuffle, then remove it.

Project Feather (SPARK-56978) removes fixed local-mode overhead so a tiny query does
not pay for a distributed execution plan. The sharpest illustration is a small
filter + ORDER BY: in Spark Classic it plans a 200-way range exchange (a full
shuffle), while Feather's ``MarkSingleTaskExecution`` rule deletes that exchange and
runs the fragment as one task.

Version-aware, on purpose:

- On Spark 4.2 and earlier it runs the baseline only, labels the exchange, and notes
  that the flag it would set does not exist until 4.3.
- On Spark 4.3+ it runs the same query with
  ``spark.sql.optimizer.singleTaskExecution.enabled`` off and on, prints both physical
  plans, the exchange count, and a median timing. It then shows the one guardrail:
  the rule caps in-memory relations at 1,000 rows, so a bigger fixture stays shuffled.

Usage:
    ./demo.sh              # locate Spark, run the demo
    spark-submit feather_demo.py --rows 800 --reps 7
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time

from pyspark.sql import SparkSession

ENABLED_KEY = "spark.sql.optimizer.singleTaskExecution.enabled"
THRESHOLD_KEY = "spark.sql.optimizer.singleTaskExecution.localTableScan.threshold"


def exchanges(plan: str) -> int:
    return plan.count("Exchange")


def register_relation(spark, rows: int) -> None:
    """Builds an in-memory relation via VALUES (a LocalRelation in the plan)."""
    vals = ",".join(f"({i},{i % 7},'{i}')" for i in range(rows))
    spark.sql(
        f"CREATE OR REPLACE TEMP VIEW t AS SELECT * FROM VALUES {vals} AS t(id, g, s)")


def plan_of(df) -> str:
    return df._jdf.queryExecution().executedPlan().toString()


def show_plan(plan: str, rows: int) -> None:
    print(f"\n  rows={rows}, Exchange nodes={exchanges(plan)}")
    for line in plan.splitlines():
        print(f"    {line}")


def timed(fn, reps: int) -> dict:
    fn()  # warm-up: JIT and codegen do not land in the reported median
    samples = []
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t) * 1000)
    return {
        "median_ms": round(statistics.median(samples), 1),
        "min_ms": round(min(samples), 1),
        "max_ms": round(max(samples), 1),
        "reps": reps,
    }


def section(title: str) -> None:
    print(f"\n{'=' * 78}\n  {title}\n{'=' * 78}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=800,
                    help="in-memory fixture size for the headline query")
    ap.add_argument("--reps", type=int, default=7,
                    help="repetitions behind each median")
    args = ap.parse_args()

    spark = (SparkSession.builder
             .master("local[*]")
             .appName("feather-demo")
             .config("spark.ui.enabled", "false")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    print(f"\nSpark {spark.version}")

    # Detect readiness without setting anything: the key exists on 4.3+, raises on 4.2.
    try:
        default_value = spark.conf.get(ENABLED_KEY)
        ready = True
    except Exception:
        ready = False
        default_value = "absent"

    register_relation(spark, args.rows)
    query = "SELECT s FROM t WHERE g = 3 ORDER BY id"

    section(f"BASELINE — {ENABLED_KEY} = {default_value}")
    df = spark.sql(query)
    plan = plan_of(df)
    show_plan(plan, args.rows)
    print("\n  One Exchange node: Spark pays for a 200-way distributed shuffle on a "
          "query that lives on a laptop and did not need one.")

    if not ready:
        print(f"\n  This Spark predates Feather — `{ENABLED_KEY}` does not exist until "
              "4.3, where it defaults to false.")
        print("  Run this demo against a Spark 4.3 (or branch-4.3) build to see the "
              "shuffle elided.")
        spark.stop()
        return 0

    section(f"FEATHER ENABLED — {ENABLED_KEY} = true")
    spark.conf.set(ENABLED_KEY, "true")
    plan = plan_of(spark.sql(query))
    show_plan(plan, args.rows)
    print(f"\n  Exchange nodes: 1 -> {exchanges(plan)}. The shuffle is gone; the sort "
          "runs over a LocalTableScan as a single task." if exchanges(plan) == 0 else
          f"\n  Exchange nodes stayed at {exchanges(plan)} for this shape.")

    section(f"TIMING — median of {args.reps}, off vs on")
    spark.conf.set(ENABLED_KEY, "false")
    r_off = timed(lambda: spark.sql(query).collect(), args.reps)
    spark.conf.set(ENABLED_KEY, "true")
    r_on = timed(lambda: spark.sql(query).collect(), args.reps)
    print(f"\n  {r_off['median_ms']:>7.1f} ms   {ENABLED_KEY}=false")
    print(f"  {r_on['median_ms']:>7.1f} ms   {ENABLED_KEY}=true")
    print(f"     (min/max off {r_off['min_ms']:.1f}/{r_off['max_ms']:.1f} ms, "
          f"on {r_on['min_ms']:.1f}/{r_on['max_ms']:.1f} ms)")
    print("     Local-mode timing is noisy: the plan is the claim, the median is the hint.")

    section(f"THE GUARDRAIL — {THRESHOLD_KEY} = {spark.conf.get(THRESHOLD_KEY)}")
    big = 2001
    register_relation(spark, big)
    # No WHERE here: the whole relation survives into the sort, so it stays over the cap.
    plan = plan_of(spark.sql("SELECT s FROM t ORDER BY id"))
    show_plan(plan, big)
    if exchanges(plan) >= 1:
        print(f"\n  With {big} rows the exchange returns: the rule caps in-memory "
              "relations at 1,000 rows by default, so a sizable fixture stays shuffled "
              "even with the flag on.")

    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
