#!/usr/bin/env bash
# Step 4: the per-shopper recommender (Scala transformWithState) under a Real-time trigger.
# Runs the jar on the Spark 4.3.0 install in SPARK_HOME (default ~/.local/opt/spark).
#   ./04_recs.sh --mode rtm --seconds 90
set -euo pipefail
cd "$(dirname "$0")"
SPARK_HOME=${SPARK_HOME:-$HOME/.local/opt/spark}
jar=scala/target/scala-2.13/bookshop-recs_2.13-0.1.0.jar
[[ -f $jar ]] || (cd scala && sbt -batch -warn package)
mode=rtm seconds=${RUN_SECONDS:-90}
while [[ $# -gt 0 ]]; do case $1 in --mode) mode=$2; shift 2;; --seconds) seconds=$2; shift 2;; *) break;; esac; done
exec "$SPARK_HOME/bin/spark-submit" --master 'local[16]' \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.3.0 \
  --conf spark.ui.showConsoleProgress=false \
  ${SHUFFLE_WAIT_MS:+--conf spark.shuffle.streaming.networkBufferMaxWaitTimeMs=$SHUFFLE_WAIT_MS} \
  --class bookshop.RecsJob "$jar" --mode "$mode" --seconds "$seconds" --demo "$PWD" "$@"
