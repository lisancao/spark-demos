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
 * The chain: five transformWithState operators feeding a sixth, keyed by lobby, in one query. Config rows from
 * CONFIG_TOPIC are fanned out to every lobby in lobbies.json. Verdicts go to Parquet and, if OUT_TOPIC is set, to Kafka.
 */
object LobbyBoard {
  def main(args: Array[String]): Unit = {
    val once = args.contains("--once")
    val out = sys.env.getOrElse("DATA_DIR", "/app/data")
    val tag = sys.env.getOrElse("RUN_TAG", "board")
    val lsOut = sys.env.getOrElse("LS_OUTPUT", "/app/ls_output")
    implicit val spark: SparkSession = SparkSession.builder().appName(s"losantos-$tag").getOrCreate()
    import spark.implicits._
    spark.sparkContext.setLogLevel("WARN")
    ProgressLog.attach(spark, s"$out/losantos/$tag/progress.jsonl")

    val ev = LosSantos.events(spark, sys.env.getOrElse("STARTING_OFFSETS", "earliest"))
    val roster = LosSantos.profiles(spark, sys.env.getOrElse("ROSTER", s"$lsOut/players.jsonl"))

    val fromPresence = LosSantos.presence(ev).flatMap { p =>
      p.change match {
        case "joined"  => Seq(Signal(p.lobby_id, "joined", p.agent_id, null, 0, 0, p.last_seen))
        case "hopped"  => Seq(Signal(p.previous_lobby, "left", p.agent_id, null, 0, 0, p.last_seen), Signal(p.lobby_id, "joined", p.agent_id, null, 0, 0, p.last_seen))
        case "left"    => Seq(Signal(p.lobby_id, "left", p.agent_id, null, 0, 0, p.last_seen))
        case "vehicle" if Set("oppressor_mk2", "deluxo", "sparrow", "lazer", "toreador").contains(p.vehicle) =>
          Seq(Signal(p.lobby_id, "pvp_vehicle", p.agent_id, p.vehicle, 0, 0, p.last_seen))
        case _ => Seq.empty
      }
    }
    // a streak counts by what it did to people who were not fighting back: sellers and civilians
    val fromStreaks = LosSantos.streaks(ev).map(s => Signal(s.lobby_id, "streak", s.attacker_id, s.closed_by, s.sellers_killed.toDouble, (s.sellers_killed + s.civilians_killed).toLong, s.ended_at))
    val fromSells = LosSantos.sells(ev).map(s => Signal(s.lobby_id, "sell", s.seller_id, s.outcome, s.value.toDouble, s.value_delivered, s.started_at))
    val fromMenace = LosSantos.menace(ev, roster).map(m => Signal(m.lobby_id, "menace", m.agent_id, m.level, m.score, m.session_kills, m.at, null, m.source_kafka_ts))
    // the sim's periodic snapshot carries its own safety verdict (computed from the hidden archetypes); it is passed
    // through as a signal so every snapshot yields a board row with both numbers side by side, for grading
    val fromSnapshots = ev.filter(_.event_type == "lobby.snapshot")
      .map(e => Signal(e.lobby_id, "snapshot", null, null, e.sim_safety.getOrElse(0).toDouble, e.population.getOrElse(0).toLong, e.event_time))

    // dynamic configuration: one JSON row on CONFIG_TOPIC becomes one signal per lobby
    val lobbies = """"([^"]+)"""".r.findAllMatchIn(new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(s"$lsOut/lobbies.json")))).map(_.group(1)).toSeq
    val config = sys.env.get("CONFIG_TOPIC").map { topic =>
      spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", Events.bootstrap).option("subscribe", topic).option("startingOffsets", "earliest").load()
        .select(col("value").cast("string").as("config"), col("timestamp").as("at"))
        .as[(String, java.sql.Timestamp)]
        .flatMap { case (cfg, at) => lobbies.map(l => Signal(l, "config", null, null, 0, 0, at, cfg)) }
    }

    // BOARD_INPUT=menace: the one-signal chain (menace -> lobby) with no union, which is what Real-time Mode accepts
    val signals = sys.env.get("BOARD_INPUT") match {
      // a typed map straight into groupByKey plans as AppendColumnsWithObjectExec, which Real-time Mode's allowlist
      // rejects (a select in between does not help: the optimizer removes the serialize/deserialize pair). Building
      // the Signal with column expressions keeps the child row-based, so groupByKey plans as AppendColumnsExec.
      case Some("menace") => LosSantos.menace(ev, roster).select(
        col("lobby_id"), lit("menace").as("kind"), col("agent_id").as("player_id"), col("level"), col("score"),
        col("session_kills").as("n"), col("at"), lit(null).cast("string").as("config"), col("source_kafka_ts")).as[Signal]
      case _ => Seq(fromPresence, fromStreaks, fromSells, fromMenace, fromSnapshots).reduce(_ union _)
    }
    val all = config.fold(signals)(signals union _)
    val verdicts = all.filter(_.lobby_id != null).groupByKey(_.lobby_id)
      .transformWithState(new LobbySafety(Weights.default.copy(window_ms = sys.env.getOrElse("WINDOW_MS", "30000").toLong)),
        TimeMode.ProcessingTime(), OutputMode.Append())

    Bounded.run(spark, () => {
      val w = sys.env.get("OUT_TOPIC") match {
        case Some(topic) =>
          verdicts.select(col("lobby_id").as("key"), to_json(struct(col("*"))).as("value"))
            .writeStream.format("kafka").option("kafka.bootstrap.servers", Events.bootstrap).option("topic", topic)
        case None =>
          verdicts.writeStream.format("parquet").option("path", s"$out/losantos/$tag/out")
      }
      // TRIGGER=rtm tries the whole chain under Real-time Mode (update mode, Kafka sink required)
      val trigger = sys.env.get("TRIGGER") match {
        case Some("rtm") => Trigger.RealTime(sys.env.getOrElse("RTM_BATCH", "30 seconds"))
        case _ => Trigger.ProcessingTime(if (once) "1 second" else sys.env.getOrElse("MICRO_INTERVAL", "2 seconds"))
      }
      w.option("checkpointLocation", s"$out/checkpoints/losantos/$tag")
        .outputMode(if (sys.env.get("TRIGGER").contains("rtm")) OutputMode.Update() else OutputMode.Append())
        .trigger(trigger)
        .queryName("lobby-board").start()
    }, once)
  }
}
