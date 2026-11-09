# The Ultimate Guide to Apache Spark 4.3: runnable examples

One script per feature from the post "The Ultimate Guide to Apache Spark 4.3", each run
for real on Spark 4.3.0 from PyPI, plus the square film scripts in `film/`. The
Real-time Mode examples live in [`../14_real_time_mode`](../14_real_time_mode).

```bash
bin/setup.sh                       # venv (pyspark==4.3.0), a small Parquet file, a tar of CSVs
.venv/bin/python feather.py        # any script below, from this directory
```

| Script | Feature | Flag it needs |
|---|---|---|
| `feather.py` | Project Feather: shuffle-free single-task execution, plan and time per query | `spark.sql.optimizer.singleTaskExecution.enabled` (set in the script) |
| `connect_ops.py` | Spark Connect: `with` sessions, operation IDs on success and failure | needs `bin/connect-server.sh start` (gRPC 15043, UI/REST 4043) |
| `zip_frames.py` | `DataFrame.zip` | none |
| `udf_transpile.py` | Python UDF transpilation, plan with it off and on | `spark.sql.experimental.optimizer.transpilePyUDFs`, ANSI on, `useArrow=False`, classic PySpark |
| `asof_join.py` | `ASOF JOIN` | `spark.sql.join.asofJoin.enabled` |
| `json_table.py` | `JSON_TABLE` | none |
| `variant_edit.py` | `variant_set`, `variant_delete`, `variant_array_append`, `variant_strip_nulls` | none |
| `nanos.py` | `TIMESTAMP_NTZ(9)`, `unix_nanos` | `spark.sql.timestampNanosTypes.enabled` |
| `sql_extras.py` | `UNNEST ... WITH ORDINALITY`, `counter_diff`, `jaro_winkler_similarity` | none |
| `archives.py` | CSVs read from inside a tar, `archivePathFilter` | `spark.sql.files.archive.reader.enabled` |
| `scd2/` | SCD Type 2 in Auto CDC (Declarative Pipelines, a Kafka change feed, Iceberg target) | see below |

## SCD Type 2 (`scd2/`)

```bash
scd2/reset.sh       # Kafka up, an empty menu-changes topic, no table, no checkpoints
scd2/publish.sh scd2/incoming/batch-1.json && scd2/run.sh && scd2/history.sh
scd2/publish.sh scd2/incoming/batch-2.json && scd2/run.sh && scd2/history.sh
scd2/publish.sh scd2/incoming/batch-3.json && scd2/run.sh && scd2/history.sh
docker compose -f scd2/compose.yaml down -v   # when done
```

The ghost kitchen's menu changes arrive on a Kafka topic (`menu-changes`, broker on
`localhost:29292`) as one JSON event per change. `transformations/menu_changes.py` reads the
topic, and `transformations/menu.sql` is the Auto CDC flow: `price` and `station` are
tracked, so changing either opens a new version; a `dish` rename (the batch 3 typo fix)
updates the current version in place; a delete closes the dish's window.

Auto CDC needs a target that implements DSv2 row-level operations, so the pipeline writes
to an Iceberg hadoop catalog under `data/scd2/warehouse`. Iceberg has not published a Spark
4.3 runtime yet (Maven Central stops at `iceberg-spark-runtime-4.1`); build
`iceberg-spark-runtime-4.3_2.13.jar` from an Iceberg checkout with Spark 4.3 support and
put it in `jars/` (`bin/setup.sh` fetches the Kafka connector jars there). The jars and
`spark.sql.extensions` are static configs, so `run.sh`
passes them to `spark-pipelines run`; the catalog is in `spark-pipeline.template.yml`, which `run.sh` turns into `spark-pipeline.yml` with this folder's absolute path filled in (pipeline storage has to be an absolute URI).

## Gotchas found building this

- Typed literals such as `TIMESTAMP_NTZ(9) '...'` and `TIME(9) '...'` don't parse; cast a
  string. `TIME` is still behind an internal flag (`spark.sql.timeType.enabled`, off).
- With nanosecond types on, a `count(DISTINCT <nanos column>)` next to another `DISTINCT`
  aggregate in the same `SELECT` overcounts the other one (even `count(DISTINCT 1)` returns
  2). `nanos.py` sticks to a single distinct. Not yet filed.
- UDF transpilation silently does nothing for Arrow UDFs, on Connect, or with ANSI off
  (with ANSI off it warns).
- PySpark workers must use the venv's Python: run the scripts with the venv activated
  (`source .venv/bin/activate`), or set `PYSPARK_PYTHON`. `conf/` keeps the logs quiet and the
  UI off (`export SPARK_CONF_DIR=$PWD/conf`).
- Set `SPARK_LOCAL_IP=127.0.0.1` when filming: the hostname warning prints the LAN address.

## Verified with

Spark 4.3.0 (`pyspark==4.3.0`), OpenJDK 17.0.20, Python 3.14 (venv), Iceberg built from a
Spark 4.3 branch, Linux. The film is in `film/` (`storyboard.md`, one square tape per
section of the post).
