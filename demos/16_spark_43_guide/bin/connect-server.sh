#!/usr/bin/env bash
# Start (or restart) a Spark 4.3 Connect server from the pip install:
# gRPC on 15043, UI and REST API on 4043.   bin/connect-server.sh start|stop
set -euo pipefail
cd "$(dirname "$0")/.."
export SPARK_HOME=$PWD/.venv/lib/python3.14/site-packages/pyspark
export SPARK_LOG_DIR=$PWD/data/logs SPARK_PID_DIR=$PWD/data/pids SPARK_LOCAL_IP=127.0.0.1
mkdir -p "$SPARK_LOG_DIR" "$SPARK_PID_DIR"
"$SPARK_HOME/sbin/stop-connect-server.sh" >/dev/null 2>&1 || true
[[ ${1:-start} == stop ]] && exit 0
"$SPARK_HOME/sbin/start-connect-server.sh" --conf spark.connect.grpc.binding.port=15043 \
  --conf spark.ui.port=4043 >/dev/null
until curl -sf localhost:4043/api/v1/applications >/dev/null; do sleep 1; done
