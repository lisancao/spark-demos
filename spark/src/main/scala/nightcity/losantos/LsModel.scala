package nightcity.losantos

import java.sql.Timestamp
import org.apache.spark.sql.{DataFrame, Dataset, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

/** One flat row per Los Santos event: the envelope plus every type-specific field a processor reads. */
case class LsEv(
    event_id: String,
    event_type: String,
    event_time: Timestamp,
    sim_tick: Long,
    agent_id: String,
    agent_name: String,
    lobby_id: String,
    location_id: String,
    target_id: String,
    faction_id: String,
    mission_id: String,
    reason: String,
    vehicle: String,
    attacker_vehicle: String,
    weapon: String,
    victim_activity: String,
    how: String,
    business: String,
    stars: Option[Int],
    kill_streak: Option[Int],
    drop: Option[Int],
    drops: Option[Int],
    value: Option[Long],
    value_delivered: Option[Long],
    value_lost: Option[Long],
    stock_value: Option[Long],
    stock_added: Option[Long],
    amount: Option[Long],
    population: Option[Int],
    sim_safety: Option[Int],
    destroyed_by: String = null,
    businesses: Seq[LsBusiness] = null,
    kafka_ts: Timestamp = null,
)

case class LsBusiness(business: String, business_type: String, stock_value: Long, location_id: String)

object LsEv {
  val schema: StructType = StructType(Seq(
    StructField("event_id", StringType), StructField("event_type", StringType), StructField("timestamp", StringType),
    StructField("sim_tick", LongType), StructField("agent_id", StringType), StructField("agent_name", StringType),
    StructField("lobby_id", StringType), StructField("location_id", StringType), StructField("target_id", StringType),
    StructField("faction_id", StringType), StructField("mission_id", StringType), StructField("reason", StringType),
    StructField("vehicle", StringType), StructField("attacker_vehicle", StringType), StructField("weapon", StringType),
    StructField("victim_activity", StringType), StructField("how", StringType), StructField("business", StringType),
    StructField("stars", IntegerType), StructField("kill_streak", IntegerType), StructField("drop", IntegerType),
    StructField("drops", IntegerType), StructField("value", LongType), StructField("value_delivered", LongType),
    StructField("value_lost", LongType), StructField("stock_value", LongType), StructField("stock_added", LongType),
    StructField("amount", LongType), StructField("population", IntegerType), StructField("sim_safety", IntegerType),
    StructField("destroyed_by", StringType),
    StructField("businesses", ArrayType(StructType(Seq(
      StructField("business", StringType), StructField("business_type", StringType),
      StructField("stock_value", LongType), StructField("location_id", StringType))))),
  ))

  def parse(raw: DataFrame)(implicit spark: SparkSession): Dataset[LsEv] = {
    import spark.implicits._
    raw.select(from_json(col("raw"), schema).as("e"), col("kafka_ts"))
      .select(col("e.*"), col("kafka_ts"))
      .withColumn("event_time", to_timestamp(col("timestamp")))
      .drop("timestamp")
      .as[LsEv]
  }
}

/** Public profile from players.jsonl: the initial state for the griefer score. No archetype in here. */
case class LsProfile(agent_id: String, agent_name: String, rank: Int, kd: Double, hours: Int, career_kills: Long, career_deaths: Long)

// Processor outputs.
case class LsPresenceUpdate(agent_id: String, agent_name: String, lobby_id: String, previous_lobby: String, location_id: String,
                            passive: Boolean, vehicle: String, change: String, last_seen: Timestamp, actions: Long)

case class StreakSummary(attacker_id: String, lobby_id: String, started_at: Timestamp, ended_at: Timestamp, kills: Int,
                         sellers_killed: Int, civilians_killed: Int, pvp_kills: Int, flying: Boolean, closed_by: String)

case class SellOutcome(mission_id: String, seller_id: String, lobby_id: String, business: String, value: Long, drops: Int,
                       deliveries: Int, value_delivered: Long, outcome: String, destroyed_by: String, started_at: Timestamp,
                       waited_ms: Long)

case class OrgUpdate(org_id: String, leader_id: String, lobby_id: String, event_type: String, businesses: Int, stock_total: Long,
                     members: Int, sells_recent: Int, sells_destroyed_recent: Int, at: Timestamp)

case class MenaceUpdate(agent_id: String, agent_name: String, lobby_id: String, rank: Int, kd: Double, session_kills: Long,
                        sellers_killed: Long, pvp_kills: Long, flying_spawns: Long, bounties_on: Long, wanted_peak: Int,
                        score: Double, level: String, trigger: String, at: Timestamp, source_kafka_ts: Long = 0L)

/** What every upstream processor sends the lobby scorer. One shape, several kinds, keyed by lobby. */
case class Signal(lobby_id: String, kind: String, player_id: String, level: String, score: Double, n: Long, at: Timestamp,
                  config: String = null, source_kafka_ts: Long = 0L)

case class LobbyVerdict(lobby_id: String, population: Int, menaces: Int, hostiles: Int, pvp_vehicles: Int, sells_recent: Int,
                        sells_destroyed_recent: Int, streak_kills_recent: Int, score: Double, verdict: String, weights: String,
                        trigger: String, at: Timestamp, sim_safety: Option[Int] = None, sim_population: Option[Int] = None,
                        source_kafka_ts: Long = 0L)
