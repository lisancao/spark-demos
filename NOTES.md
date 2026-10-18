# Run notes

Numbers here come from runs in this repo. Each entry says which topic, which command, which commit.

## Phase 1: ingest (2026-10-17)

- Live sim, 300 ticks, 10 agents per tick, Kafka sink on: 9,719 events in `sim/output/events_20261017T130517_000001.ndjson`, 9,719 messages on `nightcity.events`.
- `Bronze --once`: 9,719 rows, 22 columns, 0 null `event_time`, 0 null `event_id`, 7 event families
  (agent 8,052; combat 763; economy 318; crime 233; faction 153; world 143; relationship 57).
- Replay check, 50 ticks at 20 ms, late 5% / 3 s, dup 2% / 1 s: 1,571 source events + 37 duplicates = 1,608 delivered, 82 of them late. Matches.

## Phase 2: primer (2026-10-17)

Input: `nightcity.replay3` = the 300-tick recording looped four times (1,200 ticks at 100 ms, about 2 minutes of event time),
5% of events held back 20 s, 2% duplicated 2 s later, order shuffled within a tick. 39,655 messages: 38,876 distinct event ids + 779 duplicates.

Run: `Primer --once` with `MAX_OFFSETS_PER_TRIGGER=1000` (40 micro-batches), `WATERMARK` at 30 s, 10 s, 3 s. Engine metrics from `progress.jsonl`.

Delivery delay (Kafka append time minus event time): p50 0.00 s, p90 0.00 s, p95 2.10 s, p99 20.10 s, max 20.10 s.
Share later than 1 s: 6.82%, later than 5 s: 4.86%, later than 20 s: 2.84%, later than 30 s: 0%.

| watermark | dedup output | dropped as late (dedup) | distinct ids never output | windows emitted | events in windows | dropped as late (windows) | windows still open at end |
|---|---|---|---|---|---|---|---|
| 30 s | 38,876 | 0 | 0 | 63 | 27,938 (70.45%) | 0 | 28 |
| 10 s | 37,188 | 1,716 | 1,688 | 77 | 33,429 (84.30%) | 101 | 14 |
| 3 s | 37,091 | 1,817 | 1,785 | 84 | 36,169 (91.21%) | 170 | 7 |

What this says:
- Every duplicate was caught at every watermark, because the dup delay (2 s) is inside even the 3 s watermark. `dropDuplicatesWithinWatermark` only needs to remember an id for as long as a duplicate can lag.
- The 20 s late events are the whole story. A 30 s watermark keeps them all, and pays with 28 windows (10 s each, per family) still unresolved when the stream ends. A 10 s watermark throws them away: 1,716 rows dropped at the dedup operator, which is the 4.86% that arrived more than 10 s late (some of those dropped rows were themselves duplicates: 1,716 dropped vs 1,688 ids never output).
- "Dropped as late" is far smaller at the window operator (101 vs 1,716) because the dedup upstream already removed most late rows. Operators in a chain each apply the watermark; what the first one drops, the second never sees.
- The window counts "still open at end" are not loss. They are results the engine will not emit until the watermark passes, i.e. latency, not correctness. With a 30 s watermark on a 10 s window, a result is at least 30 s stale.

## Phase 3: first three processors (2026-10-17)

Input: `nightcity.replay3` again (4 passes of the recording, 5% late by 20 s, 2% duplicated, shuffled within tick), 40 micro-batches of 1,000 Kafka rows.
Run: `Processors <name> --once` with `DRAIN_SECONDS=30`, RocksDB state store, changelog checkpointing, checkpoint format v2.
Ground truth per pass of the recording: 109 fights (109 started, 545 rounds, 109 ended; emitted rounds equal reported rounds in every fight), 132 crimes, 101 responses (15 of them `dispatched: false`), 31 crimes never answered.
Unit tests: `sbt test`, six TwsTester cases, no SparkSession.

Engine gotcha, worth its own paragraph: `Trigger.AvailableNow` never terminates a `transformWithState` query in `TimeMode.ProcessingTime`. Once the input is drained the engine keeps scheduling empty batches so timers and TTL can fire (the first run sat at 2,171 batches, 40 with data, before I killed it). In `TimeMode.EventTime` the opposite happens: with no input there is no batch at all, so an event-time timer waiting on the watermark will not fire until more data arrives. The bounded runs here use a short processing-time trigger and stop the query themselves after `DRAIN_SECONDS` of empty batches, in the trigger gap so no batch is interrupted.

| processor | mode | output rows | engine | what the numbers say |
|---|---|---|---|---|
| presence (ValueState + 60 s TTL) | ProcessingTime | 18,075 (70 first sightings, 18,005 moves) | 40 data batches, median 288 ms; 32 empty; 70 state rows at end | 70 NPCs act in a pass. Every row is a location change. Late rows never move an NPC backwards (unit-tested). |
| combat (ValueState + event-time timers, 10 s watermark, 5 s gap) | EventTime | 431 (424 ended, 7 timeout) | 143 rows dropped as late; 1 state row at end | 436 fights expected. The 143 dropped rows are the 20 s-late combat events (5% of 3,052). `rounds_seen` disagrees with the sim's `rounds` in 153 of 424 ended fights, which is the sum of rounds that were dropped as late and rounds that were duplicated: this processor does not dedup, and the post should show the fix is a `dropDuplicatesWithinWatermark` upstream, not more code in the processor. 7 fights closed by the timer because their `ended` was late and dropped; a handful were still open when the stream ended because event-time timers need the watermark to move. |
| ncpd (ValueState + processing-time timers, 10 s SLA) | ProcessingTime | 567 (326 answered, 57 declined, 30 unanswered, 127 superseded, 27 orphan responses) | 28 state rows at end | 528 crimes, 404 responses expected. 27 orphans are responses whose crime arrived 20 s later (5% late). 127 superseded: the same location+crime key recurs across the four replay passes, 30 s apart in event time but about 4 s apart in processing time because the replay is compressed into 40 fast batches, so the SLA timer (processing time) had not fired yet. Processing-time timers measure the pipeline's clock, not the world's; a replay at real pace or an event-time SLA removes this. |

Same-timestamp ordering bug, found by these numbers: the sim resolves a whole fight, and a crime plus its response, inside one tick, so rows share an event time. Sorting by time alone put `ended` before its rounds and responses before their crimes (first run: 109 orphan responses, round counts right in only 233 fights). Fix: a per-type rank in the sort key. Both cases are now unit tests.

## Phase 4: composite state, initial state, schema evolution (2026-10-17)

Input: `nightcity.replay3`, now with a fifth pass appended (`--tick-offset 1200`, seed 11), 49,556 messages.

**faction** (MapState territories, ListState last 10 relations, ValueState cached count; `TimeMode.None`): 777 rows, 6 factions, 65 s.
Territory counts at the end equal the distinct locations each faction gains in one pass of the recording (los_nakamura 13, maxtac 5, mbekis 5, subnet_drift 4, okonkwo 2, santos 2) although the stream replays those gains five times: a MapState keyed by location is idempotent by construction. `relations` is capped at 10 by rewriting the list on overflow; mbekis_circle has 0 because the sim never emits a relation event for it.

**risk v1** (ValueState[Risk] seeded from the 70-row roster via `StatefulProcessorWithInitialState`, Avro state encoding, 4 passes): 534 rows, 14 NPCs ever emit (only attackers and the warned), 57 s. Top score kuro_the_31th: chrome 28, 138 attacks, 28 defeats, score 337, critical. Levels across rows: 333 critical, 87 elevated, 114 stable.

**risk v2 resuming v1's checkpoint** (state case class gains `last_warning_at: Option[Timestamp]`, same variable name): started at batch 41, processed the fifth pass in 10 batches, 131 new rows, no errors, 27 s. Required `spark.sql.streaming.stateStore.encodingFormat=avro` from the first run; UnsafeRow encoding would have failed the restart. The roster initial state is not re-applied on resume (it is a batch-0 thing), which is the behaviour you want.

Drain logic, third revision: "drained" now means DRAIN_SECONDS since the last batch that carried input, checked against the clock. `TimeMode.None` and `EventTime` queries run no batch at all without input, so waiting for an empty progress event never ends.

## Phase 5: looking inside, and recovery (2026-10-17)

`StateInspect <checkpoint> <stateVarName|timers>` reads a checkpoint with the state data source (`format("statestore")`, `stateVarName`, `readRegisteredTimers`, `flattenCollectionTypes`).

- **risk** after the v2 resume: 70 state rows (one per roster NPC), the value struct now has `last_warning_at`, set on the 4 NPCs with warnings and null elsewhere; 56 rows are roster seeds that never saw an event. Top attackers in state: sergeant_okafor 214 attacks, kuro_the_31th 172 attacks / 35 defeats, detective_vasquez 76. These are five replay passes of the same recording, so the counts are 5x the recording's.
- **faction** `territories` MapState: 31 rows, flattened to (faction, location, influence), the same per-faction counts as the processor's own cached count.
- **ncpd** timers at the end of the run: 0. Every SLA timer had either been cancelled by a response or fired during the drain.

Recovery: `STOP_AFTER_BATCHES=15` makes the driver exit without stopping the query (a hard kill mid-flight). On the five-pass topic the killed run had written 153 rows; the resumed run continued from the checkpoint and finished in 51 s. The resumed output and an uninterrupted run on the same topic are the same 537-row multiset (attacker, started_at, ended_at, rounds_seen, closed_by). Parquet sink plus Kafka offsets in the offset log plus RocksDB state plus changelog checkpointing: exactly-once, observed rather than asserted.

## Phase 6: micro-batch vs Real-time Mode (2026-10-17)

Same query both times: Kafka (4 partitions) -> `Ev.parse` -> filter `agent.*` -> `groupByKey(agent_id)` -> `transformWithState(PresenceLatency, ProcessingTime, Update)` -> Kafka sink, update mode, reading from the latest offsets so only live arrivals count. Input: the recording replayed at real pace (100 ms ticks, about 215 events/s, 32,318 events over 100 s) into a fresh topic after the query was up. Latency = output record's Kafka timestamp minus the input record's Kafka timestamp (`source_kafka_ts` carried through the processor), first 15 s of output skipped. `local[8]` for micro-batch, `local[12]` for Real-time (4 reader tasks + 4 stateful tasks held for the whole batch, plus headroom), `spark.sql.shuffle.partitions=4`, RocksDB with changelog checkpointing and checkpoint format v2 in both.

| trigger | output records | p50 | p90 | p99 | max | engine |
|---|---|---|---|---|---|---|
| `ProcessingTime("0 seconds")` (micro-batch, as fast as it can) | 22,702 | 228 ms | 331 ms | 431 ms | 787 ms | 519 batches with input in 150 s, triggerExecution p50 178 ms, max 721 ms |
| `RealTime("30 seconds")` | 22,799 | 44 ms | 56 ms | 61 ms | 225 ms | 3 long batches of 30 s; records flowed through continuously inside them |

Same code, same state store, same machine: the micro-batch floor here is the batch itself (plan, schedule, read, shuffle, commit, around 180 ms each), and Real-time Mode removes it by keeping the reader and the stateful operator alive and streaming the shuffle between them. The 30 s in the Real-time trigger is the checkpoint interval, not the latency.

Two things that bit on the way: `maxOffsetsPerTrigger` is rejected in Real-time Mode (there is no trigger-sized batch to cap), and stopping a Real-time query logs "connection to streaming shuffle writer closed before termination" for every long-running task it interrupts; that is the stop, not a failure.

## Phase 8: Los Santos, the lobby board (2026-10-17)

A second simulated city on the same envelope: GTA Online-style public lobbies (`sim/losantos`), 150 players with a
public profile (rank, career K/D, hours) and a hidden archetype (grinder, griefer, tryhard, tourist) that drives what
they do. Eight lobbies of up to 24. Grinders register an organisation, accrue product and sell it along a route;
griefers hunt the sell blips on Oppressors; tryhards hunt griefers; tourists wander, steal cars and rage quit.

The map, the vehicles and the weapons are the game's own: `bin/gta_world.py` extracts 87 named zones with centroids,
35 vehicles (class, type, mounted weapons, top speed) and 12 on-foot weapons from
[DurtyFree's GTA V data dumps](https://github.com/DurtyFree/gta-v-data-dumps) into `sim/losantos/world_data.json`.
A ground vehicle crosses the map at the dump's top speed with a tick as a minute of game time (an Insurgent at
35 m/s covers about 2.1 km a tick; Paleto Bay to Vespucci is 7.4 km); planes, helicopters and the two hovering
vehicles get anywhere in a tick. The business table and every behaviour number are the sim's; the game does not
publish those. Rockstar exposes no session telemetry.

The question the board answers: is this lobby safe to sell in right now.

**Airtight:** `python -m losantos.check` rebuilds the lobby world from the event log alone and checks every invariant:
kills between two players in the same lobby, neither passive; every sell, bounty, wanted level and organisation opens
before it closes and closes exactly once; nobody acts out of session; snapshots match the membership the events imply;
stock accounting balances (`org.registered` restates every business so a mid-stream consumer has a baseline); and every
`player.move` covers at most one tick of the stated vehicle's top speed, with the distance it carries matching the map.
Live recording, 600 ticks at 100 ms, seed 42: 42,117 events, all invariants hold. Mix: player.move 31,239,
org.business_stocked 2,660, org.supply_run 1,666, combat.kill 842, wanted.gained/cleared 762 each, sell.started 434
(completed 302, destroyed 129, abandoned 3), session.join/leave 471 each, bounties placed 126. Roster: 65 tourists,
55 grinders, 16 griefers, 14 tryhards. Each `lobby.snapshot` (every 25 ticks) carries `sim_safety`, the sim's own
verdict computed from the hidden archetypes, which the stream never sees and is graded against.

Replay for the stateful runs: `losantos.replay` = the recording looped three times at 50 ms per tick (1,800 ticks), 5% held back 20 s,
2% duplicated 2 s later, shuffled within a tick: 128,550 messages, 6,275 of them late, 2,562 duplicates.
Runs: `LsProcessors <name> --once`, 43 micro-batches of 3,000 rows, RocksDB, changelog checkpointing, checkpoint v2, Avro encoding.
Unit tests: `sbt test`, 16 TwsTester cases across both cities, no SparkSession.

| processor | key | state | time | output rows | what the numbers say |
|---|---|---|---|---|---|
| `LobbyPresence` (ValueState + 120 s TTL) | player | lobby, zone, passive, vehicle | ProcessingTime | 90,123 (joined 1,288, left 1,158, hopped 67, moved 87,002, passive on/off 251/206, vehicle 151) | The 67 hops are joins that arrived before the leave of the previous lobby (5% late by 20 s); the join wins and the late leave is ignored. 130 players in state at the end. |
| `GriefStreaks` (ValueState + event-time timers, 1 s gap) | attacker + lobby | kills, who they were, flying | EventTime | 2 s watermark: 143 streaks, 36 closed by the timer, 107 by `session.leave`, 180 kills dropped late, 25 open at end. 10 s watermark: 115 streaks, 4 by the timer, 111 by leave, 30 open at end. | Below: the gap an event-time timer can see is bounded by the watermark delay. 1,985 kills in closed streaks, 313 of them sellers and 283 civilians; all 313 seller kills are in griefers' streaks, none in tryhards'. |
| `SellMissions` (ValueState + processing-time timers, 15 s SLA) | mission | seller, value, deliveries | ProcessingTime | 1,357 (completed 868, destroyed 368, abandoned 6, timeout 26, late_completed 60, late_destroyed 29) | $89,750,680 of product destroyed across three passes. The 89 `late_*` rows are terminals whose `started` was held back 20 s (5% of 1,302 starts is 65) plus the terminals of the 26 sells the 15 s pipeline timer had already given up on. |
| `OrgBusinesses` (MapState stock + ListState sells + ValueState meta) | organisation | business -> stock, recent outcomes | None | 20,162 rows, 117 organisations, 497 state rows | `org.registered` restates stock, so the map is idempotent under replay (unit-tested); $81,208,068 of product sitting in businesses at the end. |
| `MenaceScore` (ValueState seeded from the 150-row roster) | player | profile + session counters | ProcessingTime | 1,950 rows | Peak level reached vs hidden archetype: griefers 16/16 menace; tryhards 3 menace, 11 hostile; grinders 55/55 civilian; tourists 65/65 civilian. The five highest scores are all griefers (OppressorDad2004 651, TrevorRider2004 636, PassiveWizardjr 428; 11 to 18 sellers killed each across three passes). The profile alone puts a 3.5 K/D player at 14 points, civilian; it takes a seller kill to reach hostile and two to reach menace. Duel kills are capped at 10 so tryhards who fight griefers all night land on hostile. |

**Event-time timers and the watermark (the streak finding).** The recording has, per pass, 230 inter-kill gaps longer than 1 s at
replay pace, 99 longer than 2 s, 44 longer than 3 s and 13 longer than 5 s. With a 1 s gap the timer closed 4 streaks under a 10 s
watermark and 36 under a 2 s one. The arithmetic: a timer registered at `last_kill + gap` only fires when the watermark passes it, the
watermark trails the newest event by the delay, and any kill that arrives before then rearms the timer. A streak therefore closes only
after a silence of at least gap + watermark delay + the batch that carries the next kill, which is 3 to 5 s under the 2 s watermark and
11 to 13 s under the 10 s one; the recording has 13 silences longer than 5 s per pass and almost none longer than 11 s. Night City's
combat processor never hit this because fights have an explicit `ended`; a streak has no end event, only an absence, and an absence
shorter than the watermark delay is invisible to event time. Processing-time timers would see it, at the cost of replay determinism
(see the recovery experiment). The real map sharpened this against the first, flat-map version of the sim: griefers now fly across the
county between kills, so the gaps are longer and the timer fires nine times as often at the same watermark.

**The board** (`LobbyBoard --once`): five `transformWithState` operators feeding a sixth in one query. Presence, streaks, sells and menace
outputs are reduced to one `Signal` shape, unioned with the sim's snapshots (pass-through, for grading) and with config rows fanned out to
every lobby, keyed by lobby, and scored by `LobbySafety` (MapState of present players with their menace level and vehicle, MapState of known
players kept across leaves, ListState of sell outcomes and streak kills pruned to a window of event time, ValueState of weights).
Score = 100 minus 12 per menace present, 4 per hostile, 6 per pvp vehicle, 15 per destroyed sell in the window, 1 per non-hunter kill
in a closed streak in the window; sell at 70, risky at 40, hop below. Window 2.5 s of event time at replay pace, which is 50 ticks.
6,773 verdict rows (hop 3,009, risky 2,454, sell 1,310), 43 batches, median 861 ms against about 285 ms for any single processor; state
rows at the end 522 (board) / 130 (presence) / 25 (streaks) / 0 (sells) / 150 (menace). `numInputRows` is 14,985 per batch, not 3,000:
each branch of the union reads the Kafka source itself, five times.

Grading against `sim_safety` on the 592 snapshot-triggered rows (three passes of 192 snapshots, plus duplicates, since the board does not
dedup): Pearson r 0.733, verdict agreement 330/592 = 55.7%, sold into a lobby the sim calls hop 8 times. Confusion matrix (sim verdict in
rows, board in columns):

| sim \ board | sell | risky | hop |
|---|---|---|---|
| sell | 62 | 89 | 12 |
| risky | 21 | 100 | 96 |
| hop | 8 | 36 | 168 |

The board has no geography, and on the real map that is the gap: a griefer hunting in Paleto Bay is charged against a seller in Vespucci
exactly as if he were overhead, while the sim's verdict only counts hunters as a lobby-wide fact too, so the disagreement is mostly about
timing (the board's window versus the sim's 25-tick one) and tryhards (3 points to the sim, a hostile or a menace to the board).

The weights are an opinion, and they were chosen by sweeping a grid offline against the same replay (`losantos_grade.py` logic over the
verdict rows' components, which is what a config row would do live). The sweep is the argument for a config topic:

| weights (menace, hostile, pvp vehicle, destroyed, streak kill) | r | agreement | sold into a hop lobby |
|---|---|---|---|
| 18, 4, 6, 10, 3 (first version) | 0.635 | 53.4% | 6 |
| 12, 4, 6, 15, 1 (shipped) | 0.733 | 55.7% | 8 |
| 12, 2, 4, 15, 1 | 0.714 | 67.4% | 18 |
| 8, 2, 6, 15, 1 | 0.720 | 66.2% | 16 |

Agreement and bad sells pull against each other: the weight sets that agree with the sim most often are the ones that tell a seller to
sell into a griefed lobby three times as often. The shipped set takes correlation and few bad sells over raw agreement. These were tuned on
the replay they are graded on, so the number to trust is the live one below.

**Two engine gotchas from the board.** A `ListState` cannot be written as an empty list: pruning everything out of the window and calling
`put` raised `ILLEGAL_STATE_STORE_VALUE.EMPTY_LIST_VALUE` and aborted the batch (the first clean-looking run stopped at batch 25 with an
`InterruptedException` in the changelog commit, which was the symptom, not the cause); the fix is `clear()` when nothing is left. And the
bounded-run stop now also waits for `status.isTriggerActive` to be false, so a long batch is never interrupted.

**State data source on a multi-operator query:** `StateInspect` needs `operatorId`. Operator 0 is the board and its `present` map reads
back as 130 (lobby, player) rows with level, score and pvp_vehicle, the same 130 players the presence operator holds and the same
populations the last verdicts carry. Asking operator 1 to 4
for `present` fails with `STDS_INVALID_OPTION_VALUE`: "State variable present is not defined for the transformWithState operator", which is
the error you want.

**Recovery:** `STOP_AFTER_BATCHES=15` (2,672 rows written), resume from the checkpoint, finish at batch 73 (the resumed run's drain was
slower): 6,794 rows against 6,773 uninterrupted, 173 rows in the symmetric difference, 95 of them sell-triggered and 32 menace-triggered.
Not identical, and the reason is the clock: `SellMissions` runs processing-time SLA timers, the resumed pipeline's clock is later than the
killed one's, so a different set of sells timed out, and each extra timeout produced a `timeout` row plus a `late_*` row when the real
terminal arrived; every verdict row after one of those carries a different `sells_recent`, which is the rest of the difference. Night City's
combat recovery was identical because its timers are event time. Event-time state replays exactly; processing-time state replays
approximately.

**Real-time Mode:** `TRIGGER=rtm` on the full chain is rejected at analysis with
`STREAMING_REAL_TIME_MODE.STATEFUL_OPERATORS_BEFORE_UNION_NOT_SUPPORTED`. A union-free chain (menace -> lobby, `BOARD_INPUT=menace`) was
then rejected by the operator allowlist: a typed `.map` into the second `groupByKey` plans as `AppendColumnsWithObjectExec`, and a `select`
in between does not help because the optimizer removes the serialize/deserialize pair. Building the second stage's input with column
expressions keeps the child row-based (`AppendColumnsExec`, which is allowlisted). That chain is what the latency comparison below runs.

**Dynamic configuration, live:** sim at real pace (1,400 ticks at 100 ms, topic `losantos.live`), board unbounded (`RUN_SECONDS=175`,
window 5 s, `CONFIG_TOPIC=losantos.config`). At 19:24:27 UTC one row was published: `{"menace": 30, "destroyed": 25}`. The first verdict
under the new weights carries the config record's Kafka timestamp, 19:24:27.425; eight config-triggered rows, one per lobby, no restart.
Before the row: 2,562 verdicts (sell 770, risky 508, hop 1,284), mean safety 41.3. After: 2,257 (sell 80, risky 419, hop 1,758), mean 18.4.
Lobby 02 at the switch: 1 menace, 1 pvp vehicle, nothing destroyed, 82 and sell before, 64 and risky after, on the same facts. A config row
is a patch: keys left out keep their current value (the first attempt reset the window to the default, because `parse` fell back to the
shipped defaults rather than the running weights). Live grading on the 448 snapshots of that run, with weights that had not seen the data:
r 0.783, agreement 61.2%, sold into a hop lobby once; on the 224 snapshots before the config row alone, agreement 73.7%.

**Latency, micro-batch vs Real-time Mode, two-stage chain (menace -> lobby):** the recording replayed once at real pace (100 ms ticks,
42,117 events over 60 s) into a fresh 4-partition topic after the query was up, output to Kafka, latency = output record's Kafka timestamp
minus the input record's (carried through both processors), first 15 s skipped. `local[16]` for Real-time Mode (4 reader tasks + 4
stateful tasks per stage held for the whole batch), `spark.sql.shuffle.partitions=4`, RocksDB + changelog checkpointing + Avro in all three.

| trigger | output records | p50 | p90 | p99 | max | engine |
|---|---|---|---|---|---|---|
| `ProcessingTime("0 seconds")` | 360 | 399 ms | 578 ms | 709 ms | 711 ms | 197 batches with input, triggerExecution p50 297 ms |
| `RealTime("20 seconds")` | 637 | 65 ms | 191 ms | 692 ms | 699 ms | 4 batches with input, each 20.2 s |
| `RealTime("60 seconds")` | 361 | 60 ms | 78 ms | 254 ms | 356 ms | 2 batches with input, each 60.2 s |

Two stateful stages under micro-batch cost about two batches (Night City's one stage was p50 228 ms on this machine). Real-time Mode
pipelines both stages through the streaming shuffle and the second stage adds milliseconds. The tail is the batch boundary: every
`RealTime` batch ends with a commit (RocksDB snapshot upload, offset log), and records that arrive across it wait for the next batch's
tasks to come up, which is the 20 s run's p99 of 692 ms; with 60 s batches the boundary comes a third as often and p99 drops to 254 ms.
The batch length in a Real-time trigger is the checkpoint interval, and it sets the tail, not the median.

Two Kafka things on the way: deleting and immediately recreating an output topic put the first Real-time run's producer into
`NotLeaderOrFollowerException` retries and a later one into `UnknownTopicOrPartitionException`; give the broker a few seconds after a
delete. And every stop of a Real-time query logs an aborted `KafkaStreamingWrite` epoch with "Flush interrupted": that is the stop.

## Phase 9: the board under Real-time Mode, served from Redis (2026-10-18)

The micro-batch chain in phase 8 (five processors unioned into a sixth) is rejected by Real-time Mode at analysis:
`STATEFUL_OPERATORS_BEFORE_UNION_NOT_SUPPORTED`. The rules that shape what it will run, all from the 4.3 docs and
confirmed here: update output mode only; a sink that is Kafka, foreach, console or memory; a batch duration of at
least 5 s (it is the checkpoint interval, not the latency); stateful operators may be chained but nothing may be
unioned after one; every physical operator must be on an allowlist; `TimeMode.None`, `ProcessingTime` and
`EventTime` are all allowed, with the event-time watermark fixed for the whole long batch; `handleInputRows` is called
once per row; the JVM API only, no PySpark processor.

So the board became two chained stages. Everything in Los Santos keys by player (presence, menace, streaks by
attacker, sells by seller), so stage one is a single `PlayerSignals` processor keyed by player, seeded from the roster
as initial state, emitting the one `Signal` shape; stage two is `LobbySafety` unchanged. Config rows from the config
topic are turned into `board.config` events in the event stream's own shape (one per lobby, via `explode`) and
unioned in *before* the first stateful operator; the sim's snapshots ride through stage one keyed by lobby. The sink
is a `ForeachWriter` into Redis (jedis, resolved at run time): a hash per lobby, a sorted set of lobbies by safety, a
capped stream of every verdict with the source record's Kafka timestamp and the write time. That is the serving path
and the latency probe in one. The same query runs under a micro-batch trigger for the comparison.

Three things the engine said on the way:
- `groupByKey` straight on a `transformWithState` output plans as `AppendColumnsWithObjectExec`, which is not on
  the allowlist; the optimizer fuses the serializer into it. An identity projection in between is removed by the
  optimizer and the fusion happens anyway. A projection with one non-trivial expression (`coalesce(lobby_id, "")`)
  survives, and the plan shows plain `AppendColumns` at every stage (`EXPLAIN=1` prints it).
- A config row synthesised with `lit(null)` for every event field it does not set hit `NOT_NULL_ASSERT_VIOLATION`
  the moment the first one arrived, 110 s into the run, because `sim_tick` is a bare `Long` in the event case class.
  The first live run died at exactly the config publish time for that reason.
- Both the Redis hash and the sorted set are idempotent per lobby, which is what the docs ask of a sink that may see a
  record again after a failure; the stream is append-only and capped.

**Live, Real-time Mode, Redis sink** (sim at real pace, 1,400 ticks, 8 lobbies of 24, `RealTime("20 seconds")`,
window 5 s, streak gap 2 s, `local[16]`, 4 partitions): 10 batches (a 2.8 s bootstrap batch that loads the roster,
then 20.2 s each with about 14,000 input rows), 590 and 150 state rows in the two operators at the end.

| | value |
|---|---|
| verdicts written to Redis | 3,914 after the first 15 s |
| latency, Kafka append of the input record to the Redis write of the verdict | p50 69 ms, p90 102 ms, p99 119 ms, max 311 ms |
| grading against `sim_safety`, 448 snapshots | r 0.725, agreement 57.8%, sold into a hop lobby 1 |

The board five seconds after the config row went out (`board_report.py board`), every lobby from the sorted set:

```
ls_public_04    58.0 risky  pop 15  menaces 1  hostiles 0  bikes 2  destroyed 0/4  last: left:p012
ls_public_02    47.0 risky  pop 18  menaces 1  hostiles 1  bikes 3  destroyed 0/7  last: sell:p014
ls_public_03    12.0 hop    pop 14  menaces 2  hostiles 1  bikes 4  destroyed 0/1  last: streak:
ls_public_08     0.0 hop    pop 14  menaces 3  hostiles 0  bikes 4  destroyed 1/2  last: streak:
...
```

and the one-line read a seller wants, from a run earlier the same afternoon:
`ls_public_03: HOP (safety 23). 2 known griefers in session; 5 armed vehicles out; 1 sell destroyed just now.`
After the sim's shutdown (everyone leaves) six of eight lobbies read `sell` with population 0; lobby 05 still read
`hop` at 21 because three of its last seven sells were destroyed inside the window. An empty lobby with a fresh
graveyard is still a lobby the board remembers.

**Dynamic configuration, live:** `{"menace": 30, "destroyed": 25}` published at 12:55:15.499 UTC; the first verdict
under the new weights carries the config record's Kafka timestamp 12:55:15.889, so the rule changed inside 400 ms of
the publish, with eight config-triggered verdicts (one per lobby) and no restart. Before the row: 2,624 verdicts
(sell 543, risky 701, hop 1,380), mean safety 40.6. After: 2,624 (sell 211, risky 191, hop 2,222), mean 13.5.
Lobby 04 at the switch, one menace, two armed vehicles, one destroyed sell: 28 before, 3 after.

**Same query, two triggers** (Kafka sink, the recording replayed once at real pace into a fresh 4-partition topic
after the query was up, latency = output record's Kafka timestamp minus the input record's, rows without a source
record such as timer-fired and pass-through signals excluded, first 15 s skipped, 1,495 records each):

| trigger | p50 | p90 | p99 | max | engine |
|---|---|---|---|---|---|
| `ProcessingTime("0 seconds")` | 433 ms | 854 ms | 868 ms | 869 ms | 186 batches with input, triggerExecution p50 300 ms |
| `RealTime("60 seconds")` | 68 ms | 92 ms | 102 ms | 357 ms | 2 long batches |

Two stateful stages under micro-batch cost about two batches; Night City's single stage on this machine was p50
228 ms. Real-time Mode streams the shuffle between the stages and the second stage costs milliseconds.

**Late data under Real-time Mode:** the recording replayed once at real pace with 5% of events held back 20 s, 2%
duplicated 2 s later and the order shuffled within a tick (42,974 messages), Redis sink, 20 s batches. Grading on the
196 snapshots: r 0.744, agreement 62.8%, sold into a hop lobby 6. Latency p50 46 ms, p90 81 ms, p99 91 ms, max 318 ms.
The stage-one streak gap and sell patience are processing-time timers here: an event-time watermark in Real-time Mode
is fixed for the whole batch, so a 2 s gap in event time could only be observed at a 20 s boundary. That is the same
trade the recovery experiment in phase 8 priced: processing time sees short gaps and replays approximately; event
time replays exactly and cannot see a gap shorter than the watermark delay.

**Micro-batch baseline on the same two-stage chain** (`--once` over the three-pass `losantos.replay`, 43 batches of
3,000): r 0.764, agreement 61.1%, sold into a hop lobby 7; median batch 413 ms against 861 ms for the five-way union
chain in phase 8 (one Kafka read instead of five), state rows 526 and 280.

The Kafka latency report originally counted every output record; rows produced by a timer or a pass-through signal
carry `source_kafka_ts` 0 and turned the p90 into an epoch. They are excluded now.
