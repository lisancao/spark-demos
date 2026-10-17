package nightcity.losantos

import java.sql.Timestamp
import java.time.Duration
import org.apache.spark.sql.streaming.{TimeMode, TwsTester}
import org.scalatest.funsuite.AnyFunSuite

/** TwsTester unit tests for the Los Santos processors: no SparkSession, a manual clock, one key at a time. */
class LosSantosSuite extends AnyFunSuite {

  private def ev(t: String, ms: Long, agent: String = "", lobby: String = "", loc: String = "", target: String = "",
                 org: String = "", mission: String = "", vehicle: String = "", attackerVehicle: String = "", activity: String = "",
                 business: String = "", stars: Option[Int] = None, drop: Option[Int] = None, drops: Option[Int] = None,
                 value: Option[Long] = None, delivered: Option[Long] = None, stock: Option[Long] = None,
                 businesses: Seq[LsBusiness] = null): LsEv =
    LsEv(s"$t-$ms-$agent", t, new Timestamp(ms), ms / 100, agent, agent, lobby, loc, target, org, mission, "", vehicle, attackerVehicle,
      "", activity, "", business, stars, None, drop, drops, value, delivered, None, stock, None, None, None, None, null, businesses)

  test("presence: join, hop (join before the late leave), leave") {
    val t = new TwsTester[String, LsEv, LsPresenceUpdate](new LobbyPresence(Duration.ofMinutes(2)), timeMode = TimeMode.ProcessingTime())
    assert(t.test("p1", List(ev("session.join", 1000, "p1", "ls_01", "vinewood"))).map(_.change) == List("joined"))
    // the join into ls_02 arrives first; the leave for ls_01 shows up later and must not clear the new state
    assert(t.test("p1", List(ev("session.join", 3000, "p1", "ls_02", "davis"))).map(p => (p.change, p.previous_lobby, p.lobby_id)) == List(("hopped", "ls_01", "ls_02")))
    assert(t.test("p1", List(ev("session.leave", 2900, "p1", "ls_01", "vinewood"))).isEmpty)
    assert(t.peekValueState[PlayerState]("player", "p1").get.lobby_id == "ls_02")
    assert(t.test("p1", List(ev("session.leave", 4000, "p1", "ls_02", "davis"))).map(_.change) == List("left"))
    assert(t.peekValueState[PlayerState]("player", "p1").isEmpty)
  }

  test("streaks: no end event, closed by the watermark; a leave closes it at once") {
    val t = new TwsTester[String, LsEv, StreakSummary](new GriefStreaks(gapMs = 5000), timeMode = TimeMode.EventTime(),
      eventTimeExtractor = Some((e: LsEv) => e.event_time.getTime))
    val k = "g1:ls_01"
    assert(t.test(k, List(
      ev("combat.kill", 1000, "g1", "ls_01", target = "s1", attackerVehicle = "oppressor_mk2", activity = "selling"),
      ev("combat.kill", 2500, "g1", "ls_01", target = "t1", attackerVehicle = "oppressor_mk2", activity = "freemode"))).isEmpty)
    assert(t.setWatermark(7000).isEmpty)                       // 2500 + 5000 = 7500 not reached
    val closed = t.setWatermark(8000)
    assert(closed.map(s => (s.attacker_id, s.kills, s.sellers_killed, s.civilians_killed, s.flying, s.closed_by)) == List(("g1", 2, 1, 1, true, "gap")))
    assert(t.test(k, List(ev("combat.kill", 9000, "g1", "ls_01", target = "s2", activity = "pvp"))).isEmpty)
    assert(t.test(k, List(ev("session.leave", 9500, "g1", "ls_01"))).map(s => (s.kills, s.closed_by)) == List((1, "left")))
    assert(t.peekValueState[Streak]("streak", k).isEmpty)
  }

  test("sells: deliveries then a terminal; a terminal before its started is reported as late") {
    val t = new TwsTester[String, LsEv, SellOutcome](new SellMissions(slaMs = 15000), timeMode = TimeMode.ProcessingTime())
    assert(t.test("m1", List(
      ev("sell.delivery", 1200, "s1", "ls_01", mission = "m1", drop = Some(1), drops = Some(2), delivered = Some(50000L)),
      ev("sell.started", 1000, "s1", "ls_01", mission = "m1", business = "s1_bunker", value = Some(100000L), drops = Some(2)))).isEmpty)
    val done = t.test("m1", List(ev("sell.completed", 1600, "s1", "ls_01", mission = "m1", delivered = Some(100000L))))
    assert(done.map(o => (o.outcome, o.deliveries, o.value_delivered, o.value)) == List(("completed", 1, 100000L, 100000L)))
    val orphan = t.test("m2", List(ev("sell.destroyed", 2000, "s2", "ls_01", mission = "m2", delivered = Some(0L), value = Some(70000L))))
    assert(orphan.map(_.outcome) == List("late_destroyed"))
  }

  test("sells: no terminal within the SLA closes as timeout (processing-time timer)") {
    val t = new TwsTester[String, LsEv, SellOutcome](new SellMissions(slaMs = 15000), timeMode = TimeMode.ProcessingTime())
    t.setProcessingTime(1)
    assert(t.test("m3", List(ev("sell.started", 1000, "s3", "ls_02", mission = "m3", value = Some(5000L), drops = Some(1)))).isEmpty)
    assert(t.setProcessingTime(14000).isEmpty)
    assert(t.setProcessingTime(15001).map(_.outcome) == List("timeout"))  // registered at clock 1 + 15000
  }

  test("orgs: registration restates stock so a replayed registration is idempotent") {
    val t = new TwsTester[String, LsEv, OrgUpdate](new OrgBusinesses(keep = 3), timeMode = TimeMode.None())
    val reg = ev("org.registered", 1000, "g1", "ls_01", org = "o1", businesses = Seq(LsBusiness("g1_bunker", "bunker", 300000L, "paleto_bay"), LsBusiness("g1_coke", "coke_lockup", 100000L, "davis")))
    assert(t.test("o1", List(reg)).map(u => (u.businesses, u.stock_total)) == List((2, 400000L)))
    assert(t.test("o1", List(ev("org.supply_run", 2000, "g1", "ls_01", org = "o1", business = "g1_coke", stock = Some(140000L)))).map(_.stock_total) == List(440000L))
    assert(t.test("o1", List(reg.copy(event_id = "again"))).map(_.stock_total) == List(400000L))
    val outcomes = (1 to 4).map(i => ev(if (i % 2 == 0) "sell.destroyed" else "sell.completed", 3000 + i, "g1", "ls_01", org = "o1", mission = s"m$i"))
    val last = t.test("o1", outcomes.toList).last
    assert((last.sells_recent, last.sells_destroyed_recent) == (3, 2))
  }

  test("menace: roster prior, then a sell kill promotes the level") {
    val t = new TwsTester[String, LsEv, MenaceUpdate](new MenaceScore(), timeMode = TimeMode.ProcessingTime(),
      initialState = List("g1" -> LsProfile("g1", "OppressorAndy", 420, 3.5, 2000, 7000, 2000)))
    val joined = t.test("g1", List(ev("session.join", 1000, "g1", "ls_01")))
    assert(joined.map(m => (m.level, m.kd)) == List(("civilian", 3.5)))   // 3.5 * 4 = 14: the profile alone is not enough
    val spawned = t.test("g1", List(ev("player.vehicle_spawned", 1500, "g1", "ls_01", vehicle = "oppressor_mk2")))
    assert(spawned.isEmpty)                                               // 24: still civilian, nothing to say
    val killed = t.test("g1", List(ev("combat.kill", 2000, "g1", "ls_01", target = "s1", attackerVehicle = "oppressor_mk2", activity = "selling")))
    assert(killed.map(m => (m.level, m.sellers_killed)) == List(("hostile", 1L)))  // 54
    val again = t.test("g1", List(ev("combat.kill", 2500, "g1", "ls_01", target = "s2", attackerVehicle = "oppressor_mk2", activity = "selling")))
    assert(again.map(_.level) == List("menace"))
    assert(t.test("g1", List(ev("session.join", 9000, "g1", "ls_03"))).map(m => (m.level, m.session_kills)) == List(("civilian", 0L)))
  }

  test("board: joins, a menace, a destroyed sell, and a config row that changes the verdict") {
    val t = new TwsTester[String, Signal, LobbyVerdict](new LobbySafety(), timeMode = TimeMode.ProcessingTime())
    def at(ms: Long) = new Timestamp(ms)
    val v1 = t.test("ls_01", List(Signal("ls_01", "joined", "a", null, 0, 0, at(1000)), Signal("ls_01", "joined", "b", null, 0, 0, at(1000)))).last
    assert((v1.population, v1.score, v1.verdict) == (2, 100.0, "sell"))
    val v2 = t.test("ls_01", List(Signal("ls_01", "menace", "b", "menace", 80, 3, at(2000)))).last
    assert((v2.menaces, v2.score, v2.verdict) == (1, 82.0, "sell"))
    val v3 = t.test("ls_01", List(Signal("ls_01", "sell", "a", "destroyed", 90000, 0, at(3000)), Signal("ls_01", "pvp_vehicle", "b", "oppressor_mk2", 0, 0, at(2500)))).last
    assert((v3.sells_destroyed_recent, v3.pvp_vehicles, v3.score, v3.verdict) == (1, 1, 66.0, "risky"))
    // the same lobby under a harsher rule: the config row is applied before anything else at its timestamp
    val v4 = t.test("ls_01", List(Signal("ls_01", "config", null, null, 0, 0, at(4000), """{"menace": 50, "destroyed": 30}"""))).last
    assert((v4.score, v4.verdict) == (14.0, "hop"))
    // the menace leaves: the record is kept, the lobby is not charged for it
    val v5 = t.test("ls_01", List(Signal("ls_01", "left", "b", null, 0, 0, at(5000)))).last
    assert((v5.population, v5.menaces, v5.score) == (1, 0, 70.0))
    // the destroyed sell ages out of the window (30 s of event time) and the lobby is forgiven
    val v6 = t.test("ls_01", List(Signal("ls_01", "joined", "c", null, 0, 0, at(34000)))).last
    assert((v6.sells_destroyed_recent, v6.score, v6.verdict) == (0, 100.0, "sell"))
    assert(t.peekMapState[String, Member]("known", "ls_01").contains("b"))
  }
}
