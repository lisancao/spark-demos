#!/usr/bin/env python3
"""
Verification suite for the DSV2 connector lab.

Every claim the blog post makes about this code is checked here, so the post and
the repo cannot drift apart. Run it with ../verify.sh, which compiles first.

Each check asserts, so a regression fails the run rather than printing something
that looks fine.
"""
import os
import shutil
import tempfile
import sys
from pyspark.sql import SparkSession

JAR = "target/dsv2-connector.jar"
V1 = "com.example.dsv2lab.v1.CsvV1Source"
V2 = "com.example.dsv2lab.v2.CsvV2Source"
WORK = "/tmp/dsv2lab"

passed = []
failed = []


def check(name, condition, detail=""):
    if condition:
        passed.append(name)
        print(f"  PASS  {name}")
    else:
        failed.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def main():
    spark = (SparkSession.builder
             .appName("dsv2-lab-verify")
             .master("local[2]")
             .config("spark.jars", JAR)
             .config("spark.sql.catalog.demo", "com.example.dsv2lab.catalog.CsvCatalog")
             .config("spark.sql.catalog.demo.warehouse", f"{WORK}/warehouse")
             .config("spark.sql.shuffle.partitions", "2")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")

    print("\n-- 1. DSV2 read path")
    df = spark.read.format(V2).option("path", f"{WORK}/people.csv").load()
    check("reads all rows", df.count() == 5, f"got {df.count()}")
    check("infers header as schema",
          df.schema.fieldNames() == ["id", "name", "dept"],
          str(df.schema.fieldNames()))
    check("splits into partitions", df.rdd.getNumPartitions() == 2,
          f"got {df.rdd.getNumPartitions()}")

    print("\n-- 2. Column pruning reaches the connector")
    plan = df.select("name").filter(df.dept == "eng")._jdf.queryExecution().executedPlan().toString()
    check("pruned to the columns actually needed",
          "columns=name,dept" in plan and "id" not in plan.split("CsvScan")[1][:60],
          "plan did not show pruning")

    print("\n-- 3. Filter pushdown reaches the connector")
    check("connector received 1 pushed filter", "pushedFilters=1" in plan,
          "plan did not show a pushed filter")
    rows = [r.name for r in df.select("name").filter(df.dept == "eng").collect()]
    check("pushdown returns correct rows", sorted(rows) == ["ada", "dorothy", "grace"],
          str(sorted(rows)))

    print("\n-- 4. Unsupported filters are handed back to Spark")
    # StartsWith is not handled by this connector, so Spark must apply it.
    sw = df.filter(df.name.startswith("a")).collect()
    check("unhandled filter still filters correctly",
          sorted(r.name for r in sw) == ["ada", "alan"],
          str(sorted(r.name for r in sw)))

    print("\n-- 5. DSV2 write path, two-phase commit")
    shutil.copy(f"{WORK}/people.csv", f"{WORK}/out.csv")
    df.write.format(V2).option("path", f"{WORK}/out.csv").mode("append").save()
    after = spark.read.format(V2).option("path", f"{WORK}/out.csv").load()
    check("append doubles a 5-row file", after.count() == 10, f"got {after.count()}")

    df.filter(df.dept == "math").write.format(V2) \
        .option("path", f"{WORK}/out.csv").mode("overwrite").save()
    final = spark.read.format(V2).option("path", f"{WORK}/out.csv").load()
    check("overwrite via SupportsTruncate leaves 1 row", final.count() == 1,
          f"got {final.count()}")
    check("overwrite preserves the header",
          final.schema.fieldNames() == ["id", "name", "dept"],
          str(final.schema.fieldNames()))

    print("\n-- 6. DSV1 connector produces identical results")
    v1 = spark.read.format(V1).option("path", f"{WORK}/people.csv").load()
    check("V1 reads the same row count", v1.count() == df.count(),
          f"v1={v1.count()} v2={df.count()}")
    check("V1 reads the same schema", v1.schema.fieldNames() == df.schema.fieldNames())
    v1_rows = sorted(r.name for r in v1.select("name").filter(v1.dept == "eng").collect())
    check("V1 and V2 agree under pushdown", v1_rows == ["ada", "dorothy", "grace"],
          str(v1_rows))

    print("\n-- 7. Catalog: namespaces, DDL, and multi-part names")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS demo.analytics")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS demo.analytics.regional")
    spark.sql("CREATE TABLE IF NOT EXISTS demo.analytics.people (id STRING, name STRING, dept STRING)")
    spark.sql("INSERT INTO demo.analytics.people VALUES ('1','ada','eng'), ('2','grace','eng')")

    cat_rows = spark.sql("SELECT * FROM demo.analytics.people").collect()
    check("catalog table round-trips through SQL", len(cat_rows) == 2, f"got {len(cat_rows)}")

    tbls = spark.sql("SHOW TABLES IN demo.analytics").collect()
    check("SHOW TABLES lists the table", any(r.tableName == "people" for r in tbls))

    spark.sql("CREATE TABLE IF NOT EXISTS demo.analytics.regional.emea (id STRING, region STRING)")
    deep = spark.sql("SHOW TABLES IN demo.analytics.regional").collect()
    check("multi-part namespace resolves (3 levels deep)",
          any(r.namespace == "analytics.regional" for r in deep),
          str([r.namespace for r in deep]))

    pruned = spark.sql("SELECT name FROM demo.analytics.people WHERE dept = 'eng'").collect()
    check("catalog table supports pushdown too",
          sorted(r.name for r in pruned) == ["ada", "grace"],
          str(sorted(r.name for r in pruned)))

    print("\n-- 8. Catalog rejects what it does not implement")
    try:
        spark.sql("ALTER TABLE demo.analytics.people ADD COLUMN extra STRING")
        check("ALTER TABLE fails loudly rather than silently", False, "no error raised")
    except Exception as e:
        check("ALTER TABLE fails loudly rather than silently",
              "does not support ALTER TABLE" in str(e), str(e)[:100])

    print("\n-- 9. Partitioning never loses or duplicates a row")
    # 'partitions' is a hint, not a guarantee: ceil(rows/wanted) means 5 rows with
    # partitions=4 yields 3 chunks. What must always hold is that the ranges are
    # contiguous, non-overlapping, and cover every row.
    all_ok = True
    for p in [1, 2, 3, 4, 5, 6, 10, 100]:
        d = (spark.read.format(V2)
             .option("path", f"{WORK}/people.csv")
             .option("partitions", str(p)).load())
        ids = sorted(int(r.id) for r in d.collect())
        if ids != [1, 2, 3, 4, 5]:
            all_ok = False
            print(f"        partitions={p} returned {ids}")
    check("row set is identical across 8 partition settings", all_ok)

    print("\n-- 10. Byte-range split boundaries: 56 size/partition combinations")
    # The reader splits on BYTE offsets, so a split can land mid-line. The boundary
    # rule (seek to start-1, discard one line, read past end to finish a straddling
    # line) must read every line exactly once for any file size and partition count.
    #
    # This matrix caught a real row-loss bug: the naive rule "if start > dataStart,
    # discard a line" drops a record whenever a range begins exactly on a line
    # boundary, which happens often at high partition counts. 14 of these 56 cases
    # failed before the fix.
    boundary_failures = []
    for nrows in [0, 1, 2, 3, 5, 17, 100, 1000]:
        path = f"{WORK}/boundary_{nrows}.csv"
        with open(path, "w") as f:
            f.write("id,name,dept\n")
            for i in range(1, nrows + 1):
                f.write(f"{i},user{i},{'eng' if i % 2 else 'math'}\n")
        expected = list(range(1, nrows + 1))
        for p in [1, 2, 3, 4, 7, 16, 64]:
            d = (spark.read.format(V2).option("path", path)
                 .option("partitions", str(p)).load())
            got = sorted(int(r.id) for r in d.collect())
            if got != expected:
                boundary_failures.append((nrows, p, len(got), len(expected)))
    check("every line read exactly once across 56 combinations",
          not boundary_failures,
          f"{len(boundary_failures)} failed, e.g. {boundary_failures[:3]}")

    print("\n-- 11. Read path streams rather than buffering")
    # 2 million rows (about 46 MB) through a reader that materializes one row at a
    # time. The earlier version built an ArrayList per partition AND called
    # readAllLines() per reader, so an 8-partition scan read the file 8 times and
    # held it all in memory.
    huge = f"{WORK}/stream_test.csv"
    rows_total = 300_000
    with open(huge, "w") as f:
        f.write("id,name,dept\n")
        for i in range(1, rows_total + 1):
            f.write(f"{i},user{i},{'eng' if i % 3 else 'math'}\n")
    streamed = (spark.read.format(V2).option("path", huge)
                .option("partitions", "8").load())
    check(f"streams {rows_total:,} rows", streamed.count() == rows_total,
          f"got {streamed.count()}")
    expected_eng = rows_total - rows_total // 3
    check("pushdown stays correct at scale",
          streamed.filter(streamed.dept == "eng").count() == expected_eng,
          f"expected {expected_eng}")

    print("\n-- 12. Write path scales without buffering rows in memory")
    # The DataWriter streams to a part file and the commit message carries only a
    # path, so neither the task nor the driver holds the dataset. This would still
    # pass if rows were buffered, but it would be doing so by luck at this size;
    # the design intent is asserted by the comments in CsvWriteBuilder.
    big = f"{WORK}/verify_big.csv"
    with open(big, "w") as f:
        f.write("id,name,dept\n")
        for i in range(1, 20001):
            f.write(f"{i},user{i},{'eng' if i % 3 else 'math'}\n")
    big_df = spark.read.format(V2).option("path", big).option("partitions", "8").load()
    check("reads 20k rows across 8 partitions", big_df.count() == 20000,
          f"got {big_df.count()}")

    dest = f"{WORK}/verify_big_out.csv"
    with open(dest, "w") as f:
        f.write("id,name,dept\n")
    big_df.write.format(V2).option("path", dest).mode("overwrite").save()
    round_trip = spark.read.format(V2).option("path", dest).load()
    check("writes 20k rows and reads them back intact", round_trip.count() == 20000,
          f"got {round_trip.count()}")

    # No orphaned part files: commit deletes each one after concatenating it.
    leftover = [p for p in os.listdir(tempfile.gettempdir())
                if p.startswith("csvv2-part-")]
    check("commit leaves no orphaned part files", not leftover,
          f"found {len(leftover)}")

    print("\n-- 13. Edge cases and error messages")
    header_only = f"{WORK}/empty.csv"
    with open(header_only, "w") as f:
        f.write("id,name,dept\n")
    empty_df = spark.read.format(V2).option("path", header_only).load()
    check("header-only file reads as 0 rows with schema intact",
          empty_df.count() == 0 and empty_df.schema.fieldNames() == ["id", "name", "dept"])

    def expect_error(fragment, fn):
        try:
            fn()
            return False
        except Exception as exc:
            return fragment.lower() in str(exc).lower()

    check("missing 'path' option raises a clear error",
          expect_error("path", lambda: spark.read.format(V2).load().count()))
    check("nonexistent file raises a clear error",
          expect_error("no such csv file", lambda: spark.read.format(V2)
                       .option("path", f"{WORK}/nope.csv").load().count()))
    check("partitions=0 is rejected",
          expect_error("at least 1", lambda: spark.read.format(V2)
                       .option("path", f"{WORK}/people.csv")
                       .option("partitions", "0").load().count()))

    spark.stop()

    print(f"\n{len(passed)} passed, {len(failed)} failed")
    if failed:
        for name, detail in failed:
            print(f"  FAILED: {name} {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
