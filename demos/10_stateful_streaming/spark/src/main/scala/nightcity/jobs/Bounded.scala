package nightcity.jobs

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.streaming.{StreamingQuery, StreamingQueryListener}

/**
 * Bounded runs for stateful queries (shared by the Los Santos jobs; the Night City Processors job has the same
 * logic inline). AvailableNow never ends a transformWithState query in ProcessingTime mode, and EventTime/None
 * queries run no batch at all without input, so "drained" is DRAIN_SECONDS of wall clock since the last batch
 * that carried input. STOP_AFTER_BATCHES=n exits hard after n data batches (the recovery experiment).
 */
object Bounded {
  def run(spark: SparkSession, start: () => StreamingQuery, once: Boolean): Unit = {
    val drainMs = sys.env.getOrElse("DRAIN_SECONDS", "20").toLong * 1000
    val stopAfter = sys.env.get("STOP_AFTER_BATCHES").map(_.toInt).getOrElse(Int.MaxValue)
    @volatile var sawData = false
    @volatile var lastDataAt = -1L
    @volatile var dataBatches = 0
    if (once) spark.streams.addListener(new StreamingQueryListener {
      override def onQueryStarted(e: StreamingQueryListener.QueryStartedEvent): Unit = ()
      override def onQueryTerminated(e: StreamingQueryListener.QueryTerminatedEvent): Unit = ()
      override def onQueryProgress(e: StreamingQueryListener.QueryProgressEvent): Unit =
        if (e.progress.numInputRows > 0) { sawData = true; lastDataAt = System.currentTimeMillis(); dataBatches += 1 }
    })
    val q = start()
    // RUN_SECONDS: an unbounded run that stops itself after a fixed wall-clock time (the live experiments)
    sys.env.get("RUN_SECONDS").map(_.toLong * 1000).foreach { ms =>
      val deadline = System.currentTimeMillis() + ms
      while (q.isActive && System.currentTimeMillis() < deadline) Thread.sleep(500)
      q.exception.foreach(e => throw e)
      if (q.isActive) q.stop()
    }
    if (once) {
      // "drained" also requires the trigger to be idle: a long batch must never be interrupted by the stop
      def drained = sawData && System.currentTimeMillis() - lastDataAt >= drainMs && !q.status.isTriggerActive
      while (q.isActive && !drained && dataBatches < stopAfter) Thread.sleep(200)
      if (dataBatches >= stopAfter) { println(s"STOP_AFTER_BATCHES reached ($dataBatches); exiting without stopping the query"); System.exit(3) }
      if (q.isActive) q.stop()
    }
    q.awaitTermination()
  }
}
