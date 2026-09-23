# Migrating a connector from DataSource V1 to DataSource V2

This guide maps every V1 concept onto its V2 equivalent, using the two working
connectors in this repo. Both read the same CSV file and return identical results,
so you can diff them:

- `src/main/java/com/example/dsv2lab/v1/` (236 lines across 2 files)
- `src/main/java/com/example/dsv2lab/v2/` (994 lines across 8 files)

The V2 version is longer. That is the honest tradeoff and worth stating up front:
V2 asks you to split one class into a few small ones, and pays you back in
capabilities V1 cannot express at all.

## The mapping

| DataSource V1 | DataSource V2 | Note |
|---|---|---|
| `RelationProvider` | `TableProvider` | Entry point for path and option based sources |
| `SchemaRelationProvider` | `TableProvider.inferSchema` plus `getTable(schema, ...)` | Schema handling is now two explicit steps |
| `BaseRelation` | `Table` | V2's `Table` is an interface, not an abstract class needing a `SQLContext` |
| `BaseRelation.schema()` | `Table.columns()` | `Table.schema()` exists but is deprecated since 3.4.0 |
| `TableScan.buildScan()` | `ScanBuilder` to `Scan` to `Batch` to `PartitionReader` | The connector describes the read, Spark executes it |
| `PrunedScan` | `SupportsPushDownRequiredColumns` | Opt-in mix-in |
| `PrunedFilteredScan` | `SupportsPushDownFilters` | Opt-in mix-in |
| `BaseRelation.unhandledFilters` | return value of `pushFilters` | Folded into one method, harder to get out of sync |
| `InsertableRelation.insert` | `WriteBuilder` to `Write` to `BatchWrite` to `DataWriter` | You get a real commit protocol |
| overwrite flag on `insert` | `SupportsTruncate` | Declared as a capability |
| returns `RDD<Row>` | returns `PartitionReader<InternalRow>` | Row becomes InternalRow, see the gotcha below |
| no equivalent | `TableCatalog`, `SupportsNamespaces` | The reason to migrate |
| no equivalent | `SupportsRowLevelOperations` | MERGE, UPDATE, DELETE |
| no equivalent | `Changelog` (Spark 4.2.0) | CDC |
| no equivalent | `TransactionalCatalogPlugin` (Spark 4.2.0) | Multi-operation transactions |

## Step by step

### 1. Split the relation into a table and a scan

A V1 `BaseRelation` does two jobs: it describes the dataset and it builds the scan.
V2 separates them. `CsvTable` says what the table is and what it can do
(`capabilities()`); `CsvScanBuilder` negotiates pushdown and plans partitions.

The split is what makes pushdown composable. In V1 you override a different
`buildScan` overload depending on which pushdown you support. In V2 you add a
mix-in interface per optimization and the signature never changes.

### 2. Move parallelism from the RDD to InputPartition

V1 hands back an `RDD<Row>`, so the connector chooses parallelism by constructing
the RDD. In practice most V1 connectors call `parallelize` on a list, which means
the driver has already materialized the data.

V2 inverts this. `planInputPartitions()` returns serializable descriptions of work,
and Spark creates one task per partition and calls your `PartitionReader` on the
executor. Nothing is read on the driver.

Practical consequence: everything reachable from an `InputPartition` or a
`PartitionReaderFactory` must be `Serializable`, and it should be small. Do not put
an open connection or file handle in an `InputPartition`.

### 3. Fold unhandledFilters into pushFilters

V1's split between `buildScan(cols, filters)` and `unhandledFilters(filters)` is a
correctness hazard: if the two disagree, Spark either double-applies a filter
(harmless) or skips one your scan never applied (silently wrong results).

V2's `pushFilters` returns the filters it did **not** accept, and `pushedFilters()`
reports what it did. One method decides, so they cannot drift.

```java
@Override
public Filter[] pushFilters(Filter[] filters) {
  List<Filter> accepted = new ArrayList<>();
  List<Filter> rejected = new ArrayList<>();
  for (Filter f : filters) {
    if (f instanceof EqualTo eq && schema.getFieldIndex(eq.attribute()).isDefined()) {
      accepted.add(f);          // we will apply this one
    } else {
      rejected.add(f);          // Spark keeps applying this one
    }
  }
  this.pushedFilters = accepted.toArray(new Filter[0]);
  return rejected.toArray(new Filter[0]);
}
```

Only claim a filter you actually apply in the reader. This repo's
`verify_all.py` check 4 exists to catch exactly that class of bug.

### 4. Adopt the commit protocol

V1's `insert(data, overwrite)` is a single method with no failure story. If it
throws halfway, the destination keeps whatever partial state it reached.

V2 splits writing across driver and executors with a two-phase commit:

```
driver:    createBatchWriterFactory(info)
executor:  DataWriter.write(row) per row
           DataWriter.commit()  -> WriterCommitMessage    (or abort() on failure)
driver:    BatchWrite.commit(messages[])                  (or abort(messages[]))
```

Your only job is making the driver-side `commit` atomic. `CsvWriteBuilder` does it
by writing a temp file and moving it into place, so a concurrent reader never sees a
half-written file.

### 5. Declare capabilities

V2 gates operations on `Table.capabilities()`. Forgetting `BATCH_READ` produces a
"table does not support batch scan" error even with a correct `newScanBuilder`.
`SupportsTruncate` is what makes `mode("overwrite")` work instead of failing.

### 6. Add a catalog, which is the actual payoff

Steps 1 to 5 give you feature parity with V1. This step gives you something V1
cannot do at all.

`CsvCatalog` implements `TableCatalog` and `SupportsNamespaces`, and registering it
turns on SQL DDL and multi-part namespaces:

```
spark.sql.catalog.demo=com.example.dsv2lab.catalog.CsvCatalog
spark.sql.catalog.demo.warehouse=/tmp/dsv2lab/warehouse
```

```sql
CREATE NAMESPACE demo.analytics;
CREATE NAMESPACE demo.analytics.regional;    -- three levels, impossible in the Hive Metastore
CREATE TABLE demo.analytics.people (id STRING, name STRING, dept STRING);
INSERT INTO demo.analytics.people VALUES ('1','ada','eng');
SELECT name FROM demo.analytics.people WHERE dept = 'eng';
```

Every statement above is exercised by `verify_all.py`.

## Gotchas found while building this

These are the things that cost time, verified against Spark 4.2.0.

**`InternalRow` is internal, and strings must be `UTF8String`.** A
`PartitionReader<InternalRow>` returns `org.apache.spark.sql.catalyst.InternalRow`,
from a package that is not part of the stable API. Putting a `java.lang.String` in a
`GenericInternalRow` compiles and then throws `ClassCastException` at runtime. V1's
`Row` took plain Strings, so this bites on migration. This is the sharpest edge in
DSV2 and the clearest sign the API is not fully insulated from Spark internals.

**`createTable` has three overloads and two are deprecated.** Implement
`createTable(Identifier, TableInfo)`, added in Spark 4.1.0. The `StructType` version
was deprecated in 3.4.0 and the `Column[]` version in 4.1.0. Tutorials predating
4.1.0 will show you a deprecated signature.

**There is no public `StructType` to `Column[]` helper.** `Table.columns()` wants
`Column[]`, and Spark converts internally with `CatalogV2Util.structTypeToV2Columns`,
which is `private[sql]`. Use `Column.create(name, type, nullable)` in a loop; see
`CatalogHelpers.asColumns`.

**`NamespaceChange` is a top-level class**, not nested in `SupportsNamespaces`, so it
needs its own import.

**Spark's own reference connectors use the deprecated `schema()` override.** The
test sources under `sql/core/src/test/java/test/org/apache/spark/sql/connector/`
(`JavaSimpleBatchTable` and friends) are the best worked examples available, but they
override `Table.schema()` rather than `columns()`. Read them for structure, not for
which methods are current.

**Spark needs `--add-opens` on JDK 17+.** Catalyst reaches into `java.base`
internals for its unsafe row format. Running Spark through `pyspark` or
`spark-submit` handles this; a bare JUnit run does not, which is why `pom.xml` sets
`argLine` and why `verify.sh` drives the checks through PySpark instead.

## What this repo does not cover

Being explicit about scope, since a connector tutorial that implies completeness is
worse than one that admits its edges:

- **Row-level DML.** `SupportsRowLevelOperations` needs a delete or position
  representation the storage layer can honor; a header-and-append CSV file cannot.
- **CDC.** `Changelog` requires per-commit versioning, so a source needs
  `_commit_version` and `_commit_timestamp` semantics to implement it.
- **Transactions.** `TransactionalCatalogPlugin` needs commit-time conflict
  resolution.
- **Columnar reads.** `PartitionReader` can return `ColumnarBatch` for vectorized
  execution. CSV is row-oriented, so there is nothing to gain here; a Parquet or
  Arrow backed source is where this matters.
- **Type inference.** Every column is a string, which keeps the DSV2 surface
  visible instead of burying it in CSV parsing.
