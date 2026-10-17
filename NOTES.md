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
