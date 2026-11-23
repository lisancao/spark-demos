-- An Iceberg table on S3 through the REST catalog, with the official
-- iceberg-spark-runtime-4.1_2.13 and iceberg-aws-bundle jars on Spark 4.1.4.
CREATE NAMESPACE IF NOT EXISTS demo.shop;
DROP TABLE IF EXISTS demo.shop.orders PURGE;

CREATE TABLE demo.shop.orders (
  order_id bigint,
  title string,
  aisle string,
  price decimal(6, 2)
)
USING iceberg
PARTITIONED BY (aisle);

INSERT INTO demo.shop.orders VALUES
  (1, 'Dune', 'scifi', 18.99),
  (2, 'Hyperion', 'scifi', 16.50),
  (3, 'The Left Hand of Darkness', 'scifi', 15.00),
  (4, 'Piranesi', 'fantasy', 14.25);

SELECT aisle, count(*) AS orders, sum(price) AS revenue FROM demo.shop.orders GROUP BY aisle ORDER BY aisle;

-- Where the data went: one Parquet file per partition, written by S3FileIO.
SELECT partition, file_path, record_count FROM demo.shop.orders.files ORDER BY file_path;
