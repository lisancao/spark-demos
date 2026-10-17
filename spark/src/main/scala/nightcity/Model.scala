package nightcity

import java.sql.Timestamp
import org.apache.spark.sql.{DataFrame, Dataset, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

/** One flat row type for every processor input: the envelope plus the type-specific fields the processors read. */
case class Ev(
    event_id: String,
    event_type: String,
    event_time: Timestamp,
    sim_tick: Long,
    agent_id: String,
    agent_name: String,
    location_id: String,
    from_location: String,
    attacker_id: String,
    target_id: String,
    round: Option[Int],
    rounds: Option[Int],
    result: String,
    district: String,
    crime_type: String,
    severity: Option[Int],
    response_ticks: Option[Int],
    dispatched: Option[Boolean],
    chrome_score: Option[Int],
    new_goal: String,
    faction_id: String,
    source_id: String,
    new_strength: Option[Double],
    old_strength: Option[Double],
    price: Option[Int],
    buyer_id: String,
    seller_id: String,
)

object Ev {
  val schema: StructType = StructType(Seq(
    StructField("event_id", StringType), StructField("event_type", StringType),
    StructField("timestamp", StringType), StructField("sim_tick", LongType),
    StructField("agent_id", StringType), StructField("agent_name", StringType),
    StructField("location_id", StringType), StructField("from_location", StringType),
    StructField("attacker_id", StringType), StructField("target_id", StringType),
    StructField("round", IntegerType), StructField("rounds", IntegerType), StructField("result", StringType),
    StructField("district", StringType), StructField("crime_type", StringType), StructField("severity", IntegerType),
    StructField("response_ticks", IntegerType), StructField("dispatched", BooleanType),
    StructField("chrome_score", IntegerType), StructField("new_goal", StringType),
    StructField("faction_id", StringType), StructField("source_id", StringType),
    StructField("new_strength", DoubleType), StructField("old_strength", DoubleType),
    StructField("price", IntegerType), StructField("buyer_id", StringType), StructField("seller_id", StringType),
  ))

  /** Parse the raw Kafka value column into typed events. */
  def parse(raw: DataFrame)(implicit spark: SparkSession): Dataset[Ev] = {
    import spark.implicits._
    raw.select(from_json(col("raw"), schema).as("e"))
      .select(col("e.*"))
      .withColumn("event_time", to_timestamp(col("timestamp")))
      .drop("timestamp")
      .as[Ev]
  }
}

// Processor outputs. Each is an event in its own right, so sinks can stay append-only.
case class PresenceUpdate(agent_id: String, agent_name: String, location_id: String, previous_location: String,
                          last_seen: Timestamp, actions: Long, first_seen: Boolean)

case class CombatSummary(attacker_id: String, target_id: String, location_id: String, started_at: Timestamp,
                         ended_at: Timestamp, rounds_seen: Int, rounds_reported: Option[Int], result: String, closed_by: String)

case class CrimeOutcome(crime_key: String, location_id: String, district: String, crime_type: String, severity: Option[Int],
                        committed_at: Timestamp, outcome: String, response_ticks: Option[Int], waited_ms: Long)
