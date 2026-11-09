"""Step 1: Structured Streaming basics, in the default micro-batch mode.

A stream is a table that keeps growing. readStream gives you a DataFrame over it,
you write ordinary DataFrame code, and writeStream runs that code again on each
new slice of input (a micro-batch) every time the trigger fires.
"""
from pyspark.sql import functions as F

from bookshop.common import BOOTSTRAP, CHECKPOINTS, CLICK_SCHEMA, CLICKS, spark

s = spark("01-basics")

# The source: every record on the `clicks` topic, as Kafka hands it over (key, value, partition, offset, timestamp).
raw = (s.readStream.format("kafka")
       .option("kafka.bootstrap.servers", BOOTSTRAP)
       .option("subscribe", CLICKS)
       .option("startingOffsets", "latest")
       .load())

# Ordinary DataFrame code: parse the JSON, keep the clicks that mean intent.
clicks = (raw.select(F.from_json(F.col("value").cast("string"), CLICK_SCHEMA).alias("c"))
          .select("c.*")
          .where(F.col("action").isin("cart", "purchase"))
          .select("user_id", "book_id", "action", F.timestamp_millis("ts").alias("clicked_at")))

# The sink, the trigger and the checkpoint: print each micro-batch, one every 5 seconds,
# and keep the Kafka offsets in the checkpoint so a restart picks up where it stopped.
q = (clicks.writeStream.format("console")
     .option("truncate", False).option("numRows", 8)
     .option("checkpointLocation", str(CHECKPOINTS / "01-basics"))
     .outputMode("append")
     .trigger(processingTime="5 seconds")
     .start())

q.awaitTermination(timeout=int(__import__("os").environ.get("RUN_SECONDS", "30")))
p = q.lastProgress
if p:
    print(f"batch {p['batchId']}: {p['numInputRows']} input rows, "
          f"{p['durationMs'].get('triggerExecution')} ms to run the batch")
q.stop()
