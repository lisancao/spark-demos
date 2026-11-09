"""Arrow-native cache vs the default cache serializer (static conf, so one process each).

  cache.py default|arrow [codec] [prefetch]    codec: none (the default), lz4 or zstd
Times a SQL aggregation over the cached data and a full toArrow() of it.
"""
import json, statistics as st, sys, time
from pyspark.sql import SparkSession, functions as F
ser = sys.argv[1]; codec = sys.argv[2] if len(sys.argv) > 2 else "none"
prefetch = sys.argv[3] if len(sys.argv) > 3 else "false"
SER = {"default": "org.apache.spark.sql.execution.columnar.DefaultCachedBatchSerializer",
       "arrow": "org.apache.spark.sql.execution.columnar.ArrowCachedBatchSerializer"}[ser]
spark = (SparkSession.builder.config("spark.sql.cache.serializer", SER)
         .config("spark.sql.execution.arrow.compression.codec", codec)
         .config("spark.sql.execution.arrow.cache.prefetch.enabled", prefetch).getOrCreate())
df = spark.range(2_000_000).select(
    F.col("id"), (F.col("id") % 50).alias("store"),
    F.concat(F.lit("sku-"), (F.col("id") % 5000).cast("string")).alias("sku"),
    F.round(F.rand(3) * 100, 2).alias("amount")).cache()
t = time.perf_counter(); df.count(); build = (time.perf_counter() - t) * 1000
size = sum(r.memSize() for r in spark.sparkContext._jsc.sc().getRDDStorageInfo())
def med(f, n):
    f(); xs = []
    for _ in range(n):
        t = time.perf_counter(); f(); xs.append((time.perf_counter() - t) * 1000)
    return round(st.median(xs), 1)
agg = med(lambda: df.groupBy("store").agg(F.sum("amount")).collect(), 15)
arrow = med(lambda: df.toArrow(), 7)
print(json.dumps({"serializer": ser, "codec": codec, "prefetch": prefetch, "build_ms": round(build),
                  "cached_mb": round(size / 2**20, 1), "agg_ms": agg, "toArrow_ms": arrow}))
