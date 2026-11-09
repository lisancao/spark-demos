# Animation: a pipelined shuffle lets stateful queries update per record instead of per batch

**Claim.** In micro-batch, a stateful query's shuffle is a barrier: records wait in shuffle files until the whole batch is written, then state updates all at once. In Spark 4.3's Real-time Mode the shuffle is pipelined, so each record updates state as it arrives; a benchmark of the same query measured the median drop. From the guide's Real-time Mode section (SPARK-57141, SPARK-58185).

**Silent first, narrated second.** It has to work muted (square posts autoplay without sound): a caption at the bottom carries every beat, one lane is in focus at a time, and the gate, the +8 jump and the +1 ticks show what the caption says. Lisa reads the captions aloud on a video underneath, so the captions are the narration script: read in order, with the piece's opening card before them and its film captions after, they have to run as one script (the 4.3 narration guidelines in brand/design-projects/Spark 4.2 Release Animations/GUIDELINES.md).

**Numbers.** Lane timing is schematic (`timing.json`), labelled on screen. The bars are `data.json`, copied from demo 14's `NOTES.md` (bench.sh 200 45, step 3 dedup + window), labelled on screen as measured. Nothing on screen or in the narration points at the spark-demos repo or a demo number: the piece has to stand alone (official channels won't link a personal repo), so it says "this query" and shows it.

**Backend:** hf. **Themes:** ide. **Formats:** square first, then portrait and landscape. **Camera cut:** no.

## Beats

| beat | start | what moves | on-screen text | VO (draft) | why this beat |
|---|---|---|---|---|---|
| `open` | 0.0 | title, both lanes and the first caption on screen from frame 0 | A dedup or a running count keeps state, so records shuffle by key. | A dedup or a running count keeps state, so records shuffle by key. | sets up why there is a shuffle at all; readable at frame 0 muted |
| `barrier` | 7.0 | Real-time lane dims; records pile into shuffle files behind a closed gate; "waiting for the whole batch" pulses | In micro-batch, each record waits in the shuffle files until the batch is written. | In micro-batch, each record waits in the shuffle files until the batch is written. | the wait is the problem 4.3 removes |
| `release` | 13.0 | the gate lifts, the batch rushes in, state jumps 0 to 8 with a +8 | Then state updates all at once, and the earliest record has waited longest. | Then state updates all at once, and the earliest record has waited longest. | the jump is what the pipelined lane avoids |
| `pipelined` | 18.5 | focus swaps; records flow straight into state, +1 each, count climbs to 16 | Real-time Mode in 4.3 pipelines that shuffle, so each record updates state as it arrives. | Real-time Mode in 4.3 pipelines that shuffle, so each record updates state as it arrives. | the contrast is the claim; same spacing as the top lane |
| `result` | 26.5 | lanes fade; bars for micro-batch 237 ms and Real-time 50 ms grow | Benchmarked on this query, the median drops from 237 ms to 50 ms. | Benchmarked on this query, the median drops from 237 milliseconds to 50. | turns the picture into a measured result |
| `tuned` | 32.5 | third bar, 2 ms, grows | Set the shuffle's flush wait to 1 ms, and it drops to 2 ms. | Set the shuffle's flush wait to one millisecond, and it drops to two. | the knob behind the 50 ms floor |

## What has to be readable

Every caption, the lane names, the box labels (map, shuffle files, state), the counts, the +8, the bar labels and values, and both notes (schematic, measured), in every format.
