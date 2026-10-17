package nightcity.processors

import java.sql.Timestamp
import java.time.Duration
import org.apache.spark.sql.streaming._
import nightcity.{Ev, PresenceUpdate}

/** What the processor remembers about one NPC. */
case class Presence(location_id: String, last_seen: Timestamp, actions: Long)

/**
 * Processor 1: where is every NPC, and when did it last do anything.
 *
 * One ValueState per agent with a processing-time TTL: an NPC that goes quiet for `idle` is forgotten by the
 * state store without any code here. Emits a row when an NPC first appears or changes location.
 * Written to work whether a key's rows arrive in one call (micro-batch) or one at a time (Real-time Mode).
 */
class NpcPresence(idle: Duration) extends StatefulProcessor[String, Ev, PresenceUpdate] {
  import implicits._
  @transient private var presence: ValueState[Presence] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    presence = getHandle.getValueState[Presence]("presence", TTLConfig(idle))

  override def handleInputRows(key: String, rows: Iterator[Ev], timerValues: TimerValues): Iterator[PresenceUpdate] = {
    val out = scala.collection.mutable.ListBuffer.empty[PresenceUpdate]
    // Rows within a batch are not ordered; process them in event-time order so "latest location" means latest.
    rows.toSeq.sortBy(_.event_time.getTime).foreach { ev =>
      val prev = if (presence.exists()) Some(presence.get()) else None
      val actions = prev.map(_.actions).getOrElse(0L) + 1
      val stale = prev.exists(_.last_seen.after(ev.event_time)) // a late row must not move the NPC backwards
      val loc = if (stale) prev.get.location_id else ev.location_id
      val seen = if (stale) prev.get.last_seen else ev.event_time
      presence.update(Presence(loc, seen, actions))
      if (prev.isEmpty || (!stale && prev.get.location_id != ev.location_id))
        out += PresenceUpdate(ev.agent_id, ev.agent_name, loc, prev.map(_.location_id).getOrElse(ev.from_location),
          seen, actions, prev.isEmpty)
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[PresenceUpdate] =
    Iterator.empty
}
