from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.getOrCreate()
orders = spark.read.parquet("data/small_orders.parquet").limit(4)

# Two projections of the same DataFrame, built separately...
ids    = orders.select("order_id", "store")
priced = orders.select(F.round(F.col("amount") * 1.13, 2).alias("with_tax"))

# ...zipped back together row by row: no join key, no shuffle
ids.zip(priced).show()
