# Opening this in IntelliJ IDEA

Two commands, then File > Open. No Maven Central access needed.

```bash
./setup-idea.sh     # points the project at the Spark install on this machine
./demo.sh           # optional: confirm it runs before opening the IDE
```

Then in IDEA:

1. **File > Open**, select the `dsv2-connector` directory (not `pom.xml`).
2. **File > Project Structure > Project**, set the SDK to a **JDK 17 or 21** install.
3. Run **Before/After Demo** from the run configuration dropdown, or open
   `src/main/java/com/example/dsv2lab/demo/BeforeAfterDemo.java` and click the green
   arrow next to `main`.

`setup-idea.sh` generates two files that cannot be committed with correct values,
because they contain an absolute path specific to your machine:

- `.idea/libraries/spark_jars.xml` points a project library named `spark-jars` at
  your Spark `jars` directory. It uses a `jarDirectory` entry, so every jar in that
  folder is on the classpath and a Spark upgrade does not require regenerating.
- `.idea/runConfigurations/Before_After_Demo.xml` is the run configuration, including
  the JVM flags below.

## Why not import pom.xml

Importing `pom.xml` makes IDEA resolve `spark-sql` and `spark-catalyst` from Maven
Central. That works if you have network access, and it is a fine way to open the
project. The script exists because it has two advantages:

- It works offline, against jars you already have.
- The compile classpath is byte-for-byte the Spark you run, so the API cannot drift
  between what compiles and what executes. When you are learning an API whose
  methods were deprecated across 3.4, 4.1, and 4.2, that matters.

Both paths are supported. The `.iml` and `pom.xml` describe the same module.

## The JVM flags are not optional

Any Spark job on JDK 17+ needs these, because Catalyst reaches into `java.base`
internals for its unsafe row format:

```
-XX:+IgnoreUnrecognizedVMOptions
--add-opens=java.base/java.lang=ALL-UNNAMED
--add-opens=java.base/java.lang.invoke=ALL-UNNAMED
--add-opens=java.base/java.lang.reflect=ALL-UNNAMED
--add-opens=java.base/java.io=ALL-UNNAMED
--add-opens=java.base/java.net=ALL-UNNAMED
--add-opens=java.base/java.nio=ALL-UNNAMED
--add-opens=java.base/java.util=ALL-UNNAMED
--add-opens=java.base/java.util.concurrent=ALL-UNNAMED
--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED
--add-opens=java.base/sun.nio.ch=ALL-UNNAMED
--add-opens=java.base/sun.nio.cs=ALL-UNNAMED
--add-opens=java.base/sun.security.action=ALL-UNNAMED
--add-opens=java.base/sun.util.calendar=ALL-UNNAMED
-Djdk.reflect.useDirectMethodHandle=false
-Dio.netty.tryReflectionSetAccessible=true
```

`spark-submit` and `pyspark` set them for you. A plain `main()` run from an IDE does
not, and without them you get `InaccessibleObjectException` during session startup.
The generated run configuration already includes them; if you build your own run
configuration, copy them into **VM options**.

## Setting breakpoints worth hitting

The point of running this in an IDE is watching Spark call into the connector. These
four breakpoints tell the whole story:

| File | Method | What you see |
|---|---|---|
| `v2/CsvScanBuilder.java` | `pushFilters` | Which filters Spark offers, and what you hand back |
| `v2/CsvScanBuilder.java` | `pruneColumns` | The narrowed schema, before any I/O happens |
| `v2/CsvScanBuilder.java` | `planInputPartitions` | Called once on the driver |
| `v2/CsvReaderFactory.java` | `createReader` | Called once per partition, on the executor |

Run the demo in debug mode and note the order: `pushFilters` and `pruneColumns` fire
during planning, `planInputPartitions` fires once, then `createReader` fires per
partition. That ordering is the API contract, and seeing it beats reading about it.

For the write path, breakpoint `CsvWriteBuilder.CsvDataWriter.commit` (per task) and
`CsvBatchWrite.commit` (once, on the driver, after every task succeeded). That is the
two-phase commit.

## Troubleshooting

**`InaccessibleObjectException` on startup.** The VM flags are missing. See above.

**`ClassNotFoundException: com.example.dsv2lab...`** Build the module first
(Build > Build Project), or check that the module output path is `target/classes`.

**`Cannot resolve symbol 'org.apache.spark'`.** The `spark-jars` library is not
attached. Re-run `./setup-idea.sh`, then File > Project Structure > Modules and
confirm `spark-jars` is listed under Dependencies.

**Forty lines of INFO logging.** `src/main/resources/log4j2.properties` is not on the
classpath. Confirm `src/main/resources` is marked as a Resources root in
File > Project Structure > Modules > Sources.
