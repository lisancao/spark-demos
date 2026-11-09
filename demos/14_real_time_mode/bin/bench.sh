#!/usr/bin/env bash
# Every latency number the post quotes, in one run. Results go to data/bench.jsonl.
#   bin/bench.sh [rate] [seconds]
set -euo pipefail
cd "$(dirname "$0")/.."
rate=${1:-200} secs=${2:-45}
out=data/bench.jsonl; : > "$out"
run() {  # label env script mode topic
  local label=$1 envs=$2; shift 2
  echo "== $label" >&2
  env $envs bin/measure.sh "$1" "$2" "$3" "$rate" "$secs" --json | sed "s/^{/{\"run\": \"$label\", /" | tee -a "$out"
}
run "2 enrich, micro-batch"          ""                 02_real_time_enrich.py micro enriched
run "2 enrich, real-time"            ""                 02_real_time_enrich.py rtm   enriched
run "3 dedup+window, micro-batch"    ""                 03_stateful_trending.py micro trending
run "3 dedup+window, real-time"      ""                 03_stateful_trending.py rtm   trending
run "3 dedup+window, real-time 1ms"  "SHUFFLE_WAIT_MS=1" 03_stateful_trending.py rtm  trending
run "4 recommender, micro-batch"     ""                 04_recs.sh micro recs
run "4 recommender, real-time"       ""                 04_recs.sh rtm   recs
run "4 recommender, real-time 1ms"   "SHUFFLE_WAIT_MS=1" 04_recs.sh rtm  recs
