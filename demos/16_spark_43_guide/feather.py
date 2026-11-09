import time
from pyspark.sql import SparkSession
from plan_summary import operators  # the plan's operators, one per line

spark = SparkSession.builder.getOrCreate()
small = "data/small_orders.parquet"   # one small file: 500 rows

def run(single_task, runs=20):
    spark.conf.set("spark.sql.optimizer.singleTaskExecution.enabled",
                   single_task)
    t = time.perf_counter()
    for _ in range(runs):
        # a fresh DataFrame each time, like a notebook cell or a test
        df = (spark.read.parquet(small)
              .groupBy("store").count().orderBy("store"))
        df.collect()
    return df, (time.perf_counter() - t) / runs * 1000

run("false", 10); run("true", 10)     # warm up both settings first
for flag in ("false", "true"):
    df, ms = run(flag)
    print(f"singleTaskExecution={flag}: {ms:.1f} ms per query")
    print(operators(df) + "\n")
