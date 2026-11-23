# Results

Run on 2026-11-22: Spark 4.1.4 (`apache/spark:4.1.4-scala2.13-java21-python3-ubuntu`), Iceberg 1.12.0 jars from Maven Central, `apache/iceberg-rest-fixture:1.10.1`, `rustfs/rustfs:1.0.6`. The full output is in `output/`.

## basics

The REST catalog gives the table location, and `S3FileIO` writes one Parquet file for each `aisle` partition:

```
fantasy	1	14.25
scifi	3	50.49
{"aisle":"fantasy"}	s3://warehouse/shop/orders/data/aisle=fantasy/00000-4-...-00002.parquet	1
{"aisle":"scifi"}	s3://warehouse/shop/orders/data/aisle=scifi/00000-4-...-00001.parquet	3
```

## no-bundle

Without `iceberg-aws-bundle`, the first query fails. The first line of the error is about a constructor. The second line names the missing AWS SDK class:

```
java.lang.IllegalArgumentException: Cannot initialize FileIO implementation org.apache.iceberg.aws.s3.S3FileIO: Cannot find constructor for interface org.apache.iceberg.io.FileIO
	Missing org.apache.iceberg.aws.s3.S3FileIO [java.lang.NoClassDefFoundError: software/amazon/awssdk/core/exception/SdkException]
```

The SDK class in the second line can change from run to run (an earlier run named `software/amazon/awssdk/services/s3/model/S3Exception`). It is always a `software/amazon/awssdk` class.

## extensions

| Statement | With the extensions | Without the extensions |
|---|---|---|
| `MERGE INTO` a v3 table | ok, `_row_id` kept | ok, `_row_id` kept |
| `UPDATE`, `DELETE` | ok | ok |
| `CALL demo.system.rewrite_data_files` | ok | ok |
| `CREATE VIEW`, `DROP VIEW` | ok | `Catalog demo does not support views` |
| `ALTER TABLE ... CREATE BRANCH` | ok | `PARSE_SYNTAX_ERROR` |
| `ALTER TABLE ... WRITE ORDERED BY` | ok | `PARSE_SYNTAX_ERROR` |

The row lineage after the `MERGE` is the same in both runs, as `(id, stock, _row_id, _last_updated_sequence_number)`: `(1, 3, 0, 1), (2, 5, 1, 2), (3, 2, 3, 2)`. Row 2 keeps `_row_id` 1 and gets sequence number 2.

## wrong-jar

The 3.5_2.12 runtime fails two times on Spark 4.1.4. First, the extensions do not load, because Scala 2.13 has no `scala.Serializable`. Spark logs this as a WARN and starts the session without the extensions. Then the first query fails, because Spark 4.1 does not have the method that the 3.5 code calls:

```
WARN SparkSession: Cannot use org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions to configure session extensions.
java.lang.NoClassDefFoundError: scala/Serializable
ERROR SparkSQLDriver: Failed in [SELECT count(*) FROM demo.shop.orders]
java.lang.NoSuchMethodError: 'org.apache.spark.sql.internal.SQLConf org.apache.spark.sql.SQLContext.conf()'
```
