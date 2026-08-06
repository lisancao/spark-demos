#!/usr/bin/env bash
#
# Points the IntelliJ IDEA project at the Spark install on THIS machine.
#
#   ./setup-idea.sh          # auto-detect Spark
#   SPARK_HOME=/opt/spark ./setup-idea.sh
#
# Then: File > Open, select this directory, and IDEA picks up the module, the Spark
# library, and a ready-made run configuration for the demo.
#
# Why not just import pom.xml: that needs Maven Central to resolve the Spark
# artifacts. This script wires the project directly to the jars in your local Spark
# distribution, so IDEA resolves everything offline and the API version cannot drift
# from the Spark you actually run.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

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

version="$(ls "$spark_jars" | sed -n 's/^spark-sql_2\.13-\(.*\)\.jar$/\1/p' | head -1)"
echo "== Spark ${version:-unknown} at $spark_jars"

mkdir -p .idea/libraries .idea/runConfigurations

# A jarDirectory entry means IDEA picks up every jar in the folder, so this survives
# a Spark upgrade without regenerating.
cat > .idea/libraries/spark_jars.xml <<XML
<component name="libraryTable">
  <library name="spark-jars">
    <CLASSES>
      <root url="file://$spark_jars" />
    </CLASSES>
    <JAVADOC />
    <SOURCES />
    <jarDirectory url="file://$spark_jars" recursive="false" />
  </library>
</component>
XML

# The --add-opens flags are required: Catalyst reaches into java.base internals for
# its unsafe row format, and a plain IDE run does not set them the way spark-submit does.
cat > .idea/runConfigurations/Before_After_Demo.xml <<'XML'
<component name="ProjectRunConfigurationManager">
  <configuration default="false" name="Before/After Demo" type="Application"
                 factoryName="Application" nameIsGenerated="false">
    <option name="MAIN_CLASS_NAME" value="com.example.dsv2lab.demo.BeforeAfterDemo" />
    <module name="dsv2-connector" />
    <option name="VM_PARAMETERS" value="-XX:+IgnoreUnrecognizedVMOptions --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.base/java.lang.invoke=ALL-UNNAMED --add-opens=java.base/java.lang.reflect=ALL-UNNAMED --add-opens=java.base/java.io=ALL-UNNAMED --add-opens=java.base/java.net=ALL-UNNAMED --add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/java.util=ALL-UNNAMED --add-opens=java.base/java.util.concurrent=ALL-UNNAMED --add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/sun.nio.cs=ALL-UNNAMED --add-opens=java.base/sun.security.action=ALL-UNNAMED --add-opens=java.base/sun.util.calendar=ALL-UNNAMED -Djdk.reflect.useDirectMethodHandle=false -Dio.netty.tryReflectionSetAccessible=true" />
    <option name="WORKING_DIRECTORY" value="$PROJECT_DIR$" />
    <method v="2">
      <option name="Make" enabled="true" />
    </method>
  </configuration>
</component>
XML

echo "== Wrote .idea/libraries/spark_jars.xml"
echo "== Wrote .idea/runConfigurations/Before_After_Demo.xml"
echo
echo "Next:"
echo "  1. IDEA: File > Open, choose $here"
echo "  2. Set the project SDK to a JDK 17 or 21 install (File > Project Structure)"
echo "  3. Run the 'Before/After Demo' configuration, or open"
echo "     src/main/java/com/example/dsv2lab/demo/BeforeAfterDemo.java and hit the green arrow"
