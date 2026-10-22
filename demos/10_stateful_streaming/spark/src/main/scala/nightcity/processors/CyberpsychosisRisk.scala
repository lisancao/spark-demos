package nightcity.processors

import java.sql.Timestamp
import org.apache.spark.sql.streaming._
import nightcity.{Ev, RiskUpdate, Roster}

/** State schema v1. */
case class Risk(agent_name: String, chrome_score: Int, cyberware_count: Int, attacks: Long, defeats: Long, warnings: Long)

/** State schema v2: one field added (last_warning_at). Avro state encoding lets a v2 query resume a v1 checkpoint. */
case class RiskV2(agent_name: String, chrome_score: Int, cyberware_count: Int, attacks: Long, defeats: Long, warnings: Long,
                  last_warning_at: Option[Timestamp])

object RiskScore {
  /** Chrome is the baseline, violence and warnings push it up. Levels mirror the sim's own cyberpsychosis thresholds. */
  def score(chrome: Int, cyberware: Int, attacks: Long, defeats: Long, warnings: Long): Double =
    chrome * 0.5 + cyberware * 2.0 + attacks * 1.5 + defeats * 4.0 + warnings * 10.0
  def level(score: Double): String = if (score >= 80) "critical" else if (score >= 50) "elevated" else "stable"
}

/**
 * Processor 5 (v1): cyberpsychosis risk per NPC, seeded from the roster. Key = NPC id.
 * StatefulProcessorWithInitialState: `handleInitialState` runs once per roster row before any event.
 * An NPC that is not on the roster (or whose roster row is late) starts from zero chrome.
 */
class CyberpsychosisRisk extends StatefulProcessorWithInitialState[String, Ev, RiskUpdate, Roster] {
  import implicits._
  @transient private var risk: ValueState[Risk] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    risk = getHandle.getValueState[Risk]("risk", TTLConfig.NONE)

  override def handleInitialState(key: String, r: Roster, timerValues: TimerValues): Unit =
    risk.update(Risk(r.agent_name, r.chrome_score, r.cyberware_count, 0, 0, 0))

  override def handleInputRows(key: String, rows: Iterator[Ev], timerValues: TimerValues): Iterator[RiskUpdate] = {
    val out = scala.collection.mutable.ListBuffer.empty[RiskUpdate]
    rows.toSeq.sortBy(_.event_time.getTime).foreach { ev =>
      val cur = if (risk.exists()) risk.get() else Risk(Option(ev.agent_name).getOrElse(key), 0, 0, 0, 0, 0)
      val next = ev.event_type match {
        case "agent.attack"        => cur.copy(attacks = cur.attacks + 1)
        case "combat.ended"        => if (ev.result == "defeat") cur.copy(defeats = cur.defeats + 1) else cur
        case "world.cyberpsychosis" => cur.copy(warnings = cur.warnings + 1, chrome_score = ev.chrome_score.getOrElse(cur.chrome_score))
        case _                     => cur
      }
      if (next != cur || !risk.exists()) {
        risk.update(next)
        val s = RiskScore.score(next.chrome_score, next.cyberware_count, next.attacks, next.defeats, next.warnings)
        out += RiskUpdate(key, next.agent_name, next.chrome_score, next.attacks, next.defeats, next.warnings, s, RiskScore.level(s), ev.event_type, ev.event_time)
      }
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[RiskUpdate] = Iterator.empty
}

/** Processor 5 (v2): same logic, state gains `last_warning_at`. Resumes a v1 checkpoint when the state encoding is Avro. */
class CyberpsychosisRiskV2 extends StatefulProcessorWithInitialState[String, Ev, RiskUpdate, Roster] {
  import implicits._
  @transient private var risk: ValueState[RiskV2] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    risk = getHandle.getValueState[RiskV2]("risk", TTLConfig.NONE)

  override def handleInitialState(key: String, r: Roster, timerValues: TimerValues): Unit =
    risk.update(RiskV2(r.agent_name, r.chrome_score, r.cyberware_count, 0, 0, 0, None))

  override def handleInputRows(key: String, rows: Iterator[Ev], timerValues: TimerValues): Iterator[RiskUpdate] = {
    val out = scala.collection.mutable.ListBuffer.empty[RiskUpdate]
    rows.toSeq.sortBy(_.event_time.getTime).foreach { ev =>
      val cur = if (risk.exists()) risk.get() else RiskV2(Option(ev.agent_name).getOrElse(key), 0, 0, 0, 0, 0, None)
      val next = ev.event_type match {
        case "agent.attack"        => cur.copy(attacks = cur.attacks + 1)
        case "combat.ended"        => if (ev.result == "defeat") cur.copy(defeats = cur.defeats + 1) else cur
        case "world.cyberpsychosis" => cur.copy(warnings = cur.warnings + 1, chrome_score = ev.chrome_score.getOrElse(cur.chrome_score), last_warning_at = Some(ev.event_time))
        case _                     => cur
      }
      if (next != cur || !risk.exists()) {
        risk.update(next)
        // v2 rule: a warning in the last 60 s of event time doubles the warning weight
        val recent = next.last_warning_at.exists(t => ev.event_time.getTime - t.getTime <= 60000)
        val s = RiskScore.score(next.chrome_score, next.cyberware_count, next.attacks, next.defeats, if (recent) next.warnings * 2 else next.warnings)
        out += RiskUpdate(key, next.agent_name, next.chrome_score, next.attacks, next.defeats, next.warnings, s, RiskScore.level(s), ev.event_type, ev.event_time)
      }
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[RiskUpdate] = Iterator.empty
}
