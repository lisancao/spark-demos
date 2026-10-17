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

Two cities share the pipeline. Night City (phases 1 to 6) is the NPC simulation; Los Santos (phase 8) is a
GTA Online-style public lobby simulator whose events feed a live "is this lobby safe to sell in" board: five
`transformWithState` processors chained into a sixth, with scoring weights changed at runtime from a config topic.
Rockstar exposes no session telemetry, so the lobby and its players are simulated, and the event log is checked
for internal consistency (`python -m losantos.check`) before anything is measured. The map, the vehicles and
the weapons are the game's own, taken from [DurtyFree's GTA V data dumps](https://github.com/DurtyFree/gta-v-data-dumps)
(zone names and bounds, vehicle class, type, mounted weapons and top speed, weapon ids) via `bin/gta_world.py`,
which writes the small subset the sim uses to `sim/losantos/world_data.json`. Ground vehicles cross the map at
the dump's top speed, one tick being a minute of game time; flying vehicles get anywhere in a tick; the
checker verifies every move against that.

## Layout

```
sim/                 simulators (Python) + Kafka sink + replay tool
  cyberpunk_sim/     Night City: NPC agents, factions, economy, crime, combat, event schema
  rpg_engine/        action resolver, triggers, combat engine the Night City sim drives
  losantos/          Los Santos: public lobbies, grinders, griefers, tryhards, tourists; invariant checker;
                     world_data.json extracted from the GTA V data dumps (bin/gta_world.py)
  replay.py          replay a recorded NDJSON log into Kafka with lateness and duplicates
  output/            Night City NDJSON event logs written by live runs (replay input)
  output_losantos/   Los Santos logs plus players.jsonl (public roster), players_truth.jsonl (hidden archetypes), lobbies.json
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

## Phase 8: Los Santos and the lobby board

```bash
python3 -I bin/gta_world.py /path/to/gta-v-data-dumps      # optional: regenerate sim/losantos/world_data.json
docker compose build sim-ls
docker compose run --rm -e SIM_MAX_TICKS=600 sim-ls                     # live lobby sim -> losantos.events + ./sim/output_losantos
(cd sim && python3 -m losantos.check "output_losantos/events_*.ndjson")  # the log is airtight, or this exits 1
docker compose run --rm replay "/output_losantos/events_*.ndjson" --topic losantos.replay   --tick-ms 50 --late-fraction 0.05 --late-delay-s 20 --dup-fraction 0.02 --shuffle-within-tick --loop --max-ticks 1800

# one processor per query
docker compose run --rm -e KAFKA_TOPIC=losantos.replay -e MAX_OFFSETS_PER_TRIGGER=3000 -e DRAIN_SECONDS=30   -e EXTRA_CONF="--conf spark.sql.streaming.stateStore.encodingFormat=avro" spark LsProcessors presence --once
#   ... streaks (add -e GAP_MS=1000 -e WATERMARK="2 seconds") | sells | orgs | menace
# the chain: five processors feeding the lobby scorer in one query
docker compose run --rm -e KAFKA_TOPIC=losantos.replay -e MAX_OFFSETS_PER_TRIGGER=3000 -e DRAIN_SECONDS=30   -e GAP_MS=1000 -e WATERMARK="2 seconds" -e WINDOW_MS=2500   -e EXTRA_CONF="--conf spark.sql.streaming.stateStore.encodingFormat=avro" spark LobbyBoard --once
python3 bin/losantos_report.py          # per-processor summaries, graded against the hidden archetypes
python3 bin/losantos_grade.py           # board score vs the sim's own verdict at every snapshot
docker compose run --rm -e OPERATOR_ID=0 spark StateInspect /app/data/checkpoints/losantos/board present

# dynamic configuration, live: board unbounded on a live topic, then publish new weights
docker compose run --rm -e KAFKA_TOPIC=losantos.live -e CONFIG_TOPIC=losantos.config -e RUN_SECONDS=175   -e GAP_MS=2000 -e WATERMARK="4 seconds" -e WINDOW_MS=5000 -e RUN_TAG=board-live   -e EXTRA_CONF="--conf spark.sql.streaming.stateStore.encodingFormat=avro" spark LobbyBoard
docker compose run --rm -e SIM_MAX_TICKS=1400 -e SIM_KAFKA_TOPIC=losantos.live -e SIM_OUTPUT_DIR=/output/live sim-ls
docker compose run --rm tools /app/bin/publish_config.py --bootstrap kafka:9092 '{"menace": 40, "destroyed": 25}'

# latency of a union-free chain (menace -> lobby) under both triggers; Real-time Mode rejects the full chain
docker compose run --rm -e KAFKA_TOPIC=losantos.lat.rtm -e STARTING_OFFSETS=latest -e OUT_TOPIC=losantos.board.rtm   -e BOARD_INPUT=menace -e TRIGGER=rtm -e RUN_SECONDS=150 -e SPARK_MASTER='local[16]'   -e EXTRA_CONF="--conf spark.sql.streaming.stateStore.encodingFormat=avro --conf spark.sql.shuffle.partitions=4" spark LobbyBoard
```

Los Santos processors (`spark/src/main/scala/nightcity/losantos`):

| | key | state | time | what it shows |
|---|---|---|---|---|
| `LobbyPresence` | player | ValueState + TTL | ProcessingTime | lobby hops under lateness: a join into a new lobby wins over the late leave of the old one |
| `GriefStreaks` | attacker + lobby | ValueState + event-time timers | EventTime | sessionization with no end event; a gap shorter than the watermark delay is never observed |
| `SellMissions` | mission | ValueState + processing-time timers | ProcessingTime | the pipeline's patience vs the game's clock; terminals after a timeout are reported late, not dropped |
| `OrgBusinesses` | organisation | MapState + ListState + ValueState | None | registration restates stock, so the map is idempotent under replay |
| `MenaceScore` | player | ValueState seeded from the roster | ProcessingTime | the profile is the prior; seller kills move the level; duel kills are capped |
| `LobbySafety` | lobby | two MapStates + two ListStates + ValueState weights | ProcessingTime | the chained second stage; recency as a window of event time; weights patched from a config topic |

Numbers from every run are in `NOTES.md`.
