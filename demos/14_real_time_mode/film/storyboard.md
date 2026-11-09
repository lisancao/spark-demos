# Film: Real-time Mode on Spark 4.3, step by step (terminal)

**Story.** The same streaming query gets faster without getting different: a micro-batch query,
then the Real-time trigger on a stateless join, then stateful dedup and counting through the
pipelined shuffle, then a per-shopper recommender in `transformWithState` whose picks change on
every click. Beats follow the post "Getting Started with Real-time Mode on Spark" and the
demo's README. VO lines are drafts written from the post (there is no video script); every
claim is checked against the code and NOTES.md.

**Tape:** `real_time_mode.tape`. **Needs:** `docker compose up -d --wait` (Kafka on 29192),
`.venv` synced, `data/catalog` built, the Scala jar built, nothing else using the 16 cores.

## Beats

| beat | shows | VO | zoom |
|---|---|---|---|
| `basics` | `01_streaming_basics.py` in nvim, `:Run` beside it; micro-batches print every 5 s while shoppers click | A stream is a table that keeps growing. You read it with readStream, write ordinary DataFrame code, and Spark runs that code on each new slice of input. In the default mode each slice is a micro-batch, and every record waits for the batch it lands in. | `basics-trigger 13-19; basics-batch 20-34` |
| `trigger` | `02_real_time_enrich.py` on its trigger lines; then the step measured in micro-batch and Real-time | Real-time Mode keeps the API and changes the execution. Long-running tasks process records as they arrive, so the only change here is the trigger, plus update mode. Micro-batch puts the median past a hundred milliseconds. Real-time, on this machine, under one. | `trig-code 4-9; trig-results 22.7-end` |
| `stateful` | `03_stateful_trending.py` on `dropDuplicates` and the windowed `groupBy`; measured in Real-time, then with the shuffle flush wait at 1 ms | New in 4.3: stateful queries. Dedup and a windowed count need a shuffle, and Real-time Mode pipelines it, streaming records straight into state. The median here is a flush timer on that shuffle, fifty milliseconds by default. Turn it down and it drops to a couple. | `st-code 4-9; st-results 24.6-end` |
| `processor` | `Recommender.scala` on `handleInputRows` | For personalisation you write a stateful processor. This one keeps a taste vector per shopper, built from book embeddings, and scores the whole catalog on every click. In Real-time Mode it's called once per row, and it has to be Scala or Java. | `proc-loop 4-9; proc-timer 10-14` |
| `live` | `bin/watch.py` following one shopper: each click, then the picks Spark sends back and how many milliseconds later | Here's one shopper browsing. Each click goes through Kafka, into the processor, and back out as fresh picks, a few milliseconds later. The starred picks are in this shopper's favourite aisles, which Spark never sees. |  |
| `grade` | `bin/grade.py`: hit rate by clicks so far against random, and the idle-timer nudges | Graded against those hidden favourites, one click already puts most picks in the right aisles, and it climbs from there. The idle timers fired too, but at the end of the batch, because a quiet partition only checks its timers when input arrives or the batch ends. | `grade-table 7.5-end-1` |

## Zoom regions

`zoom` is the landscape cut's dynamic zoom (`film zoom`): a region from this table and the
seconds into the beat it holds. Boxes are pixels of the 1920x1080 landscape render, measured
on its frames. The vertical cut isn't zoomed.

| region | landscape | vertical |
|---|---|---|
| `basics-trigger` | 30,600,1030,180 | - |
| `basics-batch` | 1060,40,740,440 | - |
| `trig-code` | 30,330,1500,280 | - |
| `trig-results` | 0,40,1270,180 | - |
| `st-code` | 30,215,1720,240 | - |
| `st-results` | 0,30,1550,200 | - |
| `proc-loop` | 30,360,1500,330 | - |
| `proc-timer` | 30,860,1200,100 | - |
| `grade-table` | 0,95,1160,220 | - |

## What has to be readable

- `basics`: the `trigger(processingTime="5 seconds")` line and a `Batch: N` header with rows.
- `trigger`: `trigger(realTime="30 seconds")`, and both latency lines (p50 for micro and Real-time).
- `stateful`: `dropDuplicates(["event_id"])`, `groupBy(F.window(...))`, both latency lines.
- `processor`: the `rows.foreach` loop, `registerTimer`, `topK`.
- `live`: at least two click lines, each followed by picks with the "ms after the click" line.
- `grade`: the hit-rate table and the nudges line.

## Not filmed here

Title cards, the architecture and shuffle diagrams (they're in the post), the catalog build.
