# Spark Connect from Rust, with DuckDB and Polars

A walkthrough of the official [Apache Spark Connect client for Rust](https://github.com/apache/spark-connect-rust)
(crate `apache-spark-connect` 4.2.0, docs at [apache.github.io/spark-connect-rust](https://apache.github.io/spark-connect-rust/)).
Spark Connect returns results as Arrow record batches, and DuckDB and Polars both consume Arrow, so one
Rust program can let Spark do the cluster-sized work and finish the job locally without a file in
between. The program takes one query through all three engines and back:

1. **Spark builds the data.** A 20M-row `orders` table (Parquet, session catalog) from `range()` and
   hash functions; nothing is downloaded.
2. **Spark -> Rust.** One city's orders (1.67M rows) come back as arrow-rs `RecordBatch`es via
   `collect_record_batches()`, as Arrow IPC via `to_arrow()`, and as `Row`s via `collect()`, each timed.
3. **DuckDB queries the batches without a copy at registration** (`vtab-arrow`; the client and duckdb-rs share arrow-rs 58; each scan still converts the vectors it reads)
   and runs an ASOF JOIN against a surge schedule that exists only in the client process. The same
   query is timed again on a native DuckDB copy of the rows.
4. **Polars gets the daily aggregates** through `to_polars()` and computes a 7-day rolling mean and
   day-over-day change per city.
5. **Polars -> DuckDB** through Arrow IPC bytes (Polars has its own Arrow implementation, `polars-arrow`).
6. **DuckDB -> Spark.** The rollup goes back through `create_dataframe` and is saved as a Spark table.
7. **Type reference.** One literal of each common Spark SQL type, pulled through the client and shown as
   arrow-rs, DuckDB and Polars each see it.

Every cross-check prints `PASS` or `FAIL`; `./verify.sh` fails if any check fails. The blog post that
walks through it is on [systemsnull.net](https://systemsnull.net/posts/data-engineering-ai/spark-connect-rust-duckdb-polars).

## What you need

| Requirement | Why | Install |
|---|---|---|
| Rust 1.98+ | polars 0.54 uses std APIs newer than 1.92. `rust-toolchain.toml` pins it, so `rustup` fetches it on its own | nothing to do with rustup |
| `protoc` | the client compiles the Spark Connect `.proto` files at build time | `apt-get install protobuf-compiler` / `brew install protobuf` |
| C++ toolchain + CMake | DuckDB is built from source (`bundled`); the first build takes several minutes | `apt-get install build-essential cmake` / `brew install cmake` |
| Docker | the Spark 4.2.0 Connect server in `compose.yaml` (or point `SPARK_REMOTE` at any Spark 4.2+ Connect server) | |

`Cargo.toml` is the part to copy exactly. The feature lists on `polars` and `duckdb` are each there
because the build or the first run fails without them (`timezones`, for instance, is needed to print any
timestamp column that came from Spark).

## Run it

```sh
docker compose up -d --wait                       # Spark 4.2.0 Connect server on sc://localhost:15002
SPARK_REMOTE=sc://localhost:15002 cargo run --release
docker compose down -v
```

`CONNECT_PORT` and `UI_PORT` change the published ports (the run below used `CONNECT_PORT=15902`
because 15002 was taken on this machine).

## Versions this was verified with

| Component | Version |
|---|---|
| Spark Connect server | 4.2.0 (`apache/spark:4.2.0-scala2.13-java21-python3-ubuntu`) |
| `apache-spark-connect` (Rust client) | 4.2.0, feature `polars` |
| `arrow` (arrow-rs) | 58.4.0 (shared by the client and `duckdb`) |
| `duckdb` (duckdb-rs) | 1.10506.1, DuckDB v1.5.6, features `bundled`, `vtab-arrow`, `appender-arrow` |
| `polars` | 0.54.4 (the line the client's `to_polars()` is built against; 0.55 is on crates.io but can't be mixed in) |
| Rust | 1.98.1 |

## A run

```
Spark 4.2.0 at sc://localhost:15902
DuckDB v1.5.6  polars 0.54

== 1. Server side: synthetic orders in Spark (Parquet, session catalog)
[13750000, chi, 1758087463000000, 57.66, 2, delivered]
[13750001, pdx, 1758075370000000, 97.48, 6, delivered]
[13750002, den, 1757036010000000, 58.35, 6, delivered]
[13750003, pdx, 1757877161000000, 26.81, 3, delivered]
[13750004, pdx, 1759120425000000, 94.3, 4, cancelled]
  orders: 20000000 rows

== 2. Spark -> Rust: one city's orders, as Arrow batches and as Rows
  176 RecordBatches, 1667285 rows
  arrow-rs schema: Field { "order_id": nullable Int64 }, Field { "city": nullable Utf8 }, Field { "ts": nullable Timestamp(µs, "Etc/UTC") }, Field { "amount": nullable Float64 }, Field { "items": nullable Int32 }, Field { "status": nullable Utf8 }
  as Arrow IPC: 77.3 MiB
  polars: 1667285 rows x 6 columns
  1667285 Rows via collect(); first: [13750009, sfo, 1757956566000000, 73, 5, refunded]
  PASS  Arrow rows == Spark count: 1667285

== 3. DuckDB over the same buffers: ASOF JOIN against a client-side surge schedule
  PASS  DuckDB count == Spark count: 1667285
  PASS  DuckDB sum(amount) == Spark sum(amount): 87512653.61 vs 87512653.61
+------------+--------+------------+----------------+----------------+
| day        | orders | revenue    | surged_revenue | avg_multiplier |
+------------+--------+------------+----------------+----------------+
| 2025-09-01 | 55829  | 2933784.48 | 3482949.81     | 1.1868         |
| 2025-09-02 | 55924  | 2927311.35 | 3476037.04     | 1.1881         |
| 2025-09-03 | 55491  | 2913342.93 | 3459069.6      | 1.1877         |
| 2025-09-04 | 55750  | 2930668.17 | 3478995.71     | 1.1875         |
| 2025-09-05 | 55557  | 2924184.29 | 3470681.85     | 1.1867         |
| 2025-09-06 | 55464  | 2907578.25 | 3452119.67     | 1.1879         |
| 2025-09-07 | 54768  | 2885203.37 | 3428876.61     | 1.1883         |
+------------+--------+------------+----------------+----------------+
  DuckDB result schema: Field { "day": nullable Date32 }, Field { "orders": nullable Int64 }, Field { "revenue": nullable Float64 }, Field { "surged_revenue": nullable Float64 }, Field { "avg_multiplier": nullable Float64 }
  PASS  ASOF JOIN kept every order: 1667285

== 4. Polars over Spark's daily aggregates: rolling 7-day mean per city
  polars schema: Schema { fields: {"city": String, "day": Date, "orders": Int64, "revenue": Float64}, metadata: () }
shape: (8, 6)
┌──────┬────────────┬────────┬───────────┬────────────┬─────────────┐
│ city ┆ day        ┆ orders ┆ revenue   ┆ revenue_7d ┆ revenue_pct │
│ ---  ┆ ---        ┆ ---    ┆ ---       ┆ ---        ┆ ---         │
│ str  ┆ date       ┆ i64    ┆ f64       ┆ f64        ┆ f64         │
╞══════╪════════════╪════════╪═══════════╪════════════╪═════════════╡
│ atl  ┆ 2025-09-01 ┆ 55524  ┆ 2.9116e6  ┆ 2.9116e6   ┆ null        │
│ atl  ┆ 2025-09-02 ┆ 55327  ┆ 2.9054e6  ┆ 2.9085e6   ┆ -0.002129   │
│ atl  ┆ 2025-09-03 ┆ 55638  ┆ 2.9335e6  ┆ 2.9168e6   ┆ 0.009665    │
│ atl  ┆ 2025-09-04 ┆ 55435  ┆ 2.9153e6  ┆ 2.9164e6   ┆ -0.00621    │
│ atl  ┆ 2025-09-05 ┆ 55449  ┆ 2904831.1 ┆ 2.9141e6   ┆ -0.003582   │
│ atl  ┆ 2025-09-06 ┆ 55498  ┆ 2.9125e6  ┆ 2.9138e6   ┆ 0.002624    │
│ atl  ┆ 2025-09-07 ┆ 55590  ┆ 2.9132e6  ┆ 2.9138e6   ┆ 0.000263    │
│ atl  ┆ 2025-09-08 ┆ 55399  ┆ 2.8960e6  ┆ 2.9115e6   ┆ -0.005917   │
└──────┴────────────┴────────┴───────────┴────────────┴─────────────┘
  PASS  Polars sum(orders) == Spark count(orders): 20000000

== 5. Polars -> DuckDB: the frame crosses as Arrow IPC bytes (two Arrow implementations)
  360 rows crossed as 17.5 KiB of IPC
+------+------------+------------+------------+
| city | day        | revenue    | revenue_7d |
+------+------------+------------+------------+
| nyc  | 2025-09-01 | 2936721.4  | 2936721.4  |
| sfo  | 2025-09-01 | 2933784.48 | 2933784.48 |
| pdx  | 2025-09-23 | 2937459.74 | 2931266.63 |
| mia  | 2025-09-03 | 2942700.06 | 2929341.22 |
| chi  | 2025-09-01 | 2924580.73 | 2924580.73 |
+------+------------+------------+------------+

== 6. DuckDB -> Spark: the surge rollup saved as a Spark table
struct<day:date,orders:bigint,revenue:double,surged_revenue:double,avg_multiplier:double>
  PASS  Spark table rows == DuckDB rows: 30
  PASS  Spark sum(surged_revenue) == DuckDB sum: 103926081.04 vs 103926081.02

== 7. Type fidelity: one Spark SQL value of each type, as each engine sees it
| Spark type | arrow-rs (client) | DuckDB | Polars |
|---|---|---|---|
| tinyint (`tinyint`) | `Int8` | `TINYINT` = 1 | `i8` = 1 |
| smallint (`smallint`) | `Int16` | `SMALLINT` = 1 | `i16` = 1 |
| int (`int`) | `Int32` | `INTEGER` = 1 | `i32` = 1 |
| bigint (`bigint`) | `Int64` | `BIGINT` = 1 | `i64` = 1 |
| float (`float`) | `Float32` | `FLOAT` = 1.5 | `f32` = 1.5 |
| double (`double`) | `Float64` | `DOUBLE` = 1.5 | `f64` = 1.5 |
| decimal(18,4) (`decimal(18,4)`) | `Decimal128(18, 4)` | `DECIMAL(18,4)` = 12345.6789 | `decimal[18,4]` = 12345.6789 |
| decimal(38,10) (`decimal(38,10)`) | `Decimal128(38, 10)` | `DECIMAL(38,10)` = 1.0000000000 | `decimal[38,10]` = 1.0000000000 |
| string (`string`) | `Utf8` | `VARCHAR` = héllo | `str` = "héllo" |
| char(5) (`string`) | `Utf8` | `VARCHAR` = ab | `str` = "ab" |
| binary (`binary`) | `Binary` | `BLOB` = \xCA\xFE | `binary` = b"\xca\xfe" |
| boolean (`boolean`) | `Boolean` | `BOOLEAN` = true | `bool` = true |
| date (`date`) | `Date32` | `DATE` = 2026-10-18 | `date` = 2026-10-18 |
| timestamp (`timestamp`) | `Timestamp(µs, "Etc/UTC")` | `TIMESTAMP WITH TIME ZONE` = 2026-10-18 12:34:56.789+00 | `datetime[μs, Etc/UTC]` = 2026-10-18 12:34:56.789 UTC |
| timestamp_ntz (`timestamp_ntz`) | `Timestamp(µs)` | `TIMESTAMP` = 2026-10-18 12:34:56.789 | `datetime[μs]` = 2026-10-18 12:34:56.789 |
| time (`time(6)`) | ERR [UNSUPPORTED_TIME_TYPE] [UNSUPPORTED_TIME_TYPE] The data type TIME is not supported. SQLSTATE: 0A000 |  | ERR [UNSUPPORTED_TIME_TYPE] [UNSUPPORTED_TIME_TYPE] The data type TIME is not supported. SQLSTATE: 0A000 |
| array<int> (`array<int>`) | `List(non-null Int32, field: 'element')` | `INTEGER[]` = [1, 2, 3] | `list[i32]` = [1, 2, 3] |
| map<string,int> (`map<string,int>`) | `Map("entries": non-null Struct("key": non-null Utf8, "value": non-null Int32), unsorted)` | `MAP(VARCHAR, INTEGER)` = {a=1} | `list[struct[2]]` = [{"a",1}] |
| struct<x:int,y:string> (`struct<x:int,y:string>`) | `Struct("x": non-null Int32, "y": non-null Utf8)` | `STRUCT(x INTEGER, y VARCHAR)` = {'x': 1, 'y': z} | `struct[2]` = {1,"z"} |
| interval day to second (`interval day to second`) | `Duration(µs)` | `INTERVAL` = 26:03:04 | `duration[μs]` = 1d 2h 3m 4s |
| interval year to month (`interval year to month`) | `Interval(YearMonth)` | `INTERVAL` = 1 year 2 months | PANIC called `Result::unwrap()` on an `Err` value: ComputeError(ErrString("cannot create series from Interval(YearMonth)")) |
| calendar interval (`interval`) | `Interval(MonthDayNano)` | `INTERVAL` = 1 year 2 months 21 days | PANIC called `Result::unwrap()` on an `Err` value: ComputeError(ErrString("could not import from `month_day_nano_interval` type. Hint: This can be imported by setting POLARS_IMPORT_INTERVAL_AS_STRUCT=1 in the environment. Note however that this is unstable functionality that may change at any time.")) |
| variant (`variant`) | `Struct("value": non-null Binary, "metadata": non-null Binary, metadata: {"variant": "true"})` | `STRUCT("value" BLOB, metadata BLOB)` = {'value': \x02\x01\x00\x00\x02\x0C\x01, 'metadata': \x01\x01\x00\x01a} | `struct[2]` = {b"\x02\x01\x00\x00\x02\x0c\x01",b"\x01\x01\x00\x01a"} |
| null (`void`) | `Null` | ERR Binder Error: Unsupported data type: Null, please file an issue https://github.com/duckdb/duckdb-rs  LINE 1: S… | `null` = null |

== Timings (ms)
| step | ms |
|---|---|
| Spark: CREATE TABLE orders AS SELECT (20M rows, server side) | 4375 |
| Spark -> Arrow: collect_record_batches() | 727 |
| Spark -> Arrow IPC file: to_arrow() | 529 |
| Arrow IPC -> Polars: IpcReader (client side only, 1.67M rows) | 70 |
| Spark -> Rows: collect() | 1503 |
| arrow-rs: concat_batches | 33 |
| Arrow -> DuckDB: register RecordBatch as view (no copy) | 0 |
| DuckDB: count + sum through the Arrow table function (1.67M rows) | 38 |
| DuckDB: CREATE TABLE AS SELECT from the Arrow view (one copy) | 159 |
| DuckDB: count + sum on the native table | 1 |
| DuckDB: ASOF JOIN + daily rollup through the Arrow table function -> Arrow | 2226 |
| DuckDB: the same ASOF JOIN + rollup on the native table | 177 |
| Spark -> Polars: to_polars() (Arrow IPC bridge) | 764 |
| Polars: sort + rolling_mean + pct_change over city | 5 |
| Polars -> IPC bytes -> arrow-rs -> DuckDB view | 1 |
| Arrow -> Rows -> create_dataframe -> saveAsTable | 191 |
```
