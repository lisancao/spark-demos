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
