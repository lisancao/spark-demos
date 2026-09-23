#!/usr/bin/env bash
#
# Runs the before/after demo. Compiles first, so this is the only command you need:
#
#   ./demo.sh
#
# To run it from IntelliJ IDEA instead, see IDEA_SETUP.md. The JVM flags below are
# what the IDE run configuration needs too, and idea-run-config.xml has them
# pre-filled.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

# ---- locate Spark ----
if [[ -n "${SPARK_HOME:-}" ]]; then
  spark_jars="$SPARK_HOME/jars"
elif [[ -d /opt/homebrew/opt/apache-spark/libexec/jars ]]; then
  spark_jars=/opt/homebrew/opt/apache-spark/libexec/jars
elif command -v spark-submit >/dev/null 2>&1; then
  spark_jars="$(dirname "$(dirname "$(readlink -f "$(command -v spark-submit)")")")/jars"
else
  echo "Could not find Spark. Set SPARK_HOME and re-run." >&2
  exit 1
fi

echo "== Compiling against $spark_jars"
mkdir -p target/classes
javac -proc:none -cp "$spark_jars/*" -d target/classes \
  $(find src/main/java -name '*.java')

# Spark on JDK 17+ needs these opens: Catalyst reaches into java.base internals for
# its unsafe row format. spark-submit sets them for you; a plain `java` run does not.
exec java \
  -XX:+IgnoreUnrecognizedVMOptions \
  --add-opens=java.base/java.lang=ALL-UNNAMED \
  --add-opens=java.base/java.lang.invoke=ALL-UNNAMED \
  --add-opens=java.base/java.lang.reflect=ALL-UNNAMED \
  --add-opens=java.base/java.io=ALL-UNNAMED \
  --add-opens=java.base/java.net=ALL-UNNAMED \
  --add-opens=java.base/java.nio=ALL-UNNAMED \
  --add-opens=java.base/java.util=ALL-UNNAMED \
  --add-opens=java.base/java.util.concurrent=ALL-UNNAMED \
  --add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED \
  --add-opens=java.base/sun.nio.ch=ALL-UNNAMED \
  --add-opens=java.base/sun.nio.cs=ALL-UNNAMED \
  --add-opens=java.base/sun.security.action=ALL-UNNAMED \
  --add-opens=java.base/sun.util.calendar=ALL-UNNAMED \
  -Djdk.reflect.useDirectMethodHandle=false \
  -Dio.netty.tryReflectionSetAccessible=true \
  -cp "target/classes:$spark_jars/*" \
  com.example.dsv2lab.demo.BeforeAfterDemo "$@"
