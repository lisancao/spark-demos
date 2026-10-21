package nightcity.jobs

import java.time.Duration
import org.apache.spark.sql.{Dataset, SparkSession}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.streaming.{OutputMode, TimeMode, Trigger}
import nightcity.{Events, ProgressLog}
import nightcity.losantos._

/** The five Los Santos signal processors, each as its own query, plus the chained board. Shared wiring. */
object LosSantos {
  def events(spark: SparkSession, startingOffsets: String = "earliest"): Dataset[LsEv] = {
    implicit val s: SparkSession = spark
    LsEv.parse(Events.readKafka(spark, startingOffsets))
  }

  def profiles(spark: SparkSession, path: String): Dataset[LsProfile] = {
    import spark.implicits._
    spark.read.json(path)
      .selectExpr("agent_id", "agent_name", "cast(rank as int) rank", "cast(kd as double) kd", "cast(hours as int) hours",
        "cast(career_kills as long) career_kills", "cast(career_deaths as long) career_deaths")
      .as[LsProfile]
  }

  val presenceTypes = Set("session.join", "session.leave", "session.passive_on", "session.passive_off", "player.move", "player.vehicle_spawned")
  val menaceTypes = Set("session.join", "combat.kill", "player.vehicle_spawned", "player.bounty_placed", "wanted.gained", "wanted.escalated")

  def presence(ev: Dataset[LsEv])(implicit spark: SparkSession): Dataset[LsPresenceUpdate] = {
    import spark.implicits._
    ev.filter(e => presenceTypes(e.event_type)).groupByKey(_.agent_id)
      .transformWithState(new LobbyPresence(Duration.ofSeconds(sys.env.getOrElse("IDLE_SECONDS", "120").toLong)), TimeMode.ProcessingTime(), OutputMode.Append())
  }

  def streaks(ev: Dataset[LsEv])(implicit spark: SparkSession): Dataset[StreakSummary] = {
    import spark.implicits._
    ev.filter(e => e.event_type == "combat.kill" || e.event_type == "session.leave")
      .withWatermark("event_time", sys.env.getOrElse("WATERMARK", "10 seconds"))
      .groupByKey(e => s"${e.agent_id}:${e.lobby_id}")
      .transformWithState(new GriefStreaks(sys.env.getOrElse("GAP_MS", "1000").toLong), TimeMode.EventTime(), OutputMode.Append())
  }

  def sells(ev: Dataset[LsEv])(implicit spark: SparkSession): Dataset[SellOutcome] = {
    import spark.implicits._
    ev.filter(_.event_type.startsWith("sell.")).groupByKey(_.mission_id)
      .transformWithState(new SellMissions(sys.env.getOrElse("SLA_MS", "15000").toLong), TimeMode.ProcessingTime(), OutputMode.Append())
  }

  def orgs(ev: Dataset[LsEv])(implicit spark: SparkSession): Dataset[OrgUpdate] = {
    import spark.implicits._
    ev.filter(e => e.event_type.startsWith("org.") || e.event_type.startsWith("sell.")).filter(_.faction_id != null)
      .groupByKey(_.faction_id)
      .transformWithState(new OrgBusinesses(sys.env.getOrElse("KEEP_SELLS", "10").toInt), TimeMode.None(), OutputMode.Append())
  }

  def menace(ev: Dataset[LsEv], roster: Dataset[LsProfile])(implicit spark: SparkSession): Dataset[MenaceUpdate] = {
    import spark.implicits._
    ev.filter(e => menaceTypes(e.event_type))
      .groupByKey(e => if (e.event_type == "player.bounty_placed") e.target_id else e.agent_id)
      .transformWithState(new MenaceScore(), TimeMode.ProcessingTime(), OutputMode.Append(), roster.groupByKey(_.agent_id))
  }
}

/**
 * run.sh LsProcessors presence|streaks|sells|orgs|menace [--once]   (env KAFKA_TOPIC=losantos.events, ROSTER)
 * One processor per query, append-only Parquet under data/losantos/<name>.
 */
object LsProcessors {
  def main(args: Array[String]): Unit = {
    val name = args.headOption.getOrElse(sys.error("usage: LsProcessors <presence|streaks|sells|orgs|menace> [--once]"))
    val once = args.contains("--once")
    val out = sys.env.getOrElse("DATA_DIR", "/app/data")
    val tag = sys.env.getOrElse("RUN_TAG", name)
    implicit val spark: SparkSession = SparkSession.builder().appName(s"losantos-$tag").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    ProgressLog.attach(spark, s"$out/losantos/$tag/progress.jsonl")
    val ev = LosSantos.events(spark)
    val result: Dataset[_] = name match {
      case "presence" => LosSantos.presence(ev)
      case "streaks"  => LosSantos.streaks(ev)
      case "sells"    => LosSantos.sells(ev)
      case "orgs"     => LosSantos.orgs(ev)
      case "menace"   => LosSantos.menace(ev, LosSantos.profiles(spark, sys.env.getOrElse("ROSTER", "/app/ls_output/players.jsonl")))
      case other      => sys.error(s"unknown processor $other")
    }
    Bounded.run(spark, () => result.writeStream.format("parquet")
      .option("path", s"$out/losantos/$tag/out")
      .option("checkpointLocation", s"$out/checkpoints/losantos/$tag")
      .outputMode(OutputMode.Append())
      .trigger(Trigger.ProcessingTime(if (once) "1 second" else "2 seconds"))
      .queryName(name).start(), once)
  }
}

/**
 * run.sh LobbyBoard [--once]
 *
 * The board as one query that Real-time Mode accepts: Kafka events and config rows are unioned before any state,
 * then two chained transformWithState operators, player-keyed `PlayerSignals` feeding lobby-keyed `LobbySafety`.
 * The same query runs under a micro-batch trigger (default; Parquet or Kafka sink) and under Trigger.RealTime
 * (TRIGGER=rtm; update mode; Kafka sink with OUT_TOPIC, or Redis with OUT=redis via a ForeachWriter).
 */
object LobbyBoard {
  def main(args: Array[String]): Unit = {
    val once = args.contains("--once")
    val rtm = sys.env.get("TRIGGER").contains("rtm")
    val out = sys.env.getOrElse("DATA_DIR", "/app/data")
    val tag = sys.env.getOrElse("RUN_TAG", "board")
    val lsOut = sys.env.getOrElse("LS_OUTPUT", "/app/ls_output")
    implicit val spark: SparkSession = SparkSession.builder().appName(s"losantos-$tag").getOrCreate()
    import spark.implicits._
    spark.sparkContext.setLogLevel("WARN")
    ProgressLog.attach(spark, s"$out/losantos/$tag/progress.jsonl")

    val events = LosSantos.events(spark, sys.env.getOrElse("STARTING_OFFSETS", "earliest"))
    val roster = LosSantos.profiles(spark, sys.env.getOrElse("ROSTER", s"$lsOut/players.jsonl"))
    val lobbies = """"([^"]+)"""".r.findAllMatchIn(new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(s"$lsOut/lobbies.json")))).map(_.group(1)).toSeq

    // dynamic configuration: a JSON row on CONFIG_TOPIC becomes one `board.config` event per lobby, in the event
    // stream's own shape, unioned in *before* the stateful stages (a union after one is not allowed in Real-time Mode)
    val configEvents = sys.env.get("CONFIG_TOPIC").map { topic =>
      val raw = spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", Events.bootstrap).option("subscribe", topic).option("startingOffsets", "earliest").load()
        .select(col("value").cast("string").as("config"), col("timestamp").as("kafka_ts"), explode(array(lobbies.map(lit): _*)).as("lobby_id"))
      val overrides = Map("config" -> col("config"), "kafka_ts" -> col("kafka_ts"), "lobby_id" -> col("lobby_id"),
        "event_time" -> col("kafka_ts"), "event_type" -> lit("board.config"), "event_id" -> concat(lit("config:"), col("lobby_id"), lit(":"), col("kafka_ts").cast("long")),
        "agent_id" -> concat(lit("config:"), col("lobby_id")),
        "sim_tick" -> lit(0L))   // the one primitive field in LsEv: a null here fails NOT_NULL_ASSERT_VIOLATION at runtime
      raw.select(events.schema.fields.map(f => overrides.getOrElse(f.name, lit(null).cast(f.dataType)).as(f.name)): _*)
    }
    val input = configEvents.fold(events.toDF())(events.toDF().unionByName(_)).as[LsEv]

    val playerKey = (e: LsEv) => e.event_type match {
      case "board.config" => s"config:${e.lobby_id}"
      case "lobby.snapshot" => s"snapshot:${e.lobby_id}"
      case "player.bounty_placed" => e.target_id   // a bounty is a fact about its target
      case _ => e.agent_id
    }
    val signals = input.filter(col("lobby_id").isNotNull).as[LsEv].groupByKey(playerKey)
      .transformWithState(new PlayerSignals(Duration.ofSeconds(sys.env.getOrElse("IDLE_SECONDS", "120").toLong),
        sys.env.getOrElse("SLA_MS", "15000").toLong, sys.env.getOrElse("GAP_MS", "1000").toLong),
        TimeMode.ProcessingTime(), OutputMode.Update(), roster.groupByKey(_.agent_id))

    // The second stage's child must stay row-based. groupByKey straight on a transformWithState output plans as
    // AppendColumnsWithObjectExec (the optimizer fuses the serializer into it), which Real-time Mode's allowlist
    // rejects; an explicit projection of the Signal columns in between keeps it AppendColumnsExec, which it accepts.
    // (an identity projection is removed by the optimizer and the fusion happens anyway, hence the coalesce)
    val signalCols = signals.schema.fieldNames.map(n => if (n == "lobby_id") coalesce(col(n), lit("")).as(n) else col(n))
    val verdicts = signals.select(signalCols: _*).as[Signal].groupByKey(_.lobby_id)
      .transformWithState(new LobbySafety(Weights.default.copy(window_ms = sys.env.getOrElse("WINDOW_MS", "30000").toLong)),
        TimeMode.ProcessingTime(), OutputMode.Update())

    if (sys.env.contains("EXPLAIN")) { verdicts.explain(true); spark.stop(); return }
    Bounded.run(spark, () => {
      val w = (sys.env.get("OUT"), sys.env.get("OUT_TOPIC")) match {
        case (Some("redis"), _) =>
          verdicts.writeStream.foreach(new RedisVerdictWriter(sys.env.getOrElse("REDIS_HOST", "redis"), sys.env.getOrElse("REDIS_PORT", "6379").toInt))
        case (_, Some(topic)) =>
          verdicts.select(col("lobby_id").as("key"), to_json(struct(col("*"))).as("value"))
            .writeStream.format("kafka").option("kafka.bootstrap.servers", Events.bootstrap).option("topic", topic)
        case _ =>
          verdicts.writeStream.format("parquet").option("path", s"$out/losantos/$tag/out")
      }
      val trigger = if (rtm) Trigger.RealTime(sys.env.getOrElse("RTM_BATCH", "30 seconds"))
        else Trigger.ProcessingTime(if (once) "1 second" else sys.env.getOrElse("MICRO_INTERVAL", "2 seconds"))
      w.option("checkpointLocation", s"$out/checkpoints/losantos/$tag")
        .outputMode(if (rtm || sys.env.get("OUT").contains("redis")) OutputMode.Update() else OutputMode.Append())
        .trigger(trigger)
        .queryName("lobby-board").start()
    }, once)
  }
}
