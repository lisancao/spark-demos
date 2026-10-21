package nightcity.jobs

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.streaming.{OutputMode, StreamingQuery, Trigger}
import nightcity.{Events, ProgressLog}

/**
 * Phase 2: the streaming primer, run as three queries over the same replayed topic.
 *
 *  lateness  : stateless. Per event, how long after it happened did it reach Kafka. Decides the watermark.
 *  dedup     : dropDuplicatesWithinWatermark on event_id. Duplicates injected by the replay should vanish.
 *  windows   : tumbling 10s event-time windows per event family, append mode. Events later than the
 *              watermark are dropped; the gap against the batch truth is the cost of the watermark you chose.
 *
 * Run with --once (AvailableNow) for a deterministic result: maxOffsetsPerTrigger keeps batches small so
 * the watermark advances through the log the way it would through time.
 */
object Primer {
  def main(args: Array[String]): Unit = {
    val once = args.contains("--once")
    val watermark = sys.env.getOrElse("WATERMARK", "30 seconds")
    val out = sys.env.getOrElse("DATA_DIR", "/app/data")
    val tag = sys.env.getOrElse("RUN_TAG", watermark.replace(' ', '_'))
    val spark = SparkSession.builder().appName(s"nightcity-primer-$tag").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    ProgressLog.attach(spark, s"$out/primer/$tag/progress.jsonl")

    def trigger = if (once) Trigger.AvailableNow() else Trigger.ProcessingTime("5 seconds")
    def sink(df: DataFrame, name: String, mode: OutputMode): StreamingQuery =
      df.writeStream.format("parquet")
        .option("path", s"$out/primer/$tag/$name")
        .option("checkpointLocation", s"$out/checkpoints/primer/$tag/$name")
        .outputMode(mode).trigger(trigger).queryName(name).start()

    val events = Events.parsed(Events.readKafka(spark))

    // 1. lateness: delivery delay per event (Kafka append time minus event time)
    val lateness = events.select(
      col("event_id"), col("event_type"), col("event_family"), col("event_time"), col("kafka_ts"),
      (unix_millis(col("kafka_ts")) - unix_millis(col("event_time"))).as("delay_ms"),
    )
    val q1 = sink(lateness, "lateness", OutputMode.Append())

    // 2. dedup within watermark on event_id
    val dedup = events
      .withWatermark("event_time", watermark)
      .dropDuplicatesWithinWatermark("event_id")
      .select("event_id", "event_type", "event_family", "event_time")
    val q2 = sink(dedup, "dedup", OutputMode.Append())

    // 3. tumbling windows per family; append mode emits a window once the watermark passes its end
    val windows = events
      .withWatermark("event_time", watermark)
      .groupBy(window(col("event_time"), "10 seconds"), col("event_family"))
      .agg(count("*").as("events"), approx_count_distinct("event_id").as("distinct_events"))
      .select(col("window.start").as("window_start"), col("window.end").as("window_end"), col("event_family"), col("events"), col("distinct_events"))
    val q3 = sink(windows, "windows", OutputMode.Append())

    Seq(q1, q2, q3).foreach(_.awaitTermination())
    if (!once) spark.streams.awaitAnyTermination()
  }
}
