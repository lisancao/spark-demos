# Film: Spark Connect from Rust, into DuckDB 2.0 and Polars (terminal)

**Story.** The video companion to the post "Spark Connect from Rust: Pull Spark outputs
into DuckDB and Polars" (systemsnull.net). Spark Connect returns results as Arrow; in
Rust they stay Arrow, and Rust is where DuckDB and Polars live, so Spark does the
cluster-sized part and the two local engines finish the job in the same process. The
film follows the post's steps (setup, data, getting Arrow out, DuckDB, Polars, back to
Spark) with this demo's one program, each step run live against its Spark 4.2.0
Connect server, and ends on `verify.sh`.

**Tape:** `spark_connect_rust.tape`. **Needs:** `docker compose up -d --wait` in this
folder and a release build in `target/` (`cargo build --release`; the program is run
once per beat, and `run-step.sh` prints only that beat's steps).

## Beats

There is no video script for the post, so every VO line is a **draft**, taken from the
post's sentences where they fit and checked against this run's output. Holds are sized
to the VO at 150 words a minute.

| beat | shows | VO | hold | zoom |
|---|---|---|---|---|
| `open` | A comment line: Spark 4.2.0, DuckDB 2.0, polars 0.55, every run live | Spark Connect sends query results to the client as Arrow. In Rust they stay Arrow, and Rust is where DuckDB and Polars live. So Spark does the part that needs a cluster, and DuckDB and Polars finish the job in the same process, with no file in between. | 17s | |
| `deps` | `Cargo.toml`: the client, arrow 60, duckdb 1.20000.1 (DuckDB 2.0), polars 0.55.2 | The Cargo.toml is the part to copy. The client is built on arrow-rs fifty-eight, DuckDB two point oh's crate on arrow sixty, and Polars has its own Arrow. So results cross between them as Arrow IPC bytes, from the client's to_arrow. | 19s | deps-ver 8-end-1 |
| `data` | Step 1 code (the CTAS) and its output: five orders, 20000000 rows | Nothing is downloaded. Spark builds a twenty-million-row orders table from range and hash functions, on the server. The collect on the end is what makes it run. | 13s | data-out 14-end-1 |
| `arrow` | Step 2 code and output: 176 RecordBatches, 1667285 rows, 77.3 MiB of IPC, rows via collect | One city's orders, one point six seven million rows, come back three ways: as Arrow record batches, as one Arrow IPC file, and as rows. Rows cost two to three times as much, so anything headed to another engine skips collect. | 18s | arrow-out 19-end-1 |
| `duckdb` | Step 3 code (`ipc_to_batch`, `arrow_view`, the ASOF JOIN) and output: the daily surge table, PASS lines | DuckDB two point oh reads those IPC bytes, registers the batch without a copy, and runs an ASOF join: every order gets the surge multiplier that was in force when it was placed, from a table that only exists in this process. | 18s | duckdb-out 23-end-1 |
| `polars` | Step 4 code and output: the polars schema, the rolling table, PASS | Spark runs the twenty-million-row group-by. Polars reads the three hundred and sixty rows of result from the same kind of IPC bytes and computes a seven-day rolling mean per city in a few milliseconds. | 15s | polars-out 22-end-1 |
| `back` | Steps 5 and 6: the Polars frame in DuckDB (best week per city), then the rollup saved as a Spark table, two PASS lines | The Polars frame crosses into DuckDB as IPC too, and DuckDB's surge rollup goes back to Spark as a table. The two sums agree to the cent, give or take floating point. | 13s | back-out 24-end-1 |
| `checks` | `./verify.sh`: the timings table and `checks: 7 PASS, 0 FAIL` | Every hop is checked against Spark. And one rule worth keeping: the ASOF join takes about two seconds through the Arrow view, and about a tenth of that on a native DuckDB copy that costs a hundred and fifty milliseconds to make. | 18s | checks-out 21-end-1 |

## Zoom regions

`zoom` is the landscape cut's dynamic zoom (`film zoom`): a region from this table and the
seconds into the beat it holds. Boxes are pixels of the 1920x1080 landscape render, measured
on its frames (square boxes on the 1080x1080 render). The vertical cut isn't zoomed. Every zoom
starts at least three seconds after the beat's window is complete, so the viewer sees the whole
code and output before the camera moves in.

| region | landscape | vertical | square |
|---|---|---|---|
| `deps-ver` | 60,210,1700,370 | - | - |
| `data-out` | 750,40,1060,220 | - | 20,360,920,200 |
| `arrow-out` | 750,40,1150,330 | - | - |
| `duckdb-out` | 750,40,1150,560 | - | 20,470,880,280 |
| `polars-out` | 750,40,1150,560 | - | 30,470,860,370 |
| `back-out` | 750,40,1150,540 | - | 20,420,920,420 |
| `checks-out` | 0,390,1300,660 | - | - |

## What has to be readable

- `deps`: `version = "60"`, `version = "1.20000.1"`, `version = "0.55.2"`, and the comment
  saying the client is on arrow 58.
- `data`: `orders: 20000000 rows`.
- `arrow`: `176 RecordBatches, 1667285 rows`, `as Arrow IPC: 77.3 MiB`.
- `duckdb`: the surge table's first rows and `PASS  ASOF JOIN kept every order: 1667285`.
- `polars`: the `revenue_7d` column and `PASS  Polars sum(orders) == Spark count(orders)`.
- `back`: both PASS lines of step 6.
- `checks`: the two ASOF rows of the timings table and `checks: 7 PASS, 0 FAIL`.

## Not filmed here

The type table (step 7): its rows are too wide for the frame; it's in the post and the
README. Title cards and the voiceover.
