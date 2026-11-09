# Notes: every number the post quotes

Machine: one Linux box, 16 cores, 156 GB RAM, OpenJDK 17.0.20.1. Spark 4.3.0 in local mode
(`local[16]`): PyPI `pyspark==4.3.0` for steps 0 to 3, the `spark-4.3.0-bin-hadoop3` tarball
(sha512 checked) with `spark-submit` for step 4. Kafka 4.0.0, one broker in Docker, 4
partitions per topic. `spark.sql.shuffle.partitions=4`. State store for every step and both
modes: RocksDB, changelog checkpointing, checkpoint format v2.

Latency = broker LogAppendTime of the output record minus the click's `ts` (generator clock,
same machine). For `trending`, the newest click counted into the row (`last_ts`). Nudges
(timer output) are excluded. First 5 s of output skipped.

## Catalog (step 0)

`00_build_catalog.py`: 5,817 books (500 in each aisle except Cooking & Drinking 395 and
Science - Physics 422), 384-dimension `BAAI/bge-small-en-v1.5` vectors via fastembed 0.9.1.
Source: `pg_catalog.csv.gz` downloaded 2026-11-04 (90,963 lines).

## Latency: `bin/bench.sh 200 45`

200 clicks/s for 45 s per run, 200 shoppers, 2% of events resent with the same `event_id`.

| run | records | p50 ms | p90 ms | p99 ms | max ms |
|---|---|---|---|---|---|
| 2 enrich, micro-batch | 8135 | 115 | 161 | 204 | 620 |
| 2 enrich, real-time | 8145 | 0 | 1 | 1 | 163 |
| 3 dedup+window, micro-batch | 1943 | 237 | 408 | 645 | 1267 |
| 3 dedup+window, real-time | 7979 | 50 | 77 | 99 | 520 |
| 3 dedup+window, real-time 1ms | 7979 | 2 | 3 | 41 | 558 |
| 4 recommender, micro-batch | 7274 | 190 | 275 | 396 | 688 |
| 4 recommender, real-time | 7931 | 29 | 49 | 158 | 554 |
| 4 recommender, real-time 1ms | 7940 | 3 | 3 | 216 | 619 |

"1ms" runs set `SHUFFLE_WAIT_MS=1` (`spark.shuffle.streaming.networkBufferMaxWaitTimeMs=1`). Raw: `data/bench.jsonl`.

## Personalisation (step 4): `bin/demo_recs.sh rtm 60 100`

100 clicks/s for 60 s (6,000 events, 118 resent), 200 shoppers with one or two hidden
favourite aisles, 80% of clicks in a favourite aisle. Recommender: decay 0.85, weights view 1 /
cart 3 / purchase 5, top 5 unseen, idle timer 20 s, TTL 30 min, `Trigger.RealTime("30 seconds")`.

| clicks so far | picks | in a favourite aisle | random picks would be |
|---|---|---|---|
| 1 | 1000 | 64% | 12% |
| 2-4 | 3000 | 73% | 12% |
| 5-9 | 5000 | 79% | 12% |
| 10-19 | 9905 | 82% | 12% |
| 20+ | 11095 | 84% | 12% |

Nudges: 200 idle timers fired after the shoppers stopped; delay after due time p50 4.3 s,
max 12.5 s (no input, so the timers were checked at the 30 s batch end).
Second run (film take, `bin/demo_recs.sh rtm 45 100`): 200 nudges, p50 18.9 s, max 28.8 s;
hit rate 64% / 73% / 79% / 82% / 83% by the same buckets.
Latency of that run (picks only): p50 29 ms, p90 49 ms, p99 129 ms.

## Findings

- The streaming shuffle's part-filled buffer wait
  (`spark.shuffle.streaming.networkBufferMaxWaitTimeMs`, internal, default 50 ms, buffer
  32 KB) sets the median of a lightly loaded stateful Real-time query. Source:
  `core/src/main/scala/org/apache/spark/internal/config/package.scala` at v4.3.0.
- Micro-batch `transformWithState` without RocksDB:
  `UNSUPPORTED_FEATURE.STORE_BACKEND_NOT_SUPPORTED_FOR_TWS`. Real-time sets RocksDB as a soft
  default; micro-batch doesn't.
- Stopping a stateful Real-time query logs `ErrorNotifier: A fatal error has occurred`
  (`Connection to streaming shuffle writer N closed before termination`), always at the moment
  `stop()` cancels the job.
- Running two demo scripts at once breaks the first: each run resets the topics, and the
  running query logs `unknown topic or partition` until it stops.

- Python UDFs under a Real-time trigger: a `pandas_udf` and a plain `udf` both fail at start
  with `STREAMING_REAL_TIME_MODE.OPERATOR_OR_SINK_NOT_IN_ALLOWLIST` naming
  `org.apache.spark.sql.execution.python.ArrowEvalPythonExec` (probe: Kafka `clicks` source,
  console sink, `trigger(realTime="10 seconds")`).

## Exploratory runs (before bench.sh, same setup, single runs)

These are the numbers in the post's opening. 200 clicks/s for 45 to 60 s.

- Step 2 Real-time with output timestamps as producer CreateTime: p50 0 ms, p90 1 ms, p99 1 ms
  (9,903 records). Same with LogAppendTime: p50 0 ms, p99 1 ms; micro-batch p50 123 ms.
- Step 3 Real-time, default flush wait: p50 43 ms, p99 93 ms; with 5 ms: p50 6 ms; with 1 ms:
  p50 2 ms.
