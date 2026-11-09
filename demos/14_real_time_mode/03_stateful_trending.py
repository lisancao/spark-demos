"""Step 3: stateful queries in Real-time Mode (new in 4.3): dedup and a windowed aggregation.

Retried events are dropped by event_id, then clicks are counted per aisle per minute.
Both operators keep state, so both need every record for a key on one task: a shuffle.
In Real-time Mode that shuffle is pipelined, so the counts still move per record.
"""
import argparse
import os

from pyspark.sql import functions as F

from bookshop.common import BOOTSTRAP, CATALOG, CHECKPOINTS, CLICK_SCHEMA, CLICKS, TRENDING, spark

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["rtm", "micro"], default="rtm")
ap.add_argument("--seconds", type=int, default=int(os.environ.get("RUN_SECONDS", "60")))
a = ap.parse_args()

s = spark(f"03-trending-{a.mode}")
books = s.read.parquet(CATALOG).select("book_id", "aisle")

clicks = (s.readStream.format("kafka")
          .option("kafka.bootstrap.servers", BOOTSTRAP)
          .option("subscribe", CLICKS)
          .option("startingOffsets", "latest")
          .load()
          .select(F.from_json(F.col("value").cast("string"), CLICK_SCHEMA).alias("c"))
          .select("c.*")
          .withColumn("event_time", F.timestamp_millis("ts")))

trending = (clicks
            .dropDuplicates(["event_id"])                       # stateful: every event_id seen so far
            .join(F.broadcast(books), "book_id")
            .withWatermark("event_time", "30 seconds")
            .groupBy(F.window("event_time", "1 minute"), "aisle")   # stateful: a running count per window and aisle
            .agg(F.count("*").alias("clicks"),
                 F.sum(F.when(F.col("action") == "purchase", 1).otherwise(0)).alias("purchases"),
                 F.max("ts").alias("last_ts")))

out = trending.select(
    F.col("aisle").alias("key"),
    F.to_json(F.struct(F.col("window.start").alias("minute"), "aisle", "clicks", "purchases",
                       "last_ts")).alias("value"))

w = (out.writeStream.format("kafka")
     .option("kafka.bootstrap.servers", BOOTSTRAP)
     .option("topic", TRENDING)
     .option("checkpointLocation", str(CHECKPOINTS / f"03-trending-{a.mode}"))
     .outputMode("update"))
w = w.trigger(realTime="30 seconds") if a.mode == "rtm" else w.trigger(processingTime="0 seconds")

q = w.start()
print(f"running in {a.mode} for {a.seconds}s", flush=True)
q.awaitTermination(timeout=a.seconds)
q.stop()
