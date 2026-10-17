package nightcity.jobs

import java.time.Duration
import org.apache.spark.sql.{Dataset, SparkSession}
import org.apache.spark.sql.streaming.{OutputMode, TimeMode, Trigger}
import nightcity.{Ev, Events, ProgressLog}
import nightcity.processors._

/**
 * Phase 3: run one stateful processor over the Kafka stream.
 *   run.sh Processors presence|combat|ncpd [--once]
 * Outputs are append-only Parquet under data/processors/<name>; engine metrics in progress.jsonl.
 */
object Processors {
  def main(args: Array[String]): Unit = {
    val name = args.headOption.getOrElse(sys.error("usage: Processors <presence|combat|ncpd> [--once]"))
    val once = args.contains("--once")
    val out = sys.env.getOrElse("DATA_DIR", "/app/data")
    val tag = sys.env.getOrElse("RUN_TAG", name)
    implicit val spark: SparkSession = SparkSession.builder().appName(s"nightcity-$tag").getOrCreate()
    import spark.implicits._
    spark.sparkContext.setLogLevel("WARN")
    ProgressLog.attach(spark, s"$out/processors/$tag/progress.jsonl")

    val events: Dataset[Ev] = Ev.parse(Events.readKafka(spark))

    val result = name match {
      case "presence" =>
        events.filter(_.event_type.startsWith("agent."))
          .groupByKey(_.agent_id)
          .transformWithState(new NpcPresence(Duration.ofSeconds(sys.env.getOrElse("IDLE_SECONDS", "60").toLong)),
            TimeMode.ProcessingTime(), OutputMode.Append())
      case "combat" =>
        events.filter(_.event_type.startsWith("combat."))
          .withWatermark("event_time", sys.env.getOrElse("WATERMARK", "10 seconds"))
          .groupByKey(_.attacker_id)
          .transformWithState(new CombatSessions(gapMs = sys.env.getOrElse("GAP_MS", "5000").toLong),
            TimeMode.EventTime(), OutputMode.Append())
      case "ncpd" =>
        events.filter(_.event_type.startsWith("crime."))
          .groupByKey(e => s"${e.location_id}:${e.crime_type}")
          .transformWithState(new NcpdResponse(slaMs = sys.env.getOrElse("SLA_MS", "10000").toLong),
            TimeMode.ProcessingTime(), OutputMode.Append())
      case other => sys.error(s"unknown processor $other")
    }

    // Bounded runs: AvailableNow never ends a transformWithState query in ProcessingTime mode (timers and TTL
    // keep asking for another, empty, batch), so --once uses a short processing-time trigger and stops the
    // query itself once the input has drained and timers have had DRAIN_SECONDS of empty batches to fire.
    // The stop is issued right after a batch commits, in the trigger gap, so no batch is interrupted.
    val drainMs = sys.env.getOrElse("DRAIN_SECONDS", "20").toLong * 1000
    @volatile var sawData = false
    @volatile var idleSince = -1L
    @volatile var stopRequested = false
    if (once) spark.streams.addListener(new org.apache.spark.sql.streaming.StreamingQueryListener {
      override def onQueryStarted(e: org.apache.spark.sql.streaming.StreamingQueryListener.QueryStartedEvent): Unit = ()
      override def onQueryTerminated(e: org.apache.spark.sql.streaming.StreamingQueryListener.QueryTerminatedEvent): Unit = ()
      override def onQueryProgress(e: org.apache.spark.sql.streaming.StreamingQueryListener.QueryProgressEvent): Unit = {
        val p = e.progress
        if (p.numInputRows > 0) { sawData = true; idleSince = -1L }
        else if (sawData && idleSince < 0) idleSince = System.currentTimeMillis()
        if (sawData && idleSince > 0 && System.currentTimeMillis() - idleSince >= drainMs) stopRequested = true
      }
    })

    val q = result.writeStream.format("parquet")
      .option("path", s"$out/processors/$tag/out")
      .option("checkpointLocation", s"$out/checkpoints/processors/$tag")
      .outputMode(OutputMode.Append())
      .trigger(Trigger.ProcessingTime(if (once) "1 second" else "2 seconds"))
      .queryName(name)
      .start()

    if (once) {
      // In EventTime mode no batch runs without input, so the listener alone would never see the drain
      // expire: check the clock here as well.
      def drained = sawData && idleSince > 0 && System.currentTimeMillis() - idleSince >= drainMs
      while (q.isActive && !stopRequested && !drained) Thread.sleep(200)
      if (q.isActive) q.stop()
    }
    q.awaitTermination()
  }
}
