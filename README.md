# 🎬 Apache Spark Demos

Spark features are easy to announce and surprisingly hard to demonstrate honestly.

Apache Spark Demos is a collection of self-contained, evidence-backed demonstrations that make one technical claim at a time and leave the machinery visible. Metric views are checked against hand-written aggregates. A Connect migration proves output parity. A DataSource V2 connector exposes the filters Spark actually pushed. Arrow batches cross from Spark into DuckDB and Polars with a type-fidelity matrix. Spark 4.3 examples exercise Real-Time Mode, `transformWithState`, Project Feather, Auto CDC, nanosecond timestamps, `JSON_TABLE`, and the rest against released artifacts.

Each demo keeps the runnable code, exact environment, prose, recorded results, and verification path together. They are independent projects under `demos/`, using the Spark release and language that the claim requires rather than pretending one setup fits everything.

**[Choose a demo](#demo-catalog)** · **[Run the smallest verified path](#run-a-demo)** · **[See how evidence is recorded](#repository-conventions)**

<a id="demo-catalog"></a>

## 🎞️ Demo catalog

| # | Demo | What it demonstrates | Verified Spark version | Status |
|---|---|---|---|---|
| 1 | [Metric Views](demos/01_metrics_views/) | Metric definitions, `MEASURE()`, aggregation grain, lifecycle commands, and a grammar probe | 4.2.0 | Verified |
| 2 | [Spark Connect](demos/02_spark_connect/) | Thin clients, server-managed sessions, application migration, artifacts, compatibility, and deployment topologies | 4.2.0 | Verified |
| 3 | [DataSource V2 connector](demos/03_dsv2_connector/) | A Java connector, filter and column pushdown, writes, and migration from DataSource V1 | 4.2.0 and 4.3.0-rc1 | Verified |
| 7 | [Project Feather baseline](demos/07_project_feather/) | Repeatable local-mode latency measurements and detection of Feather configuration support | 4.2.0 and 4.3.0-rc1 | Verified baseline |
| 8 | [Spark Connect from OCaml](demos/08_spark_connect_ocaml/) | An options workflow using an OCaml Connect client, Delta tables, metric views, `MERGE`, and time travel | 4.2.0 | Verified |
| 9 | [Spark Connect from Rust](demos/09_spark_connect_rust/) | Arrow interchange between Spark, DuckDB, and Polars, including type-fidelity checks | 4.2.0 | Verified |
| 10 | [Stateful streaming](demos/10_stateful_streaming/) | `transformWithState`, timers, state evolution, Real-Time Mode, replay, and Redis serving | 4.3.0-rc2 | Verified against RC artifacts |
| 14 | [Real-Time Mode](demos/14_real_time_mode/) | A bookshop recommender built from micro-batch basics through stateful `transformWithState`, pipelined shuffle, timers, and measured Real-Time Mode latency | 4.3.0 | Verified |
| 16 | [Apache Spark 4.3 feature guide](demos/16_spark_43_guide/) | Runnable examples for Project Feather, Spark Connect operations, Auto CDC, `DataFrame.zip`, UDF transpilation, ASOF JOIN, `JSON_TABLE`, VARIANT edits, nanosecond timestamps, and archive reads | 4.3.0 | Verified |

“Verified” means the demo directory records the environment and checks that were run. It does not imply compatibility with later Spark releases. Release-candidate results remain labeled with the exact artifact used.

<a id="run-a-demo"></a>

## 🚀 Run a demo

Open the selected demo's README and follow its quick start. For example:

```bash
cd demos/01_metrics_views
make setup
make data
make up
make doctor
make examples
```

Demo 1's `make doctor` checks the client, server, dataset, and metric-view support before the examples run. Other demos provide their own verification command, test suite, or recorded result set.

<a id="repository-conventions"></a>

## 🧭 Repository conventions

A complete demo normally contains:

- a README with prerequisites, commands, limitations, and verification status;
- source code and local infrastructure required to run it;
- a blog post, companion guide, or video script when the demo supports published material;
- checks that recompute reported values or exercise documented behavior; and
- recorded outputs when results depend on a specific Spark build or environment.

Demo numbers are stable identifiers. Gaps in the sequence are intentional.

## 📋 Requirements

Requirements vary by demo. Common dependencies include Docker with Compose v2, a supported JDK, and one of `uv`, Maven, sbt, Cargo, or Dune. Do not assume that one demo's environment can run another; use the versions documented in the selected directory.

## 🚧 Project status

Every catalog entry records the exact Spark build and environment used for verification. Results against release candidates remain labeled as release-candidate evidence; they are not silently promoted to claims about the final release.

## 📜 License

This repository does not currently declare a license.
