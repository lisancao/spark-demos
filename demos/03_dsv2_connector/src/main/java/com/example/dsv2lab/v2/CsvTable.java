/*
 * Step 2: the Table.
 *
 * Table is the central DSV2 abstraction: a named, described dataset. It does not
 * read or write anything itself. It declares what it can do via capabilities(),
 * and hands out builders through the SupportsRead and SupportsWrite mix-ins.
 *
 * The capability set is load-bearing. Spark checks it before planning, so a table
 * that forgets to declare BATCH_READ will fail with a "table does not support
 * batch scan" error even if newScanBuilder is implemented correctly.
 */
package com.example.dsv2lab.v2;

import java.util.EnumSet;
import java.util.Set;

import org.apache.spark.sql.connector.catalog.Column;
import org.apache.spark.sql.connector.catalog.SupportsRead;
import org.apache.spark.sql.connector.catalog.SupportsWrite;
import org.apache.spark.sql.connector.catalog.TableCapability;
import org.apache.spark.sql.connector.read.ScanBuilder;
import org.apache.spark.sql.connector.write.LogicalWriteInfo;
import org.apache.spark.sql.connector.write.WriteBuilder;
import org.apache.spark.sql.types.StructType;
import org.apache.spark.sql.util.CaseInsensitiveStringMap;

public class CsvTable implements SupportsRead, SupportsWrite {

  private static final Set<TableCapability> CAPABILITIES = EnumSet.of(
      TableCapability.BATCH_READ,
      TableCapability.BATCH_WRITE,
      TableCapability.TRUNCATE);

  private final StructType schema;
  private final CsvFile file;

  public CsvTable(StructType schema, CsvFile file) {
    this.schema = schema;
    this.file = file;
  }

  @Override
  public String name() {
    return "csv:" + file.path();
  }

  /**
   * columns() replaced schema() in Spark 3.4.0. Table.schema() still exists but is
   * deprecated, and the default columns() implementation just converts whatever
   * schema() returns. Overriding columns() directly is the current form; note that
   * Spark's own test sources still use the older schema() override.
   */
  @Override
  public Column[] columns() {
    return CatalogHelpers.asColumns(schema);
  }

  StructType schemaInternal() {
    return schema;
  }

  @Override
  public Set<TableCapability> capabilities() {
    return CAPABILITIES;
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
