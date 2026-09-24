#!/usr/bin/env bash
#
# Project Feather demo: run feather_demo.py against the Spark on this machine.
#
#   ./demo.sh              # 800-row fixture, flags off and on
#   ./demo.sh --rows 5000  # show the 1,000-row in-memory cap
#   SPARK_HOME=/opt/spark ./demo.sh
#
# Prefers $SPARK_HOME, then the Homebrew apache-spark install. Requires a JDK;
# defaults to Homebrew openjdk@17 when $JAVA_HOME is empty.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

if [[ -z "${SPARK_HOME:-}" ]]; then
  if [[ -d /opt/homebrew/opt/apache-spark/libexec ]]; then
    SPARK_HOME=/opt/homebrew/opt/apache-spark/libexec
  elif command -v spark-submit >/dev/null 2>&1; then
    SPARK_HOME="$(cd "$(dirname "$(command -v spark-submit)")/.." && pwd)"
  else
    echo "Could not find Spark. Set SPARK_HOME and re-run." >&2
    exit 1
  fi
fi

if [[ -z "${JAVA_HOME:-}" && -x /opt/homebrew/opt/openjdk@17/bin/java ]]; then
  JAVA_HOME=/opt/homebrew/opt/openjdk@17
fi
export JAVA_HOME
export SPARK_HOME

echo "== Spark $SPARK_HOME"
exec "$SPARK_HOME/bin/spark-submit" "$here/feather_demo.py" "$@"
