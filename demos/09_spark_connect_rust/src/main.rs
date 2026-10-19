//! Spark Connect from Rust, with DuckDB and Polars on the same Arrow batches.
//!
//! 1. Spark builds a 20M-row `orders` table server-side.
//! 2. The Rust client pulls one city's orders as Arrow RecordBatches (and, for comparison, as Rows).
//! 3. DuckDB reads those batches in place (no copy) and runs an ASOF JOIN against a surge schedule
//!    that only exists in the client process.
//! 4. Polars gets the daily aggregates through `DataFrame::to_polars()` and computes rolling stats.
//! 5. The Polars frame crosses into DuckDB through Arrow IPC bytes (polars has its own Arrow).
//! 6. DuckDB's result goes back to Spark as a table through `create_dataframe`.
//! 7. A type-fidelity sweep: every Spark SQL type, as it lands in arrow-rs, DuckDB and Polars.
//!
//! Every cross-check prints PASS or FAIL.

use std::collections::BTreeMap;
use std::error::Error;
use std::io::Cursor;
use std::sync::Arc;
use std::time::Instant;

use arrow::array::{Array, ArrayRef, Float64Array, StringArray, TimestampMicrosecondArray};
use arrow::compute::concat_batches;
use arrow::datatypes::{DataType as ArrowType, Field, Schema, TimeUnit};
use arrow::ipc::reader::StreamReader;
use arrow::record_batch::RecordBatch;
use arrow::util::pretty::pretty_format_batches;
use duckdb::vtab::arrow::{arrow_recordbatch_to_query_params, ArrowVTab};
use duckdb::Connection;
use polars::prelude::*;
use spark_connect::row::{Row, Value};
use spark_connect::types::{DataType as SparkType, StructField};
use spark_connect::{DataFrame as SparkDataFrame, SparkSession};

const CITY: &str = "sfo";
const N_ORDERS: i64 = 20_000_000;
const EPOCH_START: i64 = 1_756_684_800; // 2025-09-01T00:00:00Z
const DAYS: i64 = 30;

struct Timings(Vec<(String, f64)>);

impl Timings {
    fn add(&mut self, what: &str, t: Instant) {
        self.0.push((what.to_string(), t.elapsed().as_secs_f64() * 1000.0));
    }
}

fn section(title: &str) {
    println!("\n== {title}");
}

fn check(name: &str, ok: bool, detail: impl std::fmt::Display) {
    println!("  {}  {name}: {detail}", if ok { "PASS" } else { "FAIL" });
}

fn main() -> Result<(), Box<dyn Error>> {
    let remote = std::env::var("SPARK_REMOTE").unwrap_or_else(|_| "sc://localhost:15002".into());
    let spark = SparkSession::builder().remote(&remote).get_or_create()?;
    println!("Spark {} at {remote}", spark.version()?);
    println!("DuckDB {}  polars {}", duckdb_version()?, polars_version());
    let mut timings = Timings(Vec::new());

    // ---------------------------------------------------------------- 1. server-side data
    section("1. Server side: synthetic orders in Spark (Parquet, session catalog)");
    let t = Instant::now();
    spark
        .sql(&format!(
            "CREATE TABLE IF NOT EXISTS orders USING parquet AS
             SELECT id AS order_id,
                    element_at(array('sfo','lax','sea','nyc','chi','aus','den','pdx','phx','mia','bos','atl'),
                               CAST(pmod(xxhash64(id, 7), 12) AS INT) + 1)           AS city,
                    timestamp_seconds({EPOCH_START} + pmod(xxhash64(id, 1), {}))     AS ts,
                    CAST(round(5 + pmod(xxhash64(id, 2), 9500) / 100.0, 2) AS DOUBLE) AS amount,
                    CAST(1 + pmod(xxhash64(id, 3), 6) AS INT)                        AS items,
                    element_at(array('delivered','delivered','delivered','cancelled','refunded'),
                               CAST(pmod(xxhash64(id, 4), 5) AS INT) + 1)            AS status
             FROM range({N_ORDERS})",
            DAYS * 86_400
        ))?
        .collect()?;
    timings.add("Spark: CREATE TABLE orders AS SELECT (20M rows, server side)", t);
    let total = spark.table("orders")?.count()?;
    spark.table("orders")?.limit(5).show(5)?;
    println!("  orders: {total} rows");

    // ---------------------------------------------------------------- 2. Spark -> Arrow
    section("2. Spark -> Rust: one city's orders, as Arrow batches and as Rows");
    let slice = spark.sql(&format!(
        "SELECT order_id, city, ts, amount, items, status FROM orders WHERE city = '{CITY}'"
    ))?;
    let spark_slice_count = slice.count()?;
    let spark_slice_sum: f64 = slice
        .select([spark_connect::functions::sum(spark_connect::col("amount")).alias("s")])
        .collect()?[0]
        .get(0)
        .and_then(Value::as_f64)
        .unwrap_or(f64::NAN);

    let t = Instant::now();
    let batches = slice.collect_record_batches()?;
    timings.add("Spark -> Arrow: collect_record_batches()", t);
    let batch_rows: usize = batches.iter().map(RecordBatch::num_rows).sum();
    println!("  {} RecordBatches, {batch_rows} rows", batches.len());
    println!("  arrow-rs schema: {}", batches[0].schema());

    // The same result as one Arrow IPC file (what `to_polars()` builds internally).
    let t = Instant::now();
    let ipc = slice.to_arrow()?;
    timings.add("Spark -> Arrow IPC file: to_arrow()", t);
    println!("  as Arrow IPC: {:.1} MiB", ipc.len() as f64 / 1048576.0);
    let t = Instant::now();
    let pl_slice = IpcReader::new(Cursor::new(&ipc)).finish()?;
    timings.add("Arrow IPC -> Polars: IpcReader (client side only, 1.67M rows)", t);
    println!("  polars: {} rows x {} columns", pl_slice.height(), pl_slice.width());

    let t = Instant::now();
    let rows = slice.collect()?;
    timings.add("Spark -> Rows: collect()", t);
    println!("  {} Rows via collect(); first: {}", rows.len(), rows[0]);
    check("Arrow rows == Spark count", batch_rows as i64 == spark_slice_count, batch_rows);

    // ---------------------------------------------------------------- 3. DuckDB, in place
    section("3. DuckDB over the same buffers: ASOF JOIN against a client-side surge schedule");
    let schema = batches[0].schema();
    let t = Instant::now();
    let orders_rb = concat_batches(&schema, &batches)?;
    timings.add("arrow-rs: concat_batches", t);

    let db = Connection::open_in_memory()?;
    db.register_table_function::<ArrowVTab>("arrow")?;
    let t = Instant::now();
    arrow_view(&db, "orders", orders_rb.clone())?;
    timings.add("Arrow -> DuckDB: register RecordBatch as view (no copy)", t);

    // The surge schedule lives only here: one multiplier per 6-hour block, same Arrow timestamp
    // type as Spark's `ts` column so DuckDB sees two TIMESTAMPTZ columns.
    let ts_type = schema.field_with_name("ts")?.data_type().clone();
    arrow_view(&db, "surge", surge_schedule(&ts_type)?)?;

    let t = Instant::now();
    let duck: (i64, f64) = db.query_row("SELECT count(*), sum(amount) FROM orders", [], |r| {
        Ok((r.get(0)?, r.get(1)?))
    })?;
    timings.add("DuckDB: count + sum through the Arrow table function (1.67M rows)", t);
    // The same rows copied into a native DuckDB table, to price the table-function scan.
    let t = Instant::now();
    db.execute_batch("CREATE TABLE orders_native AS SELECT * FROM orders")?;
    timings.add("DuckDB: CREATE TABLE AS SELECT from the Arrow view (one copy)", t);
    let t = Instant::now();
    let _native: (i64, f64) =
        db.query_row("SELECT count(*), sum(amount) FROM orders_native", [], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })?;
    timings.add("DuckDB: count + sum on the native table", t);
    check("DuckDB count == Spark count", duck.0 == spark_slice_count, duck.0);
    check(
        "DuckDB sum(amount) == Spark sum(amount)",
        (duck.1 - spark_slice_sum).abs() < 1e-3,
        format!("{:.2} vs {:.2}", duck.1, spark_slice_sum),
    );

    // ts arrives as TIMESTAMP WITH TIME ZONE; a tz-aware cast to DATE needs DuckDB's ICU
    // extension, which the bundled crate leaves out, so the cast goes through TIMESTAMP (UTC).
    let rollup = |source: &str| {
        format!(
            "WITH surged AS (
                 SELECT o.order_id, o.ts, o.amount, s.multiplier, o.amount * s.multiplier AS surged
                 FROM {source} o
                 ASOF JOIN surge s ON o.city = s.city AND o.ts >= s.starts_at
             )
             SELECT CAST(CAST(ts AS TIMESTAMP) AS DATE) AS day,
                    count(*)                     AS orders,
                    round(sum(amount), 2)        AS revenue,
                    round(sum(surged), 2)        AS surged_revenue,
                    round(avg(multiplier), 4)    AS avg_multiplier
             FROM surged GROUP BY 1 ORDER BY 1"
        )
    };
    let t = Instant::now();
    let mut stmt = db.prepare(&rollup("orders"))?;
    let surge_daily: Vec<RecordBatch> = stmt.query_arrow([])?.collect();
    timings.add("DuckDB: ASOF JOIN + daily rollup through the Arrow table function -> Arrow", t);
    let t = Instant::now();
    let mut stmt = db.prepare(&rollup("orders_native"))?;
    let _native_daily: Vec<RecordBatch> = stmt.query_arrow([])?.collect();
    timings.add("DuckDB: the same ASOF JOIN + rollup on the native table", t);
    let surge_daily = concat_batches(&surge_daily[0].schema(), &surge_daily)?;
    println!("{}", pretty_format_batches(&[surge_daily.slice(0, 7)])?);
    println!("  DuckDB result schema: {}", surge_daily.schema());
    let joined: i64 = db.query_row(
        "SELECT count(*) FROM orders o ASOF JOIN surge s ON o.city = s.city AND o.ts >= s.starts_at",
        [],
        |r| r.get(0),
    )?;
    check("ASOF JOIN kept every order", joined == spark_slice_count, joined);


    // ---------------------------------------------------------------- 4. Polars
    section("4. Polars over Spark's daily aggregates: rolling 7-day mean per city");
    let daily = spark.sql(
        "SELECT city, CAST(ts AS DATE) AS day, count(*) AS orders, round(sum(amount), 2) AS revenue
         FROM orders GROUP BY 1, 2",
    )?;
    let t = Instant::now();
    let pl_daily = daily.to_polars()?;
    timings.add("Spark -> Polars: to_polars() (Arrow IPC bridge)", t);
    println!("  polars schema: {:?}", pl_daily.schema());

    let t = Instant::now();
    let rolling = pl_daily
        .clone()
        .lazy()
        .sort(["city", "day"], SortMultipleOptions::default())
        .with_columns([
            col("revenue")
                .rolling_mean(RollingOptionsFixedWindow {
                    window_size: 7,
                    min_periods: 1,
                    ..Default::default()
                })
                .over([col("city")])?
                .alias("revenue_7d"),
            col("revenue").pct_change(lit(1)).over([col("city")])?.alias("revenue_pct"),
        ])
        .collect()?;
    timings.add("Polars: sort + rolling_mean + pct_change over city", t);
    println!("{}", rolling.head(Some(8)));
    let pl_orders: i64 = pl_daily.column("orders")?.as_materialized_series().sum::<i64>()?;
    check("Polars sum(orders) == Spark count(orders)", pl_orders == total, pl_orders);

    // ---------------------------------------------------------------- 5. Polars -> DuckDB
    section("5. Polars -> DuckDB: the frame crosses as Arrow IPC bytes (two Arrow implementations)");
    let t = Instant::now();
    let mut buf = Vec::new();
    IpcStreamWriter::new(&mut buf).finish(&mut rolling.clone())?;
    let ipc_bytes = buf.len();
    let reader = StreamReader::try_new(Cursor::new(buf), None)?;
    let back: Vec<RecordBatch> = reader.collect::<Result<_, _>>()?;
    let back = concat_batches(&back[0].schema(), &back)?;
    arrow_view(&db, "rolling", back)?;
    timings.add("Polars -> IPC bytes -> arrow-rs -> DuckDB view", t);
    println!("  {} rows crossed as {:.1} KiB of IPC", rolling.height(), ipc_bytes as f64 / 1024.0);
    let mut stmt = db.prepare(
        "SELECT city, day, revenue, round(revenue_7d, 2) AS revenue_7d
         FROM rolling QUALIFY row_number() OVER (PARTITION BY city ORDER BY revenue_7d DESC) = 1
         ORDER BY revenue_7d DESC LIMIT 5",
    )?;
    let top: Vec<RecordBatch> = stmt.query_arrow([])?.collect();
    println!("{}", pretty_format_batches(&top)?);

    // ---------------------------------------------------------------- 6. DuckDB -> Spark
    section("6. DuckDB -> Spark: the surge rollup saved as a Spark table");
    let t = Instant::now();
    let (rows, schema) = record_batch_to_rows(&surge_daily)?;
    let n_back = rows.len();
    spark
        .create_dataframe(rows, schema)?
        .write()
        .mode("overwrite")
        .save_as_table("sfo_surge_daily")?;
    timings.add("Arrow -> Rows -> create_dataframe -> saveAsTable", t);
    let spark_back = spark.table("sfo_surge_daily")?;
    spark_back.print_schema()?;
    let back_count = spark_back.count()?;
    check("Spark table rows == DuckDB rows", back_count as usize == n_back, back_count);
    let spark_surge: f64 = spark
        .sql("SELECT round(sum(surged_revenue), 2) FROM sfo_surge_daily")?
        .collect()?[0]
        .get(0)
        .and_then(Value::as_f64)
        .unwrap_or(f64::NAN);
    let duck_surge: f64 = db.query_row(
        "SELECT round(sum(amount * multiplier), 2) FROM orders o ASOF JOIN surge s
         ON o.city = s.city AND o.ts >= s.starts_at",
        [],
        |r| r.get(0),
    )?;
    check(
        "Spark sum(surged_revenue) == DuckDB sum",
        (spark_surge - duck_surge).abs() < 0.05,
        format!("{spark_surge:.2} vs {duck_surge:.2}"),
    );

    // ---------------------------------------------------------------- 7. type fidelity
    section("7. Type fidelity: one Spark SQL value of each type, as each engine sees it");
    type_matrix(&spark)?;

    // ---------------------------------------------------------------- timings
    section("Timings (ms)");
    println!("| step | ms |\n|---|---|");
    for (what, ms) in &timings.0 {
        println!("| {what} | {ms:.0} |");
    }
    Ok(())
}

/// Register a RecordBatch as a DuckDB view over the Arrow table function. The two parameters are
/// the batch's address and a layout marker; the batch is read in place, and the arena behind
/// `arrow_recordbatch_to_query_params` keeps it alive for the life of the process.
fn arrow_view(db: &Connection, name: &str, rb: RecordBatch) -> duckdb::Result<()> {
    let p = arrow_recordbatch_to_query_params(rb);
    db.execute_batch(&format!(
        "CREATE VIEW {name} AS SELECT * FROM arrow({}::UBIGINT, {}::UBIGINT)",
        p[0], p[1]
    ))
}

/// One surge multiplier per 6-hour block for the whole month, for the demo city.
fn surge_schedule(ts_type: &ArrowType) -> Result<RecordBatch, Box<dyn Error>> {
    let pattern = [1.0, 1.0, 1.25, 1.5];
    let mut city = Vec::new();
    let mut starts = Vec::new();
    let mut mult = Vec::new();
    for block in 0..(DAYS * 4) {
        city.push(CITY);
        starts.push((EPOCH_START + block * 6 * 3600) * 1_000_000);
        mult.push(pattern[(block % 4) as usize]);
    }
    let tz = match ts_type {
        ArrowType::Timestamp(TimeUnit::Microsecond, tz) => tz.clone(),
        other => return Err(format!("unexpected ts type {other}").into()),
    };
    let starts = TimestampMicrosecondArray::from(starts).with_timezone_opt(tz);
    let schema = Schema::new(vec![
        Field::new("city", ArrowType::Utf8, false),
        Field::new("starts_at", ts_type.clone(), false),
        Field::new("multiplier", ArrowType::Float64, false),
    ]);
    Ok(RecordBatch::try_new(
        Arc::new(schema),
        vec![
            Arc::new(StringArray::from(city)) as ArrayRef,
            Arc::new(starts),
            Arc::new(Float64Array::from(mult)),
        ],
    )?)
}

/// The client's local-relation path takes Rows, not RecordBatches, so a batch going back to
/// Spark is unpacked column by column. Covers the types DuckDB's rollup produces.
fn record_batch_to_rows(rb: &RecordBatch) -> Result<(Vec<Row>, SparkType), Box<dyn Error>> {
    use arrow::array::{Date32Array, Int64Array};
    let names: Vec<String> = rb.schema().fields().iter().map(|f| f.name().clone()).collect();
    let mut fields = Vec::new();
    let mut columns: Vec<Vec<Value>> = Vec::new();
    for (i, f) in rb.schema().fields().iter().enumerate() {
        let a = rb.column(i);
        let (dt, vals): (SparkType, Vec<Value>) = match f.data_type() {
            ArrowType::Date32 => {
                let a = a.as_any().downcast_ref::<Date32Array>().unwrap();
                (SparkType::Date, (0..a.len()).map(|i| Value::Date(a.value(i))).collect())
            }
            ArrowType::Int64 => {
                let a = a.as_any().downcast_ref::<Int64Array>().unwrap();
                (SparkType::Long, (0..a.len()).map(|i| Value::Long(a.value(i))).collect())
            }
            ArrowType::Float64 => {
                let a = a.as_any().downcast_ref::<Float64Array>().unwrap();
                (SparkType::Double, (0..a.len()).map(|i| Value::Double(a.value(i))).collect())
            }
            ArrowType::Utf8 => {
                let a = a.as_any().downcast_ref::<StringArray>().unwrap();
                (
                    SparkType::String { collation: String::new() },
                    (0..a.len()).map(|i| Value::String(a.value(i).to_string())).collect(),
                )
            }
            other => return Err(format!("record_batch_to_rows: {} not handled", other).into()),
        };
        fields.push(StructField {
            name: f.name().clone(),
            data_type: dt,
            nullable: true,
            metadata: BTreeMap::new(),
        });
        columns.push(vals);
    }
    let rows = (0..rb.num_rows())
        .map(|r| Row::new(names.clone(), columns.iter().map(|c| c[r].clone()).collect()))
        .collect();
    Ok((rows, SparkType::Struct { fields }))
}

/// One literal per Spark SQL type; each hop is attempted separately and its failure recorded.
fn type_matrix(spark: &SparkSession) -> Result<(), Box<dyn Error>> {
    let cases: &[(&str, &str)] = &[
        ("tinyint", "CAST(1 AS TINYINT)"),
        ("smallint", "CAST(1 AS SMALLINT)"),
        ("int", "1"),
        ("bigint", "1L"),
        ("float", "CAST(1.5 AS FLOAT)"),
        ("double", "1.5D"),
        ("decimal(18,4)", "CAST(12345.6789 AS DECIMAL(18,4))"),
        ("decimal(38,10)", "CAST(1 AS DECIMAL(38,10))"),
        ("string", "'héllo'"),
        ("char(5)", "CAST('ab' AS CHAR(5))"),
        ("binary", "X'CAFE'"),
        ("boolean", "true"),
        ("date", "DATE'2026-10-18'"),
        ("timestamp", "TIMESTAMP'2026-10-18 12:34:56.789'"),
        ("timestamp_ntz", "TIMESTAMP_NTZ'2026-10-18 12:34:56.789'"),
        ("time", "TIME'12:34:56.5'"),
        ("array<int>", "array(1, 2, 3)"),
        ("map<string,int>", "map('a', 1)"),
        ("struct<x:int,y:string>", "named_struct('x', 1, 'y', 'z')"),
        ("interval day to second", "INTERVAL '1 02:03:04' DAY TO SECOND"),
        ("interval year to month", "INTERVAL '1-2' YEAR TO MONTH"),
        ("calendar interval", "make_interval(1, 2, 3)"),
        ("variant", "parse_json('{\"a\": 1}')"),
        ("null", "NULL"),
    ];
    let db = Connection::open_in_memory()?;
    db.register_table_function::<ArrowVTab>("arrow")?;
    // Polars panics (rather than erroring) on a few Arrow types; keep the table readable.
    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(|_| {}));
    println!("| Spark type | arrow-rs (client) | DuckDB | Polars |\n|---|---|---|---|");
    for (name, expr) in cases {
        let df: SparkDataFrame = spark.sql(&format!("SELECT {expr} AS v"))?;
        let spark_type = df.dtypes().map(|d| d[0].1.clone()).unwrap_or_else(|e| short(&e));
        let (arrow_cell, duck_cell) = match df.collect_record_batches() {
            Ok(b) if !b.is_empty() => {
                let f = b[0].schema().field(0).clone();
                let arrow_cell = format!("`{}`", f.data_type());
                let p = arrow_recordbatch_to_query_params(b[0].clone());
                let duck_cell = db
                    .query_row(
                        &format!(
                            "SELECT typeof(v), v::VARCHAR FROM arrow({}::UBIGINT, {}::UBIGINT)",
                            p[0], p[1]
                        ),
                        [],
                        |r| Ok((r.get::<_, String>(0)?, r.get::<_, Option<String>>(1)?)),
                    )
                    .map(|(t, v)| format!("`{t}` = {}", v.unwrap_or("NULL".into())))
                    .unwrap_or_else(|e| format!("ERR {}", short(&e)));
                (arrow_cell, duck_cell)
            }
            Ok(_) => ("(no batch)".into(), "".into()),
            Err(e) => (format!("ERR {}", short(&e)), "".into()),
        };
        let polars_cell = match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            df.to_polars().map(|pdf| {
                pdf.column("v")
                    .map(|c| {
                        let v = c.get(0).map(|v| v.to_string()).unwrap_or_default();
                        format!("`{}` = {}", c.dtype(), v)
                    })
                    .unwrap_or_else(|_| "(no column)".into())
            })
        })) {
            Ok(Ok(cell)) => cell,
            Ok(Err(e)) => format!("ERR {}", short(&e)),
            Err(p) => format!(
                "PANIC {}",
                p.downcast_ref::<&str>().map(|s| s.to_string())
                    .or_else(|| p.downcast_ref::<String>().cloned())
                    .unwrap_or_default()
            ),
        };
        println!("| {name} (`{spark_type}`) | {arrow_cell} | {duck_cell} | {polars_cell} |");
    }
    std::panic::set_hook(default_hook);
    Ok(())
}

fn short(e: &dyn std::fmt::Display) -> String {
    let s = e.to_string().replace('\n', " ").replace('|', "\\|");
    let s = s.trim();
    if s.len() > 110 {
        format!("{}…", &s[..s.char_indices().nth(110).map(|c| c.0).unwrap_or(s.len())])
    } else {
        s.to_string()
    }
}

fn duckdb_version() -> duckdb::Result<String> {
    Connection::open_in_memory()?.query_row("SELECT version()", [], |r| r.get(0))
}

fn polars_version() -> &'static str {
    "0.54"
}
