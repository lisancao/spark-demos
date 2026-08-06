/*
 * Step 3: the ScanBuilder, where pushdown is negotiated.
 *
 * This class implements three interfaces at once, which is the common shape in
 * Spark's own reference connectors:
 *   ScanBuilder -> build() produces a Scan
 *   Scan        -> describes the read (schema, description)
 *   Batch       -> plans partitions and creates the reader factory
 *
 * Two pushdown mix-ins are added on top, and they are strictly optional. A
 * connector that implements neither still returns correct results; Spark simply
 * evaluates the filters and drops the columns itself after reading everything.
 * Pushdown is an optimization, not a correctness requirement.
 *
 * Order matters: Spark applies SupportsPushDownFilters before
 * SupportsPushDownRequiredColumns, so pruneColumns receives the schema needed
 * after filtering.
 */
package com.example.dsv2lab.v2;

import java.util.ArrayList;
import java.util.List;

import org.apache.spark.sql.connector.read.Batch;
import org.apache.spark.sql.connector.read.InputPartition;
import org.apache.spark.sql.connector.read.PartitionReaderFactory;
import org.apache.spark.sql.connector.read.Scan;
import org.apache.spark.sql.connector.read.ScanBuilder;
import org.apache.spark.sql.connector.read.SupportsPushDownFilters;
import org.apache.spark.sql.connector.read.SupportsPushDownRequiredColumns;
import org.apache.spark.sql.sources.EqualTo;
import org.apache.spark.sql.sources.Filter;
import org.apache.spark.sql.types.StructType;

public class CsvScanBuilder
    implements ScanBuilder, Scan, Batch, SupportsPushDownFilters, SupportsPushDownRequiredColumns {

  private final StructType fullSchema;
  private final CsvFile file;

  private StructType requiredSchema;
  private Filter[] pushedFilters = new Filter[0];

  public CsvScanBuilder(StructType fullSchema, CsvFile file) {
    this.fullSchema = fullSchema;
    this.file = file;
    this.requiredSchema = fullSchema;
  }

  /**
   * Spark offers every filter it could push. Return the ones NOT handled, so Spark
   * knows to keep evaluating those itself. Getting this backwards is a classic
   * source of silently wrong results: claim a filter you do not apply and rows that
   * should have been removed come back.
   *
   * This connector only handles equality on string columns, which is the honest
   * limit of a CSV scan. Everything else goes back to Spark.
   */
  @Override
  public Filter[] pushFilters(Filter[] filters) {
    List<Filter> accepted = new ArrayList<>();
    List<Filter> rejected = new ArrayList<>();
    for (Filter f : filters) {
      if (f instanceof EqualTo eq && fullSchema.getFieldIndex(eq.attribute()).isDefined()) {
        accepted.add(f);
      } else {
        rejected.add(f);
      }
    }
    this.pushedFilters = accepted.toArray(new Filter[0]);
    return rejected.toArray(new Filter[0]);
  }

  /** Spark reads this back to know what it no longer needs to re-evaluate. */
  @Override
  public Filter[] pushedFilters() {
    return pushedFilters;
  }

  /** Column pruning. Spark tells the connector the narrowest schema it can use. */
  @Override
  public void pruneColumns(StructType requiredSchema) {
    this.requiredSchema = requiredSchema;
  }

  @Override
  public Scan build() {
    return this;
  }

  @Override
  public Batch toBatch() {
    return this;
  }

  @Override
  public StructType readSchema() {
    return requiredSchema;
  }

  /**
   * Shows up in EXPLAIN and the Spark UI. Worth implementing: it is how a user
   * confirms that pushdown actually happened.
   */
  @Override
  public String description() {
    return "CsvScan(path=" + file.path()
        + ", columns=" + String.join(",", requiredSchema.fieldNames())
        + ", pushedFilters=" + pushedFilters.length + ")";
  }

  /**
   * One InputPartition per byte range. Each is serialized to an executor.
   *
   * Byte ranges come from the file length alone, so planning does not read data and
   * its cost does not grow with the file.
   */
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
