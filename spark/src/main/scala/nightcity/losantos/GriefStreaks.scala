package nightcity.losantos

import java.sql.Timestamp
import org.apache.spark.sql.streaming._

case class Streak(lobby_id: String, started_at: Timestamp, last_kill: Timestamp, kills: Int, sellers: Int, civilians: Int, pvp: Int, flying: Boolean)

/**
 * Signal 2: kill streaks. Key = attacker + lobby.
 *
 * Unlike a Night City fight there is no `ended` event: a streak is only ever over because the next kill did not come.
 * Every kill (re)arms an event-time timer `gap` after it; the watermark passing that point closes the streak. A
 * `session.leave` for the attacker closes it immediately. The summary says who the kills were (sellers,
 * civilians, other hunters), which is what the lobby scorer weighs.
 */
class GriefStreaks(gapMs: Long) extends StatefulProcessor[String, LsEv, StreakSummary] {
  import implicits._
  @transient private var streak: ValueState[Streak] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    streak = getHandle.getValueState[Streak]("streak", TTLConfig.NONE)

  private def rearm(at: Long): Unit = {
    getHandle.listTimers().foreach(getHandle.deleteTimer)
    getHandle.registerTimer(at + gapMs)
  }

  private def close(key: String, s: Streak, endedAt: Timestamp, by: String): StreakSummary = {
    streak.clear()
    getHandle.listTimers().foreach(getHandle.deleteTimer)
    StreakSummary(key.takeWhile(_ != ':'), s.lobby_id, s.started_at, endedAt, s.kills, s.sellers, s.civilians, s.pvp, s.flying, by)
  }

  override def handleInputRows(key: String, rows: Iterator[LsEv], timerValues: TimerValues): Iterator[StreakSummary] = {
    val out = scala.collection.mutable.ListBuffer.empty[StreakSummary]
    rows.toSeq.sortBy(ev => (ev.event_time.getTime, if (ev.event_type == "combat.kill") 0 else 1)).foreach { ev =>
      ev.event_type match {
        case "combat.kill" =>
          val cur = if (streak.exists()) streak.get() else Streak(ev.lobby_id, ev.event_time, ev.event_time, 0, 0, 0, 0, flying = false)
          val flying = Set("oppressor_mk2", "deluxo", "sparrow", "lazer").contains(ev.attacker_vehicle)
          val next = cur.copy(
            started_at = if (ev.event_time.before(cur.started_at)) ev.event_time else cur.started_at,
            last_kill = if (ev.event_time.after(cur.last_kill)) ev.event_time else cur.last_kill,
            kills = cur.kills + 1,
            sellers = cur.sellers + (if (ev.victim_activity == "selling") 1 else 0),
            civilians = cur.civilians + (if (ev.victim_activity == "freemode" || ev.victim_activity == "supply") 1 else 0),
            pvp = cur.pvp + (if (ev.victim_activity == "pvp") 1 else 0),
            flying = cur.flying || flying)
          streak.update(next)
          rearm(next.last_kill.getTime)
        case "session.leave" =>
          if (streak.exists()) out += close(key, streak.get(), ev.event_time, "left")
        case _ =>
      }
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[StreakSummary] =
    if (streak.exists()) Iterator(close(key, streak.get(), streak.get().last_kill, "gap")) else Iterator.empty
}
