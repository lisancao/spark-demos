package nightcity

import java.io.{File, FileWriter, PrintWriter}
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.streaming.StreamingQueryListener
import org.apache.spark.sql.streaming.StreamingQueryListener._

/** Append every query progress event as one JSON line, so numbers in the post come from the engine, not from guesses. */
class ProgressLog(path: String) extends StreamingQueryListener {
  new File(path).getParentFile.mkdirs()
  private val out = new PrintWriter(new FileWriter(path, true), true)
  override def onQueryStarted(e: QueryStartedEvent): Unit = ()
  override def onQueryProgress(e: QueryProgressEvent): Unit = out.synchronized { out.println(e.progress.json) }
  override def onQueryTerminated(e: QueryTerminatedEvent): Unit = out.synchronized { out.flush() }
}

object ProgressLog {
  def attach(spark: SparkSession, path: String): Unit = spark.streams.addListener(new ProgressLog(path))
}
