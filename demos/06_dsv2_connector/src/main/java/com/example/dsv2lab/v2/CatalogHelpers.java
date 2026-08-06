/*
 * A four-line helper that exists because of a real API gap.
 *
 * Table.columns() wants a Column[]. Spark converts a StructType to Column[]
 * internally with CatalogV2Util.structTypeToV2Columns, but that object is
 * private[sql], so a third-party connector cannot call it. The public path is
 * Column.create, so every connector ends up writing this loop.
 *
 * Worth knowing if you are keeping a schema as a StructType internally, which most
 * connectors do because the read and write paths still speak StructType.
 */
package com.example.dsv2lab.v2;

import org.apache.spark.sql.connector.catalog.Column;
import org.apache.spark.sql.types.StructField;
import org.apache.spark.sql.types.StructType;

public final class CatalogHelpers {

  private CatalogHelpers() {}

  public static Column[] asColumns(StructType schema) {
    StructField[] fields = schema.fields();
    Column[] columns = new Column[fields.length];
    for (int i = 0; i < fields.length; i++) {
      columns[i] = Column.create(fields[i].name(), fields[i].dataType(), fields[i].nullable());
    }
    return columns;
  }
}
