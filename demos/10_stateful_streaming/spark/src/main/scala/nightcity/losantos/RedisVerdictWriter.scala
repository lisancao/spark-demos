package nightcity.losantos

import scala.jdk.CollectionConverters._
import org.apache.spark.sql.ForeachWriter
import redis.clients.jedis.{Jedis, StreamEntryID}
import redis.clients.jedis.params.XAddParams

/**
 * The serving path. One of the sinks Real-time Mode allows is `foreach`, one record at a time, so the board
 * writes straight into Redis from the query: a hash per lobby (the current verdict), a sorted set of lobbies by
 * safety (the leaderboard read), and a capped stream of every verdict with the source record's Kafka timestamp
 * and the write time (the latency and grading read). Writes are idempotent per lobby, which is what the docs ask
 * of a sink that may see a record twice after a failure.
 */
class RedisVerdictWriter(host: String, port: Int) extends ForeachWriter[LobbyVerdict] {
  @transient private var jedis: Jedis = _

  override def open(partitionId: Long, epochId: Long): Boolean = { jedis = new Jedis(host, port); true }

  override def process(v: LobbyVerdict): Unit = {
    val fields = Map(
      "lobby_id" -> v.lobby_id, "population" -> v.population.toString, "menaces" -> v.menaces.toString,
      "hostiles" -> v.hostiles.toString, "pvp_vehicles" -> v.pvp_vehicles.toString, "sells_recent" -> v.sells_recent.toString,
      "sells_destroyed_recent" -> v.sells_destroyed_recent.toString, "streak_kills_recent" -> v.streak_kills_recent.toString,
      "score" -> v.score.toString, "verdict" -> v.verdict, "weights" -> v.weights, "trigger" -> v.trigger,
      "at" -> v.at.getTime.toString, "sim_safety" -> v.sim_safety.map(_.toString).getOrElse(""),
      "sim_population" -> v.sim_population.map(_.toString).getOrElse(""), "source_kafka_ts" -> v.source_kafka_ts.toString,
      "written_at" -> System.currentTimeMillis().toString).asJava
    val p = jedis.pipelined()
    p.hset(s"lobby:${v.lobby_id}", fields)
    p.zadd("lobbies:safety", v.score, v.lobby_id)
    p.xadd("verdicts", XAddParams.xAddParams().id(StreamEntryID.NEW_ENTRY).maxLen(500000).approximateTrimming(), fields)
    p.sync()
  }

  override def close(errorOrNull: Throwable): Unit = if (jedis != null) jedis.close()
}
