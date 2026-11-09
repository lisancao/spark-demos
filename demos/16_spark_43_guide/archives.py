from pyspark.sql import SparkSession

spark = (SparkSession.builder
         .config("spark.sql.files.archive.reader.enabled", "true")  # opt-in
         .getOrCreate())

# A tar of daily CSV exports, read without unpacking it first
(spark.read.option("header", "true")
      .option("archivePathFilter", "*.csv")      # skip the README inside
      .csv("data/exports.tar")
      .show())
