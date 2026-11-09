package bookshop

import java.time.Duration

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._
import org.apache.spark.sql.streaming.{OutputMode, TimeMode, Trigger}
import org.apache.spark.sql.types._

/**
 * clicks (Kafka) -> Recommender (transformWithState, keyed by shopper) -> recs (Kafka)
 *
 *   spark-submit --class bookshop.RecsJob ... bookshop-recs.jar --mode rtm --seconds 90
 */
object RecsJob {
  def main(argv: Array[String]): Unit = {
    val args = argv.grouped(2).collect { case Array(k, v) => k.stripPrefix("--") -> v }.toMap
    val mode = args.getOrElse("mode", "rtm")
    val seconds = args.getOrElse("seconds", "90").toLong
    val demo = args.getOrElse("demo", ".")
    val bootstrap = sys.env.getOrElse("KAFKA_BOOTSTRAP", "localhost:29192")
    val idleMs = args.getOrElse("idle-seconds", "20").toLong * 1000

    val spark = SparkSession.builder().appName(s"04-recs-$mode")
      .config("spark.sql.shuffle.partitions", "4")
      // transformWithState needs RocksDB. Real-time Mode sets these three by itself;
      // micro-batch does not, so the job sets them for both modes.
      .config("spark.sql.streaming.stateStore.providerClass",
        "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider")
      .config("spark.sql.streaming.stateStore.rocksdb.changelogCheckpointing.enabled", "true")
      .config("spark.sql.streaming.stateStore.checkpointFormatVersion", "2")
      .getOrCreate()
    import spark.implicits._

    // The catalog from step 0, collected once on the driver and broadcast to every task.
    val rows = spark.read.parquet(s"$demo/data/catalog").orderBy("book_id")
      .select("book_id", "title", "aisle", "vector").collect()
    val dim = rows.head.getSeq[Float](3).length
    val vecs = new Array[Float](rows.length * dim)
    rows.zipWithIndex.foreach { case (r, i) =>
      val v = r.getSeq[Float](3).toArray
      val n = math.sqrt(v.map(x => x * x).sum).toFloat
      System.arraycopy(v.map(_ / n), 0, vecs, i * dim, dim)
    }
    val catalog = spark.sparkContext.broadcast(Catalog(
      rows.map(_.getLong(0)), rows.map(_.getString(1)), rows.map(_.getString(2)), vecs, dim))

    val clickSchema = new StructType()
      .add("event_id", StringType).add("user_id", StringType).add("book_id", LongType)
      .add("action", StringType).add("ts", LongType)

    val clicks = spark.readStream.format("kafka")
      .option("kafka.bootstrap.servers", bootstrap)
      .option("subscribe", "clicks")
      .option("startingOffsets", "latest")
      .load()
      .select(from_json($"value".cast("string"), clickSchema).as("c"))
      .select("c.*")
      .as[Click]

    val recs = clicks
      .groupByKey(_.user_id)
      .transformWithState(
        new Recommender(catalog, Duration.ofMinutes(30), idleMs),
        TimeMode.ProcessingTime(),
        OutputMode.Update())

    val out = recs.select($"user_id".as("key"), to_json(struct($"*")).as("value"))

    val writer = out.writeStream.format("kafka")
      .option("kafka.bootstrap.servers", bootstrap)
      .option("topic", "recs")
      .option("checkpointLocation", s"$demo/data/checkpoints/04-recs-$mode")
      .outputMode("update")
    val q = (if (mode == "rtm") writer.trigger(Trigger.RealTime("30 seconds"))
             else writer.trigger(Trigger.ProcessingTime(0))).start()

    println(s"running in $mode for ${seconds}s")
    q.awaitTermination(seconds * 1000)
    q.stop()
    spark.stop()
  }
}
