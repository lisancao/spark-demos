/*
 * The Table a catalog hands back.
 *
 * It delegates its read and write paths to the same CsvTable used by the
 * path-based source, which is the reuse the DSV2 shape is meant to give you: the
 * catalog answers "which table is this name", and the table answers "how do I scan
 * and write it". Neither concern leaks into the other.
 */
package com.example.dsv2lab.catalog;

import java.nio.file.Path;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import org.apache.spark.sql.connector.catalog.Column;
import org.apache.spark.sql.connector.catalog.Identifier;
import org.apache.spark.sql.connector.catalog.SupportsRead;
import org.apache.spark.sql.connector.catalog.SupportsWrite;
import org.apache.spark.sql.connector.catalog.TableCapability;
import org.apache.spark.sql.connector.read.ScanBuilder;
import org.apache.spark.sql.connector.write.LogicalWriteInfo;
import org.apache.spark.sql.connector.write.WriteBuilder;
import org.apache.spark.sql.types.StructType;
import org.apache.spark.sql.util.CaseInsensitiveStringMap;

import com.example.dsv2lab.v2.CsvFile;
import com.example.dsv2lab.v2.CsvScanBuilder;
import com.example.dsv2lab.v2.CsvWriteBuilder;

public class CsvCatalogTable implements SupportsRead, SupportsWrite {

  private static final Set<TableCapability> CAPABILITIES = EnumSet.of(
      TableCapability.BATCH_READ,
      TableCapability.BATCH_WRITE,
      TableCapability.TRUNCATE);

  private final Identifier ident;
  private final CsvFile file;
  private final StructType schema;

  private CsvCatalogTable(Identifier ident, CsvFile file, StructType schema) {
    this.ident = ident;
    this.file = file;
    this.schema = schema;
  }

  static CsvCatalogTable load(Identifier ident, Path path) {
    Map<String, String> opts = new HashMap<>();
    opts.put("path", path.toString());
    CsvFile file = CsvFile.from(new CaseInsensitiveStringMap(opts));
    return new CsvCatalogTable(ident, file, file.schema());
  }

  @Override
  public String name() {
    return ident.toString();
  }

  @Override
  public Column[] columns() {
    Column[] out = new Column[schema.fields().length];
    for (int i = 0; i < out.length; i++) {
      out[i] = Column.create(
          schema.fields()[i].name(), schema.fields()[i].dataType(), schema.fields()[i].nullable());
    }
    return out;
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
