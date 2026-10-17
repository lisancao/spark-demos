package nightcity.losantos

import org.apache.spark.sql.streaming._

/** State: the public profile plus what the player has done this session. */
case class Menace(agent_name: String, rank: Int, kd: Double, lobby_id: String, session_kills: Long, sellers_killed: Long,
                  civilians_killed: Long, pvp_kills: Long, flying_spawns: Long, bounties_on: Long, wanted_peak: Int)

object MenaceLevel {
  /**
   * The profile is the prior; what the player does to sellers and civilians in this session moves it. Kills of other
   * hunters count a little and are capped: a tryhard who duels griefers all night is not the seller's problem.
   */
  def score(m: Menace): Double =
    m.kd * 4.0 + m.sellers_killed * 30.0 + m.civilians_killed * 10.0 + math.min(m.pvp_kills, 10) * 1.0 + m.flying_spawns * 10.0 +
      m.bounties_on * 4.0 + m.wanted_peak * 1.5
  def level(s: Double): String = if (s >= 60) "menace" else if (s >= 30) "hostile" else "civilian"
}

/**
 * Signal 5: how dangerous is this player to someone with product in the back of a van. Key = player.
 *
 * StatefulProcessorWithInitialState: the roster (rank, career K/D) seeds the state before any event, which is the
 * data a studio has on file before the session. Session counters reset on join. A `bounty_placed` is keyed by its
 * target, not its placer, so the job keys those rows differently upstream.
 */
class MenaceScore extends StatefulProcessorWithInitialState[String, LsEv, MenaceUpdate, LsProfile] {
  import implicits._
  @transient private var st: ValueState[Menace] = _
  private val flying = Set("oppressor_mk2", "deluxo", "sparrow", "lazer")

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    st = getHandle.getValueState[Menace]("menace", TTLConfig.NONE)

  override def handleInitialState(key: String, p: LsProfile, timerValues: TimerValues): Unit =
    st.update(Menace(p.agent_name, p.rank, p.kd, null, 0, 0, 0, 0, 0, 0, 0))

  override def handleInputRows(key: String, rows: Iterator[LsEv], timerValues: TimerValues): Iterator[MenaceUpdate] = {
    val out = scala.collection.mutable.ListBuffer.empty[MenaceUpdate]
    rows.toSeq.sortBy(ev => (ev.event_time.getTime, if (ev.event_type == "session.join") 0 else 1)).foreach { ev =>
      val cur = if (st.exists()) st.get() else Menace(Option(ev.agent_name).getOrElse(key), 0, 0.0, null, 0, 0, 0, 0, 0, 0, 0)
      val next = ev.event_type match {
        case "session.join" => cur.copy(lobby_id = ev.lobby_id, session_kills = 0, sellers_killed = 0, civilians_killed = 0, pvp_kills = 0,
          flying_spawns = 0, bounties_on = 0, wanted_peak = 0)
        case "combat.kill" => cur.copy(lobby_id = ev.lobby_id, session_kills = cur.session_kills + 1,
          sellers_killed = cur.sellers_killed + (if (ev.victim_activity == "selling") 1 else 0),
          civilians_killed = cur.civilians_killed + (if (ev.victim_activity == "freemode" || ev.victim_activity == "supply") 1 else 0),
          pvp_kills = cur.pvp_kills + (if (ev.victim_activity == "pvp") 1 else 0))
        case "player.vehicle_spawned" => cur.copy(lobby_id = ev.lobby_id, flying_spawns = cur.flying_spawns + (if (flying(ev.vehicle)) 1 else 0))
        case "player.bounty_placed" => cur.copy(lobby_id = ev.lobby_id, bounties_on = cur.bounties_on + 1)   // keyed by target upstream
        case "wanted.gained" | "wanted.escalated" => cur.copy(lobby_id = ev.lobby_id, wanted_peak = math.max(cur.wanted_peak, ev.stars.getOrElse(0)))
        case _ => cur
      }
      val before = if (st.exists()) Some(MenaceLevel.level(MenaceLevel.score(cur))) else None
      st.update(next)
      val s = MenaceLevel.score(next)
      val lvl = MenaceLevel.level(s)
      // emit when the level changes, on join (so the lobby learns the prior), and on anything done to a seller
      if (ev.event_type == "session.join" || !before.contains(lvl) || ev.victim_activity == "selling")
        out += MenaceUpdate(key, next.agent_name, next.lobby_id, next.rank, next.kd, next.session_kills, next.sellers_killed, next.pvp_kills,
          next.flying_spawns, next.bounties_on, next.wanted_peak, s, lvl, ev.event_type, ev.event_time,
          Option(ev.kafka_ts).map(_.getTime).getOrElse(0L))
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[MenaceUpdate] = Iterator.empty
}
