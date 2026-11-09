#!/usr/bin/env bash
# Start the SCD2 example over: no table, no checkpoints, an empty menu-changes topic.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f scd2/compose.yaml up -d --wait >/dev/null 2>&1
K="docker exec s43-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092"
$K --delete --topic menu-changes >/dev/null 2>&1 || true
until $K --create --topic menu-changes --partitions 1 >/dev/null 2>&1; do sleep 1; done
rm -rf data/scd2
SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python bin/lake.py 2>/dev/null
