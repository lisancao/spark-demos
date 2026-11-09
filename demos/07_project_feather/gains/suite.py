"""A test suite's worth of tiny DataFrames: N createDataFrame + aggregate + sort, total wall time.

  suite.py false|true N [list|pandas]
"""
import json, random, sys, time
from pyspark.sql import SparkSession, functions as F
flag, n = sys.argv[1], int(sys.argv[2])
source = sys.argv[3] if len(sys.argv) > 3 else "list"   # list | pandas
import pandas as pd
spark = (SparkSession.builder
         .config("spark.sql.optimizer.singleTaskExecution.enabled", flag).getOrCreate())
def case(i):
    rnd = random.Random(i)
    rows = [(rnd.randrange(5), rnd.randrange(100)) for _ in range(rnd.randrange(5, 50))]
    if source == "pandas":                        # Arrow path: a LocalRelation, eligible
        df = spark.createDataFrame(pd.DataFrame(rows, columns=["k", "v"]).astype("int32"))
    else:                                         # a Python list: a LogicalRDD, not eligible
        df = spark.createDataFrame(rows, "k int, v int")
    return df.groupBy("k").agg(F.sum("v").alias("s"), F.countDistinct("v").alias("d")).orderBy("k").collect()
for i in range(10): case(-i)                     # warm-up, like pytest's first fixture
t = time.perf_counter()
for i in range(n): case(i)
total = (time.perf_counter() - t) * 1000
print(json.dumps({"flag": flag, "source": source, "cases": n, "total_ms": round(total), "per_case_ms": round(total / n, 2)}))
