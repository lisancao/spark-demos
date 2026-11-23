#!/usr/bin/env bash
# Run each scenario in the Spark container and save what it prints to output/.
#
#   bin/run.sh               all scenarios
#   bin/run.sh basics        one of: basics, no-bundle, extensions, wrong-jar
#
# Needs `docker compose up -d --wait` and bin/fetch_jars.sh first.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p output
ICEBERG="${ICEBERG:-1.12.0}"
J=/opt/demo/jars
RUNTIME_41="$J/iceberg-spark-runtime-4.1_2.13-$ICEBERG.jar"
RUNTIME_35="$J/iceberg-spark-runtime-3.5_2.12-$ICEBERG.jar"
AWS_BUNDLE="$J/iceberg-aws-bundle-$ICEBERG.jar"
EXTENSIONS=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions

# The catalog: Iceberg's REST catalog, with S3FileIO pointed at RustFS.
CATALOG=(
  --conf spark.sql.catalog.demo=org.apache.iceberg.spark.SparkCatalog
  --conf spark.sql.catalog.demo.type=rest
  --conf spark.sql.catalog.demo.uri=http://rest:8181
  --conf spark.sql.catalog.demo.io-impl=org.apache.iceberg.aws.s3.S3FileIO
  --conf spark.sql.catalog.demo.s3.endpoint=http://object-store:9000
  --conf spark.sql.catalog.demo.s3.path-style-access=true
  --conf spark.sql.catalog.demo.client.region=us-east-1
  --conf spark.sql.catalog.demo.warehouse=s3://warehouse/
  --conf spark.ui.enabled=false
)

in_spark() { docker exec iceberg-runtime-spark "$@"; }

# Keep the lines a reader needs: results, errors, and our own [ok]/[fail] lines.
errors_only() { grep -E '^\[|Exception|Error|Cannot use|^spark |^[0-9]|s3://|^[A-Za-z_]+\s' | awk '/Cannot use/ || !/WARN/' | grep -vE '^\s+at |INFO|NativeCodeLoader|^Using Spark|^To adjust|^Time taken' | awk '!seen[$0]++' | head -40; }

basics() {
  echo "# runtime 4.1 + aws-bundle + extensions, Spark 4.1.4, REST catalog on S3"
  in_spark /opt/spark/bin/spark-sql -S --jars "$RUNTIME_41,$AWS_BUNDLE" \
    --conf spark.sql.extensions=$EXTENSIONS "${CATALOG[@]}" -f /opt/demo/sql/basics.sql 2>&1 | errors_only
}

no_bundle() {
  echo "# runtime 4.1 only (no iceberg-aws-bundle), same catalog"
  in_spark /opt/spark/bin/spark-sql -S --jars "$RUNTIME_41" \
    --conf spark.sql.extensions=$EXTENSIONS "${CATALOG[@]}" -e "SELECT count(*) FROM demo.shop.orders" 2>&1 | errors_only
}

extensions() {
  echo "# with the extensions"
  in_spark /opt/spark/bin/spark-submit --jars "$RUNTIME_41,$AWS_BUNDLE" \
    --conf spark.sql.extensions=$EXTENSIONS "${CATALOG[@]}" /opt/demo/bin/checks.py 2>&1 | errors_only
  echo
  echo "# without the extensions"
  in_spark /opt/spark/bin/spark-submit --jars "$RUNTIME_41,$AWS_BUNDLE" \
    "${CATALOG[@]}" /opt/demo/bin/checks.py 2>&1 | errors_only
}

wrong_jar() {
  echo "# runtime 3.5_2.12 + aws-bundle on Spark 4.1.4"
  in_spark /opt/spark/bin/spark-sql -S --jars "$RUNTIME_35,$AWS_BUNDLE" \
    --conf spark.sql.extensions=$EXTENSIONS "${CATALOG[@]}" -e "SELECT count(*) FROM demo.shop.orders" 2>&1 | errors_only
}

run() { local name=$1 fn=$2; echo "== $name"; "$fn" | tee "output/$name.txt"; echo; }

case "${1:-all}" in
  basics) run basics basics ;;
  no-bundle) run no-bundle no_bundle ;;
  extensions) run extensions extensions ;;
  wrong-jar) run wrong-jar wrong_jar ;;
  all) run basics basics; run no-bundle no_bundle; run extensions extensions; run wrong-jar wrong_jar ;;
  *) echo "unknown scenario: $1" >&2; exit 2 ;;
esac
