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
they do. Six lobbies of up to 30. Grinders register an organisation, accrue product and sell it; griefers hunt sells on
Oppressors; tryhards hunt griefers; tourists wander, steal cars and rage quit. Nothing comes from the game (Rockstar
exposes no session telemetry; the old Social Club profile page is what the roster fields are modelled on).

The question the board answers: is this lobby safe to sell in right now.

**Airtight:** `python -m losantos.check` rebuilds the lobby world from the event log alone and checks every invariant
(kills between two players in the same lobby, neither passive; every sell, bounty, wanted level and organisation opens
before it closes and closes exactly once; nobody acts out of session; snapshots match the membership the events imply;
stock accounting balances, with `org.registered` restating every business so a mid-stream consumer has a baseline).
Live recording, 600 ticks at 100 ms, seed 42: 38,399 events, all invariants hold. Mix: player.move 26,269, org.business_stocked 2,955,
org.supply_run 1,914, combat.kill 1,139, wanted.gained/cleared 789 each, sell.started 502 (completed 336, destroyed 163, abandoned 3),
session.join/leave 476 each, bounties placed 171. Each `lobby.snapshot` (every 25 ticks) carries `sim_safety`, the sim's own verdict
computed from the hidden archetypes, which the stream never sees and is graded against.

Replay for the stateful runs: `losantos.replay` = the recording looped three times at 50 ms per tick (1,800 ticks), 5% held back 20 s,
2% duplicated 2 s later, shuffled within a tick: 117,152 messages, 5,644 of them late, 2,320 duplicates.
Runs: `LsProcessors <name> --once`, 40 micro-batches of 3,000 rows, RocksDB, changelog checkpointing, checkpoint v2, Avro encoding.
Unit tests: `sbt test`, 16 TwsTester cases across both cities (7 for Los Santos), no SparkSession.

| processor | key | state | time | output rows | what the numbers say |
|---|---|---|---|---|---|
| `LobbyPresence` (ValueState + 120 s TTL) | player | lobby, area, passive, vehicle | ProcessingTime | 75,175 (joined 1,318, left 1,189, hopped 44, moved 71,775, passive on/off 432/351, vehicle 66) | 44 hops are joins that arrived before the leave of the previous lobby (5% late by 20 s); the join wins and the late leave is ignored. 129 players in state at the end. |
| `GriefStreaks` (ValueState + event-time timers, 1 s gap) | attacker + lobby | kills, who they were, flying | EventTime | 10 s watermark: 54 streaks, every one closed by `session.leave`, 0 by timer, 166 kills dropped late, 23 open at end. 2 s watermark: 59 streaks, 5 closed by the timer. | See below: an event-time gap shorter than the watermark delay is never observed. |
| `SellMissions` (ValueState + processing-time timers, 15 s SLA) | mission | seller, value, deliveries | ProcessingTime | 1,562 (completed 953, destroyed 466, abandoned 6, timeout 32, late_completed 73, late_destroyed 32) | $153,329,495 of product destroyed across three passes. The 105 `late_*` rows are terminals whose `started` was held back 20 s (5% of 1,506 starts is 75) plus the terminals of the 32 sells the 15 s pipeline timer had already given up on. |
| `OrgBusinesses` (MapState stock + ListState sells + ValueState meta) | organisation | business -> stock, recent outcomes | None | 22,360 rows, 139 organisations, 578 state rows | `org.registered` restates stock, so the map is idempotent under replay (unit-tested); $94,970,510 of product sitting in businesses at the end. |
| `MenaceScore` (ValueState seeded from the 150-row roster) | player | profile + session counters | ProcessingTime | 2,040 rows | Peak level reached vs hidden archetype: griefers 9/9 menace; tryhards 5 menace, 9 hostile; grinders 64/64 civilian; tourists 63/63 civilian. The five highest scores are all griefers (SharkPigeon_YT, NightclubSeagull, GhostWizard_TTV, TurboCivilian69, LesterPigeon69; 14 to 17 sellers killed each). The profile alone puts a 3.5 K/D player at 14 points, civilian; it takes a seller kill to reach hostile and two to reach menace. Duel kills are capped at 10 so tryhards who fight griefers all night land on hostile, not menace. |

**Event-time timers and the watermark (the streak finding).** The recording has, per pass, 180 inter-kill gaps longer than 1 s at replay pace,
20 longer than 3 s and 5 longer than 5 s. With a 1 s gap and a 10 s watermark the timer never fired once (`numExpiredTimers` 0 in every
batch); with a 2 s watermark it fired five times. The arithmetic: a timer registered at `last_kill + gap` only fires when the watermark
passes it, the watermark trails the newest event by the delay, and any kill that arrives before then rearms the timer. A streak therefore
closes only after a silence of at least gap + watermark delay + the batch that carries the next kill, which here is 3 to 5 s, and the
recording has about 5 to 20 such silences per pass, most of them from attackers who then leave. Night City's combat processor never hit
this because fights have an explicit `ended`; a streak has no end event, only an absence, and an absence shorter than the watermark delay
is invisible to event time. Processing-time timers would see it, at the cost of replay determinism (see the recovery experiment).

**The board** (`LobbyBoard --once`): five `transformWithState` operators feeding a sixth in one query. Presence, streaks, sells and menace
outputs are reduced to one `Signal` shape, unioned with the sim's snapshots (pass-through, for grading) and with config rows fanned out to
every lobby, keyed by lobby, and scored by `LobbySafety` (MapState of present players with their menace level and vehicle, MapState of known
players kept across leaves, ListState of sell outcomes and streak kills pruned to a window of event time, ValueState of weights).
Score = 100 minus menace 18 per menace present, 4 per hostile, 6 per pvp vehicle, 10 per destroyed sell in the window, 3 per non-hunter
kill in a closed streak in the window; sell at 70, risky at 40, hop below. Window 2.5 s of event time at replay pace, which is 50 ticks.
6,752 verdict rows (hop 3,752, risky 1,817, sell 1,183), 40 batches, median 803 ms against about 285 ms for any single processor; state
rows at the end 487 (board) / 129 (presence) / 22 (streaks) / 0 (sells) / 150 (menace). `numInputRows` is 14,975 per batch, not 3,000:
each branch of the union reads the Kafka source itself, five times.

Grading against `sim_safety` on the 437 snapshot-triggered rows (three passes of 144 snapshots, plus duplicates, since the board does not
dedup): Pearson r 0.749, verdict agreement 300/437 = 68.6%. The confusion matrix (sim verdict in rows, board in columns):

| sim \ board | sell | risky | hop |
|---|---|---|---|
| sell | 51 | 61 | 25 |
| risky | 11 | 53 | 24 |
| hop | 1 | 15 | 196 |

The board is pessimistic: it told a seller to sell into a lobby the sim calls hop once in 437 snapshots, and it called 25 safe lobbies hop.
The gap is mostly tryhards: the sim charges 3 points for one, the board cannot tell a tryhard who kills tourists from a griefer who has not
found a seller yet, and charges a menace. Earlier versions of the board, same data: recency as the last 6 or 8 outcomes regardless of time,
r 0.603 and 59.0%; a 5 s window, r 0.727 and 65.7%; the 2.5 s window above. These weights were tuned on the same replay they are graded on,
so the number to trust is the live one below, not this one. Board population vs sim population at each snapshot: equal in 120 of 437,
off by one in 186, by two in 86; the difference is late joins and leaves (5% by 20 s) and the duplicates.

**Two engine gotchas from the board.** A `ListState` cannot be written as an empty list: pruning everything out of the window and calling
`put` raised `ILLEGAL_STATE_STORE_VALUE.EMPTY_LIST_VALUE` and aborted the batch (the first clean-looking run stopped at batch 25 with an
`InterruptedException` in the changelog commit, which was the symptom, not the cause); the fix is `clear()` when nothing is left. And the
bounded-run stop now also waits for `status.isTriggerActive` to be false, so a long batch is never interrupted.

**State data source on a multi-operator query:** `StateInspect` needs `operatorId`. Operator 0 is the board: `present` reads back as
129 (lobby, player) rows with level, score and pvp_vehicle, 20 to 24 per lobby, the same populations the last verdicts carry. Asking
operator 1 to 4 for `present` fails with `STDS_INVALID_OPTION_VALUE`: "State variable present is not defined for the transformWithState
operator", which is the error you want.

**Recovery:** `STOP_AFTER_BATCHES=15` (2,817 rows written), resume, finish at batch 39: 6,763 rows against 6,752 uninterrupted, 47 rows in
the symmetric difference, 13 and 24 of them sell-triggered. Not identical, and the reason is the clock: `SellMissions` runs processing-time
SLA timers, the resumed pipeline's clock is later than the killed one's, so a different set of sells timed out, and each extra timeout
produced a `timeout` row plus a `late_*` row when the real terminal arrived. Night City's combat recovery was identical because its timers
are event time. Event-time state replays exactly; processing-time state replays approximately. The `RocksDBFileManager` "Error zipping"
at the end of the resumed run is the stop interrupting a snapshot upload, not a failure.

**Real-time Mode:** `TRIGGER=rtm` on the full chain is rejected at analysis with
`STREAMING_REAL_TIME_MODE.STATEFUL_OPERATORS_BEFORE_UNION_NOT_SUPPORTED`. A chain without a union (menace -> lobby, `BOARD_INPUT=menace`)
is what the latency comparison below runs.

**Dynamic configuration, live:** sim at real pace (1,400 ticks at 100 ms, topic `losantos.live`), board unbounded (`RUN_SECONDS=175`,
window 5 s, `CONFIG_TOPIC=losantos.config`). At 17:00:15 UTC one row was published: `{"menace": 40, "destroyed": 25}`. The first verdict
under the new weights carries the config record's Kafka timestamp, 17:00:15.983; six config-triggered rows, one per lobby, no restart.
Before the row: 2,322 verdicts (sell 633, risky 547, hop 1,142), mean safety 40.6. After: 2,365 (hop 2,302, risky 51, sell 12), mean 1.7.
Lobby 05 at the switch: 2 menaces, 0 destroyed, 48 risky before, 4 hop after, same facts. A config row is a patch: keys left out keep their
current value (the first attempt reset the window to the default, because `parse` fell back to the shipped defaults rather than the running
weights). Live grading on the 336 snapshots of that run: r 0.661, agreement 63.7%, sold into a hop lobby 0 times.

**Latency, micro-batch vs Real-time Mode, on a two-stage chain** (menace -> lobby, `BOARD_INPUT=menace`, no union): the recording
replayed once at real pace (601 ticks at 100 ms, 38,399 events over 60 s) into a fresh 4-partition topic after the query was up, output
to Kafka in update mode, latency = output record's Kafka timestamp minus the input record's (`source_kafka_ts` carried through both
processors), first 15 s skipped. `spark.sql.shuffle.partitions=4`; `local[8]` for micro-batch, `local[16]` for Real-time (4 reader tasks
plus 4 stateful tasks per stage, held for the whole batch).

| trigger | output records | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| `ProcessingTime("0 seconds")` | 386 | 378 ms | 546 ms | 691 ms | 980 ms |
| `RealTime("20 seconds")` | 387 | 49 ms | 66 ms | 95 ms | 195 ms |

Two stateful stages cost about two micro-batches (Night City's single stage was p50 228 ms); Real-time Mode pipelines both through the
streaming shuffle and the second stage adds a few milliseconds, not a batch. Getting there took two rejections: the full chain fails on
`STATEFUL_OPERATORS_BEFORE_UNION_NOT_SUPPORTED`, and a typed `.map(... => Signal)` straight into the second `groupByKey` plans as
`AppendColumnsWithObjectExec`, which is not in `RealTimeModeAllowlist` (a `select` in between does not help; the optimizer removes the
serialize/deserialize pair). Building the second stage's input with column expressions keeps the child row-based, plans as
`AppendColumnsExec`, and is accepted. `spark.sql.streaming.realTimeMode.allowlistCheck=false` would also have run it, at your own risk.
