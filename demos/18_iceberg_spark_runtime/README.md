# What's in the Iceberg Spark runtime

An Iceberg table on S3 through the Iceberg REST catalog, on the newest Spark that has a released Iceberg runtime. The demo then removes parts of the setup one at a time, so that you can see what each part of `iceberg-spark-runtime` does.

The demo uses official images and official jars only. The Iceberg jars come from Maven Central, and `bin/fetch_jars.sh` checks each jar against the SHA-1 that Maven Central publishes.

| Part | Version | Why this version |
|---|---|---|
| Apache Spark | `apache/spark:4.1.4-scala2.13-java21-python3-ubuntu` | Iceberg 1.12.0 publishes runtime jars for Spark 3.5, 4.0 and 4.1, but not for 4.2 or 4.3. |
| Iceberg jars | `iceberg-spark-runtime-4.1_2.13`, `iceberg-spark-runtime-3.5_2.12` and `iceberg-aws-bundle`, all 1.12.0 | The newest Iceberg release. |
| REST catalog | `apache/iceberg-rest-fixture:1.10.1` | The newest released tag. The `latest` tag is a snapshot of `main`. |
| S3 storage | `rustfs/rustfs:1.0.6` | The newest RustFS release. |

| Scenario | Jars on the classpath | What it shows |
|---|---|---|
| `basics` | runtime 4.1 + `iceberg-aws-bundle` | A partitioned table, an insert, a read, and the data files in S3. |
| `no-bundle` | runtime 4.1 only | The runtime jar contains `S3FileIO`, but not the AWS SDK. |
| `extensions` | runtime 4.1 + `iceberg-aws-bundle` | The same statements with and without `spark.sql.extensions`. |
| `wrong-jar` | runtime 3.5_2.12 + `iceberg-aws-bundle` | A runtime jar for a different Spark version. |

The blog post "The Iceberg Spark Runtime: what's in the jar, and why it has to match your Spark" on [systemsnull.net](https://systemsnull.net) explains the results. [NOTES.md](NOTES.md) records the output of each scenario.

## What you need

- Docker with Compose.
- About 160 MB of disk for the jars.

## Run it

```sh
bin/fetch_jars.sh              # download the jars and check them against Maven Central
docker compose up -d --wait    # Spark, the REST catalog and RustFS
bin/run.sh                     # all scenarios; output goes to output/<scenario>.txt
bin/run.sh extensions          # one scenario: basics, no-bundle, extensions or wrong-jar
docker compose down -v
```

To use a different Iceberg release, set `ICEBERG` for both scripts, for example `ICEBERG=1.11.0 bin/fetch_jars.sh`.

## Files

| File | What it contains |
|---|---|
| `compose.yaml` | The stack. |
| `bin/fetch_jars.sh` | Downloads the runtime jars for Spark 4.1 and 3.5 and the AWS bundle, and checks them. |
| `bin/run.sh` | The catalog configuration and the four scenarios. |
| `sql/basics.sql` | The table, the insert, the read, and a query of the `files` metadata table. |
| `bin/checks.py` | One statement at a time, with `[ok]` or `[fail]` for each. |
| `output/` | The output of the last run. |
