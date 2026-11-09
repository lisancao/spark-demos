# Film: The Ultimate Guide to Apache Spark 4.3 (terminal, square)

**Story.** One short square clip per feature, in the order of the post, which follows the
Databricks launch post and the Apache release notes: stateful Real-time Mode, SCD Type 2 in
Auto CDC, Project Feather, Spark Connect operations, PySpark, then SQL. Every clip runs the
feature for real on Spark 4.3.0 from PyPI (Real-time Mode reuses demo 14's stack).

VO lines are drafts written from the post (there is no video script); every claim was
checked against a run of the script on 4.3.0. Holds are sized at 150 words a minute.

**Tapes** (one per section of the post, square first):

| tape | beats | needs |
|---|---|---|
| `rtm.tape` | `rtm-stateful`, `rtm-live` | `--demo ../14_real_time_mode`; Kafka up there (`docker compose up -d --wait`), its catalog and Scala jar built |
| `scd2.tape` | `scd2-flow`, `scd2-v1`, `scd2-v2`, `scd2-v3` | `.venv`; the Iceberg 4.3 runtime and the Kafka jars in `jars/` (`bin/setup.sh`); Docker for the Kafka broker |
| `feather.tape` | `feather` | `.venv`, `data/small_orders.parquet` (`bin/setup.sh`) |
| `connect.tape` | `connect-client`, `connect-rest` | `.venv`; the beat starts its own Connect server on 15043 (UI 4043) |
| `pyspark.tape` | `zip`, `transpile` | `.venv` |
| `sql.tape` | `asof`, `json-table`, `variant`, `nanos`, `sql-extras`, `archives` | `.venv`, `data/exports.tar` |

```bash
film render demos/16_spark_43_guide/film/sql.tape --format square
film render demos/16_spark_43_guide/film/rtm.tape --format square --demo demos/14_real_time_mode
```

## Beats

| beat | shows | VO | zoom |
|---|---|---|---|
| `rtm-stateful` | demo 14's `03_stateful_trending.py` on `dropDuplicates` and the windowed count; measured in Real-time Mode, then with the shuffle flush wait at 1 ms | New in 4.3: stateful queries in Real-time Mode. Dedup and a windowed count need a shuffle, and Real-time Mode pipelines it, streaming records straight into state. The median here is a flush timer on that shuffle. Turn it down and it drops to a couple of milliseconds. | |
| `rtm-live` | demo 14's `bin/watch.py` following one shopper: each click, then the picks a `transformWithState` processor sends back | And custom state: a Scala transformWithState processor keeps a taste vector per shopper. Each click goes through Kafka, into the processor, and back out as fresh picks a few milliseconds later. | |
| `rtm-code` | phone cut (`rtm-square.tape`): `03_stateful_trending.py` full frame; `dropDuplicates` and the windowed `groupBy` highlighted, then `outputMode` and the Real-time trigger | (draft) New in 4.3: stateful queries in Real-time Mode. Dedup and a windowed count are stateful, so they need a shuffle. The only Real-time line is the trigger. | rtm-stateful 4-10; rtm-trigger 10.5-end-1 |
| `rtm-run` | phone cut: `bin/measure.sh` full frame, Real-time Mode, then with the shuffle flush wait at 1 ms; the latency figures on their own line | (draft) Real-time Mode pipelines that shuffle, streaming records into state. The median is a flush timer on the shuffle. Set the wait to one millisecond and it drops to a couple. | rtm-out1 8-12; rtm-out2 20-end-1 |
| `scd2-flow` | `scd2/transformations/menu_changes.py` (the Kafka source), then `menu.sql`: `STORED AS SCD TYPE 2`, `TRACK HISTORY ON (price, station)` | Auto CDC in 4.3 can keep history. The kitchen's menu changes arrive on Kafka, one JSON event each. Same flow as before: keys, a sequence column, a delete rule. Two new clauses: store it as SCD Type 2, and say which columns open a new version. | |
| `scd2-v1` | batch 1 published to Kafka; `scd2/run.sh`; `scd2/history.py` shows two open versions | The first batch puts two dishes on the menu. Each gets one version, open-ended: an end of NULL means current. | |
| `scd2-v2` | batch 2; run; the burger's price goes up, the tacos move to the plancha, khao soi arrives | The burger goes up to fifteen and the tacos move to the plancha. Price and station are tracked, so their old rows close at version two and new ones open. | |
| `scd2-v3` | batch 3; run; the "Birra" typo fix updates in place, a delete closes khao soi's window | A typo fix in the name isn't tracked, so it updates the current row in place. And taking khao soi off the menu doesn't erase it: it closes its window. | |
| `feather` | `feather.py` in nvim, `:Run` below it: the same small query with single-task execution off, then on | Project Feather goes after small data. The same aggregation over one small file, twice. With single-task execution on, both shuffles and their exchanges are gone from the plan, and each query is faster. It's opt-in in 4.3. | |
| `connect-client` | `connect_ops.py`: a `with` block around a Connect session, the operation ID of a success and of a failure | Spark Connect clients now create an operation ID before every request, so you get it back on success and on failure. And a session works as a context manager now. | |
| `connect-rest` | `curl` against the new `/connect/sessions` and `/connect/operations` REST endpoints, then the failed operation's detail by its ID | The server has new REST endpoints for sessions and operations. Take the failed ID from the client, and the server's record has the same operation, with the full error. | |
| `zip` | `zip_frames.py`: two projections of one DataFrame zipped back together | DataFrame zip puts two projections of the same DataFrame side by side, row for row. No join key, no shuffle. It works in Spark Connect too. | |
| `transpile` | `udf_transpile.py` (dish names): the plan with UDF transpilation off (BatchEvalPython) and on (no Python step) | An experimental optimizer rule turns simple Python UDFs into Spark expressions. With it off there's a Python worker in the plan. On, len becomes Spark's own length, and the Python step is gone. It needs ANSI mode. | |
| `asof` | `asof_join.py`: predictions matched to the feature version that was out when each was made | ASOF JOIN is the point-in-time join. A prediction made at ten oh three gets the features published at ten, not the ones from ten oh five. It's a preview behind a flag. | |
| `json-table` | `json_table.py`: one order's items array expanded into typed rows | JSON TABLE expands a JSON array into rows and types each field in one table function, with an ordinal and an exists check. | |
| `variant` | `variant_edit.py`: set, delete, append and strip nulls on a VARIANT | VARIANT values can be edited in place now: set a field, delete one, append to an array, strip the nulls. | |
| `nanos` | `nanos.py`: two trades one nanosecond apart, at micro and nano precision | Nanosecond timestamps are in preview. Two trades a nanosecond apart look identical at microsecond precision. With a precision of nine they stay two. | |
| `sql-extras` | `sql_extras.py`: `UNNEST ... WITH ORDINALITY`, `counter_diff`, `jaro_winkler_similarity` | Smaller additions: ANSI UNNEST with an ordinal, counter diff for turning running counters into deltas, with a reset as NULL, and Jaro Winkler for fuzzy names. | |
| `archives` | `archives.py`: CSVs read straight out of a tar, with `archivePathFilter` skipping the README | And Spark can read files inside tar, zip and 7z archives without unpacking them, filtered by path. It's opt-in. | |

## Zoom regions

`zoom` is `film zoom`'s dynamic zoom: a region from this table and the seconds into the beat it
holds. Boxes are pixels of the 1080x1080 square render of `rtm-square.tape`, measured on its frames.

| region | square |
|---|---|
| `rtm-stateful` | 100,230,700,175 |
| `rtm-trigger` | 100,850,700,70 |
| `rtm-out1` | 28,125,720,75 |
| `rtm-out2` | 28,330,720,75 |

## What has to be readable

- `rtm-stateful`: `dropDuplicates`, the windowed `groupBy`, both latency lines.
- `rtm-live`: at least two click lines, each followed by picks with their "ms after the click".
- `scd2-*`: the two SCD2 clauses; each history table in full, `__START_AT`/`__END_AT` columns.
- `feather`: both timing lines; the two `Exchange` lines in the first plan and none in the second.
- `connect-client`: `with SparkSession...`, both operation IDs. `connect-rest`: the failed
  operation's `detail` naming `revenue`, and that its ID matches the client's.
- `transpile`: `BatchEvalPython` in the first plan, absent from the second.
- `asof`: `MATCH_CONDITION`, and `v1` against 10:03.
- `nanos`: the `.000000001`/`.000000002` values and `trades 2, distinct_nanos 2`.
- Everything else: the code above and its full output below.

## Not filmed here

Title cards and diagrams (they're in the post); setup (`bin/setup.sh`, the Iceberg build).
