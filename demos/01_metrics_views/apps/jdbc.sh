#!/usr/bin/env bash
# Run SQL against the Spark Connect server over JDBC, from beeline, with no Python involved.
#
#   apps/jdbc.sh "SELECT region, MEASURE(conversion_rate) FROM delivery_metrics GROUP BY region"
#   apps/jdbc.sh            # interactive beeline prompt
#
# The Spark Connect JDBC driver (spark-connect-client-jdbc) and the JVM client it wraps are
# fetched from Maven Central into apps/jdbc/ on first use. Beeline itself comes from the same
# Spark image the server runs on. The URL scheme is jdbc:sc://, the Connect server's own.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
jars="$here/jdbc"
version="4.2.0"
image="apache/spark:${version}-scala2.13-java21-python3-ubuntu"
remote="${SPARK_REMOTE:-sc://localhost:15002}"
url="jdbc:${remote}"

mkdir -p "$jars"
for artifact in spark-connect-client-jdbc_2.13 spark-connect-client-jvm_2.13; do
  jar="$jars/${artifact}-${version}.jar"
  if [ ! -f "$jar" ]; then
    echo "fetching ${artifact} ${version} from Maven Central" >&2
    curl -fsSL -o "$jar" \
      "https://repo1.maven.org/maven2/org/apache/spark/${artifact}/${version}/${artifact}-${version}.jar"
  fi
done

args=(--silent=true --outputformat=table
      -d org.apache.spark.sql.connect.client.jdbc.SparkConnectDriver -u "$url")
for statement in "$@"; do args+=(-e "$statement"); done

tty=(); [ -t 0 ] && tty=(-it)
exec docker run --rm "${tty[@]}" --network host \
  -e HOME=/tmp -e SPARK_DIST_CLASSPATH='/jdbc/*' -v "$jars:/jdbc:ro" \
  "$image" /opt/spark/bin/beeline "${args[@]}" 2>/dev/null
