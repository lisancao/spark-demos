# How DataSource V2 Made Spark Table Formats Pluggable

*How the DataSource V2 connector and catalog interfaces made Apache Iceberg and Delta Lake first-class in Apache Spark.*

*By Lisa N. Cao and Szehon Ho*

> Verified against Apache Spark **4.2.0** (released 2026-07-14) on 2026-09-23:
> `demos/03_dsv2_connector/demo.sh` and `verify.sh` (its 29 assertions) run against a
> Homebrew `apache-spark` 4.2.0 install with JDK 17, and `examples/check_blog_code.py`
> confirms every Java sample in this post still matches the committed source. Every API
> name was additionally checked against the Spark source at tag `v4.2.0`, and every JIRA
> link was resolved against issues.apache.org.

Unmarked claims were exercised by `demo.sh` or `verify.sh`, or read from the Spark 4.2.0
source and cited. Claims about JIRA issue state come from issues.apache.org and are cited.
Forward-looking items in "What is landing next" are labeled by status.

## Table of Contents

1. [Summary](#summary)
2. [Key takeaways](#key-takeaways)
3. [What is DataSource V2 in Apache Spark?](#what-is-datasource-v2-in-apache-spark)
4. [Why wasn't the Hive Metastore enough?](#why-wasnt-the-hive-metastore-enough)
5. [Why not just use Spark session extensions?](#why-not-just-use-spark-session-extensions)
6. [Where does the table format end and the catalog begin?](#where-does-the-table-format-end-and-the-catalog-begin)
7. [What does DSV2 unify for users?](#what-does-dsv2-unify-for-users)
8. [Why has DSV2 taken so long?](#why-has-dsv2-taken-so-long)
9. [How do I migrate to a DSV2 catalog?](#how-do-i-migrate-to-a-dsv2-catalog)
10. [Should I write a DSV2 connector?](#should-i-write-a-dsv2-connector)
11. [What is landing next in DSV2?](#what-is-landing-next-in-dsv2)
12. [Frequently asked questions](#frequently-asked-questions)
13. [Tutorial: build a DSV2 connector and see the difference](#tutorial-build-a-dsv2-connector-and-see-the-difference)
14. [About the authors](#about-the-authors)
15. [Run it yourself](#run-it-yourself)
---

## Summary

- **What it is:** DataSource V2 is the Apache Spark API that lets a table format plug in as a first-class citizen, replacing the Hive Metastore's fixed model of databases, tables, and partitions with pluggable catalogs for tables, functions, procedures, and namespaces.
- **The challenge it solves:** Before DSV2, Iceberg and Delta Lake injected their own parser and planner rules through Spark session extensions, which conflicted across libraries, broke on Spark upgrades, and forced users to learn a different SQL dialect per format.
- **The outcome:** The same `MERGE INTO` now runs against either format, and a connector is thin enough to write in six steps. This post includes a runnable Spark 4.2 connector, a DSV1 migration, and 29 passing assertions.

---

## Key takeaways

- **DataSource V2 (DSV2) is the Apache Spark API that lets an external table format plug into Spark as a first-class citizen**, not just as a source of bytes to read and write.
- **DSV1 covered reading and writing files.** DSV2 covers metadata: catalogs that resolve tables, functions, procedures, views, and multi-part namespaces.
- **The Hive Metastore modeled tables, columns, and partitions.** Formats like Apache Iceberg and Delta Lake need versioned metadata, time travel, and transactional guarantees over millions of rows, so Spark needed a wider plug-in surface than a metastore wrapper.
- **Before DSV2, connectors injected custom parser rules and execution strategies through Spark session extensions.** That pattern conflicts across libraries, breaks on Spark upgrades, and forces users to learn per-format syntax.
- **The design goal is that users never notice DSV2 at all.** The same `MERGE INTO` runs against Iceberg and Delta Lake, and the connector implementation is thin enough to swap without touching the query.

## What is DataSource V2 in Apache Spark?

DataSource V2 is the Apache Spark API that external data sources implement to integrate with Spark's analyzer, optimizer, and execution engine. Where the original DataSource V1 API covered reading and writing data, DSV2 expands the surface area to metadata: a DSV2 connector plugs catalogs into Spark, and those catalogs resolve tables, functions, procedures, views, and namespaces during query analysis.

The practical result is that Apache Iceberg, Delta Lake, and any other table format can expose the same user experience through Spark. The same `MERGE INTO` statement, the same maintenance procedure syntax, and the same execution path apply regardless of what stores the metadata underneath.

DSV2 is easier to understand by asking what it replaced, so this piece works through the Hive Metastore's limits, the fragile pattern that preceded DSV2, the boundary between a table format and an engine, and what is still missing.

## Why wasn't the Hive Metastore enough?

The Hive Metastore modeled a narrow set of entities: databases, tables that map to a directory, columns, and partitions that map to subdirectories keyed by column values. That model survived far longer than its simplicity suggests it should have, and for a decade it was sufficient, because the data lived in Parquet files and the metadata layer above them was thin.

Table formats broke that assumption. The reason Iceberg and Delta Lake became dominant is not the file format, since both sit on Parquet. It is the metadata layer, which is rich enough to give transactional guarantees over huge operations. Modifying millions of rows safely requires metadata versions, snapshot lineage, time travel, and row-level lineage, none of which the Hive Metastore expressed.

Extending Spark's read and write path would not have helped, because reading and writing was never the problem. The gap was in everything around the data: which entities a data source can define, and how Spark resolves them.

### Namespaces

The Hive Metastore addressed a table as `database.table`, a fixed two-level hierarchy. Iceberg supports multi-part namespaces, so Spark needed a way for a catalog to declare arbitrary namespace depth rather than assuming two levels. The `SupportsNamespaces` mix-in covers this, with `listNamespaces`, `createNamespace`, `alterNamespace`, and `dropNamespace`.

### Partition transforms

Hive-style partitioning uses the value of a column as the partition. Iceberg partition transforms instead apply a function to a column to decide where a row lands, such as bucketing an identifier or truncating a timestamp to days. Spark cannot resolve a function it does not know about, which is one of the needs that motivated a pluggable function catalog. `FunctionCatalog.loadFunction` returns an `UnboundFunction`, and a table's `partitioning()` returns `Transform` values such as `IdentityTransform`, `BucketTransform`, and `YearsTransform`.

### Procedures and views

Table formats ship with maintenance operations: expiring old snapshots, vacuuming orphan files, rewriting data files, and clustering a table for better layout. The rich metadata layer is a double-edged sword, because metadata that enables time travel also has to be maintained. There was no way to look up a procedure in the Hive Metastore, since procedures were not modeled there at all. Spark now exposes `ProcedureCatalog`, whose `loadProcedure` returns an `UnboundProcedure`, invoked as `CALL catalog.procedure(args)` ([Spark DSV2 docs](https://spark.apache.org/docs/4.2.0/sql-data-sources-v2.html)).

Views are a subtler case. The Hive Metastore does store views, so the gap is not their existence but their portability: an engine-neutral view specification with defined dialect handling is a different thing from a stored view definition that only one engine can interpret. `ViewCatalog` exists in the DSV2 API surface, and the Spark documentation describes it as work in progress, so treat portable views through Spark as an incomplete story rather than a shipped one.

![The Hive Metastore modeled only databases, tables, columns, and partitions. Each DSV2 catalog interface answers a need it did not model: TableCatalog, SupportsNamespaces, FunctionCatalog, ProcedureCatalog, and ViewCatalog.](graphics/g3-catalog-interfaces.png)

The pattern repeats across each of these. Wherever a table format needed an entity Spark did not model, the catalog became the mechanism for plugging that entity in. When Spark analyzes a query and hits a name it cannot resolve, it consults the appropriate catalog, retrieves the definition, and continues. Governance reinforces the same design, because operators want tables, views, and functions governed together rather than through separate systems, which pushes the catalog toward being the central control point.

## Why not just use Spark session extensions?

Spark session extensions let a library inject a parser extension, resolution rules, and planner strategies directly into Spark, and both Iceberg and Delta Lake used that path in their early days. The pattern works, and it is also fragile enough that it should not be the way a data source integrates with Spark.

Three problems compound:

1. **Extensions conflict.** Injected rules from independent libraries have no coordination mechanism, so two extensions in one session can interfere.
2. **Extensions do not survive upgrades.** They hook into internals, so upgrading Spark frequently means upgrading a chain of libraries in lockstep just to keep the integration compiling.
3. **Syntax fragments.** Every data source ends up with its own dialect for the same operation, so a user has to know which format is underneath before writing a statement, and code does not port between them.

The last point is the one that reaches users. Before a unified DSV2, Iceberg and Delta Lake each had custom implementations of DML and of procedures, with different syntax for the same operation, and a query written against one did not move to the other.

![Before DataSource V2, connectors injected parser, resolution, and planner rules into Spark internals, causing conflicts and upgrade breakage. With DataSource V2, every connector meets Spark at one stable API boundary and returns metadata only.](graphics/g2-extensions-vs-dsv2.png)

### DSV1 vs session extensions vs DSV2

| Dimension | DataSource V1 | Session extensions | DataSource V2 |
|---|---|---|---|
| Scope | Read and write file-based sources | Arbitrary internal hooks | Catalogs, metadata entities, DML, execution |
| Metadata model | Thin wrapper over Hive Metastore | Whatever the extension implements | Pluggable catalogs per entity type |
| Namespaces | Two-level `database.table` | Custom | Multi-part, catalog-declared |
| Custom syntax | Not supported | Injected parser rules | Unified Spark syntax, no injection |
| Upgrade stability | Stable but limited | Breaks across versions | Stable API contract |
| Where complexity lives | Split | In the connector | In Spark |
| User awareness of format | Low | High, per-format dialects | None by design |

## Where does the table format end and the catalog begin?

Three layers stack, and keeping them separate resolves most of the confusion about what DSV2 does. The table format specification defines what content represents a table, a view, a function, or a procedure. The catalog specification defines an API for saving and looking those entities up by name within a namespace. DSV2 defines how Spark resolves a name against whichever catalog is registered, and it is deliberately indifferent to what stores the metadata.

![Three layers: the table format specification defines what content represents an entity, the catalog specification defines how entities are saved and looked up by name, and Spark DataSource V2 resolves names against whichever catalog is registered.](graphics/g1-three-layers.png)

That indifference is the point. During Spark's analysis phase, resolution takes a name the engine does not recognize, asks the registered catalog for a definition, and substitutes the result into the plan. A function catalog that returns a usable definition satisfies DSV2 whether it is backed by the Iceberg REST catalog, Unity Catalog, Apache Polaris, or something internal. Swapping the catalog does not change the query.

DSV2 is also scoped to Spark alone. It is not a cross-engine specification, and it does not translate one format's specification into another's. Interoperability between Iceberg and Delta Lake metadata is a separate effort happening at the format layer, between those two communities. DSV2 handles the engine-side question of how a Spark SQL statement resolves against whatever is registered.

### What is catalog federation, and why are there two kinds?

Catalog federation exists at two layers, which is why discussions of it tend to talk past each other.

**Logical federation, in Spark.** DSV2 resolution is catalog-based, and Spark can hold multiple catalogs at once. Registering several catalogs and addressing entities as `catalog.namespace.entity` sends each reference to the right catalog, whether the entity is a table, view, function, or procedure.

**Physical federation, in the catalog.** A catalog implementation can itself reference entities from other catalogs. Unity Catalog and Apache Polaris both support this, so a lookup arriving at one catalog may be served from another.

Spark's layer is logical, an addressing and resolution mechanism. The physical catalog owns the actual metadata representation. Both are called federation, and they are not the same thing.

## What does DSV2 unify for users?

DSV2 moves the complex, shared logic into Spark so that every connector inherits it, and the most visible payoff is DML. `UPDATE`, `MERGE`, and `DELETE` are among the most heavily used SQL statements on Spark, and they are exactly the statements that depend on transactional guarantees from the metadata layer. Implementing them once in Spark rather than once per format means the same statement works against Iceberg and Delta Lake.

Two interfaces carry this. `SupportsDeleteV2` handles the cheap case, where `canDeleteWhere` and `deleteWhere` let a source drop whole partitions or files without reading them. `SupportsRowLevelOperations` handles the general case: `newRowLevelOperationBuilder` yields a `RowLevelOperation` that pairs a scan of the affected rows with a write of the rewritten data. Critically, the interface does not pick a physical strategy: a format can implement the same `RowLevelOperation` contract with a delta-based (merge-on-read) or a group-based (copy-on-write) rewrite, so the strategy choice stays inside the connector and never changes the user's SQL.

DML is not a simple API, which is precisely the argument for centralizing it:

- **Schema evolution for DML.** A merge whose source and target schemas are not aligned needs columns added or updated for the operation to succeed, and that resolution logic belongs in the engine. Spark exposes it as explicit syntax, `MERGE INTO ... WITH SCHEMA EVOLUTION` ([SPARK-47627](https://issues.apache.org/jira/browse/SPARK-47627)), with the DSV2 implementation and the wider umbrella resolved in Spark 4.1.0 ([SPARK-52991](https://issues.apache.org/jira/browse/SPARK-52991), [SPARK-54274](https://issues.apache.org/jira/browse/SPARK-54274)), including type widening ([SPARK-53629](https://issues.apache.org/jira/browse/SPARK-53629)).
- **Operation metrics.** A merge statement rewrites data, so it carries real risk of corruption, and users want metrics confirming that what happened is what they intended. DSV2 carries these through `CustomMetric` and `CustomTaskMetric` (Spark 3.2.0), with `CustomSumMetric` and `CustomAvgMetric` as ready-made aggregations, so a connector reports its own operation counters into the Spark UI rather than inventing a side channel.
- **Transactions.** Atomic `CREATE TABLE AS SELECT` was already possible through `StagingTableCatalog`, which stages one table's changes and commits them via `StagedTable.commitStagedChanges`. Spark 4.2.0 added a broader boundary: a catalog implementing `TransactionalCatalogPlugin` returns a `Transaction` from `beginTransaction`, and Spark runs multiple read and write operations inside it before calling `commit` or `abort`. The transaction's catalog tracks the operations that occurred within its boundaries, which is what lets a connector do conflict resolution at commit time. That extends atomicity past single-table staging to multi-statement work.
- **Change data capture.** Versioned table formats can answer what changed between two versions, which is what feeds materialized views and declarative pipelines. Spark 4.2.0 added `Changelog` as the connector interface for CDC ([SPARK-55668](https://issues.apache.org/jira/browse/SPARK-55668)), and the division of labor is explicit in its contract: a connector exposes raw change data, and Spark handles post-processing, specifically carry-over removal, update detection, and net change computation. A connector implementing it returns rows carrying `_change_type` (`insert`, `delete`, `update_preimage`, or `update_postimage`), `_commit_version`, and `_commit_timestamp`, and Spark derives the reconciled change set from those. That is better UX and usually better performance, since Spark does the reconciliation once rather than each connector doing it independently.

None of these are advanced APIs in isolation. The value is in having them done correctly once, on the Spark side, where they need engine participation anyway.

The version history shows how gradually this arrived. `SupportsNamespaces` and `StagingTableCatalog` landed in Spark 3.0.0, `FunctionCatalog` in 3.2.0, `SupportsRowLevelOperations` in 3.3.0, `SupportsDeleteV2` in 3.4.0, `ProcedureCatalog` in 4.0.0, and both `Changelog` and `ViewCatalog` in 4.2.0. DSV2 is not a single release. It is a plug-in surface that has been widening steadily since Spark 3.0.0.

## Why has DSV2 taken so long?

DSV2 has taken years because the extension-based integrations worked well enough that moving to a generic API meant losing functionality. Building something generic is more work than injecting a rule, and then the connector communities have to accept a migration that costs them capabilities. Iceberg and Delta Lake were competing hard with real customer demand behind them, and neither had an incentive to trade working features for architectural purity.

Two gaps illustrate the cost concretely.

**Expression coverage.** DSV2 deliberately exposes an abstract, SQL-oriented expression library, because it is an API for external consumers. Spark's internal Catalyst set is far larger, and anything a connector cannot express through the public library is something it cannot push down.

The gap is measurable. Spark's `FunctionRegistry` registers just over 500 built-in expressions, while `GeneralScalarExpression`, the class that carries a pushed-down scalar expression to a connector, documents 66 supported expression names. Aggregate pushdown is narrower still: `Min`, `Max`, `Sum`, `Count`, `CountStar`, `Avg`, plus `GeneralAggregateFunc` and a user-defined escape hatch. A connector can therefore push down a fraction of what Spark can evaluate, and everything else has to be computed after the data crosses the boundary.

**Readers and writers.** DSV1 let a connector reuse Spark's existing reader and writer and inherit their optimizations. DSV2 abstracted further and effectively required connectors to reimplement a reader and a writer, which for a mature connector is a regression rather than an upgrade.

Both gaps are being closed rather than defended, and the direction of the fix is to hand connectors the real thing instead of a reduced abstraction. `SupportsPushDownCatalystFilters` lets a scan builder receive Catalyst expressions directly rather than translated connector predicates, which sidesteps the translation gap entirely. Worth being precise about its status: the interface currently sits in `org.apache.spark.sql.internal.connector` and Spark's own `FileScanBuilder` uses it, so it is not yet a public API a third-party connector should build against. Related work is extending the same idea to runtime filters ([SPARK-58523](https://issues.apache.org/jira/browse/SPARK-58523), open).

The same approach is being explored for readers and writers, though this one is still at the design stage rather than in a release: package Spark's existing Parquet reader and writer so a connector does not reimplement them. Those code paths carry years of investment and tuning, which is exactly why re-implementing them is the least appealing part of a DSV2 migration.

It would also settle a recurring question about native readers. Plugging an accelerated reader such as Apache DataFusion Comet into each connector separately has been a live debate in the Iceberg community, and it largely dissolves if the connector can delegate reading back to Spark. These table formats are metadata over Parquet, so reinventing the reader is avoidable work. The shape of the fix is a connector saying: here is where the Parquet file is, use the native Spark reader.

### Does DSV2 support columnar and Arrow-based execution?

Yes. A `PartitionReader` iterates over either rows or `ColumnarBatch` instances, so a connector holding Arrow-backed data returns batches instead of rows and gets vectorized execution through the operator chain. The opt-in is the reader's return type rather than a configuration flag.

## How do I migrate to a DSV2 catalog?

Migration to DSV2 starts by registering a catalog, because DSV2 is catalog-based rather than path-based. Setting `spark.sql.catalog.<name>` to a catalog implementation is the entry point, after which references of the form `catalog.namespace.entity` resolve through that catalog:

```properties
spark.sql.catalog.my_catalog=com.example.MyCatalog
spark.sql.catalog.my_catalog.warehouse=s3://bucket/warehouse
spark.sql.defaultCatalog=my_catalog
```

Any property sharing the `spark.sql.catalog.<name>.` prefix is passed through to `CatalogPlugin.initialize(name, options)`, which is how a catalog receives its own configuration. `spark.sql.defaultCatalog` sets the catalog used when a name is not qualified, and defaults to `spark_catalog` ([configuration reference](https://spark.apache.org/docs/latest/configuration.html), available since Spark 3.0.0).

Once a catalog is registered, the multi-part namespaces described earlier stop being theoretical. A catalog implementing `TableCatalog` and `SupportsNamespaces` supports this directly:

```sql
CREATE NAMESPACE demo.analytics;
CREATE NAMESPACE demo.analytics.regional;   -- three levels, no Hive Metastore equivalent
CREATE TABLE demo.analytics.people (id STRING, name STRING, dept STRING);
INSERT INTO demo.analytics.people VALUES ('1','ada','eng'), ('2','grace','eng');
SELECT name FROM demo.analytics.people WHERE dept = 'eng';
SHOW TABLES IN demo.analytics.regional;
```

The `demo.analytics.regional.emea` form is the concrete thing `database.table` could not express, and it is why namespace depth needed its own interface rather than a convention.

For most users, that is the whole migration. The larger share of the work sits with connector maintainers, who implement the DSV2 interfaces and, where a V1 connector already exists, keep behavior consistent so that existing code does not change meaning. Delta Lake is the case to watch, since it historically shipped a V1 connector, which makes the move to DSV2 a config-level change for users and a compatibility exercise for the community: the old connector's behavior has to carry over so that existing pipelines do not shift underneath their owners. Check the Delta Lake release notes for the current state rather than assuming, since this is actively moving.

Version coupling improves as a side effect. Deep custom integration meant that upgrading Spark often forced upgrading a chain of libraries, because the integration touched many internal points. A thin connector against a stable API can be swapped without that cascade.

### What actually changes when porting a V1 connector?

Porting a connector from DSV1 to DSV2 means splitting one class into a few small ones and adopting a commit protocol. The mapping below is taken from a pair of working connectors that read the same file and return identical results.

![Mapping DataSource V1 concepts onto DataSource V2: RelationProvider to TableProvider, BaseRelation to Table, buildScan to the ScanBuilder chain, PrunedFilteredScan to pushdown mix-ins, insert to the two-phase commit, and a final row of capabilities with no V1 equivalent.](graphics/g5-v1-to-v2-migration.png)

| DataSource V1 | DataSource V2 |
|---|---|
| `RelationProvider` | `TableProvider` |
| `BaseRelation` | `Table` (an interface, no `SQLContext` needed) |
| `BaseRelation.schema()` | `Table.columns()` (`schema()` deprecated in 3.4.0) |
| `TableScan.buildScan()` returning `RDD<Row>` | `ScanBuilder` to `Scan` to `Batch` to `PartitionReader<InternalRow>` |
| `PrunedScan` | `SupportsPushDownRequiredColumns` |
| `PrunedFilteredScan` | `SupportsPushDownFilters` |
| `unhandledFilters` | return value of `pushFilters` |
| `InsertableRelation.insert` | `WriteBuilder` to `Write` to `BatchWrite` to `DataWriter` |
| overwrite boolean | `SupportsTruncate` capability |
| no equivalent | `TableCatalog`, `SupportsNamespaces`, row-level DML, CDC, transactions |

Two of these are more than renames. Parallelism moves from the connector to Spark: a V1 `buildScan` returns an RDD the connector constructed, often by materializing rows on the driver, while a V2 connector returns serializable `InputPartition` descriptions and Spark creates the tasks. And the write path gains a real failure story, since V1's single `insert` call leaves the destination in whatever state it reached if it throws, whereas `BatchWrite` gives per-task commit and abort with a driver-side decision.

Three details cost real time when porting, all verified against Spark 4.2.0:

- **`InternalRow` is an internal API, and strings must be `UTF8String`.** V1's `Row` accepted a `java.lang.String`; putting one into a `GenericInternalRow` compiles and then throws `ClassCastException: class java.lang.String cannot be cast to class org.apache.spark.unsafe.types.UTF8String` at runtime. This is the sharpest edge in DSV2 and the clearest evidence the API is not fully insulated from Spark internals.
- **`createTable` has three overloads and two are deprecated.** Implement `createTable(Identifier, TableInfo)`, current since Spark 4.1.0. The `StructType` form was deprecated in 3.4.0, the `Column[]` form in 4.1.0, so any tutorial older than 4.1.0 shows a deprecated signature.
- **There is no public helper converting `StructType` to `Column[]`.** Spark uses `CatalogV2Util.structTypeToV2Columns` internally, but it is `private[sql]`, so every connector writes the same short loop over `Column.create`.

## Should I write a DSV2 connector?

If DSV2 is doing its job, writing a connector should be straightforward, because the design philosophy is to centralize complexity in Spark. A connector does not resolve names, does not plan execution, and does not implement operator behavior. Most of what it does is return metadata: Spark asks for table metadata and the connector returns it, Spark hands over metadata to persist and the connector persists it.

The read path shows the division. A connector implements `newScanBuilder`, and Spark drives the rest: `ScanBuilder` negotiates pushdown, `Scan` reports the read schema, `Batch` plans `InputPartition[]` and hands out a `PartitionReaderFactory`, and `PartitionReader` does per-task I/O. Pushdown is opt-in one mix-in at a time, so a connector implements `SupportsPushDownRequiredColumns` for column pruning and adds `SupportsPushDownFilters`, `SupportsPushDownAggregates`, `SupportsPushDownLimit`, or `SupportsPushDownTopN` only as far as its storage layer can actually exploit them. A connector that pushes nothing down still works correctly, just with more data crossing the boundary. On the write side, `BatchWrite` runs a two-phase commit where per-task `DataWriter` instances commit or abort and the driver makes the final call, so a connector gets commit coordination rather than implementing it.

![The DataSource V2 read path. A connector implements newScanBuilder and PartitionReader; Spark drives ScanBuilder pushdown negotiation, Scan, Batch, InputPartition planning, and the reader factory.](graphics/g4-read-path.png)

Pushdown negotiation is the one place worth showing in full, because it is where a connector can quietly introduce wrong results. `pushFilters` returns the filters the connector did **not** accept, so Spark knows what it must still evaluate:

```java
@Override
public Filter[] pushFilters(Filter[] filters) {
  List<Filter> accepted = new ArrayList<>();
  List<Filter> rejected = new ArrayList<>();
  for (Filter f : filters) {
    if (f instanceof EqualTo eq && fullSchema.getFieldIndex(eq.attribute()).isDefined()) {
      accepted.add(f);          // this connector will apply it
    } else {
      rejected.add(f);          // Spark keeps applying it
    }
  }
  this.pushedFilters = accepted.toArray(new Filter[0]);
  return rejected.toArray(new Filter[0]);
}
```

Claim a filter here and fail to apply it in the reader, and rows that should have been removed come back, with no error. The upside of the design is that a connector supporting no pushdown at all is still correct, just slower.

Implementing `Scan.description()` makes the negotiation observable in `EXPLAIN`, which is the fastest way to confirm pushdown actually reached the connector:

```
BatchScan csv:/tmp/dsv2lab/people.csv[name#1, dept#2]
  CsvScan(path=/tmp/dsv2lab/people.csv, columns=name,dept, pushedFilters=1)
```

`columns=name,dept` shows column pruning dropped a third column. `pushedFilters=1` shows the equality filter arrived.

That division reflects where expertise actually lives. The communities building table formats are good at storing data and metadata efficiently. They are not, and do not need to be, specialists in predicate pushdown and query plan optimization. Keeping Spark out of their way is the goal.

The practical starting points:

- **The Spark documentation now has a dedicated DSV2 section** covering entry points, catalog interfaces, the read and write paths, row-level DML, expressions, and streaming: [Spark Data Source V2](https://spark.apache.org/docs/4.2.0/sql-data-sources-v2.html).
- **Read existing connectors.** Iceberg, Delta Lake, LanceDB, and JDBC are all DSV2 connectors, so there are reference implementations at several levels of complexity. The Python Data Source API added in Spark 4.0 is also a DSV2 connector under the hood: `PythonDataSourceV2` extends `TableProvider`, the same entry point any JVM connector implements, which makes it a compact example of the API's shape. Spark's own worked examples live in the test sources under `sql/core/src/test/java/test/org/apache/spark/sql/connector/`, starting with `JavaSimpleDataSourceV2`; read them for structure, but note they still override the deprecated `Table.schema()` rather than `columns()`.
- **Generate the skeleton.** Current language models handle DSV2 connector scaffolding well, and pointing one at existing connector implementations is a reasonable way to start.
- **Report gaps upstream.** Organizations running custom internal formats have plugged into DSV2 and contributed missing functionality back to the framework. If the API does not meet a use case, that is worth raising with the community rather than working around it.

## What is landing next in DSV2?

Recent and in-flight work concentrates on closing gaps rather than adding headline features. The items below are at different stages, from shipped to under design.

| Area | Interface | Status |
|---|---|---|
| Row-level DML | `SupportsRowLevelOperations`, `SupportsDeleteV2` | Shipped, Spark 3.3.0 and 3.4.0 |
| Procedures | `ProcedureCatalog` | Shipped, Spark 4.0.0 |
| CDC | `Changelog`, `ChangelogRange` | Shipped, Spark 4.2.0 |
| Transactions | `TransactionalCatalogPlugin`, `Transaction` | Shipped, Spark 4.2.0 |
| Portable views | `ViewCatalog` | Spark 4.2.0, documented as work in progress |
| MERGE schema evolution | `MERGE INTO ... WITH SCHEMA EVOLUTION` | Shipped, Spark 4.1.0 |
| Generated columns | `GenerationExpression` | Merged for Spark 4.3.0, unreleased |
| Catalyst filter pushdown | `SupportsPushDownCatalystFilters` | Internal package, not yet public API |
| Reader and writer reuse | Connectors delegate to Spark's Parquet reader and writer | Design discussion |

Generated columns show the pattern in miniature. The feature originated in Delta Lake, and the work in progress for Spark 4.3.0 moves the logic into Spark so any connector inherits it ([SPARK-57644](https://issues.apache.org/jira/browse/SPARK-57644)). `GenerationExpression` lets a connector define a generated column either as a Spark SQL string or as a portable connector `Expression` following ANSI SQL semantics, and Spark tries the portable expression first, falling back to parsing the SQL string. The payoff beyond correctness is optimization: deriving partition filters from generated columns lets Spark prune partitions from a predicate on the source column ([SPARK-58269](https://issues.apache.org/jira/browse/SPARK-58269), open).

No single item is a big bang. Taken together they move the stack toward working properly end to end, whatever sits underneath.

The forward-looking case for this work is that the connector space is where the innovation is happening. LanceDB pioneered table formats built for AI workloads, and vector types and new file layouts are arriving quickly. A stable, capable DSV2 means Spark does not need a winner among formats. Users can try different file formats and different table formats, with the same interface and the same performance characteristics, and switch when something better appears.

## Frequently asked questions

**Is DataSource V2 the same as Spark Connect?**

No. Spark Connect is a client-to-server protocol that decouples a client application from the Spark cluster. DataSource V2 is an in-process API that data sources implement so Spark can resolve and execute against their metadata. Both provide a stable boundary that survives version changes, but they sit at opposite ends of the engine: Spark Connect faces the application, DSV2 faces the storage layer.

**Do Spark users need to know whether they are using DSV2?**

No, and that is the design criterion. A successful DSV2 means the same `MERGE INTO` or maintenance procedure works whether the table is Iceberg or Delta Lake, with no format-specific syntax. Before DSV2, users did have to know, because each format shipped its own custom implementation and dialect.

**Does DSV2 replace DataSource V1?**

DSV2 is the path forward for new connectors, and V1 connectors continue to work. The migration cost historically fell on connector maintainers rather than users, since a V1 connector reusing Spark's readers and writers had to give those up to move. Ongoing work to let DSV2 connectors delegate reading and writing back to Spark reduces that cost.

**Is DSV2 specific to Apache Iceberg?**

No. DSV2 is format-neutral by design and is used by Iceberg, Delta Lake, LanceDB, and JDBC, among others. Iceberg's requirements did drive several catalog APIs, because Iceberg pushed on entities such as multi-part namespaces and partition transform functions that Spark did not model, but the resulting APIs are generic.

**Can Iceberg and Delta Lake share the same DML syntax?**

Yes, and that is one of the clearest wins of DSV2. Unifying `MERGE`, `UPDATE`, and `DELETE` in Spark rather than per connector means a query written against one format runs against the other, which was not true when each format implemented DML through its own session extension.

**Does the catalog now do more than the Hive Metastore ever did?**

Considerably more. The Hive Metastore tracked databases, tables, columns, and partitions. Modern catalogs track views, functions, and procedures as well, with multi-part namespaces, and they serve as the governance boundary for all of those entities together. The Iceberg REST catalog is substantially more expansive than the Hive Metastore in this respect.

## Tutorial: build a DSV2 connector and see the difference

The rest of this article is a hands-on walkthrough with the code inline, so it reads without a checkout. Every snippet below is real code from the project in this repository (`demos/03_dsv2_connector`), which contains a DSV2 connector, the same source written against DSV1, and a catalog, all running against Apache Spark 4.2.0. Every plan and table shown is captured output, not an illustration.

Prerequisites are a JDK 17 or 21 and an Apache Spark 4.2.0 install. Nothing else needs downloading, because the project compiles against the jars in your Spark distribution.

The connector is eight files, and the order below is also the order to read them:

```
v2/CsvV2Source.java        TableProvider, the entry point
v2/CsvTable.java           Table, and why capabilities() matters
v2/CsvScanBuilder.java     pushdown negotiation and partition planning
v2/CsvInputPartition.java  a serializable unit of work
v2/CsvReaderFactory.java   per-task I/O, where InternalRow bites
v2/CsvWriteBuilder.java    the write path and two-phase commit
v2/CsvFile.java            storage plumbing, not DSV2
v2/CatalogHelpers.java     StructType to Column[], because there is no public one
```

### Step 0: run the before/after demo

```bash
./demo.sh
```

The demo runs one query, `SELECT name FROM people WHERE dept = 'eng'`, against the same five-row CSV file through three connectors, and prints the physical plan each time. Start here, because the plans are the whole argument.

```
  people.csv:
    id,name,dept
    1,ada,eng
    2,grace,eng
    3,alan,research
    4,katherine,math
    5,dorothy,eng
```

### Step 1: what the DSV1 version looks like

The V1 connector is a `RelationProvider` returning a `BaseRelation` that mixes in `PrunedFilteredScan` and `InsertableRelation`. The whole read path is one method returning an RDD:

```java
public class CsvV1Source implements RelationProvider {

  @Override
  public BaseRelation createRelation(
      SQLContext sqlContext, scala.collection.immutable.Map<String, String> parameters) {
    String path = parameters.get("path").getOrElse(() -> {
      throw new IllegalArgumentException("CsvV1Source requires a 'path' option");
    });
    return new CsvRelation(sqlContext, path);
  }

  public static class CsvRelation extends BaseRelation
      implements PrunedFilteredScan, InsertableRelation {

    @Override
    public RDD<Row> buildScan(String[] requiredColumns, Filter[] filters) {
      StructType full = schema();
      List<Row> rows = new ArrayList<>();
      for (String line : V1CsvIo.dataLines(path)) {
        List<String> cells = V1CsvIo.split(line);
        if (!matches(cells, full, filters)) {
          continue;
        }
        Object[] projected = new Object[requiredColumns.length];
        for (int i = 0; i < requiredColumns.length; i++) {
          int src = (int) full.getFieldIndex(requiredColumns[i]).get();
          // plain java.lang.String: V1 speaks Row, not InternalRow
          projected[i] = src < cells.size() ? cells.get(src) : null;
        }
        rows.add(RowFactory.create(projected));
      }
      JavaSparkContext jsc = JavaSparkContext.fromSparkContext(sqlContext.sparkContext());
      JavaRDD<Row> rdd = jsc.parallelize(rows, 2);
      return rdd.rdd();
    }

    /** Declared separately from buildScan, which is the hazard. */
    @Override
    public Filter[] unhandledFilters(Filter[] filters) {
      List<Filter> unhandled = new ArrayList<>();
      for (Filter f : filters) {
        if (!(f instanceof EqualTo)) {
          unhandled.add(f);
        }
      }
      return unhandled.toArray(new Filter[0]);
    }
  }
}
```

Note `parallelize(rows, 2)`: the driver has already materialized every row before Spark sees any of them. That is typical of V1 connectors and it is the thing Step 2 fixes.

It works, and the demo's first section shows it returning the right answer:

```
  Physical plan:
    *(1) Project [name#1]
    +- *(1) Filter isnotnull(dept#2)
       +- *(1) Scan com.example.dsv2lab.v1.CsvV1Source$CsvRelation@76d220eb [name#1,dept#2]
          PushedFilters: [IsNotNull(dept), *EqualTo(dept,eng)],
          ReadSchema: struct<name:string,dept:string>
```

Pushdown happens: the star on `*EqualTo(dept,eng)` marks the filter the connector claimed. Three things are true about this connector, though, and the third is the one that matters:

1. It builds the RDD itself, because `buildScan` returns `RDD<Row>`, so the driver materializes rows.
2. It reports leftover filters through a separate `unhandledFilters` method, which can drift out of sync with what the scan actually applies.
3. It cannot be addressed as `catalog.namespace.table`, cannot support `CREATE TABLE`, and cannot do MERGE, CDC, or transactions. Not "does not yet". A V1 source has no catalog to hang any of that on.

### Step 2: port the read path

The V2 entry point is `TableProvider`, which answers a narrower question than `createRelation` did: given these options, what table is this?

```java
public class CsvV2Source implements TableProvider {

  @Override
  public StructType inferSchema(CaseInsensitiveStringMap options) {
    return CsvFile.from(options).schema();
  }

  @Override
  public Table getTable(
      StructType schema, Transform[] partitioning, Map<String, String> properties) {
    return new CsvTable(schema, CsvFile.from(new CaseInsensitiveStringMap(properties)));
  }

  @Override
  public boolean supportsExternalMetadata() {
    return true;
  }
}
```

`Table` then declares what it can do. The capability set is load-bearing rather than documentation: omit `BATCH_READ` and Spark refuses to plan a scan even with a correct `newScanBuilder`.

```java
public class CsvTable implements SupportsRead, SupportsWrite {

  private static final Set<TableCapability> CAPABILITIES = EnumSet.of(
      TableCapability.BATCH_READ,
      TableCapability.BATCH_WRITE,
      TableCapability.TRUNCATE);

  @Override
  public Set<TableCapability> capabilities() {
    return CAPABILITIES;
  }

  // columns() replaced schema() in Spark 3.4.0
  @Override
  public Column[] columns() {
    return CatalogHelpers.asColumns(schema);
  }

  @Override
  public ScanBuilder newScanBuilder(CaseInsensitiveStringMap options) {
    return new CsvScanBuilder(schema, file);
  }

  @Override
  public WriteBuilder newWriteBuilder(LogicalWriteInfo info) {
    return new CsvWriteBuilder(info.schema(), file);
  }
}
```

`ScanBuilder` replaces `buildScan`, and the connector describes the read while Spark executes it. Implementing `ScanBuilder`, `Scan`, and `Batch` on one class is the common shape, matching Spark's own reference connectors. Pushdown is then added one mix-in at a time:

```java
public class CsvScanBuilder implements ScanBuilder, Scan, Batch,
    SupportsPushDownFilters, SupportsPushDownRequiredColumns {

  @Override
  public Scan build() {
    return this;
  }

  @Override
  public Batch toBatch() {
    return this;
  }

  /** Spark hands over the narrowest schema it can use. */
  @Override
  public void pruneColumns(StructType requiredSchema) {
    this.requiredSchema = requiredSchema;
  }

  /** One InputPartition per byte range. Serialized to an executor. */
  @Override
  public InputPartition[] planInputPartitions() {
    List<long[]> ranges = file.byteRanges();
    InputPartition[] partitions = new InputPartition[ranges.size()];
    for (int i = 0; i < ranges.size(); i++) {
      partitions[i] = new CsvInputPartition(ranges.get(i)[0], ranges.get(i)[1]);
    }
    return partitions;
  }

  @Override
  public PartitionReaderFactory createReaderFactory() {
    return new CsvReaderFactory(fullSchema, requiredSchema, pushedFilters, file);
  }
}
```

Nothing is read on the driver now. An `InputPartition` is a small serializable handle, so keep open connections and file handles out of it, and Spark creates one task per partition.

Note that the split unit is a **byte range**, not a row range. Row ranges look simpler and are a trap: to know where row N begins you must read rows 0 through N-1, so every task ends up reading the whole file and a scan becomes O(partitions x file size). Byte ranges are computed from the file length alone, so planning reads no data at all.

Splitting on bytes means a boundary can land mid-line, which needs the rule every splittable-text reader uses: seek to `start - 1`, discard one line, then read past the end offset far enough to finish a line that straddles the boundary. Seeking a byte early is the part that is easy to miss. Without it, a range that happens to begin exactly on a line boundary discards a record no other range will read, and rows vanish silently at higher partition counts.

The reader itself is where the sharpest edge in DSV2 lives, and where a second scaling decision hides. `PartitionReader` is a cursor, `next()` then `get()`, and that shape exists so a connector streams rather than materializing. Building a `List` of rows in the constructor is the tempting shortcut, and it means a task holding one partition of a production table runs out of memory. Convert one row per `next()`:

```java
@Override
public boolean next() {
  while (range.next()) {
    List<String> cells = CsvFile.splitLine(range.get());
    if (!matchesPushedFilters(cells, fullSchema, pushedFilters)) {
      continue;
    }
    Object[] values = new Object[projection.length];
    for (int i = 0; i < projection.length; i++) {
      int src = projection[i];
      // UTF8String, not String. A java.lang.String here compiles and then throws
      // ClassCastException at runtime.
      values[i] = src < cells.size() ? UTF8String.fromString(cells.get(src)) : null;
    }
    currentRow = new GenericInternalRow(values);
    return true;
  }
  currentRow = null;
  return false;
}
```

V1's `Row` accepted a plain `String`, so this is the error most likely to greet a migration.

### Step 3: watch pushdown arrive

The V2 plan for the identical query:

```
  Physical plan:
    *(1) Project [name#12]
    +- *(1) Filter isnotnull(dept#13)
       +- BatchScan csv:/tmp/dsv2lab/people.csv[name#12, dept#13]
          CsvScan(path=/tmp/dsv2lab/people.csv, columns=name,dept, pushedFilters=1)
          RuntimeFilters: []
```

![The same query under DSV1 and DSV2. The V1 plan shows a Scan node naming the relation object; the V2 plan shows a BatchScan node containing the connector's own description, reporting pruned columns and pushed filter count. Results are identical.](graphics/g6-plan-before-after.png)

The results are identical to V1, which is the point of a migration. What changed is the `BatchScan` node, and the parenthesized text inside it is the connector's own `Scan.description()`. It reports `columns=name,dept`, meaning column pruning dropped `id` before any I/O, and `pushedFilters=1`, meaning the equality filter reached the connector. Spark still applies `isnotnull(dept)` itself, because `pushFilters` declined it.

Implementing `description()` costs three lines and is the cheapest way to make pushdown observable. Without it, you are guessing.

### Step 4: adopt the commit protocol

`InsertableRelation.insert(data, overwrite)` becomes a chain: `WriteBuilder` to `Write` to `BatchWrite` to `DataWriter`. Spark runs the protocol, and the connector supplies the pieces:

```
driver:    createBatchWriterFactory(info)
executor:  DataWriter.write(row) per row
           DataWriter.commit() -> WriterCommitMessage   (or abort() on task failure)
driver:    BatchWrite.commit(messages[])                (or abort(messages[]))
```

Declaring `SupportsTruncate` is what makes `mode("overwrite")` work rather than fail:

```java
public class CsvWriteBuilder implements WriteBuilder, SupportsTruncate {

  @Override
  public WriteBuilder truncate() {
    this.truncate = true;
    return this;
  }
}
```

The connector's only real job is making the driver-side commit atomic. Staging is the usual way, and it makes `abort` cheap because nothing was ever moved into place.

The detail that decides whether a connector scales is **what a `WriterCommitMessage` carries**. It travels from executor to driver, so it must hold a reference, not the data:

```java
/** Carries a path, not data. Commit messages are collected on the driver. */
static final class CsvCommitMessage implements WriterCommitMessage {
  final String partFile;

  CsvCommitMessage(String partFile) {
    this.partFile = partFile;
  }
}
```

Each task streams its rows to its own part file and returns that path:

```java
@Override
public void write(InternalRow record) {
  String[] cells = new String[schema.fields().length];
  for (int i = 0; i < cells.length; i++) {
    cells[i] = record.isNullAt(i) ? "" : record.getUTF8String(i).toString();
  }
  try {
    out.write(String.join(",", cells));
    out.newLine();
  } catch (IOException e) {
    throw new UncheckedIOException(e);
  }
}

@Override
public WriterCommitMessage commit() {
  out.flush();
  out.close();
  return new CsvCommitMessage(partFile.toString());
}
```

Then the driver stitches the parts together and performs one atomic move:

```java
@Override
public void commit(WriterCommitMessage[] messages) {
  Path dest = Paths.get(file.path());
  Path staged = Files.createTempFile("csvv2-commit-", ".csv");

  try (BufferedWriter out = Files.newBufferedWriter(staged, StandardCharsets.UTF_8)) {
    for (WriterCommitMessage m : messages) {
      Path part = Paths.get(((CsvCommitMessage) m).partFile);
      try (Stream<String> rows = Files.lines(part, StandardCharsets.UTF_8)) {
        for (String line : (Iterable<String>) rows::iterator) {
          out.write(line);
          out.newLine();
        }
      }
      Files.deleteIfExists(part);
    }
  }
  Files.move(staged, dest, StandardCopyOption.REPLACE_EXISTING);
}
```

Two properties matter here, and both are easy to get wrong. Rows are streamed rather than buffered, because a task owns one partition and that can be millions of rows, so accumulating them in a `List` is an out-of-memory error waiting for production data. And the rows never pass through the driver, only paths do. A writer that returns its data inside the commit message passes every small-scale test and then puts the entire dataset in driver memory the first time it meets a real table.

A concurrent reader never sees a half-written file, because the move is the only mutation to the destination. Compare that to V1, where a single `insert` throwing halfway leaves the destination in whatever state it reached.

### Step 5: add the catalog, which is the actual payoff

Steps 2 through 4 reach parity with V1. This step does something V1 cannot.

Implement `TableCatalog` and `SupportsNamespaces`. The registration hook is `initialize`, which receives every property under the catalog's prefix:

```java
public class CsvCatalog implements TableCatalog, SupportsNamespaces {

  @Override
  public void initialize(String name, CaseInsensitiveStringMap options) {
    this.name = name;
    String dir = options.get("warehouse");   // from spark.sql.catalog.demo.warehouse
    if (dir == null) {
      throw new IllegalArgumentException(
          "CsvCatalog needs spark.sql.catalog." + name + ".warehouse set to a directory");
    }
    this.warehouse = Paths.get(dir);
    Files.createDirectories(warehouse);
  }

  @Override
  public Table loadTable(Identifier ident) throws NoSuchTableException {
    Path f = tableFile(ident);
    if (!Files.exists(f)) {
      throw new NoSuchTableException(ident);
    }
    return CsvCatalogTable.load(ident, f);
  }

  /**
   * Use this overload. createTable has been rewritten twice:
   *   (Identifier, StructType, Transform[], Map)  deprecated 3.4.0
   *   (Identifier, Column[],   Transform[], Map)  deprecated 4.1.0
   *   (Identifier, TableInfo)                     current, since 4.1.0
   */
  @Override
  public Table createTable(Identifier ident, TableInfo info) throws TableAlreadyExistsException {
    Path f = tableFile(ident);
    if (Files.exists(f)) {
      throw new TableAlreadyExistsException(ident);
    }
    List<String> header = new ArrayList<>();
    for (Column c : info.columns()) {
      header.add(c.name());
    }
    Files.write(f, List.of(String.join(",", header)));
    return CsvCatalogTable.load(ident, f);
  }

  /** Arbitrary namespace depth: this is what database.table could not express. */
  @Override
  public String[][] listNamespaces(String[] namespace) {
    Path dir = namespaceDir(namespace);   // resolves each part as a nested directory
    List<String[]> out = new ArrayList<>();
    try (Stream<Path> paths = Files.list(dir)) {
      paths.filter(Files::isDirectory).forEach(p -> {
        String[] child = new String[namespace.length + 1];
        System.arraycopy(namespace, 0, child, 0, namespace.length);
        child[namespace.length] = p.getFileName().toString();
        out.add(child);
      });
    }
    return out.toArray(new String[0][]);
  }
}
```

Register the class and SQL DDL starts working:

```properties
spark.sql.catalog.demo=com.example.dsv2lab.catalog.CsvCatalog
spark.sql.catalog.demo.warehouse=/tmp/dsv2lab/demo-warehouse
```

```sql
CREATE NAMESPACE demo.analytics;
CREATE NAMESPACE demo.analytics.regional;
CREATE TABLE demo.analytics.people (id STRING, name STRING, dept STRING);
INSERT INTO demo.analytics.people VALUES ('1','ada','eng'), ('2','grace','eng');
SELECT name FROM demo.analytics.people WHERE dept = 'eng';
```

The query is now plain SQL with no format string and no path, and the plan shows the same `BatchScan` with the same pushdown, because the catalog only answers "which table is this name" and hands off to the same scan code:

```
  Physical plan (same BatchScan, same pushdown):
    *(1) Project [name#47]
    +- *(1) Filter isnotnull(dept#48)
       +- BatchScan analytics.people[name#47, dept#48]
          CsvScan(path=/tmp/dsv2lab/demo-warehouse/analytics/people.csv,
                  columns=name,dept, pushedFilters=1)
```

And the three-level namespace resolves:

```
  Three-level namespace, which database.table cannot express:
+------------------+---------+-----------+
|namespace         |tableName|isTemporary|
+------------------+---------+-----------+
|analytics.regional|emea     |false      |
+------------------+---------+-----------+
```

`demo.analytics.regional.emea` is the name `database.table` could not express, which is why namespace depth needed `SupportsNamespaces` rather than a convention.

### Step 6: step through it in a debugger

Reading about an API contract is weaker than watching it fire. Open the project in IntelliJ IDEA:

```bash
./setup-idea.sh     # points the project at your local Spark, writes a run config
```

That avoids importing `pom.xml`, which would send IDEA to Maven Central for the Spark artifacts. Pointing the project at a local Spark install instead means it resolves offline, and the compile classpath is byte-for-byte the Spark that runs, which matters when learning an API whose methods were deprecated across 3.4, 4.1, and 4.2.

Then **File > Open** on the directory, set the SDK to a JDK 17 or 21, and run `BeforeAfterDemo`. One flag set is not optional:

```
-XX:+IgnoreUnrecognizedVMOptions
--add-opens=java.base/java.lang=ALL-UNNAMED
--add-opens=java.base/java.lang.invoke=ALL-UNNAMED
--add-opens=java.base/java.nio=ALL-UNNAMED
--add-opens=java.base/sun.nio.ch=ALL-UNNAMED
   ... and nine more
```

Catalyst reaches into `java.base` internals for its unsafe row format, so `spark-submit` and `pyspark` set these for you. A plain `main()` run from an IDE does not, and without them the session dies at startup with `InaccessibleObjectException`. The generated run configuration includes them.

With that running, four breakpoints tell the whole story:

| File | Method | What it shows |
|---|---|---|
| `CsvScanBuilder` | `pushFilters` | The filters Spark offers, and what you hand back |
| `CsvScanBuilder` | `pruneColumns` | The narrowed schema, before any I/O |
| `CsvScanBuilder` | `planInputPartitions` | Fires once, on the driver |
| `CsvReaderFactory` | `createReader` | Fires once per partition, on the executor |

Run in debug mode and watch the order: pushdown negotiation happens during planning, partition planning happens once, then readers are created per partition. For the write path, breakpoint `CsvDataWriter.commit` (per task) and `CsvBatchWrite.commit` (once, after every task succeeded) to see the two-phase commit.

Note that a plain IDE run needs `--add-opens` flags that `spark-submit` sets for you, because Catalyst reaches into `java.base` internals for its unsafe row format. The generated run configuration includes them.

### What the repository verifies

`./verify.sh` runs 29 assertions against a real Spark session. Two matter most for correctness: that pushdown reaches the connector, asserted against the physical plan rather than the results, and that a filter the connector declines is still applied by Spark. That second check exists because claiming a filter you never apply returns extra rows with no error, which is the most dangerous bug a connector can have.

The V1 and V2 connectors are also checked to return identical output, which is what makes the migration mapping above trustworthy rather than aspirational.

The tradeoff is worth stating plainly, since the demo prints it: the V1 connector is 236 lines across 2 files, the V2 connector is 994 lines across 8, plus 365 lines for the catalog. V2 is more code. You are buying capability, not brevity.

Every code sample in this article comes from that repository, and every API name was checked against the Spark 4.2.0 source rather than from memory.

## About the authors

**Szehon Ho** is a software engineer on the Apache Spark team at Databricks, an Apache Spark committer, an Apache Iceberg PMC member, and an Apache Hive PMC member. He first encountered Spark as a user on the Hive on Spark project roughly a decade ago, later worked on Iceberg at Apple, and now works on DSV2, the layer where table formats and Spark meet.

**Lisa N. Cao** works on Apache Spark at Databricks and hosts the Apache Spark YouTube channel.

*This article is based on a conversation on the Apache Spark YouTube channel.*

---

## Run it yourself

Clone this repository and run, from `demos/03_dsv2_connector/`, `./demo.sh` to see the same query's physical
plan under DSV1, DSV2, and DSV2 behind a catalog. If you maintain a connector, read
`MIGRATION.md` for the V1 to V2 mapping and the three API gotchas that cost real
time. Contributions to DSV2 are welcome on the Apache Spark JIRA.

---

---

*Verified against Apache Spark 4.2.0 with `demos/03_dsv2_connector` (`demo.sh` and
`verify.sh`), 2026-09-23.*
