# Night City, stateful: NPC simulation events through Spark 4.3 Structured Streaming

A runnable companion to a post on `transformWithState` and Real-Time Mode in Apache Spark 4.3.
The input is a headless cyberpunk city simulation (hundreds of NPCs with schedules, goals,
factions, cyberware, an economy, crime and combat) that emits one JSON event per thing that
happens. The processors treat each NPC, faction, combat and crime as a key with memory, timers
and a forgetting policy, which is what a game engine calls an entity and Spark calls state.

Inspired by the structure of AWS's
[real-time gaming leaderboard with Apache Flink](https://github.com/build-on-aws/real-time-gaming-leaderboard-apache-flink)
(ingestion, enrichment, leaderboard, dynamic config, late data and replay), rebuilt on Spark 4.3
with a simulation instead of a random generator.

## Layout

```
sim/                 Night City simulator (Python) + Kafka sink + replay tool
  cyberpunk_sim/     the sim: NPC agents, factions, economy, crime, combat, event schema
  rpg_engine/        action resolver, triggers, combat engine the sim drives
  replay.py          replay a recorded NDJSON log into Kafka with lateness and duplicates
  output/            NDJSON event logs written by live runs (replay input)
spark/               sbt project: processors and jobs (Scala 2.13, Spark 4.3.0)
bin/run.sh           spark-submit wrapper used by the `spark` compose service
docker-compose.yml   Kafka (KRaft), sim, replay, spark
data/                bronze Parquet, checkpoints, processor outputs (gitignored)
```

## Prerequisites

- Docker with Compose v2
- JDK 17+ and `sbt` on the host to build the Spark jar
- A Spark 4.3.0 image tagged `rc2-spark:base`. Until 4.3.0 is on Docker Hub, build one from the
  rc2 binary distribution: `cd spark-4.3.0-bin-hadoop3 && ./bin/docker-image-tool.sh -t base build`
  then `docker tag spark:base rc2-spark:base`. Jars resolve from the rc2 staging Maven repository
  (`orgapachespark-1538`); switch `build.sbt` and `bin/run.sh` to Central once 4.3.0 is released.

## Phase 1: events into Kafka, Kafka into bronze

```bash
docker compose up -d kafka
docker compose run --rm -e SIM_MAX_TICKS=300 sim        # live sim: Kafka + ./sim/output/*.ndjson
(cd spark && sbt package)                                # builds spark/target/scala-2.13/nightcity_2.13-*.jar
docker compose run --rm spark Bronze --once              # Kafka -> ./data/bronze/events (Parquet, by event family)
```

`docker compose up sim` runs the simulation forever at ten agent turns per 100 ms tick.

### Replaying a recording

Reproducible input for the stateful experiments. Timestamps are re-stamped to replay time, the
original is kept in `source_timestamp`. Late events are held back and delivered after a delay
with the timestamp of when they happened; duplicates are the same payload sent again a little
later, like a retried producer.

```bash
docker compose run --rm replay "/output/events_*.ndjson" \
  --tick-ms 100 --late-fraction 0.05 --late-delay-s 20 --dup-fraction 0.02 --loop
```

### Event envelope

Every event carries `event_id`, `event_type` (`family.action`), `timestamp`, `sim_tick`,
`sim_day`, `sim_time_phase`, and the id of the entity it is about (`agent_id`, `faction_id`,
`mission_id`, `location_id`, ...). The Kafka key is that entity id, so a consumer grouping by it
sees its events in order. Families: `agent`, `combat`, `crime`, `economy`, `faction`,
`relationship`, `world`, `mission`.

## Phases 2 to 6: the stateful part

```bash
(cd spark && sbt test)                                   # 9 TwsTester unit tests, no SparkSession
docker compose run --rm -e KAFKA_TOPIC=nightcity.replay3 -e MAX_OFFSETS_PER_TRIGGER=1000 -e WATERMARK="10 seconds" spark Primer --once
python3 bin/primer_report.py data/primer/10_seconds

docker compose run --rm -e KAFKA_TOPIC=nightcity.replay3 -e MAX_OFFSETS_PER_TRIGGER=1000 -e DRAIN_SECONDS=30 spark Processors presence --once
#   ... combat | ncpd | faction | risk (then risk2 to resume with the evolved state schema; both need
#   -e EXTRA_CONF="--conf spark.sql.streaming.stateStore.encodingFormat=avro")
python3 bin/processors_report.py

docker compose run --rm spark StateInspect /app/data/checkpoints/processors/risk risk        # state data source
docker compose run --rm -e RUN_TAG=combat-recover -e STOP_AFTER_BATCHES=15 spark Processors combat --once   # hard kill
docker compose run --rm -e RUN_TAG=combat-recover spark Processors combat --once                            # resume

# latency, same query under both triggers (start the query, then the replay at real pace)
docker compose run --rm -e KAFKA_TOPIC=nightcity.live.rtm -e OUT_TOPIC=nightcity.presence.rtm -e RUN_SECONDS=150 \
  -e SPARK_MASTER='local[12]' -e EXTRA_CONF="--conf spark.sql.shuffle.partitions=4" spark Latency rtm
docker compose run --rm replay "/output/events_*.ndjson" --topic nightcity.live.rtm --tick-ms 100 --max-ticks 1000 --loop
docker compose run --rm tools /app/bin/latency_report.py --bootstrap kafka:9092 --topic nightcity.presence.rtm --skip-first-s 15
```

Processors (`spark/src/main/scala/nightcity/processors`):

| | key | state | time | what it shows |
|---|---|---|---|---|
| `NpcPresence` | NPC | ValueState + TTL | ProcessingTime | forgetting without code; late rows do not move an NPC backwards |
| `CombatSessions` | attacker | ValueState + event-time timers | EventTime | sessionization; lost `ended` closed by timer once the watermark passes |
| `NcpdResponse` | location+crime | ValueState + processing-time timers | ProcessingTime | an absence (no response within the SLA) becomes an event |
| `FactionTerritory` | faction | MapState + ListState + cached count | None | composite state; a map keyed by location is idempotent under replay |
| `CyberpsychosisRisk` / `V2` | NPC | ValueState seeded from the roster | ProcessingTime | initial state; v2 adds a state field and resumes v1's checkpoint (Avro encoding) |
| `PresenceLatency` | NPC | ValueState + TTL | ProcessingTime | the latency probe, run under micro-batch and `Trigger.RealTime` |

Numbers from every run are in `NOTES.md`.
