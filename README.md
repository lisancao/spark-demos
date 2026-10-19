# Apache Spark Demos

DevRel demos for Apache Spark features, each self-contained in `demos/NN_<feature>/`
with its own blog post, companion guide, runnable examples, and a verification script
that re-checks the claims in the prose.

| # | Demo | Feature | Spark versions verified |
|---|------|---------|-------------------------|
| 1 | Metrics Views | Native semantic layer (`demos/01_metrics_views`) | 4.2.0 |
| 2 | Spark Connect | Decoupled client, embed in AI (`demos/02_spark_connect`) | 4.2.0 |
| 3 | DataSource V2 | Table formats as first-class plugins (`demos/03_dsv2_connector`) | 4.2.0, 4.3.0-rc1 |
| 7 | Project Feather | Local-mode latency ([SPARK-56978](https://issues.apache.org/jira/browse/SPARK-56978), `demos/07_project_feather`) | 4.2.0 baseline, 4.3.0-rc1 |
| 8 | Spark Connect from OCaml | An options desk driven by the [spark-connect-ocaml](https://github.com/lisancao/spark-connect-ocaml) client: Python data source, Delta, metric view, MERGE and time travel (`demos/08_spark_connect_ocaml`) | 4.2.0 |
| 9 | Spark Connect from Rust | DuckDB and Polars on the same Arrow batches: the official [spark-connect-rust](https://github.com/apache/spark-connect-rust) client, DuckDB reading Spark results in place for an ASOF JOIN, Polars via `to_polars()`, results back to Spark, and a type-fidelity matrix (`demos/09_spark_connect_rust`) | 4.2.0 |

Demos 1 and 2 bring their own Compose stacks and run against the official
`apache/spark:4.2.0` image; re-validating them on 4.3 waits for the official images
published with the 4.3 release. Demos 3 and 7 run against a local Spark install and
are verified against both 4.2.0 and the published 4.3.0-rc1 distribution.
