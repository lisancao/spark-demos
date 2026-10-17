package nightcity

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

/** The Night City event envelope as the sim emits it, plus the Kafka plumbing to read it. */
object Events {

  /** Fields every event carries. Type-specific fields stay in `raw` and are pulled out per processor. */
  val envelope: StructType = StructType(Seq(
    StructField("event_id", StringType),
    StructField("event_type", StringType),
    StructField("timestamp", StringType),
    StructField("source_timestamp", StringType),
    StructField("sim_tick", LongType),
    StructField("sim_day", IntegerType),
    StructField("sim_time_phase", StringType),
    StructField("sim_phase_tick", IntegerType),
    StructField("agent_id", StringType),
    StructField("agent_name", StringType),
    StructField("location_id", StringType),
    StructField("faction_id", StringType),
    StructField("mission_id", StringType),
    StructField("source_id", StringType),
    StructField("target_id", StringType),
  ))

  def bootstrap: String = sys.env.getOrElse("KAFKA_BOOTSTRAP", "localhost:29092")
  def topic: String = sys.env.getOrElse("KAFKA_TOPIC", "nightcity.events")

  /** Raw Kafka stream: one row per record, value as string, offsets kept for provenance. */
  def readKafka(spark: SparkSession, startingOffsets: String = "earliest"): DataFrame =
    spark.readStream
      .format("kafka")
      .option("kafka.bootstrap.servers", bootstrap)
      .option("subscribe", topic)
      .option("startingOffsets", startingOffsets)
      .option("maxOffsetsPerTrigger", sys.env.getOrElse("MAX_OFFSETS_PER_TRIGGER", "200000"))
      .load()
      .select(
        col("key").cast("string").as("kafka_key"),
        col("value").cast("string").as("raw"),
        col("partition").as("kafka_partition"),
        col("offset").as("kafka_offset"),
        col("timestamp").as("kafka_ts"),
      )

  /** Parse the envelope out of the raw JSON; keep `raw` for per-processor field extraction. */
  def parsed(raw: DataFrame): DataFrame =
    raw
      .withColumn("e", from_json(col("raw"), envelope))
      .select(col("e.*"), col("raw"), col("kafka_key"), col("kafka_partition"), col("kafka_offset"), col("kafka_ts"))
      .withColumn("event_time", to_timestamp(col("timestamp")))
      .withColumn("event_family", split(col("event_type"), "\\.").getItem(0))
}
