package nightcity.losantos

import org.apache.spark.sql.streaming._

case class OrgMeta(leader_id: String, lobby_id: String, members: Int)

/**
 * Signal 4: what each organisation holds. Key = org id.
 *
 * MapState  stock:   business -> product value. `org.registered` restates every business, so the map is idempotent
 *                    under replay; supply runs and accrual add, a sell zeroes.
 * ListState sells:   the last `keep` sell outcomes, newest last; trimmed only on overflow.
 * ValueState meta:   leader, lobby, member count.
 */
class OrgBusinesses(keep: Int) extends StatefulProcessor[String, LsEv, OrgUpdate] {
  import implicits._
  @transient private var stock: MapState[String, Long] = _
  @transient private var sells: ListState[String] = _
  @transient private var meta: ValueState[OrgMeta] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit = {
    stock = getHandle.getMapState[String, Long]("stock", TTLConfig.NONE)
    sells = getHandle.getListState[String]("sells", TTLConfig.NONE)
    meta = getHandle.getValueState[OrgMeta]("meta", TTLConfig.NONE)
  }

  private def rank(t: String) = t match { case "org.registered" => 0; case "org.disbanded" => 9; case _ => 1 }

  override def handleInputRows(key: String, rows: Iterator[LsEv], timerValues: TimerValues): Iterator[OrgUpdate] = {
    val out = scala.collection.mutable.ListBuffer.empty[OrgUpdate]
    rows.toSeq.sortBy(ev => (ev.event_time.getTime, rank(ev.event_type))).foreach { ev =>
      val m = if (meta.exists()) meta.get() else OrgMeta(ev.agent_id, ev.lobby_id, 0)
      ev.event_type match {
        case "org.registered" =>
          meta.update(OrgMeta(ev.agent_id, ev.lobby_id, 0))
          Option(ev.businesses).getOrElse(Seq.empty).foreach(b => stock.updateValue(b.business, b.stock_value))
        case "org.member_joined" => meta.update(m.copy(members = m.members + 1))
        case "org.member_left"   => meta.update(m.copy(members = math.max(0, m.members - 1)))
        case "org.business_stocked" | "org.supply_run" =>
          ev.stock_value.foreach(v => stock.updateValue(ev.business, v))
        case "sell.started" =>
          stock.updateValue(ev.business, 0L)
        case "sell.completed" | "sell.destroyed" | "sell.expired" | "sell.abandoned" =>
          sells.appendValue(s"${ev.mission_id}:${ev.event_type.stripPrefix("sell.")}")
          val all = sells.get().toArray
          if (all.length > keep) sells.put(all.takeRight(keep))
        case "org.disbanded" =>
          meta.update(m.copy(members = 0))
        case _ =>
      }
      val entries = stock.iterator().toSeq
      val recent = sells.get().toSeq
      val mm = if (meta.exists()) meta.get() else m
      out += OrgUpdate(key, mm.leader_id, mm.lobby_id, ev.event_type, entries.size, entries.map(_._2).sum, mm.members,
        recent.size, recent.count(_.endsWith(":destroyed")), ev.event_time)
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[OrgUpdate] = Iterator.empty
}
