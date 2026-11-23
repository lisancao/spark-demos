#!/usr/bin/env bash
# Download the official Iceberg jars this demo uses from Maven Central and check each
# one against the SHA-1 that Maven Central publishes next to it. Nothing here is built
# from source: the demo only runs released artifacts.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p jars
ICEBERG="${ICEBERG:-1.12.0}"
BASE=https://repo1.maven.org/maven2/org/apache/iceberg
for artifact in iceberg-spark-runtime-4.1_2.13 iceberg-spark-runtime-3.5_2.12 iceberg-aws-bundle; do
  jar="$artifact-$ICEBERG.jar"
  if [[ ! -f "jars/$jar" ]]; then
    curl -fsSL -o "jars/$jar" "$BASE/$artifact/$ICEBERG/$jar"
  fi
  want="$(curl -fsSL "$BASE/$artifact/$ICEBERG/$jar.sha1" | cut -c1-40)"
  have="$(sha1sum "jars/$jar" | cut -c1-40)"
  if [[ "$want" != "$have" ]]; then
    echo "checksum mismatch for $jar (want $want, have $have)" >&2
    exit 1
  fi
  printf '%-48s %s  ok\n' "$jar" "$have"
done
