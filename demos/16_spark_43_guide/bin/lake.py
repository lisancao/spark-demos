"""A classic SparkSession on the same Iceberg warehouse the SCD2 pipeline writes to."""
import os
from pyspark.sql import SparkSession

DEMO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def lake():
    spark = (SparkSession.builder.master("local[2]")
        .config("spark.jars", f"{DEMO}/jars/iceberg-spark-runtime-4.3_2.13.jar")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.lake", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lake.type", "hadoop")
        .config("spark.sql.catalog.lake.warehouse", f"file://{DEMO}/data/scd2/warehouse")
        .config("spark.ui.enabled", "false")
        .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    return spark

if __name__ == "__main__":
    lake().sql("CREATE NAMESPACE IF NOT EXISTS lake.kitchen")
