#!/usr/bin/env bash
# Run one streaming step against fresh topics while the shoppers generate clicks, then
# read the output topic's end-to-end latency.
#   bin/measure.sh 02_real_time_enrich.py rtm enriched [rate] [seconds]
set -euo pipefail
cd "$(dirname "$0")/.."
script=$1 mode=$2 topic=$3 rate=${4:-200} secs=${5:-60}
py=.venv/bin/python
rm -rf data/checkpoints/*"-$mode"
$py bin/shoppers.py --reset --rate 0.001 --seconds 0 --quiet >/dev/null 2>&1   # topics only
log=data/logs/${script%.*}-$mode.log; mkdir -p data/logs
if [[ $script == *.sh ]]; then run=("./$script"); else run=("$py" "$script"); fi
RUN_SECONDS=$((secs + 15)) "${run[@]}" --mode "$mode" >"$log" 2>&1 &
spark=$!
until grep -q "^running" "$log"; do sleep 1; done
sleep 8                                                 # first batch planned and tasks up
$py bin/shoppers.py --rate "$rate" --seconds "$secs" --quiet >>data/logs/shoppers.log 2>&1
wait $spark || true
$py bin/latency.py "$topic" --warmup 5 "${@:6}"
