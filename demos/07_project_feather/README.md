# Project Feather baseline harness

Companion code for the blog post *How Project Feather makes Spark fast on a laptop*.

Project Feather ([SPARK-56978](https://issues.apache.org/jira/browse/SPARK-56978)) is
a Spark Improvement Proposal to cut local-mode query latency. This harness measures
the overheads it targets, on whatever Spark you have installed.

## Quick start

```bash
python3 bench/feather_baseline.py --reps 9
```

Requires an Apache Spark install and PySpark. Nothing to build.

## Why a baseline, not a before/after

**None of Feather's configuration flags exist in Spark 4.2.0**, the current release.
Verified by probing a live session rather than reading release notes:

| Config | 4.2.0 | Note |
|---|---|---|
| `spark.sql.optimizer.singleTaskExecution.enabled` | absent | Public config in 4.3, defaults to **false** |
| `spark.sql.optimizer.singleTaskExecution.localTableScan.threshold` | absent | Defaults to **1000 rows** in 4.3 |
| `spark.sql.execution.arrow.cache.prefetch.enabled` | absent | |
| `spark.sql.unionOutputPartitioning.enabled` | absent | |
| `spark.sql.cache.serializer` | present | Predates Feather. 4.3 adds `ArrowCachedBatchSerializer` as an option; the default is unchanged |

Two things this table is designed to prevent you from assuming. The shuffle-free rule
ships **off** in 4.3, so upgrading alone changes nothing. And for in-memory relations it
only applies at or below **1,000 rows**, which is why this harness defaults to 800: a
5,000-row fixture would stay ineligible even with the flag on, and you would conclude
the feature does nothing.

The Arrow cache ([SPARK-57268](https://issues.apache.org/jira/browse/SPARK-57268))
and shuffle-free single-task execution
([SPARK-57851](https://issues.apache.org/jira/browse/SPARK-57851)) are resolved on
master and targeted for 4.3.0, which has not shipped. Local repartition
([SPARK-57399](https://issues.apache.org/jira/browse/SPARK-57399)) is still open.

So a true before/after is not runnable yet. What this harness does instead is measure
the baseline and probe for the configs, so the same script tells you when your build
has them. Run it now, run it again after upgrading, and the delta is your own number
rather than someone else's benchmark.

## What it measures

Each measurement maps to a claim in the SPIP:

| Measurement | Why |
|---|---|
| Session creation | Community feedback on the SPIP: sessions can take multiple seconds. Matters for agents issuing many small queries. |
| `Exchange` count in the plan | Categories 1 and 3: small queries get shuffles they do not need. Feather elides them. |
| Filter + sort latency | The SPIP's own example shape: a sort over a small scan. |
| Aggregate latency | The other shuffle-inducing operator `MarkSingleTaskExecution` covers. |
| Cached query latency | Category 2: `df.cache` is the ad hoc prototyping path. |
| `SELECT 1` latency | The floor. A query with no data still pays planning and scheduling. |

Methodology notes, since they affect how much to trust the numbers:

- The first run of each measurement is discarded as warm-up, so JIT and codegen cost
  does not land in the reported figure.
- Medians are reported alongside min and max. On a laptop with other work running,
  the max is often much higher; the median is the honest number.
- `Exchange` count is read from the physical plan, not inferred from timing.

## Sample output

Spark 4.2.0, Apple silicon, 5,000 in-memory rows, 9 reps:

```
Spark 4.2.0 on Darwin arm64
Feather configs present: 0 of 8
  -> This Spark predates Feather. Numbers below are the baseline it improves on.

  session creation        3342.3 ms
  filter + sort            190.7 ms (median of 9)   exchanges=1
  aggregate                131.6 ms (median of 9)   exchanges=1
  cached query              47.8 ms (median of 9)
  SELECT 1                  20.4 ms (median of 18)
```

Expect variance. Across runs on the same machine, session creation ranged from 2.9 to
4.6 seconds and filter-and-sort from 162 to 191 ms. Quote ranges rather than single
figures, and compare your own before and after rather than these numbers.

Two things worth noting in that output. A sort over five thousand rows plans a
shuffle, which is the exact case Feather's `MarkSingleTaskExecution` rule removes. And
`SELECT 1`, with no data at all, costs 20 ms, which is the floor planning and
scheduling impose.

## What this harness does not do

- **It does not benchmark Feather.** The optimizations are not in a release yet.
- **It is not a comparison against other engines.** The SPIP explicitly does not aim
  to outperform specialized single-node engines, so a DuckDB or Polars race would be
  measuring something the proposal is not claiming.
- **It does not test correctness.** These are timing and plan-shape measurements.

If you build Spark from master, the harness will report the Feather configs as
present and you can enable them to see the difference. That path is not scripted here
because a source build is a multi-hour prerequisite.

## Files

```
bench/feather_baseline.py   the harness
bench/results.json          written on each run
graphics/                   diagrams used in the blog post (SVG source + PNG)
```
