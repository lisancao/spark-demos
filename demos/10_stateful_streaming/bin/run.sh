#!/usr/bin/env bash
# Entry point used by the `spark` compose service: run.sh <job> [args...]
# Jobs are classes under nightcity.jobs; the fat-ish jar is built by `sbt package`
# and the Kafka connector is resolved from the 4.3.0-rc2 staging repository.
set -euo pipefail
JOB="${1:?usage: run.sh <job> [args]}"; shift || true
JAR="$(ls /app/jars/nightcity_2.13-*.jar | head -1)"
SPARK_VERSION="${SPARK_VERSION:-4.3.0}"
STAGING="${SPARK_STAGING_REPO:-https://repository.apache.org/content/repositories/orgapachespark-1538/}"
exec /opt/spark/bin/spark-submit \
  --master "${SPARK_MASTER:-local[8]}" \
  --driver-memory "${SPARK_DRIVER_MEMORY:-4g}" \
  --packages "org.apache.spark:spark-sql-kafka-0-10_2.13:${SPARK_VERSION}${EXTRA_PACKAGES:+,$EXTRA_PACKAGES}" \
  --repositories "${STAGING}" \
  --conf spark.jars.ivy=/app/ivy \
  --conf spark.sql.shuffle.partitions=8 \
  --conf spark.sql.streaming.stateStore.providerClass=org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider \
  --conf spark.sql.streaming.stateStore.rocksdb.changelogCheckpointing.enabled=true \
  --conf spark.sql.streaming.stateStore.checkpointFormatVersion=2 \
  --conf spark.ui.showConsoleProgress=false \
  ${EXTRA_CONF:-} \
  --class "nightcity.jobs.${JOB}" \
  "$JAR" "$@"
