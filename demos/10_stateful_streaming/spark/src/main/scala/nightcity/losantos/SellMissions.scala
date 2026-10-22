package nightcity.losantos

import java.sql.Timestamp
import org.apache.spark.sql.streaming._

case class OpenSell(seller_id: String, lobby_id: String, business: String, value: Long, drops: Int, deliveries: Int,
                    value_delivered: Long, started_at: Timestamp, registered_at_ms: Long)

/**
 * Signal 3: every sell mission from `started` to whatever ended it. Key = mission id.
 *
 * The sim always closes a sell (completed, destroyed, expired, abandoned), so the processing-time timer here is the
 * pipeline's patience, not the game's clock: a sell with no terminal event `sla` after it was registered is reported
 * as `timeout`, and the terminal that shows up later is reported as late rather than dropped.
 */
class SellMissions(slaMs: Long) extends StatefulProcessor[String, LsEv, SellOutcome] {
  import implicits._
  @transient private var open: ValueState[OpenSell] = _
  private val terminal = Set("sell.completed", "sell.destroyed", "sell.expired", "sell.abandoned")

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit =
    open = getHandle.getValueState[OpenSell]("open_sell", TTLConfig.NONE)

  private def rank(t: String) = t match { case "sell.started" => 0; case "sell.delivery" => 1; case _ => 2 }

  override def handleInputRows(key: String, rows: Iterator[LsEv], timerValues: TimerValues): Iterator[SellOutcome] = {
    val out = scala.collection.mutable.ListBuffer.empty[SellOutcome]
    val now = timerValues.getCurrentProcessingTimeInMs()
    rows.toSeq.sortBy(ev => (ev.event_time.getTime, rank(ev.event_type), ev.drop.getOrElse(0))).foreach { ev =>
      ev.event_type match {
        case "sell.started" =>
          if (!open.exists()) {
            open.update(OpenSell(ev.agent_id, ev.lobby_id, ev.business, ev.value.getOrElse(0L), ev.drops.getOrElse(0), 0, 0L, ev.event_time, now))
            getHandle.registerTimer(now + slaMs)
          }
        case "sell.delivery" =>
          if (open.exists()) {
            val s = open.get()
            open.update(s.copy(deliveries = math.max(s.deliveries, ev.drop.getOrElse(0)), value_delivered = math.max(s.value_delivered, ev.value_delivered.getOrElse(0L))))
          }
        case t if terminal(t) =>
          val outcome = t.stripPrefix("sell.")
          if (open.exists()) {
            val s = open.get()
            out += SellOutcome(key, s.seller_id, s.lobby_id, s.business, s.value, s.drops, s.deliveries,
              ev.value_delivered.getOrElse(s.value_delivered), outcome, ev.destroyed_by, s.started_at, now - s.registered_at_ms)
            open.clear()
            getHandle.listTimers().foreach(getHandle.deleteTimer)
          } else {
            // terminal with no open sell: either its `started` is late, or we already timed it out
            out += SellOutcome(key, ev.agent_id, ev.lobby_id, ev.business, ev.value.getOrElse(ev.value_lost.getOrElse(0L) + ev.value_delivered.getOrElse(0L)),
              0, 0, ev.value_delivered.getOrElse(0L), s"late_$outcome", ev.destroyed_by, ev.event_time, 0L)
          }
        case _ =>
      }
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[SellOutcome] = {
    if (!open.exists()) return Iterator.empty
    val s = open.get()
    open.clear()
    Iterator(SellOutcome(key, s.seller_id, s.lobby_id, s.business, s.value, s.drops, s.deliveries, s.value_delivered, "timeout", null,
      s.started_at, info.getExpiryTimeInMs() - s.registered_at_ms))
  }
}
