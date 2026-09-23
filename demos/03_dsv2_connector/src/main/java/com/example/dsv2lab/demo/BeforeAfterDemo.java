/*
 * The before/after demo. Run this class directly from your IDE (green arrow) or
 * with ./demo.sh.
 *
 * It runs the SAME query against the same file through three connectors and prints
 * what changed:
 *
 *   BEFORE  DataSource V1  (com.example.dsv2lab.v1.CsvV1Source)
 *   AFTER   DataSource V2  (com.example.dsv2lab.v2.CsvV2Source)
 *   AFTER+  DataSource V2 via a catalog (com.example.dsv2lab.catalog.CsvCatalog)
 *
 * Nothing here is mocked. Every plan printed below comes from a real Spark
 * session on this machine.
 */
package com.example.dsv2lab.demo;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.SparkSession;

public final class BeforeAfterDemo {

  private static final String V1 = "com.example.dsv2lab.v1.CsvV1Source";
  private static final String V2 = "com.example.dsv2lab.v2.CsvV2Source";
  private static final String WORK = "/tmp/dsv2lab";
  private static final String DATA = WORK + "/people.csv";

  public static void main(String[] args) throws IOException {
    quietSparkLogs();
    writeFixture();

    SparkSession spark = SparkSession.builder()
        .appName("dsv2-before-after")
        .master("local[2]")
        .config("spark.sql.catalog.demo", "com.example.dsv2lab.catalog.CsvCatalog")
        .config("spark.sql.catalog.demo.warehouse", WORK + "/demo-warehouse")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate();
    spark.sparkContext().setLogLevel("ERROR");

    banner("THE QUERY (identical in every case)");
    System.out.println("  SELECT name FROM people WHERE dept = 'eng'");
    System.out.println();
    System.out.println("  people.csv:");
    for (String line : Files.readAllLines(Paths.get(DATA))) {
      System.out.println("    " + line);
    }

    // ---------------- BEFORE ----------------
    banner("BEFORE: DataSource V1");
    Dataset<Row> v1 = spark.read().format(V1).option("path", DATA).load();
    Dataset<Row> v1q = v1.select("name").filter(v1.col("dept").equalTo("eng"));

    System.out.println("  Result:");
    show(v1q);
    System.out.println("  Physical plan:");
    indent(plan(v1q));
    note("""
          What the connector had to do:
            - build the RDD itself (buildScan returns RDD<Row>)
            - report leftovers separately, via unhandledFilters()
            - write with a single insert() call: no commit, no abort
          What it CANNOT do, at all:
            - be addressed as catalog.namespace.table
            - CREATE TABLE / SHOW TABLES / multi-part namespaces
            - MERGE, UPDATE, DELETE, CDC, transactions""");

    // ---------------- AFTER ----------------
    banner("AFTER: DataSource V2");
    Dataset<Row> v2 = spark.read().format(V2).option("path", DATA).load();
    Dataset<Row> v2q = v2.select("name").filter(v2.col("dept").equalTo("eng"));

    System.out.println("  Result (identical, which is the point):");
    show(v2q);
    System.out.println("  Physical plan:");
    indent(plan(v2q));
    note("""
          Read the BatchScan line above. The connector's own description() reports
          what Spark handed it:
            columns=name,dept   column pruning dropped 'id' before any I/O
            pushedFilters=1     the equality filter reached the connector
          Spark still applies isnotnull(dept), because pushFilters() declined it.""");

    // ---------------- AFTER, with a catalog ----------------
    banner("AFTER+: the same V2 code behind a catalog");
    spark.sql("CREATE NAMESPACE IF NOT EXISTS demo.analytics");
    spark.sql("CREATE NAMESPACE IF NOT EXISTS demo.analytics.regional");
    spark.sql("CREATE TABLE IF NOT EXISTS demo.analytics.people "
        + "(id STRING, name STRING, dept STRING)");
    spark.sql("CREATE TABLE IF NOT EXISTS demo.analytics.regional.emea "
        + "(id STRING, region STRING)");
    if (spark.sql("SELECT * FROM demo.analytics.people").count() == 0) {
      spark.sql("INSERT INTO demo.analytics.people VALUES "
          + "('1','ada','eng'), ('2','grace','eng'), ('3','alan','research')");
    }

    System.out.println("  Now it is SQL, with no format string and no path:");
    System.out.println("    SELECT name FROM demo.analytics.people WHERE dept = 'eng'");
    Dataset<Row> sqlq = spark.sql("SELECT name FROM demo.analytics.people WHERE dept = 'eng'");
    show(sqlq);
    System.out.println("  Physical plan (same BatchScan, same pushdown):");
    indent(plan(sqlq));

    System.out.println("  Three-level namespace, which database.table cannot express:");
    show(spark.sql("SHOW TABLES IN demo.analytics.regional"));

    // ---------------- the honest part ----------------
    banner("THE TRADEOFF");
    long v1Lines = countJava(Paths.get("src/main/java/com/example/dsv2lab/v1"));
    long v2Lines = countJava(Paths.get("src/main/java/com/example/dsv2lab/v2"));
    long catLines = countJava(Paths.get("src/main/java/com/example/dsv2lab/catalog"));
    if (v1Lines > 0) {
      System.out.printf("  V1 connector        %4d lines across 2 files%n", v1Lines);
      System.out.printf("  V2 connector        %4d lines across 8 files%n", v2Lines);
      System.out.printf("  V2 catalog          %4d lines across 2 files%n", catLines);
      System.out.println();
      System.out.println("  V2 is more code. You are buying capability, not brevity:");
      System.out.println("  the catalog, DML, CDC, and transactions have no V1 equivalent.");
    } else {
      System.out.println("  (run from the repo root to see the line count comparison)");
    }

    banner("WHAT TO OPEN NEXT");
    note("""
          Read the V2 connector in this order:
            1  v2/CsvV2Source.java       TableProvider, the entry point
            2  v2/CsvTable.java          Table, and why capabilities() matters
            3  v2/CsvScanBuilder.java    pushdown negotiation  <-- the interesting one
            4  v2/CsvReaderFactory.java  per-task I/O, and the UTF8String trap
            5  v2/CsvWriteBuilder.java   two-phase commit
            6  catalog/CsvCatalog.java   what V1 structurally cannot do
          Then diff against v1/CsvV1Source.java, and read MIGRATION.md.""");

    spark.stop();
  }

  // ---------- helpers ----------

  /**
   * Quiets Spark's startup logging.
   *
   * SparkContext.setLogLevel only takes effect after the context exists, by which
   * point roughly forty INFO lines have printed. src/main/resources/log4j2.properties
   * does the real work; this is a belt-and-braces call for IDE runs where resources
   * may not be on the classpath.
   */
  private static void quietSparkLogs() {
    System.setProperty("org.apache.logging.log4j.level", "ERROR");
    try {
      org.apache.logging.log4j.core.config.Configurator.setRootLevel(
          org.apache.logging.log4j.Level.ERROR);
    } catch (Throwable ignored) {
      // Not fatal: the properties file already handles this.
    }
  }

  /**
   * Prints a block indented by four spaces, after removing whatever common leading
   * margin the Java text block carried in. Keeps relative indentation intact.
   */
  private static void note(String block) {
    String[] lines = block.stripTrailing().split("\n");
    int margin = Integer.MAX_VALUE;
    for (String line : lines) {
      if (!line.isBlank()) {
        margin = Math.min(margin, line.length() - line.stripLeading().length());
      }
    }
    if (margin == Integer.MAX_VALUE) {
      margin = 0;
    }
    for (String line : lines) {
      System.out.println(line.isBlank() ? "" : "    " + line.substring(margin));
    }
  }

  private static void banner(String title) {
    System.out.println();
    System.out.println("=".repeat(74));
    System.out.println("  " + title);
    System.out.println("=".repeat(74));
  }

  private static void show(Dataset<Row> df) {
    df.show(false);
  }

  private static String plan(Dataset<Row> df) {
    return df.queryExecution().executedPlan().toString().trim();
  }

  private static void indent(String block) {
    for (String line : block.split("\n")) {
      System.out.println("    " + line);
    }
    System.out.println();
  }

  private static long countJava(Path dir) {
    if (!Files.isDirectory(dir)) {
      return 0;
    }
    try (var files = Files.list(dir)) {
      return files.filter(p -> p.toString().endsWith(".java"))
          .mapToLong(p -> {
            try {
              return Files.readAllLines(p).size();
            } catch (IOException e) {
              return 0;
            }
          }).sum();
    } catch (IOException e) {
      return 0;
    }
  }

  private static void writeFixture() throws IOException {
    Files.createDirectories(Paths.get(WORK));
    Path data = Paths.get(DATA);
    if (!Files.exists(data)) {
      Files.write(data, List.of(
          "id,name,dept",
          "1,ada,eng",
          "2,grace,eng",
          "3,alan,research",
          "4,katherine,math",
          "5,dorothy,eng"), StandardCharsets.UTF_8);
    }
  }
}
