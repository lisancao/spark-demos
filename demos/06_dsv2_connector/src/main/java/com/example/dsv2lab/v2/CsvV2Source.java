/*
 * Step 1 of the DSV2 connector: the entry point.
 *
 * TableProvider is what Spark looks for when you call
 * spark.read.format("com.example.dsv2lab.v2.CsvV2Source"). It answers one
 * question: given these options, what Table am I dealing with?
 *
 * Note that TableProvider is for path-and-option style sources. A catalog-backed
 * source implements TableCatalog instead, which is the CatalogCsvSource class in
 * the catalog package.
 */
package com.example.dsv2lab.v2;

import java.util.Map;

import org.apache.spark.sql.connector.catalog.Table;
import org.apache.spark.sql.connector.catalog.TableProvider;
import org.apache.spark.sql.connector.expressions.Transform;
import org.apache.spark.sql.types.StructType;
import org.apache.spark.sql.util.CaseInsensitiveStringMap;

public class CsvV2Source implements TableProvider {

  /**
   * Spark calls this first when the user did not supply a schema. Inferring means
   * reading enough of the source to know its shape. This connector reads the header
   * line and treats every column as a string, which keeps the example honest: real
   * type inference is a separate concern from the DSV2 API.
   */
  @Override
  public StructType inferSchema(CaseInsensitiveStringMap options) {
    return CsvFile.from(options).schema();
  }

  /**
   * Spark calls this to get the Table. The schema argument is either what
   * inferSchema returned or the schema the user supplied explicitly, so a
   * connector should honor it rather than re-inferring.
   */
  @Override
  public Table getTable(StructType schema, Transform[] partitioning, Map<String, String> properties) {
    return new CsvTable(schema, CsvFile.from(new CaseInsensitiveStringMap(properties)));
  }

  /**
   * Returning false means Spark will not pass a user-specified schema straight
   * through without calling inferSchema. Set this to true only if the source can
   * genuinely accept an arbitrary schema, because Spark relies on the answer when
   * it decides whether to validate.
   */
  @Override
  public boolean supportsExternalMetadata() {
    return true;
  }
}
