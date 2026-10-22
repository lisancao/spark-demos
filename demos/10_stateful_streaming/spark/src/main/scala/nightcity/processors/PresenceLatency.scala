package nightcity.processors

import java.time.Duration
import org.apache.spark.sql.streaming._
import nightcity.{Ev, LatencySample}

/**
 * Phase 6 probe: the presence processor's state logic, but it emits one row per input row and carries the input
 * record's Kafka append time through, so the output topic's timestamps give end-to-end latency per event.
 * Same code runs under a micro-batch trigger and under Trigger.RealTime.
 */
class PresenceLatency(idle: Duration) extends StatefulProcessor[String, Ev, LatencySample] {
  import implicits._
  @transient private var presence: ValueState[Presence] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    presence = getHandle.getValueState[Presence]("presence", TTLConfig(idle))

  override def handleInputRows(key: String, rows: Iterator[Ev], timerValues: TimerValues): Iterator[LatencySample] =
    rows.map { ev =>
      val prev = if (presence.exists()) Some(presence.get()) else None
      val actions = prev.map(_.actions).getOrElse(0L) + 1
      val stale = prev.exists(_.last_seen.after(ev.event_time))
      val next = if (stale) prev.get.copy(actions = actions) else Presence(ev.location_id, ev.event_time, actions)
      presence.update(next)
      LatencySample(key, next.location_id, actions, ev.kafka_ts.getTime)
    }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[LatencySample] =
    Iterator.empty
}
