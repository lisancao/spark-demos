package nightcity.losantos

import java.sql.Timestamp
import java.time.Duration
import org.apache.spark.sql.streaming._

/** What the processor remembers about one player. Cleared on leave, forgotten by TTL if the leave never arrives. */
case class PlayerState(lobby_id: String, location_id: String, passive: Boolean, vehicle: String, last_seen: Timestamp, actions: Long)

/**
 * Signal 1: who is in which lobby, where, passive or not, on what. Key = player.
 *
 * Same shape as Night City's presence processor with one more thing to get right: a player who hops lobbies
 * emits `leave` then `join`, and under lateness the join can arrive first. A join into a different lobby is a hop
 * whatever came before it; a leave for a lobby the player is no longer in is ignored. Late rows never move a
 * player backwards in time.
 */
class LobbyPresence(idle: Duration) extends StatefulProcessor[String, LsEv, LsPresenceUpdate] {
  import implicits._
  @transient private var st: ValueState[PlayerState] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    st = getHandle.getValueState[PlayerState]("player", TTLConfig(idle))

  private def rank(t: String) = t match { case "session.leave" => 0; case "session.join" => 1; case _ => 2 }

  override def handleInputRows(key: String, rows: Iterator[LsEv], timerValues: TimerValues): Iterator[LsPresenceUpdate] = {
    val out = scala.collection.mutable.ListBuffer.empty[LsPresenceUpdate]
    rows.toSeq.sortBy(ev => (ev.event_time.getTime, rank(ev.event_type))).foreach { ev =>
      val prev = if (st.exists()) Some(st.get()) else None
      val stale = prev.exists(_.last_seen.after(ev.event_time))
      def emit(change: String, s: PlayerState, prevLobby: String): Unit =
        out += LsPresenceUpdate(key, ev.agent_name, s.lobby_id, prevLobby, s.location_id, s.passive, s.vehicle, change, s.last_seen, s.actions)
      val actions = prev.map(_.actions).getOrElse(0L) + 1
      ev.event_type match {
        case "session.join" =>
          val next = PlayerState(ev.lobby_id, ev.location_id, passive = false, null, ev.event_time, actions)
          prev match {
            case Some(p) if p.lobby_id == ev.lobby_id && !stale => st.update(next.copy(actions = actions)) // duplicate join, no news
            case Some(p) if stale => st.update(p.copy(actions = actions))
            case Some(p) => st.update(next); emit("hopped", next, p.lobby_id)
            case None => st.update(next); emit("joined", next, null)
          }
        case "session.leave" =>
          prev match {
            case Some(p) if p.lobby_id == ev.lobby_id && !stale => st.clear(); emit("left", p.copy(last_seen = ev.event_time), p.lobby_id)
            case Some(p) => st.update(p.copy(actions = actions)) // a leave for a lobby we already left, or a late one
            case None => // leave with no join seen: nothing to clear
          }
        case _ if stale => st.update(prev.get.copy(actions = actions))
        case _ if prev.isEmpty => // activity before any join (the join is late): ignore until it arrives
        case "player.move" =>
          val next = prev.get.copy(location_id = ev.location_id, vehicle = Option(ev.vehicle).getOrElse(prev.get.vehicle), last_seen = ev.event_time, actions = actions)
          st.update(next); emit("moved", next, next.lobby_id)
        case "player.vehicle_spawned" =>
          val next = prev.get.copy(vehicle = ev.vehicle, last_seen = ev.event_time, actions = actions)
          st.update(next); emit("vehicle", next, next.lobby_id)
        case "session.passive_on" | "session.passive_off" =>
          val next = prev.get.copy(passive = ev.event_type == "session.passive_on", last_seen = ev.event_time, actions = actions)
          st.update(next); emit(if (next.passive) "passive_on" else "passive_off", next, next.lobby_id)
        case _ => st.update(prev.get.copy(last_seen = ev.event_time, actions = actions))
      }
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[LsPresenceUpdate] =
    Iterator.empty
}
