package nightcity.processors

import org.apache.spark.sql.streaming._
import nightcity.{Ev, FactionUpdate}

/**
 * Processor 4: what each faction holds and who it has been dealing with. Key = faction_id.
 *
 * MapState  territories: location_id -> influence. Point lookups and updates; the map is never read whole
 *                        except to count it, which is the one operation MapState is bad at (it iterates).
 * ListState relations:   the last `keep` relation descriptions, newest last. Appends are cheap; trimming
 *                        means rewriting the list, so it is done only when the list overflows.
 */
class FactionTerritory(keep: Int) extends StatefulProcessor[String, Ev, FactionUpdate] {
  import implicits._
  @transient private var territories: MapState[String, Double] = _
  @transient private var relations: ListState[String] = _
  @transient private var count: ValueState[Int] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit = {
    territories = getHandle.getMapState[String, Double]("territories", TTLConfig.NONE)
    relations = getHandle.getListState[String]("relations", TTLConfig.NONE)
    count = getHandle.getValueState[Int]("territory_count", TTLConfig.NONE) // cached size: counting a MapState is a scan
  }

  override def handleInputRows(key: String, rows: Iterator[Ev], timerValues: TimerValues): Iterator[FactionUpdate] = {
    val out = scala.collection.mutable.ListBuffer.empty[FactionUpdate]
    rows.toSeq.sortBy(_.event_time.getTime).foreach { ev =>
      ev.event_type match {
        case "faction.territory_gained" =>
          val isNew = !territories.containsKey(ev.location_id)
          territories.updateValue(ev.location_id, ev.influence.getOrElse(0.0))
          if (isNew) count.update((if (count.exists()) count.get() else 0) + 1)
        case "faction.territory_lost" =>
          if (territories.containsKey(ev.location_id)) {
            territories.removeKey(ev.location_id)
            count.update(count.get() - 1)
          }
        case "faction.relation_change" =>
          val text = Option(ev.description).getOrElse(Option(ev.involved_factions).map(_.mkString(" <> ")).getOrElse(""))
          relations.appendValue(text)
          val all = relations.get().toArray
          if (all.length > keep) relations.put(all.takeRight(keep))
        case _ =>
      }
      val recent = relations.get().length
      out += FactionUpdate(key, ev.event_type, if (count.exists()) count.get() else 0, ev.location_id, ev.influence,
        recent, ev.description, ev.event_time)
    }
    out.iterator
  }

  override def handleExpiredTimer(key: String, timerValues: TimerValues, info: ExpiredTimerInfo): Iterator[FactionUpdate] =
    Iterator.empty
}
