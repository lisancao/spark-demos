# Project Feather: making Spark fast for local prototyping

*By Lisa N. Cao and Daniel Tenedorio*

Apache Spark was built to process data at any scale, and for large jobs it does. On a laptop, over a few hundred megabytes, the same architecture that makes a distributed job reliable makes an interactive one slow. Project Feather is the community's proposal to fix that.

Daniel Tenedorio and Liang-Chi Hsieh brought Feather to the Spark developer list in May 2026, where it passed a community vote as [SPARK-56978](https://issues.apache.org/jira/browse/SPARK-56978). Part of the work is merged for Spark 4.3. The rest is still being built.

## What the proposal targets

Feather's objective is narrow. It makes Spark more usable and interactive for small-data queries, aimed at individuals and beginners rather than at benchmark wins against specialized single-node engines. The point is that a newcomer's first experience of Spark on a laptop should be a reasonable one, and that the path from there to a cluster should involve no change of tools.

That framing rules some things out. Feather is not a new engine, and it changes no APIs. The SQL language, the SQL API, and the DataFrame APIs in Python and Scala all stay as they are, deliberately, because years of community work sit behind them. What changes is the fixed cost Spark pays around a query.

## The problem

Spark's architecture is optimized for distributed, large-scale processing. Every query gets a plan, stages, and tasks. The scheduler dispatches those tasks to executors, serializing and deserializing task descriptions on the way. Catalyst traverses the plan repeatedly for analysis and optimization. Blocking shuffles separate the stages, which is what allows adaptive query execution to re-plan on real statistics. All of it serves fault tolerance, transient failure recovery, and adaptive execution.

Individually these costs are small, tens of milliseconds and sometimes less. Nobody notices them in a job that runs for an hour. Under 100 MB, though, they add up to something you feel: queries that often take three seconds or more.

Three seconds is long enough to change behavior. Users doing basic analysis reach for a simpler single-node engine, and once they do, they rarely come back to Spark for the next small job either. That habit is a barrier to adoption rather than a preference, and it is visible from outside the project: benchmarks and essays comparing Spark unfavorably to Dask and to single-node tools on small data are easy to find, and Feather's authors cite them.

![Fixed overhead dominates a small query and is a rounding error on a large ETL job.](graphics/f1-overhead-stack.png)

The shape of the problem is visible in a physical plan. Sorting a few hundred rows on Spark 4.2 produces this:

```
AdaptiveSparkPlan isFinalPlan=false
+- Project [s#2]
   +- Sort [id#0L ASC NULLS FIRST], true, 0
      +- Exchange rangepartitioning(id#0L ASC NULLS FIRST, 200), ENSURE_REQUIREMENTS
         +- Project [cast(id#0L as string) AS s#2, id#0L]
            +- Filter ((id#0L % 7) = 3)
               +- Range (0, 800, step=1, splits=10)
```

The `Exchange` line shuffles 800 rows across 200 partitions so the sort has the range partitioning it requires. `ENSURE_REQUIREMENTS` marks it as inserted to satisfy that requirement, not because the data needed moving. On this dataset the shuffle is pure overhead, and removing it is one of the things Feather does.

## What the work entails

Feather's optimizations fall into three groups. They differ in risk, in how far along they are, and in how much of Spark they touch.

![The three Project Feather categories and their status.](graphics/f2-three-categories.png)

### Query compilation and task scheduling

Query compilation covers analysis, optimization, and physical planning. On large data it is noise; on small data it dominates. This category collects optimizer and planner improvements aimed at small-data scenarios, reduced metadata access times, and lower task serialization and deserialization overhead.

One concrete change: when the planner knows a scan comprises exactly one file, it can report `SinglePartition` output partitioning instead of the default. Spark then skips an intermediate shuffle before a following aggregation or hash join. In an early prototype, a filter-and-sort over a few thousand rows went from two stages and 330 milliseconds to one stage and 150 milliseconds, a 2x improvement on that query.

A larger piece of this work is the [single-pass analyzer](https://issues.apache.org/jira/browse/SPARK-49834), tracked separately and still open, which rewrites Catalyst's analysis as a single tree traversal. Temper your expectations on that one: it targets queries with complex plans, not the average query, where latency is dominated by other things.

Status: no ticket filed yet. This category is described in the proposal, but the three open subtasks all belong to the other two.

### Arrow-based df.cache

`df.cache` is the workhorse of ad hoc analysis. You compute the expensive part once, cache it, then iterate against the cached result. Feather gives it a dedicated track because that loop is where local prototyping actually happens.

Arrow format replaces Spark's existing in-memory cache representation as an option, not as the default. Two payoffs are expected: vectorized columnar reads, and a smaller footprint from Arrow IPC compression, so more of the working set fits in memory.

The numbers are already public, and they are mixed. Arrow is competitive with or faster than the existing format on primitive and columnar data, and it wins biggest when re-reading a cache without copying. At higher compression levels the old format still wins. That is why Arrow arrives as a choice rather than a default: you select it through `spark.sql.cache.serializer`.

Status: merged ([SPARK-57268](https://issues.apache.org/jira/browse/SPARK-57268)), present in `branch-4.3`.

### Shuffle-free execution

Spark separates stages with blocking shuffles: data is serialized, written to disk, then read back. For a distributed job that boundary is what makes fault tolerance and adaptive re-planning possible. For a query that fits on one node, it is cost without benefit.

![Blocking shuffle versus in-process channels.](graphics/f3-shuffle-vs-channel.png)

The work has two parts. The first, merged for 4.3, adds a conservative optimizer rule called `MarkSingleTaskExecution`. It matches a plan that reads a single small file, or a small in-memory relation, with at most one shuffle-inducing operator above it: sort, aggregate, window, expand, or limit and offset. Eligible scans report `SinglePartition` output partitioning, which lets `EnsureRequirements` elide the shuffle. Joins are deliberately left for a follow-up.

For the second part, not yet contributed, in-process channels replace the disk hop:

```
Traditional execution:        Multi-threaded execution:
Task -> Disk -> Task          Task -> Channel -> Task (in-process)
Serialize to and from disk     Direct memory transfer
```

Each input partition gets an asynchronous sender task, with Java virtual threads as the proposed mechanism. Threads communicate over FIFO queues with configurable size limits and automatic backpressure, so senders pause when a channel fills.

The risks are real and named. Virtual threads would require JDK 21 or later, so that mechanism is conditional, with a fallback to platform threads for older environments. Buffer sizing could cause out-of-memory crashes if misconfigured, mitigated with conservative defaults of 100 elements per queue. Complex locking in the channel gates carries a deadlock risk, to be addressed with concurrency testing and simple lock ordering.

There is also a deliberate loss. Adaptive query execution works at shuffle boundaries, so removing the shuffle removes AQE's opportunity to re-plan. That is why the planner has to be confident the query is small before choosing this path.

Status: part one merged ([SPARK-57851](https://issues.apache.org/jira/browse/SPARK-57851)); local repartition ([SPARK-57399](https://issues.apache.org/jira/browse/SPARK-57399)) open; multi-threaded execution not yet contributed.

## Scope boundaries

Feather is scoped to local mode. Three boundaries follow from that, and they explain design decisions that would otherwise look conservative.

**Clusters are out of scope**, and the reason is capability rather than preference. Shuffle-free execution only works when all the data fits and is processed in a single JVM, so it cannot replace distributed shuffle on a multi-node cluster. Cluster jobs will pick up some benefit incidentally, mostly from cheaper task serialization. There is a maintenance argument too: a second execution path in distributed jobs would mean anyone debugging a production pipeline has to work out which path their query took.

**Spark Connect is independent.** Connect decouples the client from the cluster, so you write logic against one API and run it against a driver elsewhere, which solves a version-coupling problem rather than a latency one. Feather addresses how fast the engine executes locally. You can run a Connect server on your own machine and get Feather's benefits, or use classic mode where your program becomes the driver and get them there too.

**Session creation is a neighboring problem**, deliberately left out. Someone raised it during review, pointing at automated test cycles where every run pays to start a new session. The authors agreed it was worth looking at and then set it aside to keep the scope manageable, so no ticket covers it today.

## Status and what to expect

Apache Spark 4.2.0 is the current release, and **none of Feather's configuration flags exist in it**. The merged work sits in `branch-4.3`, targeted at 4.3.0, which is in release candidate (rc1 published). Estimates put the remaining work at three to six months, depending on how many people are on it.

| Category | Merged | Available |
|---|---|---|
| Query compilation and task scheduling | No subtask filed | Unscheduled |
| Arrow-based `df.cache` | Yes | 4.3, opt-in via `spark.sql.cache.serializer` |
| Shuffle-free execution, part 1 | Yes | 4.3, off by default, capped at 1,000 rows for in-memory relations |
| Shuffle-free execution, part 2 | No | Unscheduled |
| Local repartition | No, ticket open | Unscheduled |

Two details in that table will shape your first experience of 4.3. The shuffle-free rule ships disabled, so upgrading alone changes nothing until you set `spark.sql.optimizer.singleTaskExecution.enabled`. And for in-memory relations it applies only at or below 1,000 rows by default, so a larger test fixture stays ineligible even with the flag on. The eventual goal is that none of this needs tuning, since Spark already knows when it is running locally. For now it is opt-in while the code settles.

Each of the three categories has to clear its own milestone, and each comes with macro-benchmarks so anyone can reproduce the gains. That last part matters more than it sounds, because how much faster you get depends on your machine, your data, and your query shape. A [companion harness](https://github.com/lisancao/spark-demos) measures session creation, small-query latency, and the shuffle count in your plans, so you can take your own before-and-after reading across the upgrade.

## Getting involved

Work is tracked on [SPARK-56978](https://issues.apache.org/jira/browse/SPARK-56978) and its subtasks; the mailing list discussion wrapped up in May 2026. Pull requests are welcome, and local repartition is the clearest thing to pick up, since the ticket is open and unclaimed. Community suggestions did shape the plan during review, though not every idea made the cut.

For a project whose original promise was running anywhere, from a laptop to a thousand nodes, closing the gap at the small end is a return to form rather than a new direction.

## About the authors

**Daniel Tenedorio** is a software engineer working on Apache Spark and a Spark committer, contributing since 2022, initially on SQL features. He co-authored the Project Feather proposal with Liang-Chi Hsieh.

**Lisa N. Cao** works on Apache Spark at Databricks and hosts the Apache Spark YouTube channel.

*Based on a conversation on the Apache Spark YouTube channel and the [public SPIP document](https://docs.google.com/document/d/1Nphejrf_vh4YRECn0JPgKClqxDS_lB6wufZFJQxyY98/edit). Technical claims were checked against the proposal and its comment thread; config names, defaults, and merge status come from `branch-4.3` of the Apache Spark source and from JIRA.*
