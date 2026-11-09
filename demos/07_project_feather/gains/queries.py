"""The small queries the Feather gains benchmark times: one parquet file, 1,000 rows."""
from pyspark.sql import functions as F, Window

FILE = "gains/data/orders.parquet"

def make_data(spark):
    (spark.range(1000).select(
        F.col("id").alias("order_id"),
        (F.col("id") % 8).alias("store"),
        (F.col("id") % 25).alias("item"),
        F.round(F.rand(7) * 60 + 5, 2).alias("amount"))
     .coalesce(1).write.mode("overwrite").parquet(FILE))

def queries(spark):
    """Name -> a function that builds the query from scratch (so timing one builds only it)."""
    o = lambda: spark.read.parquet(FILE)
    by_store = Window.partitionBy("store").orderBy(F.desc("amount"))
    return {
        "group by":               lambda: o().groupBy("store").agg(F.sum("amount")),
        "group by, order by":     lambda: o().groupBy("store").agg(F.sum("amount")).orderBy("store"),
        "rank per store":         lambda: o().withColumn("rank", F.row_number().over(by_store))
                                             .orderBy("store", "rank"),
        "distinct, group, order": lambda: o().select("store", "item").distinct()
                                             .groupBy("store").count().orderBy(F.desc("count")),
        "rollup, order by":       lambda: o().rollup("store", "item").agg(F.sum("amount"))
                                             .orderBy("store", "item"),
        "top 3 per store":        lambda: o().withColumn("rank", F.row_number().over(by_store))
                                             .where("rank <= 3").orderBy("store", "rank"),
    }

def exchanges(df):
    plan = df._jdf.queryExecution().executedPlan().toString().split("== Initial Plan ==")[0]
    return sum(1 for l in plan.splitlines() if "Exchange " in l and "ReusedExchange" not in l)
