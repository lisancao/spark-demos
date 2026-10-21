package nightcity.jobs

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.streaming.Trigger
import nightcity.Events

/** Kafka -> Parquet bronze table, partitioned by event family. Stateless; the point is provenance and replayability. */
object Bronze {
  def main(args: Array[String]): Unit = {
    val once = args.contains("--once")
    val out = sys.env.getOrElse("DATA_DIR", "/app/data")
    val spark = SparkSession.builder().appName("nightcity-bronze").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    val stream = Events.parsed(Events.readKafka(spark))
      .writeStream
      .format("parquet")
      .option("path", s"$out/bronze/events")
      .option("checkpointLocation", s"$out/checkpoints/bronze")
      .partitionBy("event_family")
      .trigger(if (once) Trigger.AvailableNow() else Trigger.ProcessingTime("5 seconds"))
      .start()

    stream.awaitTermination()
  }
}
