package nightcity.processors

import java.sql.Timestamp
import org.apache.spark.sql.streaming._
import nightcity.{CombatSummary, Ev}

case class Combat(target_id: String, location_id: String, started_at: Timestamp, last_event: Timestamp, rounds_seen: Int)

/**
 * Processor 2: sessionize combat. Key = attacker (the sim runs one fight per attacker at a time).
 *
 * `combat.started` opens a session, `combat.round` extends it, `combat.ended` closes it and emits a summary.
 * Every event (re)arms an event-time timer `gap` after the latest event seen; if the watermark passes that
 * point with no `ended`, the session is closed as a timeout. Rounds arriving out of order still count; a
 * round arriving before its `started` opens the session on its own.
 */
class CombatSessions(gapMs: Long) extends StatefulProcessor[String, Ev, CombatSummary] {
  import implicits._
  @transient private var combat: ValueState[Combat] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    combat = getHandle.getValueState[Combat]("combat", TTLConfig.NONE)

  private def rearm(at: Long): Unit = {
    getHandle.listTimers().foreach(getHandle.deleteTimer)
    getHandle.registerTimer(at + gapMs)
  }

  override def handleInputRows(key: String, rows: Iterator[Ev], timerValues: TimerValues): Iterator[CombatSummary] = {
    val out = scala.collection.mutable.ListBuffer.empty[CombatSummary]
    // Same-timestamp events (the sim resolves a whole fight in one tick) need a stable order: started, rounds, ended.
    def rank(t: String) = t match { case "combat.started" => 0; case "combat.round" => 1; case "combat.ended" => 2; case _ => 3 }
    rows.toSeq.sortBy(ev => (ev.event_time.getTime, rank(ev.event_type), ev.round.getOrElse(0))).foreach { ev =>
      val cur = if (combat.exists()) Some(combat.get()) else None
      ev.event_type match {
        case "combat.started" =>
          val c = cur.getOrElse(Combat(ev.target_id, ev.location_id, ev.event_time, ev.event_time, 0))
          combat.update(c.copy(started_at = minTs(c.started_at, ev.event_time), last_event = maxTs(c.last_event, ev.event_time)))
          rearm(combat.get().last_event.getTime)
        case "combat.round" =>
          val c = cur.getOrElse(Combat(ev.target_id, ev.location_id, ev.event_time, ev.event_time, 0))
          combat.update(c.copy(rounds_seen = c.rounds_seen + 1, last_event = maxTs(c.last_event, ev.event_time)))
          rearm(combat.get().last_event.getTime)
        case "combat.ended" =>
          val c = cur.getOrElse(Combat(ev.target_id, ev.location_id, ev.event_time, ev.event_time, 0))
          out += CombatSummary(key, c.target_id, c.location_id, c.started_at, ev.event_time, c.rounds_seen, ev.rounds, ev.result, "ended")
          combat.clear()
          getHandle.listTimers().foreach(getHandle.deleteTimer)
        case _ => // not a combat event for this key
      }
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[CombatSummary] = {
    if (!combat.exists()) return Iterator.empty
    val c = combat.get()
    combat.clear()
    Iterator(CombatSummary(key, c.target_id, c.location_id, c.started_at, c.last_event, c.rounds_seen, None, "unknown", "timeout"))
  }

  private def minTs(a: Timestamp, b: Timestamp) = if (a.before(b)) a else b
  private def maxTs(a: Timestamp, b: Timestamp) = if (a.after(b)) a else b
}
