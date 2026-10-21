package nightcity.jobs

import java.time.Duration
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._
import org.apache.spark.sql.streaming.{OutputMode, TimeMode, Trigger}
import nightcity.{Ev, Events, ProgressLog}
import nightcity.processors.PresenceLatency

/**
 * Phase 6: the same JVM transformWithState query under a micro-batch trigger and under Trigger.RealTime.
 *   run.sh Latency micro|rtm      env: KAFKA_TOPIC (input), OUT_TOPIC, RUN_SECONDS, RTM_BATCH ("30 seconds")
 * Reads from the latest offsets so only live arrivals are measured; writes to Kafka in update mode (the only
 * output mode Real-time Mode accepts).
 */
object Latency {
  def main(args: Array[String]): Unit = {
    val mode = args.headOption.getOrElse(sys.error("usage: Latency micro|rtm"))
    val out = sys.env.getOrElse("DATA_DIR", "/app/data")
    val outTopic = sys.env.getOrElse("OUT_TOPIC", s"nightcity.presence.$mode")
    val runSeconds = sys.env.getOrElse("RUN_SECONDS", "120").toLong
    implicit val spark: SparkSession = SparkSession.builder().appName(s"nightcity-latency-$mode").getOrCreate()
    import spark.implicits._
    spark.sparkContext.setLogLevel("WARN")
    ProgressLog.attach(spark, s"$out/latency/$mode/progress.jsonl")

    val samples = Ev.parse(Events.readKafka(spark, startingOffsets = "latest"))
      .filter(_.event_type.startsWith("agent."))
      .groupByKey(_.agent_id)
      .transformWithState(new PresenceLatency(Duration.ofSeconds(120)), TimeMode.ProcessingTime(), OutputMode.Update())

    val trigger = mode match {
      case "micro" => Trigger.ProcessingTime(sys.env.getOrElse("MICRO_INTERVAL", "0 seconds"))
      case "rtm"   => Trigger.RealTime(sys.env.getOrElse("RTM_BATCH", "30 seconds"))
      case other   => sys.error(s"unknown mode $other")
    }

    val q = samples
      .select(col("agent_id").as("key"), to_json(struct(col("*"))).as("value"))
      .writeStream.format("kafka")
      .option("kafka.bootstrap.servers", Events.bootstrap)
      .option("topic", outTopic)
      .option("checkpointLocation", s"$out/checkpoints/latency/$mode")
      .outputMode(OutputMode.Update())
      .trigger(trigger)
      .queryName(s"latency-$mode")
      .start()

    val deadline = System.currentTimeMillis() + runSeconds * 1000
    while (q.isActive && System.currentTimeMillis() < deadline) Thread.sleep(500)
    q.exception.foreach(e => throw e)
    if (q.isActive) q.stop()
    println(s"latency-$mode: ran ${runSeconds}s, last progress batch ${Option(q.lastProgress).map(_.batchId).getOrElse(-1L)}")
  }
}
