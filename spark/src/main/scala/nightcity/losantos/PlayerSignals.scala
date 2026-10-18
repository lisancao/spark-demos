package nightcity.losantos

import java.time.Duration
import org.apache.spark.sql.streaming._

/**
 * Stage one of the Real-time chain: everything the board needs to know about one player, in one processor.
 *
 * Real-time Mode allows a chain of stateful operators but no union after a stateful one, so the four per-player
 * signals (presence, menace, sells, streaks) that ran as four queries in micro-batch become one processor keyed by
 * player, emitting one `Signal` shape for the lobby stage. Config rows and the sim's snapshots are keyed by lobby
 * (`config:<lobby>`, `snapshot:<lobby>`) and pass straight through.
 *
 * TimeMode.ProcessingTime throughout: the presence TTL needs it, and the streak gap and sell patience are wall-clock
 * timers here rather than the event-time timers the standalone processors use. In Real-time Mode an event-time
 * watermark is fixed for the whole long batch, so a 1 s gap would only ever be observed at a batch boundary; a
 * processing-time timer fires as soon as the next row reaches the partition after the deadline.
 */
class PlayerSignals(idle: Duration, sellSlaMs: Long, streakGapMs: Long)
    extends StatefulProcessorWithInitialState[String, LsEv, Signal, LsProfile] {
  import implicits._
  @transient private var presence: ValueState[PlayerState] = _
  @transient private var menace: ValueState[Menace] = _
  @transient private var sell: ValueState[OpenSell] = _
  @transient private var sellDeadline: ValueState[Long] = _
  @transient private var streak: ValueState[Streak] = _
  @transient private var streakDeadline: ValueState[Long] = _
  private val terminalSell = Set("sell.completed", "sell.destroyed", "sell.expired", "sell.abandoned")

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit = {
    presence = getHandle.getValueState[PlayerState]("presence", TTLConfig(idle))
    menace = getHandle.getValueState[Menace]("menace", TTLConfig.NONE)
    sell = getHandle.getValueState[OpenSell]("sell", TTLConfig.NONE)
    sellDeadline = getHandle.getValueState[Long]("sell_deadline", TTLConfig.NONE)
    streak = getHandle.getValueState[Streak]("streak", TTLConfig.NONE)
    streakDeadline = getHandle.getValueState[Long]("streak_deadline", TTLConfig.NONE)
  }

  override def handleInitialState(key: String, p: LsProfile, timerValues: TimerValues): Unit =
    menace.update(Menace(p.agent_name, p.rank, p.kd, null, 0, 0, 0, 0, 0, 0, 0))

  private def rank(t: String) = t match {
    case "session.leave" => 0; case "session.join" => 1; case "sell.started" => 2; case "combat.kill" => 3
    case "sell.delivery" => 4; case _ => 5
  }
  private def ts(ev: LsEv): Long = Option(ev.kafka_ts).map(_.getTime).getOrElse(0L)

  private def retime(deadline: ValueState[Long], at: Long): Unit = {
    if (deadline.exists()) getHandle.deleteTimer(deadline.get())
    deadline.update(at)
    getHandle.registerTimer(at)
  }
  private def disarm(deadline: ValueState[Long]): Unit =
    if (deadline.exists()) { getHandle.deleteTimer(deadline.get()); deadline.clear() }

  private def closeStreak(out: scala.collection.mutable.ListBuffer[Signal], endedAt: java.sql.Timestamp, by: String, src: Long): Unit = {
    val s = streak.get()
    out += Signal(s.lobby_id, "streak", null, by, s.sellers.toDouble, (s.sellers + s.civilians).toLong, endedAt, null, src)
    streak.clear()
    disarm(streakDeadline)
  }

  override def handleInputRows(key: String, rows: Iterator[LsEv], timerValues: TimerValues): Iterator[Signal] = {
    val out = scala.collection.mutable.ListBuffer.empty[Signal]
    val now = timerValues.getCurrentProcessingTimeInMs()
    rows.toSeq.sortBy(ev => (ev.event_time.getTime, rank(ev.event_type), ev.drop.getOrElse(0))).foreach { ev =>
      val src = ts(ev)
      ev.event_type match {
        // ---- pass-through rows keyed by lobby -------------------------------------------------------------------
        case "board.config" => out += Signal(ev.lobby_id, "config", null, null, 0, 0, ev.event_time, ev.config, src)
        case "lobby.snapshot" =>
          out += Signal(ev.lobby_id, "snapshot", null, null, ev.sim_safety.getOrElse(0).toDouble, ev.population.getOrElse(0).toLong, ev.event_time, null, src)

        // ---- presence: joins, leaves, pvp vehicles ----------------------------------------------------------------
        case "session.join" =>
          val prev = if (presence.exists()) Some(presence.get()) else None
          val stale = prev.exists(_.last_seen.after(ev.event_time))
          if (!stale) {
            prev.filter(_.lobby_id != ev.lobby_id).foreach(p => out += Signal(p.lobby_id, "left", key, null, 0, 0, ev.event_time, null, src))
            if (!prev.exists(_.lobby_id == ev.lobby_id)) out += Signal(ev.lobby_id, "joined", key, null, 0, 0, ev.event_time, null, src)
            presence.update(PlayerState(ev.lobby_id, ev.location_id, passive = false, null, ev.event_time, prev.map(_.actions).getOrElse(0L) + 1))
          }
          // menace: a session resets the counters and tells the lobby the prior
          val m = if (menace.exists()) menace.get() else Menace(Option(ev.agent_name).getOrElse(key), 0, 0.0, null, 0, 0, 0, 0, 0, 0, 0)
          val reset = m.copy(lobby_id = ev.lobby_id, session_kills = 0, sellers_killed = 0, civilians_killed = 0, pvp_kills = 0, flying_spawns = 0, bounties_on = 0, wanted_peak = 0)
          menace.update(reset)
          out += Signal(ev.lobby_id, "menace", key, MenaceLevel.level(MenaceLevel.score(reset)), MenaceLevel.score(reset), 0, ev.event_time, null, src)
        case "session.leave" =>
          if (presence.exists() && presence.get().lobby_id == ev.lobby_id && !presence.get().last_seen.after(ev.event_time)) {
            out += Signal(ev.lobby_id, "left", key, null, 0, 0, ev.event_time, null, src)
            presence.clear()
          }
          if (streak.exists()) closeStreak(out, ev.event_time, "left", src)
        case "player.vehicle_spawned" =>
          if (presence.exists()) presence.update(presence.get().copy(vehicle = ev.vehicle, last_seen = ev.event_time))
          if (Vehicles.pvp.contains(ev.vehicle)) out += Signal(ev.lobby_id, "pvp_vehicle", key, ev.vehicle, 0, 0, ev.event_time, null, src)
          menaceStep(out, ev, src)
        case "player.move" | "session.passive_on" | "session.passive_off" =>
          if (presence.exists() && !presence.get().last_seen.after(ev.event_time))
            presence.update(presence.get().copy(location_id = ev.location_id, passive = ev.event_type == "session.passive_on" || (ev.event_type == "player.move" && presence.get().passive), last_seen = ev.event_time, actions = presence.get().actions + 1))

        // ---- kills: menace score and the streak -------------------------------------------------------------------
        case "combat.kill" =>
          menaceStep(out, ev, src)
          val cur = if (streak.exists()) streak.get() else Streak(ev.lobby_id, ev.event_time, ev.event_time, 0, 0, 0, 0, flying = false)
          streak.update(cur.copy(
            last_kill = if (ev.event_time.after(cur.last_kill)) ev.event_time else cur.last_kill,
            kills = cur.kills + 1,
            sellers = cur.sellers + (if (ev.victim_activity == "selling") 1 else 0),
            civilians = cur.civilians + (if (ev.victim_activity == "freemode" || ev.victim_activity == "supply") 1 else 0),
            pvp = cur.pvp + (if (ev.victim_activity == "pvp") 1 else 0),
            flying = cur.flying || Vehicles.flying.contains(ev.attacker_vehicle)))
          retime(streakDeadline, now + streakGapMs)
        case "player.bounty_placed" | "wanted.gained" | "wanted.escalated" => menaceStep(out, ev, src)

        // ---- sells (one in flight per seller) ----------------------------------------------------------------------
        case "sell.started" =>
          if (!sell.exists()) {
            sell.update(OpenSell(key, ev.lobby_id, ev.business, ev.value.getOrElse(0L), ev.drops.getOrElse(0), 0, 0L, ev.event_time, now))
            retime(sellDeadline, now + sellSlaMs)
          }
        case "sell.delivery" =>
          if (sell.exists()) { val s = sell.get(); sell.update(s.copy(deliveries = math.max(s.deliveries, ev.drop.getOrElse(0)), value_delivered = math.max(s.value_delivered, ev.value_delivered.getOrElse(0L)))) }
        case t if terminalSell(t) =>
          val outcome = t.stripPrefix("sell.")
          if (sell.exists()) {
            val s = sell.get()
            out += Signal(s.lobby_id, "sell", key, outcome, s.value.toDouble, ev.value_delivered.getOrElse(s.value_delivered), s.started_at, null, src)
            sell.clear(); disarm(sellDeadline)
          } else {
            out += Signal(ev.lobby_id, "sell", key, s"late_$outcome", ev.value.getOrElse(0L).toDouble, ev.value_delivered.getOrElse(0L), ev.event_time, null, src)
          }
        case _ =>
      }
    }
    out.iterator
  }

  /** Apply one event to the menace score; emit on a level change or anything done to a seller. */
  private def menaceStep(out: scala.collection.mutable.ListBuffer[Signal], ev: LsEv, src: Long): Unit = {
    val cur = if (menace.exists()) menace.get() else Menace(Option(ev.agent_name).getOrElse(ev.agent_id), 0, 0.0, null, 0, 0, 0, 0, 0, 0, 0)
    val next = ev.event_type match {
      case "combat.kill" => cur.copy(lobby_id = ev.lobby_id, session_kills = cur.session_kills + 1,
        sellers_killed = cur.sellers_killed + (if (ev.victim_activity == "selling") 1 else 0),
        civilians_killed = cur.civilians_killed + (if (ev.victim_activity == "freemode" || ev.victim_activity == "supply") 1 else 0),
        pvp_kills = cur.pvp_kills + (if (ev.victim_activity == "pvp") 1 else 0))
      case "player.vehicle_spawned" => cur.copy(lobby_id = ev.lobby_id, flying_spawns = cur.flying_spawns + (if (Vehicles.flying.contains(ev.vehicle)) 1 else 0))
      case "player.bounty_placed" => cur.copy(lobby_id = ev.lobby_id, bounties_on = cur.bounties_on + 1)
      case "wanted.gained" | "wanted.escalated" => cur.copy(lobby_id = ev.lobby_id, wanted_peak = math.max(cur.wanted_peak, ev.stars.getOrElse(0)))
      case _ => cur
    }
    val before = MenaceLevel.level(MenaceLevel.score(cur))
    menace.update(next)
    val s = MenaceLevel.score(next); val lvl = MenaceLevel.level(s)
    if (lvl != before || ev.victim_activity == "selling")
      out += Signal(next.lobby_id, "menace", ev.agent_id, lvl, s, next.session_kills, ev.event_time, null, src)
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[Signal] = {
    val out = scala.collection.mutable.ListBuffer.empty[Signal]
    val t = info.getExpiryTimeInMs()
    if (sellDeadline.exists() && sellDeadline.get() <= t && sell.exists()) {
      val s = sell.get()
      out += Signal(s.lobby_id, "sell", key, "timeout", s.value.toDouble, s.value_delivered, s.started_at, null, 0L)
      sell.clear(); sellDeadline.clear()
    }
    if (streakDeadline.exists() && streakDeadline.get() <= t && streak.exists()) {
      val s = streak.get()
      out += Signal(s.lobby_id, "streak", null, "gap", s.sellers.toDouble, (s.sellers + s.civilians).toLong, s.last_kill, null, 0L)
      streak.clear(); streakDeadline.clear()
    }
    out.iterator
  }
}
