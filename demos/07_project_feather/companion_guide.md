# How Project Feather makes Spark fast on a laptop

*By Lisa N. Cao and Daniel Tenedorio*

## Key takeaways

- **Project Feather ([SPARK-56978](https://issues.apache.org/jira/browse/SPARK-56978)) is a Spark improvement proposal to cut local-mode latency**, targeting the case where you are prototyping on a laptop over a small dataset rather than running a distributed job.
- **The problem is accumulated overhead, not one bottleneck.** Scheduling, task serialization, plan traversal, and shuffles each cost a hundred milliseconds or so. That is invisible in an hour-long ETL job and dominant on 100 MB.
- **It is not a new engine.** The SQL and DataFrame APIs stay exactly as they are. Feather is a collection of targeted optimizations under one theme, grouped into three categories.
- **Nothing about it is opt-in for users.** Spark already knows when it is running in local mode, so the improvements are meant to apply automatically when that is true and stay out of the way of cluster jobs.
- **On stock Spark 4.2, a 5,000-row filter-and-sort still plans a shuffle and a session takes over three seconds to start.** Both are measurable today with the companion harness, and both are what Feather removes.

## What is Project Feather?

Project Feather is a Spark Improvement Proposal, authored by Daniel Tenedorio and Liang-Chi Hsieh, to make Apache Spark queries run faster in local mode. It targets small-data interactive work: the prototyping loop on a laptop, not the distributed pipeline.

The stated goal is worth quoting precisely, because it is narrower than "make Spark fast." The proposal does not aim to outperform specialized single-node engines. It aims to lower the barrier to entry, so that someone starting out on a laptop has a reasonable experience and can grow into a cluster later without switching tools.

## Why is Spark slow on small data?

Because Spark's architecture is built for distributed reliability, and that machinery has a fixed cost per query that small datasets cannot amortize.

Every query gets a plan, stages, and tasks. The scheduler dispatches those tasks to executors. Along the way Spark serializes and deserializes task descriptions, traverses the query plan repeatedly for analysis and optimization, and inserts blocking shuffles at stage boundaries so that adaptive query execution can re-plan based on real statistics. All of that exists for good reasons: fault tolerance, transient failure recovery, and the ability to adapt a long-running job as it learns about its data.

The costs are individually small. A hundred milliseconds for scheduling here, a hundred there. Nobody notices in a job that runs for an hour. The SPIP puts the small-data consequence bluntly: queries over less than 100 MB can take three seconds or more.

That is the gap that sends people to a specialized single-node engine for exploratory work, and it is the reason the proposal exists. Notably, the SPIP does not rest on the authors' own impressions: it cites third-party benchmarks and critiques of Spark's small-data performance as evidence, including [a Spark versus Dask comparison](https://medium.com/coiled-hq/spark-vs-dask-27216502b129) and [an argument that Spark is not always the right choice for not-so-big data](https://medium.com/@pined.lao/why-spark-isnt-always-the-best-choice-for-not-so-big-data-f7b888c3ce59). The motivation is a reputation problem the community can see from outside.

![Fixed overhead dominates a small query and is a rounding error on a large ETL job. Measured on Spark 4.2.0: a 5,000-row filter and sort takes 191 ms and still plans one shuffle.](graphics/f1-overhead-stack.png)

### What the overhead looks like on Spark 4.2

Measured on stock Spark 4.2.0, before any Feather work is available, over an in-memory table of 5,000 rows:

| Operation | Observed range | Shuffles in plan |
|---|---|---|
| Session creation | 2.9 to 4.6 s (median 3.5 s) | n/a |
| `SELECT s FROM t WHERE g = 3 ORDER BY id` | 162 to 191 ms | 1 |
| `SELECT g, count(*) FROM t GROUP BY g` | 83 to 132 ms | 1 |
| Query over a cached DataFrame | 31 to 48 ms | n/a |
| `SELECT 1` | 16 to 20 ms | n/a |

Two things stand out. A sort over five thousand rows plans a shuffle it does not need, because the planner does not know the scan is small enough to run in one task. And `SELECT 1`, a query with no data at all, still costs around 20 milliseconds, which is the floor that scheduling and planning impose.

Ranges rather than single figures, because a laptop under real load is noisy: these are medians across repeated runs, with session creation measured in a fresh process each time. Session creation is the number that surprised the authors. It was not in the original proposal. It came from community feedback after the SPIP was published, and it matters for a reason that did not exist a few years ago: AI agents issue many small queries, and a multi-second session start is paid on every one.

## What are the three categories of work?

Feather groups its optimizations into three tracks. The split matters because they have different risk profiles and different delivery timelines.

| Category | What it changes | Where it lands |
|---|---|---|
| Query compilation and task scheduling | Cheaper analysis, optimization, and planning; less task serialization; fewer plan traversals | Merged, targeted for 4.3 |
| Arrow-based `df.cache` | Columnar cache format, replacing a less efficient one | [SPARK-57268](https://issues.apache.org/jira/browse/SPARK-57268), merged, targeted for 4.3 |
| Shuffle-free execution | Small queries run in one task, or exchange data over in-process channels instead of disk | [SPARK-57851](https://issues.apache.org/jira/browse/SPARK-57851) merged for 4.3; multi-threaded execution still ahead |

![The three Project Feather categories: query compilation and task scheduling, Arrow-based df.cache, and shuffle-free execution, with merge status for each.](graphics/f2-three-categories.png)

### Category 1: stop paying for planning you do not need

Query compilation covers analysis, optimization, and physical planning. On a large dataset it is noise. On a small one it can be most of the wall clock.

The concrete example from the proposal: when the planner knows a scan comprises exactly one file, it can report `SinglePartition` output partitioning instead of the default `UnknownPartition`. That lets Spark skip an intermediate shuffle before a following aggregation or hash join. In the proposal's prototype, a filter-and-sort over a few thousand rows went from two stages and 330 milliseconds to one stage and 150 milliseconds. A 2x improvement, from deleting a shuffle that was never needed for correctness.

The larger piece in this category is the [single-pass analyzer](https://issues.apache.org/jira/browse/SPARK-49834), a separate SPIP that rewrites Catalyst's analysis as one bottom-up tree traversal. That work is incremental and long-running, with pieces landing across 4.0 and 4.1. The bar the authors set for it is strict: query plans must be identical before and after the rewrite, which is enforced rather than hoped for.

### Category 2: make the cache worth using

`df.cache` is the workhorse of ad hoc analysis. You do the expensive part once, cache it, then iterate against the cached result. It is important enough to Feather that it got its own track.

The change is to store the cache in Apache Arrow format instead of Spark's existing in-memory representation. Two payoffs follow. Reads get faster because Arrow is columnar and supports vectorized access. And the cache gets smaller, because columnar data compresses better, which means more of the working set fits in memory.

The risk the SPIP names is honest: the conversion cost to and from Arrow must not exceed what the compression and vectorized reads win back. That is a microbenchmark question, and the proposal commits to answering it that way.

### Category 3: stop shuffling through the disk

Category 3 is the most invasive change and the one still mostly ahead.

Spark's stages are separated by blocking shuffles. Data is serialized, written to disk, then read back by the next stage. For a distributed job that boundary is what makes fault tolerance and adaptive re-planning possible. For a query that fits on one node, it is pure cost.

Feather's approach has two parts. The first, already merged for 4.3, is a conservative optimizer rule (`MarkSingleTaskExecution`) that identifies small single-partition scans with a shuffle-inducing operator on top, such as a sort, aggregate, distinct, window, or limit, and lets `EnsureRequirements` elide the shuffle. It is gated behind internal configs under `spark.sql.optimizer.singleTaskExecution.*` and is off by default. Joins are deliberately excluded from this first pass.

![Blocking shuffle writes to disk between stages, which buys fault tolerance and an adaptive query execution boundary. Feather's in-process channels transfer data directly in memory, giving up the AQE boundary in exchange.](graphics/f3-shuffle-vs-channel.png)

The second part, not yet contributed, replaces the disk hop with in-process channels:

```
Traditional execution:        Multi-threaded execution:
Task -> Disk -> Task          Task -> Channel -> Task (in-process)
Serialize to and from disk     Direct memory transfer
```

Each input partition gets its own asynchronous sender task on a Java virtual thread, and threads communicate over FIFO channels with automatic backpressure. The design brings real risks, and the SPIP lists them rather than glossing: a dependency on JDK 21 or later for virtual threads, with fallback to platform threads; buffer sizing that could cause out-of-memory crashes if misconfigured, mitigated with conservative defaults; and the deadlock risk inherent in any channel-and-lock design.

There is also a deliberate loss. Adaptive query execution works at shuffle boundaries. Remove the shuffle and you remove AQE's opportunity to re-plan, which is exactly why the planner has to be confident the query is small before choosing this path.

## Will this work on clusters too?

Not initially, and the reason is about debuggability rather than difficulty.

Feather is scoped to local mode, keyed off the fact that Spark already knows when it is running with the `LocalSchedulerBackend`. The authors could extrapolate some of it to clusters later, and some pieces, particularly the planning and serialization work, are general enough to help everywhere. But multi-threaded shuffle-free execution is a genuinely different execution model, and adding a second code path to distributed jobs means anyone debugging a production pipeline has to ask which path their query took. That cost is not worth paying for a prototyping optimization.

The line the proposal draws is that improvements to cluster execution will be tangential only.

## How does this relate to Spark Connect?

Project Feather and Spark Connect are independent, and both should improve.

Spark Connect decouples the client from the cluster, so you write logic against one API and run it against a Spark driver elsewhere. It solves a version-coupling problem: upgrade the cluster without rewriting jobs, use clients in different languages, and keep memory-hungry client work from competing with the driver's planning memory.

Feather is about how fast the engine executes locally. You can run a Spark Connect server on your own machine, connect a local client, and get Feather's benefits; you can also use classic mode, where your program becomes the driver, and get them there too. Spark Connect is the better default for most people because the same code moves between a laptop and any cluster without changes, but it is orthogonal to what Feather does.

## How will we know if it worked?

The SPIP commits to three milestones, one per category, plus a reproducibility requirement that is the most useful part for anyone evaluating the work later:

| Milestone | Scope |
|---|---|
| 1 | The query compilation and task scheduling improvements, grouped as one milestone since they are many small independent changes |
| 2 | Implement and launch the columnar `df.cache` |
| 3 | Implement and launch multi-threaded shuffle-free execution in local mode |

The performance check is to build macro-benchmarks for each milestone so the gains are reproducibly verifiable. That matters because the honest answer to "how much faster" depends on your machine, your data, and your query shape. A committed benchmark suite means the claim can be checked rather than taken on faith, which is also why the companion harness measures your baseline instead of quoting someone else's speedup.

## What can I use today?

Nothing yet, and that is worth being direct about, because the timeline is easy to misread.

Apache Spark 4.2.0 is the current release, and **none of Feather's configuration flags exist in it**. The Arrow cache ([SPARK-57268](https://issues.apache.org/jira/browse/SPARK-57268)) and shuffle-free single-task execution ([SPARK-57851](https://issues.apache.org/jira/browse/SPARK-57851)) are both resolved on master and targeted for 4.3.0, which has not shipped. Local repartition ([SPARK-57399](https://issues.apache.org/jira/browse/SPARK-57399)) is still open. The SPIP itself estimates three to six months of work depending on how many engineers are involved.

What you can do now is measure the baseline. The companion harness reports session creation time, small-query latency, and the shuffle count in your plans on whatever Spark you have installed, and it probes for Feather's configs so the same script tells you when your build has them:

```bash
python3 bench/feather_baseline.py --reps 9
```

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

Run it once now and again after upgrading to 4.3, and the delta is your answer rather than someone else's benchmark.

## Frequently asked questions

**Is Project Feather a new execution engine?**

No. It is a collection of targeted optimizations to the existing engine, grouped under one theme. The SQL language, the SQL API, and the DataFrame APIs in Python and Scala are unchanged, deliberately, because the community has invested years in them.

**Will I need to change my code or set flags?**

The design goal is no. Spark knows when it is in local mode, so the intent is that these optimizations apply automatically in that environment. Individual pieces have configs during development, and the shuffle-free rule is currently off by default while it stabilizes.

**Does this make Spark competitive with single-node engines like DuckDB or Polars?**

That is not the goal the proposal sets. It aims to lower the barrier to entry so a beginner on a laptop has a reasonable experience, not to win single-node benchmarks. The argument for staying on Spark is the ecosystem and the fact that the same code scales to a cluster without a migration.

**Will Spark ever be a millisecond-latency serving system?**

No, and the authors say so. The goal is a fast prototyping loop, getting most local queries under a second, not real-time serving.

**Why does session creation matter so much?**

It was community feedback rather than part of the original proposal. Creating a Spark session can take multiple seconds, which is irrelevant to a large ETL job and significant when you are iterating locally. It matters more now that AI agents issue many small queries in sequence, each paying that cost.

**How can I get involved?**

The SPIP thread on the Spark developer mailing list is the main venue, and pull requests on GitHub are welcome. The authors have already folded community suggestions, including the session-creation work, into the plan.

## About the authors

**Daniel Tenedorio** is a software engineer working on Apache Spark and a Spark committer, with over four years contributing to the project, initially on SQL features. He co-authored the Project Feather SPIP with Liang-Chi Hsieh.

**Lisa N. Cao** works on Apache Spark at Databricks and hosts the Apache Spark YouTube channel.

*This article draws on a conversation on the Apache Spark YouTube channel and on the [public SPIP document](https://docs.google.com/document/d/1Nphejrf_vh4YRECn0JPgKClqxDS_lB6wufZFJQxyY98/edit). Every claim attributed to the proposal was checked against that document; API names and merge status came from the Apache Spark source and JIRA. [Link to video]*
