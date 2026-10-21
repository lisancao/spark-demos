package nightcity.jobs

import org.apache.spark.sql.SparkSession

/**
 * Phase 5: read a transformWithState checkpoint with the state data source.
 *   run.sh StateInspect <checkpoint> <stateVarName|timers> [batchId]
 * Prints the schema and row count and a few rows; also writes the full read to data/inspect/<tag>.
 */
object StateInspect {
  def main(args: Array[String]): Unit = {
    val Array(checkpoint, what, rest @ _*) = args
    val out = sys.env.getOrElse("DATA_DIR", "/app/data")
    val spark = SparkSession.builder().appName(s"nightcity-inspect-$what").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    var reader = spark.read.format("statestore").option("flattenCollectionTypes", "true")
    reader = if (what == "timers") reader.option("readRegisteredTimers", "true") else reader.option("stateVarName", what)
    rest.headOption.foreach(b => reader = reader.option("batchId", b))
    // a query with several stateful operators (the Los Santos board has five) needs the operator picked out
    sys.env.get("OPERATOR_ID").foreach(id => reader = reader.option("operatorId", id))
    val df = reader.load(checkpoint)
    df.printSchema()
    println(s"rows: ${df.count()}")
    df.show(20, truncate = false)
    val tag = sys.env.getOrElse("RUN_TAG", s"${checkpoint.split('/').last}-${sys.env.getOrElse("OPERATOR_ID", "0")}-$what")
    df.write.mode("overwrite").parquet(s"$out/inspect/$tag")
    spark.stop()
  }
}
