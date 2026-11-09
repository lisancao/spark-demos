#!/usr/bin/env bash
# Run the pipeline once. The Iceberg and Kafka jars and the SQL extensions are static configs, so
# they go to spark-submit; the catalog itself is set in spark-pipeline.template.yml.
set -euo pipefail
cd "$(dirname "$0")"
source ../.venv/bin/activate
sed "s#@DEMO@#$(cd .. && pwd)#g" spark-pipeline.template.yml > spark-pipeline.yml
export SPARK_LOCAL_IP=${SPARK_LOCAL_IP:-127.0.0.1}
spark-pipelines run \
  --jars "$(ls ../jars/*.jar | paste -sd,)" \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.ui.enabled=false "$@" 2>&1 | tr '\r' '\n' |
  grep --line-buffered -E 'has COMPLETED|Run is|FAILED|Exception' | sed -u 's/^[0-9-]* [0-9:]*: //'
