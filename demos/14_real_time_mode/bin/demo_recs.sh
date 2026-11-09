#!/usr/bin/env bash
# Step 4 end to end: shoppers browse for a while, then stop; the recommender keeps running long
# enough for the idle timers to fire. Then grade the picks.
#   bin/demo_recs.sh [rtm|micro] [shop_seconds] [rate]
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:-rtm} shop=${2:-60} rate=${3:-100}
py=.venv/bin/python
rm -rf data/checkpoints/04-recs-"$mode"; mkdir -p data/logs
$py bin/shoppers.py --reset --rate 0.001 --seconds 0 --quiet >/dev/null 2>&1
log=data/logs/04_recs-$mode-demo.log
RUN_SECONDS=$((shop + 75)) ./04_recs.sh --mode "$mode" >"$log" 2>&1 &
spark=$!
until grep -q "^running" "$log"; do sleep 1; done; sleep 8
$py bin/shoppers.py --rate "$rate" --seconds "$shop" --quiet
echo "shoppers stopped at $(date +%T); recommender runs on for 75 s"
wait $spark || true
$py bin/latency.py recs --warmup 5
$py bin/grade.py
