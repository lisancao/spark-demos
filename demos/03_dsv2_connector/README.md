# Demo 3: DataSource V2 Connector in Apache Spark 4.2

A working Apache Spark DataSource V2 connector, the same connector written against
DataSource V1 for comparison, and a catalog implementation. Everything here compiles
and runs against **Apache Spark 4.2.0**, and every claim is checked by a script.

Companion project for the blog post [`blog_dsv2.md`](blog_dsv2.md), *How DataSource V2
Made Spark Table Formats Pluggable*, and for the written deep dive
[`companion_guide.md`](companion_guide.md).

## Quick start

Three entry points, in the order most people want them:

```bash
./demo.sh          # the before/after walkthrough: one query, three connectors
./verify.sh        # 29 assertions proving every claim in the blog post
./setup-idea.sh    # wire the project to your local Spark, then File > Open in IDEA
```

All three compile against the Spark jars already on your machine. No Maven Central
access needed, no dependency download, no version drift between what compiles and
what runs.

`./demo.sh` prints the same query's physical plan under DSV1, then DSV2, then DSV2
behind a catalog, so the difference is visible rather than described. Start there.

`./verify.sh` ends with:

```
29 passed, 0 failed
== All checks passed
```

If Spark is not on the default Homebrew path, set `SPARK_HOME`:

```bash
SPARK_HOME=/opt/spark ./demo.sh
```

Requirements: a JDK 17 or 21, and an Apache Spark 4.2.0 install.

A `pom.xml` is included for anyone who prefers `mvn package` or wants IDEA to import
a Maven project, but the scripts are the supported path because they need nothing but
Spark. See `IDEA_SETUP.md` for the IDE walkthrough, including the four breakpoints
worth setting.

## What is here

```
src/main/java/com/example/dsv2lab/
├── demo/
│   └── BeforeAfterDemo.java  the runnable walkthrough (start here in an IDE)
├── v2/                       the DSV2 connector, read in this order
│   ├── CsvV2Source.java        1. TableProvider, the entry point
│   ├── CsvTable.java           2. Table and its capabilities
│   ├── CsvScanBuilder.java     3. pushdown negotiation and partition planning
│   ├── CsvInputPartition.java  4. a serializable unit of work
│   ├── CsvReaderFactory.java   5. per-task reader (InternalRow lives here)
│   ├── CsvWriteBuilder.java    6. write path and two-phase commit
│   ├── CsvFile.java            storage plumbing, not DSV2
│   └── CatalogHelpers.java     StructType to Column[], because there is no public one
├── v1/
│   ├── CsvV1Source.java      the same source in DSV1, for diffing
│   └── V1CsvIo.java
└── catalog/
    ├── CsvCatalog.java       TableCatalog + SupportsNamespaces
    └── CsvCatalogTable.java  the Table a catalog returns
```

Read `MIGRATION.md` for the V1 to V2 mapping table, the step-by-step, and the
gotchas that cost real time.

## Try it yourself

```bash
./verify.sh                                   # build the jar first
pyspark --jars target/dsv2-connector.jar \
  --conf spark.sql.catalog.demo=com.example.dsv2lab.catalog.CsvCatalog \
  --conf spark.sql.catalog.demo.warehouse=/tmp/dsv2lab/warehouse
```

```python
FMT = "com.example.dsv2lab.v2.CsvV2Source"
df = spark.read.format(FMT).option("path", "/tmp/dsv2lab/people.csv").load()

# Watch pushdown reach the connector: the plan shows which columns and how many
# filters the connector was actually given.
df.select("name").filter(df.dept == "eng").explain()
```

The physical plan includes the connector's own `description()`:

```
BatchScan csv:/tmp/dsv2lab/people.csv[name#1, dept#2]
  CsvScan(path=/tmp/dsv2lab/people.csv, columns=name,dept, pushedFilters=1)
```

`columns=name,dept` is column pruning (`id` was dropped). `pushedFilters=1` is the
equality filter. Implementing `description()` is the cheapest way to make pushdown
observable, and worth doing in any real connector.

SQL through the catalog:

```sql
CREATE NAMESPACE demo.analytics;
CREATE NAMESPACE demo.analytics.regional;   -- multi-part, no Hive Metastore equivalent
CREATE TABLE demo.analytics.people (id STRING, name STRING, dept STRING);
INSERT INTO demo.analytics.people VALUES ('1','ada','eng'), ('2','grace','eng');
SELECT name FROM demo.analytics.people WHERE dept = 'eng';
SHOW TABLES IN demo.analytics.regional;
```

## What the checks verify

| # | Check | Why it matters |
|---|---|---|
| 1 | Read, schema inference, partitioning | The basic contract |
| 2 | Column pruning reaches the connector | Confirms `SupportsPushDownRequiredColumns` is wired |
| 3 | Filter pushdown reaches the connector | Confirms `pushFilters` is honored, and results stay correct |
| 4 | Unhandled filters still filter | Catches the classic "claimed a filter it never applied" bug |
| 5 | Append, overwrite, header preserved | Exercises the two-phase commit and `SupportsTruncate` |
| 6 | V1 and V2 agree exactly | The migration preserves behavior |
| 7 | Catalog DDL and multi-part namespaces | The capability V1 cannot have |
| 8 | `ALTER TABLE` fails loudly | Unimplemented operations should error, not silently no-op |
| 9 | No row loss across 8 partition settings | Ranges stay contiguous and non-overlapping |
| 10 | 56 byte-range boundary combinations | Every line read exactly once, at any file size and partition count |
| 11 | 300k-row streaming read | The reader is a cursor, not a buffer |
| 12 | 20k-row write round-trips, no orphaned part files | The write path streams and cleans up after itself |
| 13 | Edge cases: header-only file, missing options, bad input | Errors are clear rather than cryptic |

Plus a drift check: the blog post inlines code from these files, so
`examples/check_blog_code.py` compares every Java snippet in the post against the
real source, ignoring comments and formatting. Edit a connector and the check fails
until the article is updated, which keeps the two from disagreeing silently.

### Tested beyond local mode

`verify.sh` runs in `local[2]`, which executes tasks in the driver JVM. That can hide
serialization bugs, because an `InputPartition` that is not really serializable still
works when it never leaves the process. The connector has also been checked under
`local-cluster`, which starts genuine separate executor JVMs:

```bash
spark-submit --master "local-cluster[2,1,1024]" \
  --jars target/dsv2-connector.jar your_script.py
```

Read, append, and overwrite all behave identically there, so the `InputPartition` and
`PartitionReaderFactory` really do survive being shipped to an executor. A 50,000-row
file was also cross-checked against an independent Python count to confirm filter
pushdown returns exactly the right rows rather than merely a plausible number.

### What the connector reads and writes

Plain CSV files on the local filesystem. `people.csv` is a five-row fixture the scripts
generate; the larger checks generate 20,000 and 50,000 row files. Every column is typed
`STRING`, deliberately, so the DSV2 surface stays visible instead of being buried in CSV
parsing and type inference.

Both paths stream, and both are worth reading closely because the shape generalizes.

The read path splits on **byte ranges**, computed from the file length, so planning
never reads data. Each task seeks to its own offset and streams lines with a cursor,
converting one row per `next()`. A row-range split would force every task to read the
whole file to find where its rows begin.

The write path:

- Each task streams its rows to its own temp part file, rather than buffering them in a
  `List`. A task owns one partition, which in production is millions of rows.
- A `WriterCommitMessage` carries **a path, not the rows**. Commit messages are
  collected on the driver, so data in them means the whole dataset in driver memory.
- The driver concatenates the parts, then does a single atomic `Files.move` into place,
  so a concurrent reader never sees a half-written file.

**Limitation, stated plainly:** the part files are local temp files, which works because
the driver and executors share a filesystem (`local`, `local-cluster`, or a cluster with
a shared mount). A production connector writes parts to the target storage system, such
as object storage, so the driver can reach them from any node. The protocol is identical;
only the location of the parts changes.

### A note on the `partitions` option

`partitions` is a hint, not a guarantee. The chunk size is `ceil(rows / wanted)`, so a
5-row file with `partitions=4` produces 3 partitions, not 4. What always holds is that
the ranges are contiguous, non-overlapping, and cover every row, which check 9 asserts
across eight different settings. Real connectors have the same property: partition
count follows the storage layout (file blocks, shards) rather than a requested number.

## Scope

Deliberately not covered, because a CSV file cannot honor them: row-level DML
(`SupportsRowLevelOperations`), CDC (`Changelog`), transactions
(`TransactionalCatalogPlugin`), and columnar reads (`ColumnarBatch`). `MIGRATION.md`
explains what each would require. Every column is typed `STRING` so the DSV2 surface
stays visible rather than being buried in CSV parsing.

## Reference implementations in Spark itself

The best worked examples ship with Spark, in
`sql/core/src/test/java/test/org/apache/spark/sql/connector/`: `JavaSimpleDataSourceV2`,
`JavaAdvancedDataSourceV2`, `JavaColumnarDataSourceV2`, and `JavaSimpleWritableDataSource`.
Read them for structure, but note they override the deprecated `Table.schema()` rather
than `columns()`.

The official API documentation is
[Spark Data Source V2](https://spark.apache.org/docs/4.2.0/sql-data-sources-v2.html),
new as of Spark 4.2.0.

## Verification Status

On 2026-09-23, against a Homebrew `apache-spark` 4.2.0 install
(`/opt/homebrew/Cellar/apache-spark/4.2.0/libexec`) with Homebrew JDK 17
(`openjdk@17`) and a Python 3.13 venv carrying the matching `py4j==0.10.9.9`:

- `./demo.sh` exited with status 0 and printed the DSV1, DSV2 and catalog plans from
  the blog post, including the 236 / 994 / 365 line counts of the three connector
  parts.
- `./verify.sh` ended with `29 passed, 0 failed`.
- `examples/check_blog_code.py` reported `blog_dsv2.md` (117 code lines) and
  `companion_guide.md` (71 code lines) in agreement with the committed source.
- Every API name in the prose was checked against the Spark source at tag `v4.2.0`,
  and every JIRA link was resolved against issues.apache.org on the same date.
