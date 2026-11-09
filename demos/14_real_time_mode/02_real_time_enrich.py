"""Step 2: the same kind of query in Real-time Mode, plus a stream-static join.

Each click is joined to the catalog (a static Parquet table, broadcast to every task)
and written to the `enriched` topic with its title and aisle. The query is stateless,
so the only change for Real-time Mode is the trigger, and the update output mode it
requires.

  python 02_real_time_enrich.py --mode rtm      # Trigger.RealTime
  python 02_real_time_enrich.py --mode micro    # the default engine, for comparison
"""
import argparse
import os

from pyspark.sql import functions as F

from bookshop.common import BOOTSTRAP, CATALOG, CHECKPOINTS, CLICK_SCHEMA, CLICKS, ENRICHED, spark

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["rtm", "micro"], default="rtm")
ap.add_argument("--seconds", type=int, default=int(os.environ.get("RUN_SECONDS", "60")))
a = ap.parse_args()

s = spark(f"02-enrich-{a.mode}")
books = s.read.parquet(CATALOG).select("book_id", "title", "author", "aisle")

clicks = (s.readStream.format("kafka")
          .option("kafka.bootstrap.servers", BOOTSTRAP)
          .option("subscribe", CLICKS)
          .option("startingOffsets", "latest")
          .load()
          .select(F.from_json(F.col("value").cast("string"), CLICK_SCHEMA).alias("c"))
          .select("c.*"))

enriched = (clicks.join(F.broadcast(books), "book_id")
            .select(F.col("user_id").alias("key"),
                    F.to_json(F.struct("event_id", "user_id", "action", "ts", "book_id",
                                       "title", "aisle")).alias("value")))

w = (enriched.writeStream.format("kafka")
     .option("kafka.bootstrap.servers", BOOTSTRAP)
     .option("topic", ENRICHED)
     .option("checkpointLocation", str(CHECKPOINTS / f"02-enrich-{a.mode}"))
     .outputMode("update"))
if a.mode == "rtm":
    w = w.trigger(realTime="30 seconds")       # a checkpoint every 30 s; records don't wait for it
else:
    w = w.trigger(processingTime="0 seconds")  # micro-batches back to back, as fast as they go

q = w.start()
print(f"running in {a.mode} for {a.seconds}s", flush=True)
q.awaitTermination(timeout=a.seconds)
q.stop()
