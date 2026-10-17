package nightcity.losantos

import org.apache.spark.sql.streaming._

/** Scoring weights. Replaced at runtime by a row on the config topic; the default is what ships. */
case class Weights(menace: Double, hostile: Double, pvp_vehicle: Double, destroyed: Double, streak_kill: Double, window_ms: Long) {
  def json: String = s"""{"menace":$menace,"hostile":$hostile,"pvp_vehicle":$pvp_vehicle,"destroyed":$destroyed,"streak_kill":$streak_kill,"window_ms":$window_ms}"""
}
object Weights {
  /** `window_ms` is event time: how long a destroyed sell or a streak keeps counting against the lobby. */
  val default: Weights = Weights(menace = 18, hostile = 4, pvp_vehicle = 6, destroyed = 10, streak_kill = 3, window_ms = 30000)
  private val num = """"(\w+)"\s*:\s*(-?[0-9.]+)""".r
  /** Keys missing from the JSON keep the value in `base`: a config row is a patch, not a replacement. */
  def parse(s: String, base: Weights = default): Weights = {
    val m = num.findAllMatchIn(s).map(x => x.group(1) -> x.group(2).toDouble).toMap
    Weights(m.getOrElse("menace", base.menace), m.getOrElse("hostile", base.hostile), m.getOrElse("pvp_vehicle", base.pvp_vehicle),
      m.getOrElse("destroyed", base.destroyed), m.getOrElse("streak_kill", base.streak_kill), m.getOrElse("window_ms", base.window_ms.toDouble).toLong)
  }
}

case class Member(level: String, score: Double, pvp_vehicle: Boolean)

/**
 * The board. Key = lobby. Second stage of the chain: its input is the union of the five processors' outputs,
 * reduced to `Signal`, plus config rows fanned out to every lobby.
 *
 * MapState  present:  player -> what we know (menace level, on a pvp vehicle). Joins add, leaves remove.
 * MapState  known:    player -> latest menace level, kept across leaves so a returning player carries their record.
 * ListState sells:    sell outcomes in this lobby with their event time; ListState streaks: streak kill counts likewise.
 *                     Both are pruned to the configured window at every input, in event time, so a quiet lobby
 *                     is forgiven and a busy one is judged on what just happened.
 * ValueState weights: the scoring rule, replaced by a config row without a restart.
 *
 * Score is "how much is wrong with this lobby"; the verdict is for someone with a full bunker.
 */
class LobbySafety(defaults: Weights = Weights.default) extends StatefulProcessor[String, Signal, LobbyVerdict] {
  import implicits._
  @transient private var present: MapState[String, Member] = _
  @transient private var known: MapState[String, Member] = _
  @transient private var sells: ListState[String] = _
  @transient private var streaks: ListState[String] = _
  @transient private var weights: ValueState[String] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit = {
    present = getHandle.getMapState[String, Member]("present", TTLConfig.NONE)
    known = getHandle.getMapState[String, Member]("known", TTLConfig.NONE)
    sells = getHandle.getListState[String]("sells", TTLConfig.NONE)
    streaks = getHandle.getListState[String]("streaks", TTLConfig.NONE)
    weights = getHandle.getValueState[String]("weights", TTLConfig.NONE)
  }

  private def rank(k: String) = k match { case "config" => 0; case "joined" => 1; case "left" => 2; case _ => 3 }

  /** Entries are "value@eventTimeMs". Prune everything older than the window; rewrite only if something was dropped. */
  private def prune(ls: ListState[String], nowMs: Long, windowMs: Long): Seq[String] = {
    val all = ls.get().toArray
    val kept = all.filter(e => nowMs - e.substring(e.lastIndexOf('@') + 1).toLong <= windowMs)
    // a ListState may not be written as an empty list (ILLEGAL_STATE_STORE_VALUE.EMPTY_LIST_VALUE): clear it instead
    if (kept.isEmpty && all.nonEmpty) ls.clear() else if (kept.length != all.length) ls.put(kept)
    kept.toSeq.map(e => e.substring(0, e.lastIndexOf('@')))
  }

  override def handleInputRows(key: String, rows: Iterator[Signal], timerValues: TimerValues): Iterator[LobbyVerdict] = {
    val out = scala.collection.mutable.ListBuffer.empty[LobbyVerdict]
    rows.toSeq.sortBy(s => (s.at.getTime, rank(s.kind))).foreach { sig =>
      sig.kind match {
        case "config" =>
          val cur = if (weights.exists()) Weights.parse(weights.get(), defaults) else defaults
          weights.update(Weights.parse(sig.config, cur).json)
        case "joined" =>
          val prior = if (known.containsKey(sig.player_id)) known.getValue(sig.player_id) else Member("civilian", 0.0, pvp_vehicle = false)
          present.updateValue(sig.player_id, prior.copy(pvp_vehicle = false))
        case "left" => if (present.containsKey(sig.player_id)) present.removeKey(sig.player_id)
        case "menace" =>
          val m = Member(sig.level, sig.score, present.containsKey(sig.player_id) && present.getValue(sig.player_id).pvp_vehicle)
          known.updateValue(sig.player_id, m)
          if (present.containsKey(sig.player_id)) present.updateValue(sig.player_id, m)
        case "pvp_vehicle" =>
          if (present.containsKey(sig.player_id)) present.updateValue(sig.player_id, present.getValue(sig.player_id).copy(pvp_vehicle = true))
        case "sell" => sells.appendValue(s"${sig.level}@${sig.at.getTime}")
        case "streak" => streaks.appendValue(s"${sig.n}@${sig.at.getTime}")
        case "snapshot" => // the sim's own verdict rides along for grading; it never touches the score
        case _ =>
      }
      val ww = if (weights.exists()) Weights.parse(weights.get(), defaults) else defaults
      val members = present.iterator().toSeq
      val menaces = members.count(_._2.level == "menace")
      val hostiles = members.count(_._2.level == "hostile")
      val bikes = members.count(_._2.pvp_vehicle)
      val recentSells = prune(sells, sig.at.getTime, ww.window_ms)
      val destroyed = recentSells.count(_ == "destroyed")
      val streakKills = prune(streaks, sig.at.getTime, ww.window_ms).map(_.toInt).sum
      val score = ww.menace * menaces + ww.hostile * hostiles + ww.pvp_vehicle * bikes + ww.destroyed * destroyed + ww.streak_kill * streakKills
      val safety = math.max(0.0, 100.0 - score)
      val verdict = if (safety >= 70) "sell" else if (safety >= 40) "risky" else "hop"
      out += LobbyVerdict(key, members.size, menaces, hostiles, bikes, recentSells.size, destroyed, streakKills, safety, verdict, ww.json,
        s"${sig.kind}:${Option(sig.player_id).getOrElse("")}", sig.at,
        if (sig.kind == "snapshot") Some(sig.score.toInt) else None, if (sig.kind == "snapshot") Some(sig.n.toInt) else None,
        sig.source_kafka_ts)
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[LobbyVerdict] = Iterator.empty
}
