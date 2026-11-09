# Getting started with Real-time Mode on Spark 4.3

A bookshop that re-ranks its recommendations while you browse, built up one streaming step at a
time on Spark 4.3.0. The steps go from a plain micro-batch query to a stateful, personalised
recommender running under a Real-time trigger:

| Step | File | What it shows |
|---|---|---|
| 0 | `00_build_catalog.py` | Batch: 5,817 Project Gutenberg books in 12 aisles, each embedded once with `BAAI/bge-small-en-v1.5` inside Spark (`mapInPandas` + fastembed) |
| 1 | `01_streaming_basics.py` | Structured Streaming basics: Kafka source, DataFrame code, console sink, a processing-time trigger and a checkpoint |
| 2 | `02_real_time_enrich.py` | Real-time Mode on a stateless query: a broadcast stream-static join from `clicks` to `enriched`, `--mode rtm` or `--mode micro` |
| 3 | `03_stateful_trending.py` | Stateful queries in Real-time Mode (new in 4.3): `dropDuplicates` on `event_id` and a windowed `groupBy` per aisle, through the pipelined shuffle |
| 4 | `04_recs.sh` + `scala/` | Personalisation: a Scala `transformWithState` processor keeps a taste vector per shopper (value and map state, TTL, an idle timer) and scores the whole catalog on every click |

The blog post that walks through it is "Getting started with Real-time Mode on Spark" on
[systemsnull.net](https://systemsnull.net). Every latency the post quotes comes from
`bin/bench.sh` and is recorded in [NOTES.md](NOTES.md).

## What you need

| Requirement | Why |
|---|---|
| Java 17, 21 or 25 | Spark 4.3 |
| Python 3.12 and [uv](https://docs.astral.sh/uv/) | steps 0 to 3 run on `pyspark==4.3.0` from PyPI |
| Spark 4.3.0 binary (`SPARK_HOME`, default `~/.local/opt/spark`) and sbt | step 4 is a Scala jar run with `spark-submit`; Real-time Mode runs only the JVM `transformWithState` |
| Docker | one Kafka broker (`compose.yaml`, host port 29192, `KAFKA_PORT` to change it) |
| 16 cores (8 at a squeeze) | a Real-time query holds one core per Kafka partition plus one per shuffle partition for the whole batch: 4 + 4 here |

## Run it

```sh
uv sync                                   # pyspark 4.3.0, fastembed, confluent-kafka
docker compose up -d --wait               # Kafka on localhost:29192
curl -fsSL -o data/pg_catalog.csv.gz https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv.gz
.venv/bin/python 00_build_catalog.py      # data/catalog (Parquet, with embeddings)

# Step 1: start the shoppers, then the query, and watch micro-batches print
.venv/bin/python bin/shoppers.py --reset --rate 50 --seconds 60 &
.venv/bin/python 01_streaming_basics.py

# Steps 2 to 4, each with fresh topics and its latency read off the output topic
bin/measure.sh 02_real_time_enrich.py rtm enriched
bin/measure.sh 03_stateful_trending.py rtm trending
bin/measure.sh 04_recs.sh rtm recs

# Step 4 end to end: shoppers browse then stop, idle timers fire, the picks are graded
bin/demo_recs.sh rtm 60 100
.venv/bin/python bin/watch.py             # in another terminal while it runs: one shopper, live

bin/bench.sh                              # every number in NOTES.md, both modes
docker compose down -v
```

`--mode micro` on any step runs the same query on the default micro-batch engine.
`SHUFFLE_WAIT_MS=1` sets the internal `spark.shuffle.streaming.networkBufferMaxWaitTimeMs`
(default 50 ms) for the stateful steps; see NOTES.md for what it does to latency.

## How latency is measured

Output topics are created with `message.timestamp.type=LogAppendTime`, so each output record
carries the time the broker appended it. `bin/latency.py` subtracts the click's own `ts` (set by
the shopper when it produced the click) from that, which covers the input hop, Spark, Spark's
producer and the output hop. For `trending` the click is the newest one counted into the row.
Both clocks are this machine's.

## Gotchas this demo hit

- `transformWithState` needs the RocksDB state store. Real-time Mode makes RocksDB the default by
  itself; a micro-batch query does not, and fails with
  `UNSUPPORTED_FEATURE.STORE_BACKEND_NOT_SUPPORTED_FOR_TWS`. Every step sets RocksDB, changelog
  checkpointing and checkpoint format v2 explicitly so both modes run on the same state store.
- Stopping a stateful Real-time query logs `ERROR ErrorNotifier: A fatal error has occurred` with
  `Connection to streaming shuffle writer N closed before termination`. It is the job being
  cancelled by `stop()`, not a failure.
- A processing-time timer on a quiet shopper fires when the next row reaches its partition or when
  the Real-time batch ends, so after the shoppers stop, nudges arrive at the batch boundary
  (seconds late with a 30-second batch). This is documented behaviour.
- PySpark workers need the venv's Python (`PYSPARK_PYTHON`, set in `bookshop/common.py`), and
  pandas 3 is not yet supported by PySpark 4.3 (pinned below 3).

## Versions this was verified with

Spark 4.3.0 (PyPI `pyspark==4.3.0` and the `spark-4.3.0-bin-hadoop3` tarball), Scala 2.13.18,
OpenJDK 17.0.20, Python 3.12, Kafka 4.0.0 (`apache/kafka:4.0.0`), fastembed 0.9.1, Linux.
