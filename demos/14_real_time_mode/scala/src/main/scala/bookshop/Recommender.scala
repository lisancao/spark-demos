package bookshop

import java.time.Duration

import org.apache.spark.broadcast.Broadcast
import org.apache.spark.sql.Encoders
import org.apache.spark.sql.streaming._

/** One shopper event, parsed from the `clicks` topic. */
case class Click(event_id: String, user_id: String, book_id: Long, action: String, ts: Long)

/** One recommended book. */
case class Pick(book_id: Long, title: String, aisle: String, score: Float)

/** What the recommender emits: fresh picks after a click, or a nudge after the shopper goes quiet. */
case class Recs(user_id: String, kind: String, event_id: String, ts: Long, clicks: Long, picks: Seq[Pick])

/** The embedded catalog, flattened so it broadcasts as a few arrays. Vectors are unit length. */
case class Catalog(ids: Array[Long], titles: Array[String], aisles: Array[String], vecs: Array[Float], dim: Int) {
  val size: Int = ids.length
  private val index: Map[Long, Int] = ids.zipWithIndex.toMap
  def row(bookId: Long): Option[Int] = index.get(bookId)
}

/**
 * Keeps a taste vector per shopper and re-ranks the whole catalog against it on every click.
 *
 * State (all expire after `ttl` without a click, so shoppers who leave stop costing memory):
 *   taste   ValueState[Array[Float]]  decayed, action-weighted sum of the clicked books' embeddings
 *   clicks  ValueState[Long]          how many distinct clicks fed the taste vector
 *   seen    MapState[Long, Long]      book_id -> last click time; seen books are never recommended
 *   events  MapState[String, Long]    event_id -> time; drops a retried event (same event_id)
 * Timer: one processing-time timer per shopper, `idleMs` after their last click; when it fires the
 * processor emits a "nudge" (the picks you'd email someone who wandered off).
 *
 * Real-time Mode calls handleInputRows once per row; micro-batch passes all of a key's rows for the
 * batch at once. The loop below handles both the same way.
 */
class Recommender(catalog: Broadcast[Catalog], ttl: Duration, idleMs: Long, k: Int = 5, decay: Float = 0.85f)
    extends StatefulProcessor[String, Click, Recs] {

  @transient private var taste: ValueState[Array[Float]] = _
  @transient private var clicks: ValueState[Long] = _
  @transient private var seen: MapState[Long, Long] = _
  @transient private var events: MapState[String, Long] = _

  override def init(outputMode: OutputMode, timeMode: TimeMode): Unit = {
    val h = getHandle
    val ttlConfig = TTLConfig(ttl)
    taste = h.getValueState("taste", Encoders.kryo[Array[Float]], ttlConfig)
    clicks = h.getValueState("clicks", Encoders.scalaLong, ttlConfig)
    seen = h.getMapState("seen", Encoders.scalaLong, Encoders.scalaLong, ttlConfig)
    events = h.getMapState("events", Encoders.STRING, Encoders.scalaLong, ttlConfig)
  }

  private def weight(action: String): Float = action match {
    case "purchase" => 5f
    case "cart" => 3f
    case _ => 1f
  }

  override def handleInputRows(user: String, rows: Iterator[Click], timers: TimerValues): Iterator[Recs] = {
    val cat = catalog.value
    val vec = if (taste.exists()) taste.get() else new Array[Float](cat.dim)
    var n = if (clicks.exists()) clicks.get() else 0L
    var last: Click = null
    rows.foreach { c =>
      if (!events.containsKey(c.event_id)) {          // a retried event is ignored
        events.updateValue(c.event_id, c.ts)
        cat.row(c.book_id).foreach { r =>
          val w = weight(c.action)
          var i = 0
          while (i < cat.dim) { vec(i) = vec(i) * decay + w * cat.vecs(r * cat.dim + i); i += 1 }
          seen.updateValue(c.book_id, c.ts)
          n += 1
          last = c
        }
      }
    }
    if (last == null) return Iterator.empty
    taste.update(vec)
    clicks.update(n)

    // One idle timer per shopper, pushed back on every click.
    getHandle.listTimers().foreach(t => getHandle.deleteTimer(t))
    getHandle.registerTimer(timers.getCurrentProcessingTimeInMs() + idleMs)

    Iterator.single(Recs(user, "picks", last.event_id, last.ts, n, topK(cat, vec)))
  }

  override def handleExpiredTimer(user: String, timers: TimerValues, info: ExpiredTimerInfo): Iterator[Recs] = {
    if (!taste.exists()) return Iterator.empty
    val n = if (clicks.exists()) clicks.get() else 0L
    Iterator.single(Recs(user, "nudge", "", info.getExpiryTimeInMs(), n, topK(catalog.value, taste.get())))
  }

  /** Cosine similarity against every book (vectors are unit length, so a dot product), seen books skipped. */
  private def topK(cat: Catalog, raw: Array[Float]): Seq[Pick] = {
    var norm = 0.0
    raw.foreach(x => norm += x * x)
    val q = if (norm > 0) raw.map(x => (x / math.sqrt(norm)).toFloat) else raw
    val best = new Array[Int](k)
    val bestScore = Array.fill(k)(Float.NegativeInfinity)
    var r = 0
    while (r < cat.size) {
      var s = 0f
      var i = 0
      val off = r * cat.dim
      while (i < cat.dim) { s += q(i) * cat.vecs(off + i); i += 1 }
      if (s > bestScore(k - 1) && !seen.containsKey(cat.ids(r))) {
        var j = k - 1
        while (j > 0 && bestScore(j - 1) < s) { bestScore(j) = bestScore(j - 1); best(j) = best(j - 1); j -= 1 }
        bestScore(j) = s; best(j) = r
      }
      r += 1
    }
    (0 until k).filter(j => bestScore(j) > Float.NegativeInfinity)
      .map(j => Pick(cat.ids(best(j)), cat.titles(best(j)), cat.aisles(best(j)), bestScore(j)))
  }
}
