/*
 * The BEFORE side of the migration: the same CSV source written against
 * DataSource V1.
 *
 * V1's shape is a RelationProvider that returns a BaseRelation. The relation
 * mixes in scan traits to opt into pushdown:
 *   TableScan          -> buildScan()
 *   PrunedScan         -> buildScan(requiredColumns)
 *   PrunedFilteredScan -> buildScan(requiredColumns, filters)
 *   InsertableRelation -> insert(dataFrame, overwrite)
 *
 * Three things to notice, because they are what the migration actually changes:
 *
 * 1. V1 has no concept of a catalog. A V1 source is addressed by path and options
 *    only, so there is nowhere to hang namespaces, functions, or procedures. This
 *    is the structural limit, not a missing feature.
 *
 * 2. buildScan returns an RDD, so the connector controls parallelism by
 *    constructing the RDD itself. In V2, the connector describes partitions and
 *    Spark builds the execution.
 *
 * 3. unhandledFilters is a separate method from buildScan, so the "which filters
 *    did you actually apply" answer is given in a different place from where they
 *    are applied. V2 folds this into pushFilters returning the leftovers, which is
 *    harder to get wrong.
 *
 * Also note that BaseRelation is an abstract Scala CLASS requiring a SQLContext,
 * which is deprecated API. That awkwardness from Java is itself a migration signal.
 */
package com.example.dsv2lab.v1;

import java.util.ArrayList;
import java.util.List;

import org.apache.spark.api.java.JavaRDD;
import org.apache.spark.api.java.JavaSparkContext;
import org.apache.spark.rdd.RDD;
import org.apache.spark.sql.Dataset;
import org.apache.spark.sql.Row;
import org.apache.spark.sql.RowFactory;
import org.apache.spark.sql.SQLContext;
import org.apache.spark.sql.sources.BaseRelation;
import org.apache.spark.sql.sources.EqualTo;
import org.apache.spark.sql.sources.Filter;
import org.apache.spark.sql.sources.InsertableRelation;
import org.apache.spark.sql.sources.PrunedFilteredScan;
import org.apache.spark.sql.sources.RelationProvider;
import org.apache.spark.sql.types.DataTypes;
import org.apache.spark.sql.types.Metadata;
import org.apache.spark.sql.types.StructField;
import org.apache.spark.sql.types.StructType;

public class CsvV1Source implements RelationProvider {

  @Override
  public BaseRelation createRelation(SQLContext sqlContext, scala.collection.immutable.Map<String, String> parameters) {
    String path = parameters.get("path").getOrElse(() -> {
      throw new IllegalArgumentException("CsvV1Source requires a 'path' option");
    });
    return new CsvRelation(sqlContext, path);
  }

  /** The V1 relation. Compare this to CsvTable plus CsvScanBuilder on the V2 side. */
  public static class CsvRelation extends BaseRelation implements PrunedFilteredScan, InsertableRelation {

    private final SQLContext sqlContext;
    private final String path;

    public CsvRelation(SQLContext sqlContext, String path) {
      this.sqlContext = sqlContext;
      this.path = path;
    }

    @Override
    public SQLContext sqlContext() {
      return sqlContext;
    }

    @Override
    public StructType schema() {
      List<String> header = V1CsvIo.header(path);
      StructField[] fields = new StructField[header.size()];
      for (int i = 0; i < header.size(); i++) {
        fields[i] = new StructField(header.get(i), DataTypes.StringType, true, Metadata.empty());
      }
      return new StructType(fields);
    }

    /**
     * V1 pushdown. The connector builds the RDD itself, applies what it can, and
     * separately reports leftovers through unhandledFilters.
     */
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
          // Note: plain java.lang.String here, because V1 speaks Row, not
          // InternalRow. The V2 path needs UTF8String instead.
          projected[i] = src < cells.size() ? cells.get(src) : null;
        }
        rows.add(RowFactory.create(projected));
      }

      JavaSparkContext jsc = JavaSparkContext.fromSparkContext(sqlContext.sparkContext());
      JavaRDD<Row> rdd = jsc.parallelize(rows, 2);
      return rdd.rdd();
    }

    /**
     * Reports which filters Spark must still apply. Declared apart from buildScan,
     * so the two can drift out of sync. V2 removes that hazard by having
     * pushFilters return the rejects directly.
     */
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

    private static boolean matches(List<String> cells, StructType schema, Filter[] filters) {
      for (Filter f : filters) {
        if (f instanceof EqualTo eq) {
          var idx = schema.getFieldIndex(eq.attribute());
          if (idx.isEmpty()) {
            continue;
          }
          int i = (int) idx.get();
          String actual = i < cells.size() ? cells.get(i) : null;
          if (actual == null || !actual.equals(String.valueOf(eq.value()))) {
            return false;
          }
        }
      }
      return true;
    }

    /**
     * The V1 write path: one method, no commit protocol. If this throws halfway
     * through, the destination is left in whatever state it reached. Compare to
     * the V2 side, where Spark coordinates task commits and the connector only has
     * to make its own commit atomic.
     */
    @Override
    public void insert(Dataset<Row> data, boolean overwrite) {
      List<String> lines = new ArrayList<>();
      if (!overwrite) {
        lines.addAll(V1CsvIo.dataLines(path));
      }
      for (Row r : data.collectAsList()) {
        String[] cells = new String[r.length()];
        for (int i = 0; i < r.length(); i++) {
          cells[i] = r.isNullAt(i) ? "" : String.valueOf(r.get(i));
        }
        lines.add(String.join(",", cells));
      }
      V1CsvIo.write(path, data.schema().fieldNames(), lines);
    }
  }
}
