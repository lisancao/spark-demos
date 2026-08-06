# Project Feather: making Spark fast for local prototyping

*By Lisa N. Cao and Daniel Tenedorio*

Apache Spark was built to process data at any scale, and for large jobs it does. On a laptop, over a few hundred megabytes, the same architecture that makes a distributed job reliable makes an interactive one slow. Project Feather is the community's proposal to fix that.

The proposal ([SPARK-56978](https://issues.apache.org/jira/browse/SPARK-56978)) was authored by Daniel Tenedorio and Liang-Chi Hsieh, discussed on the Spark developer list from 4 May 2026, and passed its vote on 20 May 2026. Part of the work is merged for Spark 4.3. The rest is in progress.

## What the proposal targets

Feather's objective is narrow. The proposal aims to improve Spark's usability and interactivity for small-data queries, making it more useful for individuals and beginners. It does not aim to outperform specialized single-node engines. The goal is to lower the barrier to entry, so that a newcomer's first experience of Spark on a laptop is a reasonable one. The path from there to a cluster should then involve no change of tools.

That framing rules some things out. Feather is not a new engine, and it changes no APIs. The SQL language, the SQL API, and the DataFrame APIs in Python and Scala all stay as they are, deliberately, because years of community work sit behind them. What changes is the fixed cost Spark pays around a query.

## The problem

Spark's architecture is optimized for distributed, large-scale processing. Every query gets a plan, stages, and tasks. The scheduler dispatches those tasks to executors, serializing and deserializing task descriptions on the way. Catalyst traverses the plan repeatedly for analysis and optimization. Blocking shuffles separate the stages, which is what allows adaptive query execution to re-plan on real statistics. All of it serves fault tolerance, transient failure recovery, and adaptive execution.

Individually these costs are small, tens of milliseconds and sometimes less. Nobody notices them in a job that runs for an hour. The SPIP states the small-data consequence directly: queries over less than 100 MB often run for three seconds or more.

Three seconds is long enough to change behavior. Users doing basic analysis reach for a simpler single-node engine, which the proposal identifies as a barrier to Spark adoption rather than a preference. The SPIP does not rest on the authors' own impressions here. It cites third-party writing on Spark's small-data performance: a Spark versus Dask comparison, an essay on Spark and not-so-big data, and a runtime benchmark. The motivation is a reputation problem visible from outside the project.

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

The proposal groups its optimizations into three categories. They differ in risk, in how far along they are, and in how much of Spark they touch.

![The three Project Feather categories and their status.](graphics/f2-three-categories.png)

### Query compilation and task scheduling

Query compilation covers analysis, optimization, and physical planning. On large data it is noise; on small data it dominates. This category collects optimizer and planner improvements aimed at small-data scenarios, reduced metadata access times, and lower task serialization and deserialization overhead.

In the proposal's example, when the planner knows a scan comprises exactly one file it can report `SinglePartition` output partitioning instead of the default. Spark then skips an intermediate shuffle before a following aggregation or hash join. A prototype of a filter-and-sort over a few thousand rows went from two stages and 330 milliseconds to one stage and 150 milliseconds, which the SPIP describes as a 2x boost on that example.

A larger piece in this category is the [single-pass analyzer](https://issues.apache.org/jira/browse/SPARK-49834), a separate and still-open proposal that rewrites Catalyst's analysis as a single tree traversal. Its own scope note is worth reading alongside Feather's: it does not target average-query latency, and Feather claims its benefit for queries of high plan complexity.

Status: described in the SPIP, but the umbrella has three subtasks and none is this category. Milestone 1 has not started as filed work.

### Arrow-based df.cache

`df.cache` is the workhorse of ad hoc analysis. You compute the expensive part once, cache it, then iterate against the cached result. Feather gives it a dedicated track because that loop is where local prototyping actually happens.

Arrow format replaces Spark's existing in-memory cache representation as an option, not as the default. Two payoffs are expected: vectorized columnar reads, and a smaller footprint from Arrow IPC compression, so more of the working set fits in memory.

Benchmark results are already in the tree. The committed benchmarks show Arrow competitive with or faster than the default on primitive and columnar workloads, with the largest win on the zero-copy re-cache path, and the default still faster at higher compression levels. That mixed picture is why it ships opt-in, selected through `spark.sql.cache.serializer`.

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

Documented risks follow. Using virtual threads introduces a dependency on JDK 21 or later, which the proposal frames as conditional, with fallback to platform threads for older environments. Buffer sizing could cause out-of-memory crashes if misconfigured, mitigated with conservative defaults of 100 elements per queue. Complex locking in the channel gates carries a deadlock risk, to be addressed with concurrency testing and simple lock ordering.

There is also a deliberate loss. Adaptive query execution works at shuffle boundaries, so removing the shuffle removes AQE's opportunity to re-plan. That is why the planner has to be confident the query is small before choosing this path.

Status: part one merged ([SPARK-57851](https://issues.apache.org/jira/browse/SPARK-57851)); local repartition ([SPARK-57399](https://issues.apache.org/jira/browse/SPARK-57399)) open; multi-threaded execution not yet contributed.

## Scope boundaries

Feather is scoped to local mode. Three boundaries follow from that, and they explain design decisions that would otherwise look conservative.

**Clusters are out of scope.** The proposal's reason is a capability constraint: shuffle-free execution only works when all data fits and is processed in a single JVM, so it cannot replace distributed shuffle for multi-node clusters. Improvements to cluster execution will be tangential only, with reduced task serialization named as the example that generalizes. Daniel also raised a maintenance concern in conversation: a second execution path in distributed jobs means anyone debugging a production pipeline has to ask which path their query took.

**Spark Connect is independent.** Connect decouples the client from the cluster, so you write logic against one API and run it against a driver elsewhere, which solves a version-coupling problem rather than a latency one. Feather addresses how fast the engine executes locally. You can run a Connect server on your own machine and get Feather's benefits, or use classic mode where your program becomes the driver and get them there too.

**Session creation is adjacent, not included.** It came up in discussion, and the authors' reply was that it could be useful to look at but risked making the proposal too complex, so it was left for separate investigation. The motivation raised was automated test cycles, where every run starts a new session. It appears in no milestone and no subtask.

## Status and what to expect

Apache Spark 4.2.0 is the current release and **none of Feather's configuration flags exist in it**. The merged work is present in `branch-4.3` with fix version 4.3.0, which has not shipped. The SPIP estimates three to six months depending on how many engineers work concurrently.

| Category | Merged | Available |
|---|---|---|
| Query compilation and task scheduling | No subtask filed | Unscheduled |
| Arrow-based `df.cache` | Yes | 4.3, opt-in via `spark.sql.cache.serializer` |
| Shuffle-free execution, part 1 | Yes | 4.3, off by default, capped at 1,000 rows for in-memory relations |
| Shuffle-free execution, part 2 | No | Unscheduled |
| Local repartition | No, ticket open | Unscheduled |

Two details in that table will shape your first experience of 4.3. The shuffle-free rule ships disabled, so upgrading alone changes nothing until you set `spark.sql.optimizer.singleTaskExecution.enabled`. And for in-memory relations it applies only at or below 1,000 rows by default, so a larger test fixture stays ineligible even with the flag on. The end state the proposal describes needs no tuning, since Spark knows when it is running locally; the current state is opt-in while the work stabilizes.

Success criteria come from the SPIP itself: three milestones, one per category, and a performance check requiring macro-benchmarks for each so the gains are reproducibly verifiable. That last commitment is the useful one, because how much faster depends on your machine, your data, and your query shape. If you want your own numbers before and after upgrading, a [companion harness](https://github.com/lisancao/spark-42-demos) measures session creation, small-query latency, and the shuffle count in your plans.

## Getting involved

The umbrella JIRA [SPARK-56978](https://issues.apache.org/jira/browse/SPARK-56978) and its subtasks are where the work is tracked; the DISCUSS and VOTE threads closed in May 2026. Pull requests are welcome, and the open subtask on local repartition is the clearest place to help. The authors engaged with community suggestions in the proposal's comment thread, though not everything raised was adopted.

For a project whose original promise was running anywhere, from a laptop to a thousand nodes, closing the gap at the small end is a return to form rather than a new direction.

## About the authors

**Daniel Tenedorio** is a software engineer working on Apache Spark and a Spark committer, contributing since 2022, initially on SQL features. He co-authored the Project Feather proposal with Liang-Chi Hsieh.

**Lisa N. Cao** works on Apache Spark at Databricks and hosts the Apache Spark YouTube channel.

*Based on a conversation on the Apache Spark YouTube channel and the [public SPIP document](https://docs.google.com/document/d/1Nphejrf_vh4YRECn0JPgKClqxDS_lB6wufZFJQxyY98/edit). Claims attributed to the proposal were checked against that document and its comment thread; config names, defaults, and merge status were read from `branch-4.3` of the Apache Spark source and from JIRA. [Link to video]*
