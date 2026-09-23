/*
 * Step 4: the reader factory and the reader.
 *
 * The factory is created on the driver and serialized to every executor, so
 * everything it holds must be Serializable. The reader it creates does the actual
 * per-task I/O.
 *
 * The reader STREAMS. next() advances one line at a time and get() converts just
 * that line, so memory is constant regardless of partition size. The tempting
 * alternative, building a List of rows in the constructor, works in a demo and then
 * runs a task out of memory on a real partition. A DSV2 PartitionReader is a cursor
 * for exactly this reason.
 *
 * A caveat worth stating plainly, because it is the sharpest edge in DSV2: a
 * PartitionReader<InternalRow> returns InternalRow, and InternalRow lives in
 * org.apache.spark.sql.catalyst, which is an internal package. String values must
 * be UTF8String, not java.lang.String, or you get a ClassCastException at runtime
 * rather than a compile error. Spark's own connectors do exactly this. It is the
 * unavoidable internal dependency in an otherwise public API, and it is part of why
 * "just return metadata" is easier said than done.
 */
package com.example.dsv2lab.v2;

import java.util.List;

import org.apache.spark.sql.catalyst.InternalRow;
import org.apache.spark.sql.catalyst.expressions.GenericInternalRow;
import org.apache.spark.sql.connector.read.InputPartition;
import org.apache.spark.sql.connector.read.PartitionReader;
import org.apache.spark.sql.connector.read.PartitionReaderFactory;
import org.apache.spark.sql.sources.EqualTo;
import org.apache.spark.sql.sources.Filter;
import org.apache.spark.sql.types.StructType;
import org.apache.spark.unsafe.types.UTF8String;

public class CsvReaderFactory implements PartitionReaderFactory {

  private static final long serialVersionUID = 1L;

  private final StructType fullSchema;
  private final StructType requiredSchema;
  private final Filter[] pushedFilters;
  private final CsvFile file;

  public CsvReaderFactory(
      StructType fullSchema, StructType requiredSchema, Filter[] pushedFilters, CsvFile file) {
    this.fullSchema = fullSchema;
    this.requiredSchema = requiredSchema;
    this.pushedFilters = pushedFilters;
    this.file = file;
  }

  @Override
  public PartitionReader<InternalRow> createReader(InputPartition partition) {
    CsvInputPartition p = (CsvInputPartition) partition;
    return new CsvPartitionReader(p, fullSchema, requiredSchema, pushedFilters, file);
  }

  /** The reader: next() advances, get() returns the current row, close() releases. */
  static final class CsvPartitionReader implements PartitionReader<InternalRow> {

    private final StructType fullSchema;
    private final Filter[] pushedFilters;
    private final int[] projection;
    private final CsvFile.LineRange range;

    private InternalRow currentRow;

    CsvPartitionReader(
        CsvInputPartition partition,
        StructType fullSchema,
        StructType requiredSchema,
        Filter[] pushedFilters,
        CsvFile file) {

      this.fullSchema = fullSchema;
      this.pushedFilters = pushedFilters;

      // Map each required column to its position in the full row, so pruning is
      // applied while building the row rather than after.
      this.projection = new int[requiredSchema.fields().length];
      for (int i = 0; i < projection.length; i++) {
        projection[i] = (int) fullSchema.getFieldIndex(requiredSchema.fields()[i].name()).get();
      }

      // Opens a handle over this partition's byte range only. Nothing is read yet.
      this.range = file.open(partition.startByte, partition.endByte);
    }

    /**
     * Pulls lines until one passes the pushed filters, converting exactly one row.
     * Filtering here rather than after materializing is what makes pushdown pay off.
     */
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
          // UTF8String, not String. This is the internal-API edge described above.
          values[i] = src < cells.size() ? UTF8String.fromString(cells.get(src)) : null;
        }
        currentRow = new GenericInternalRow(values);
        return true;
      }
      currentRow = null;
      return false;
    }

    @Override
    public InternalRow get() {
      return currentRow;
    }

    /**
     * Applies only the filters this connector claimed in pushFilters. Since the
     * builder claimed them, Spark will not re-check them, so the logic here has to
     * be right.
     */
    private static boolean matchesPushedFilters(
        List<String> cells, StructType fullSchema, Filter[] filters) {
      for (Filter f : filters) {
        if (f instanceof EqualTo eq) {
          int idx = (int) fullSchema.getFieldIndex(eq.attribute()).get();
          String actual = idx < cells.size() ? cells.get(idx) : null;
          if (actual == null || !actual.equals(String.valueOf(eq.value()))) {
            return false;
          }
        }
      }
      return true;
    }

    /** Releases the file handle. Spark calls this once per partition. */
    @Override
    public void close() {
      range.close();
    }
  }
}
