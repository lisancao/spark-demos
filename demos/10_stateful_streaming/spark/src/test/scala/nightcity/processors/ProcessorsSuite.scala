package nightcity.processors

import java.sql.Timestamp
import java.time.Duration
import org.apache.spark.sql.streaming.{TimeMode, TwsTester}
import org.scalatest.funsuite.AnyFunSuite
import nightcity.Ev

/** Unit tests with Spark 4.3's TwsTester: no SparkSession, no stream, just the processor and a manual clock. */
class ProcessorsSuite extends AnyFunSuite {

  private def ev(t: String, ms: Long, agent: String = "", loc: String = "", attacker: String = "", target: String = "",
                 round: Option[Int] = None, rounds: Option[Int] = None, result: String = "", district: String = "",
                 crime: String = "", dispatched: Option[Boolean] = None, responseTicks: Option[Int] = None): Ev =
    Ev(s"$t-$ms", t, new Timestamp(ms), ms / 100, agent, agent, loc, "", attacker, target, round, rounds, result,
      district, crime, None, responseTicks, dispatched, None, "", "", "", None, None, None, "", "")

  test("presence: first sighting and moves emit, repeats and late rows do not") {
    val t = new TwsTester[String, Ev, nightcity.PresenceUpdate](new NpcPresence(Duration.ofMinutes(1)), timeMode = TimeMode.ProcessingTime())
    val first = t.test("smasher", List(ev("agent.look", 1000, "smasher", "megabuilding_0")))
    assert(first.map(p => (p.location_id, p.first_seen, p.actions)) == List(("megabuilding_0", true, 1L)))
    assert(t.test("smasher", List(ev("agent.rest", 2000, "smasher", "megabuilding_0"))).isEmpty)
    val moved = t.test("smasher", List(ev("agent.move", 3000, "smasher", "megabuilding_4")))
    assert(moved.map(p => (p.previous_location, p.location_id, p.actions)) == List(("megabuilding_0", "megabuilding_4", 3L)))
    // a late row from before the move must not drag the NPC back
    assert(t.test("smasher", List(ev("agent.talk", 2500, "smasher", "megabuilding_0"))).isEmpty)
    assert(t.peekValueState[Presence]("presence", "smasher").get.location_id == "megabuilding_4")
    // out-of-order rows in one batch are sorted before they are applied
    val batch = t.test("padre", List(ev("agent.move", 5000, "padre", "b"), ev("agent.look", 4000, "padre", "a")))
    assert(batch.map(_.location_id) == List("a", "b"))
  }

  test("combat: started/rounds/ended closes with a summary and clears state") {
    val t = new TwsTester[String, Ev, nightcity.CombatSummary](new CombatSessions(gapMs = 5000), timeMode = TimeMode.EventTime(),
      eventTimeExtractor = Some((e: Ev) => e.event_time.getTime))
    assert(t.test("vasquez", List(ev("combat.started", 1000, attacker = "vasquez", target = "muamar", loc = "camp"))).isEmpty)
    assert(t.test("vasquez", List(ev("combat.round", 1300, attacker = "vasquez", round = Some(3)), ev("combat.round", 1100, attacker = "vasquez", round = Some(1)), ev("combat.round", 1200, attacker = "vasquez", round = Some(2)))).isEmpty)
    val closed = t.test("vasquez", List(ev("combat.ended", 1400, attacker = "vasquez", rounds = Some(3), result = "victory")))
    assert(closed.map(c => (c.target_id, c.rounds_seen, c.rounds_reported, c.result, c.closed_by)) == List(("muamar", 3, Some(3), "victory", "ended")))
    assert(t.peekValueState[Combat]("combat", "vasquez").isEmpty)
    assert(t.setWatermark(60000).isEmpty) // nothing left to time out
  }

  test("combat: a lost `ended` is closed by the event-time timer once the watermark passes") {
    val t = new TwsTester[String, Ev, nightcity.CombatSummary](new CombatSessions(gapMs = 5000), timeMode = TimeMode.EventTime(),
      eventTimeExtractor = Some((e: Ev) => e.event_time.getTime))
    t.test("okafor", List(ev("combat.started", 1000, attacker = "okafor", target = "x", loc = "clinic"), ev("combat.round", 1500, attacker = "okafor", round = Some(1))))
    assert(t.setWatermark(6000).isEmpty)      // 1500 + 5000 = 6500 not yet reached
    val timedOut = t.setWatermark(7000)
    assert(timedOut.map(c => (c.rounds_seen, c.closed_by, c.ended_at.getTime)) == List((1, "timeout", 1500L)))
    assert(t.peekValueState[Combat]("combat", "okafor").isEmpty)
  }

  test("combat: a whole fight in one tick, shuffled, still sessionizes in order") {
    val t = new TwsTester[String, Ev, nightcity.CombatSummary](new CombatSessions(gapMs = 5000), timeMode = TimeMode.EventTime(),
      eventTimeExtractor = Some((e: Ev) => e.event_time.getTime))
    val fight = List(
      ev("combat.ended", 2000, attacker = "a", rounds = Some(2), result = "defeat"),
      ev("combat.round", 2000, attacker = "a", round = Some(2)),
      ev("combat.started", 2000, attacker = "a", target = "b", loc = "bar"),
      ev("combat.round", 2000, attacker = "a", round = Some(1)))
    val out = t.test("a", fight)
    assert(out.map(c => (c.target_id, c.rounds_seen, c.closed_by)) == List(("b", 2, "ended")))
  }

  test("ncpd: crime and response in the same tick, response first in the batch, is still answered") {
    val t = new TwsTester[String, Ev, nightcity.CrimeOutcome](new NcpdResponse(slaMs = 10000), timeMode = TimeMode.ProcessingTime())
    val out = t.test("k", List(
      ev("crime.ncpd_response", 1000, loc = "k", crime = "theft", dispatched = Some(true), responseTicks = Some(5)),
      ev("crime.committed", 1000, loc = "k", crime = "theft")))
    assert(out.map(_.outcome) == List("answered"))
  }

  test("ncpd: answered within SLA, declined, and unanswered by timer") {
    val t = new TwsTester[String, Ev, nightcity.CrimeOutcome](new NcpdResponse(slaMs = 10000), timeMode = TimeMode.ProcessingTime())
    t.setProcessingTime(1000)
    assert(t.test("hideout:theft", List(ev("crime.committed", 1000, loc = "hideout", district = "gang", crime = "theft"))).isEmpty)
    t.setProcessingTime(4000)
    val answered = t.test("hideout:theft", List(ev("crime.ncpd_response", 4000, loc = "hideout", crime = "theft", dispatched = Some(true), responseTicks = Some(10))))
    assert(answered.map(o => (o.outcome, o.response_ticks, o.waited_ms)) == List(("answered", Some(10), 3000L)))
    assert(t.peekValueState[OpenCrime]("open_crime", "hideout:theft").isEmpty)

    t.test("tower:fraud", List(ev("crime.committed", 5000, loc = "tower", crime = "fraud")))
    val declined = t.test("tower:fraud", List(ev("crime.ncpd_response", 5000, loc = "tower", crime = "fraud", dispatched = Some(false))))
    assert(declined.map(_.outcome) == List("declined"))

    t.test("stall:assault", List(ev("crime.committed", 6000, loc = "stall", crime = "assault")))
    assert(t.setProcessingTime(13000).isEmpty)          // registered at 4000 processing time, SLA at 14000
    val fired = t.setProcessingTime(14000)
    assert(fired.map(o => (o.outcome, o.waited_ms)) == List(("unanswered", 10000L)))
    assert(t.peekValueState[OpenCrime]("open_crime", "stall:assault").isEmpty)
  }
}

class Phase4Suite extends AnyFunSuite {
  private def ev(t: String, ms: Long, agent: String = "", loc: String = "", faction: String = "", influence: Option[Double] = None,
                 description: String = null, result: String = "", chrome: Option[Int] = None): Ev =
    Ev(s"$t-$ms", t, new Timestamp(ms), ms / 100, agent, agent, loc, "", agent, "", None, None, result,
      "", "", None, None, None, chrome, "", faction, "", None, None, None, "", "", influence, description, null, null)

  test("faction: territories are a map, relations a bounded list") {
    val t = new TwsTester[String, Ev, nightcity.FactionUpdate](new FactionTerritory(keep = 3))
    t.test("nakamura", List(ev("faction.territory_gained", 1000, faction = "nakamura", loc = "stall_24", influence = Some(0.7))))
    t.test("nakamura", List(ev("faction.territory_gained", 2000, faction = "nakamura", loc = "stall_24", influence = Some(0.9)))) // same place, stronger grip
    val out = t.test("nakamura", List(ev("faction.territory_gained", 3000, faction = "nakamura", loc = "bar_3", influence = Some(0.2))))
    assert(out.map(_.territories) == List(2))
    assert(t.peekMapState[String, Double]("territories", "nakamura") == Map("stall_24" -> 0.9, "bar_3" -> 0.2))
    (1 to 5).foreach(i => t.test("nakamura", List(ev("faction.relation_change", 4000 + i, faction = "nakamura", description = s"talk $i"))))
    assert(t.peekListState[String]("relations", "nakamura") == List("talk 3", "talk 4", "talk 5"))
    val lost = t.test("nakamura", List(ev("faction.territory_lost", 9000, faction = "nakamura", loc = "bar_3")))
    assert(lost.map(_.territories) == List(1))
  }

  test("risk: roster seeds the state, events move the score, unknown NPCs start from zero") {
    val t = new TwsTester[String, Ev, nightcity.RiskUpdate](new CyberpsychosisRisk(),
      initialState = List(("smasher", nightcity.Roster("smasher", "Smasher", "solo_merc", 75, 4))), timeMode = TimeMode.ProcessingTime())
    assert(t.peekValueState[Risk]("risk", "smasher").get.chrome_score == 75)
    val a = t.test("smasher", List(ev("agent.attack", 1000, agent = "smasher")))
    assert(a.map(r => (r.attacks, r.score, r.level)) == List((1L, 75 * 0.5 + 4 * 2.0 + 1.5, "stable")))
    val w = t.test("smasher", List(ev("world.cyberpsychosis", 2000, agent = "smasher", chrome = Some(80))))
    assert(w.map(r => (r.warnings, r.chrome_score, r.level)) == List((1L, 80, "elevated")))
    assert(t.test("smasher", List(ev("agent.move", 3000, agent = "smasher"))).isEmpty) // not a risk event
    val stranger = t.test("nobody", List(ev("combat.ended", 4000, agent = "nobody", result = "defeat")))
    assert(stranger.map(r => (r.chrome_score, r.defeats, r.score)) == List((0, 1L, 4.0)))
  }

  test("risk v2: a recent warning doubles the warning weight") {
    val t = new TwsTester[String, Ev, nightcity.RiskUpdate](new CyberpsychosisRiskV2(),
      initialState = List(("x", nightcity.Roster("x", "X", "ganger", 40, 2))), timeMode = TimeMode.ProcessingTime())
    val w = t.test("x", List(ev("world.cyberpsychosis", 1000, agent = "x", chrome = Some(40))))
    assert(w.map(_.score) == List(40 * 0.5 + 2 * 2.0 + 2 * 10.0))
    val later = t.test("x", List(ev("agent.attack", 100000, agent = "x")))
    assert(later.map(_.score) == List(40 * 0.5 + 2 * 2.0 + 1.5 + 10.0))
  }
}
