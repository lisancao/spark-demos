#!/usr/bin/env bash
# One-time setup: the venv, the Kafka connector jars, the small Parquet file and the tar of CSV exports.
# The Iceberg runtime for Spark 4.3 isn't on Maven Central yet; build it from an
# Iceberg checkout with Spark 4.3 support and copy it to jars/.
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync -q
# The Kafka source for the SCD2 pipeline (its jars go on spark-submit with Iceberg's).
mkdir -p jars
M=https://repo1.maven.org/maven2
for j in org/apache/spark/spark-sql-kafka-0-10_2.13/4.3.0/spark-sql-kafka-0-10_2.13-4.3.0.jar \
         org/apache/spark/spark-token-provider-kafka-0-10_2.13/4.3.0/spark-token-provider-kafka-0-10_2.13-4.3.0.jar \
         org/apache/kafka/kafka-clients/3.9.2/kafka-clients-3.9.2.jar \
         org/apache/commons/commons-pool2/2.13.1/commons-pool2-2.13.1.jar; do
  [[ -f jars/${j##*/} ]] || curl -fsSL -o jars/${j##*/} $M/$j
done
mkdir -p data/archive_src
SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python - <<'PY' 2>/dev/null
from pyspark.sql import SparkSession, functions as F
SparkSession.builder.getOrCreate().range(500).select(F.col("id").alias("order_id"), (F.col("id") % 7).alias("store"),
    (F.rand(1) * 100).alias("amount")).coalesce(1) \
    .write.mode("overwrite").parquet("data/small_orders.parquet")
PY
printf 'order_id,kitchen\nO1001,San Francisco\nO1002,Los Angeles\n' > data/archive_src/2026-11-04.csv
printf 'order_id,kitchen\nO1003,Chicago\n'                         > data/archive_src/2026-11-05.csv
printf 'not,a,match\n'                    > data/archive_src/README.txt
(cd data/archive_src && tar -cf ../exports.tar 2026-11-04.csv 2026-11-05.csv README.txt)
