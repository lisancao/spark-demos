#!/usr/bin/env bash
#
# Builds and verifies the whole lab against a local Apache Spark 4.2.0 install.
#
# Why this script instead of `mvn test`: the pom.xml is here and works if you have
# network access to Maven Central, but the checks below need nothing except a Spark
# install, which you already have if you are running Spark. Everything compiles
# against the jars in your Spark distribution, so the versions cannot drift.
#
# Usage:
#   ./verify.sh              # find Spark automatically
#   SPARK_HOME=/path ./verify.sh
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

if [[ ! -d "$spark_jars" ]]; then
  echo "No jars directory at $spark_jars" >&2
  exit 1
fi

spark_version="$(ls "$spark_jars" | sed -n 's/^spark-sql_2\.13-\(.*\)\.jar$/\1/p' | head -1)"
echo "== Spark $spark_version at $spark_jars"
case "$spark_version" in
  4.2.*|4.3.*|5.*) : ;;
  *) echo "   WARNING: this lab targets Spark 4.2.0. ProcedureCatalog, Changelog, and"
     echo "   TableInfo need 4.x; the catalog example needs 4.1.0 or newer." ;;
esac

# ---- compile ----
echo "== Compiling"
rm -rf target/classes target/*.jar
mkdir -p target/classes
javac -proc:none -Xlint:deprecation \
  -cp "$spark_jars/*" \
  -d target/classes \
  $(find src/main/java -name '*.java')

jar cf target/dsv2-connector.jar -C target/classes .
echo "   built target/dsv2-connector.jar"

# ---- fixtures ----
work=/tmp/dsv2lab
mkdir -p "$work"
rm -rf "$work/warehouse"
printf 'id,name,dept\n1,ada,eng\n2,grace,eng\n3,alan,research\n4,katherine,math\n5,dorothy,eng\n' \
  > "$work/people.csv"

# ---- run the checks ----
echo "== Running verification suite"
python3 examples/verify_all.py

# The blog post inlines code from these files. Catch drift between the two.
echo
echo "== Checking the blog post's code samples still match this source"
python3 examples/check_blog_code.py || {
  echo "   Post and code have drifted. Fix whichever is wrong." >&2
  exit 1
}

echo
echo "== All checks passed"
