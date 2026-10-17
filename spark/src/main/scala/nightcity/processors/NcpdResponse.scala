package nightcity.processors

import java.sql.Timestamp
import org.apache.spark.sql.streaming._
import nightcity.{CrimeOutcome, Ev}

case class OpenCrime(location_id: String, district: String, crime_type: String, severity: Option[Int],
                     committed_at: Timestamp, registered_at_ms: Long)

/**
 * Processor 3: did NCPD answer. Key = location + crime type.
 *
 * `crime.committed` opens a case and arms a processing-time timer `sla` from now. A `crime.ncpd_response`
 * for the same key closes it as answered (or declined, when `dispatched` is false) and cancels the timer.
 * If the timer fires first, the case closes as unanswered. The sim never answers roughly a quarter of
 * crimes, so this is the processor that turns an absence into an event.
 */
class NcpdResponse(slaMs: Long) extends StatefulProcessor[String, Ev, CrimeOutcome] {
  import implicits._
  @transient private var open: ValueState[OpenCrime] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    open = getHandle.getValueState[OpenCrime]("open_crime", TTLConfig.NONE)

  override def handleInputRows(key: String, rows: Iterator[Ev], timerValues: TimerValues): Iterator[CrimeOutcome] = {
    val out = scala.collection.mutable.ListBuffer.empty[CrimeOutcome]
    val now = timerValues.getCurrentProcessingTimeInMs()
    // The sim emits the response in the same tick as the crime: at equal timestamps the crime goes first.
    rows.toSeq.sortBy(ev => (ev.event_time.getTime, if (ev.event_type == "crime.committed") 0 else 1)).foreach { ev =>
      ev.event_type match {
        case "crime.committed" =>
          if (open.exists()) {
            // a second crime before the first was resolved: the first one is unanswered by definition
            val c = open.get()
            out += CrimeOutcome(key, c.location_id, c.district, c.crime_type, c.severity, c.committed_at, "superseded", None, now - c.registered_at_ms)
            getHandle.listTimers().foreach(getHandle.deleteTimer)
          }
          open.update(OpenCrime(ev.location_id, ev.district, ev.crime_type, ev.severity, ev.event_time, now))
          getHandle.registerTimer(now + slaMs)
        case "crime.ncpd_response" =>
          if (open.exists()) {
            val c = open.get()
            val outcome = if (ev.dispatched.contains(false)) "declined" else "answered"
            out += CrimeOutcome(key, c.location_id, c.district, c.crime_type, c.severity, c.committed_at, outcome, ev.response_ticks, now - c.registered_at_ms)
            open.clear()
            getHandle.listTimers().foreach(getHandle.deleteTimer)
          } else {
            // response without an open case: the committed event was late or lost
            out += CrimeOutcome(key, ev.location_id, ev.district, ev.crime_type, None, ev.event_time, "orphan_response", ev.response_ticks, 0L)
          }
        case _ =>
      }
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[CrimeOutcome] = {
    if (!open.exists()) return Iterator.empty
    val c = open.get()
    open.clear()
    Iterator(CrimeOutcome(key, c.location_id, c.district, c.crime_type, c.severity, c.committed_at, "unanswered", None,
      info.getExpiryTimeInMs() - c.registered_at_ms))
  }
}
