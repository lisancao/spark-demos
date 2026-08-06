# Demo 2 — Spark Connect: *"same code, laptop to AI agent"*

Spark 4.2's decoupled client/server (gRPC + Arrow). The client is a **true thin wheel**
(`pyspark-client`) — no local JVM, no `jars/`, no local Spark. The DataFrame code is identical
to what you'd run locally; only the connection string moves. Then embed that session in an
**AI tool** that answers questions with Demo 1's governed metric.

📖 **Deep dive:** [`companion_guide.md`](companion_guide.md)

## What it shows

| Beat | Proof |
|------|--------|
| Same DataFrame code, remote | `spark.version` is the *server's* |
| Thin client | no `pyspark/jars/` in the install |
| 4.2: `spark.read.json(df)` | nested schema from a Kafka-shaped string column |
| Honest RDD boundary | `df.rdd` fails; `zipWithIndex` is the replacement |
| AI tool | Q&A via `MEASURE()` on `delivery_metrics` |

```
Q: What's our overall conversion rate?  → 0.0923   (not the 0.238 lie)
Q: How many active users this month?    → 9994
Q: Which region converts best?          → remote
```

## Project layout

```
02_spark_connect/
  DEMO.md / TASKS.md             # brand + checklist
  companion_guide.md             # written deep dive
  pyproject.toml                 # pyspark-client==4.2.0 (thin!)
  .env.example                   # -> .env (SPARK_REMOTE=sc://localhost:15099)
  src/spark_connect_demo/
    config.py                    # get_spark() + assert_thin_client()
    run_demo.py                  # beat storyboard (the reel runner)
    thin_client.py               # one-liner companion
    ai_tool.py                   # embed the session in an AI tool
  notebooks/demo_spark_connect.ipynb
```

## Run it

```bash
cd demos/02_spark_connect
cp .env.example .env

# clean env so a full local Spark install cannot shadow the thin wheel
unset SPARK_HOME PYTHONPATH

uv sync

# Option A — Docker sandbox (from repo root):
#   docker compose -p spark42demos -f compose/docker-compose.yml up -d
#
# Option B — local Spark 4.2.0 Connect (no Docker):
#   ./scripts/start-local-connect.sh          # leave running in another terminal

uv run python -m spark_connect_demo.run_demo          # full storyboard
uv run python -m spark_connect_demo.run_demo --pause  # live / recorded take
uv run python -m spark_connect_demo.thin_client       # short path
uv run python -m spark_connect_demo.ai_tool           # needs Demo 1's delivery_metrics
```

`ai_tool` / beat 5 depend on Demo 1 having created `delivery_metrics` on the server. They
guard for that and tell you if it's missing — the rest of the Connect demo still stands alone.

## Thin client vs full PySpark — do not mix these up

| Package | What you get |
|---------|----------------|
| `pyspark-client` | Pure Python Connect client. **No jars, no JRE.** This demo. |
| `pyspark[connect]` | Full PySpark + Connect extras. Has a local runtime. |
| `pyspark-connect` | Makes Connect the default session factory for full PySpark. |

If `os.path.isdir(.../pyspark/jars)` is `True`, you are not on the thin client.

## 4.2 Connect improvements worth naming

- **`spark.read.json/csv/xml(DataFrame)`** — DataFrame-native replacement for `read.*(rdd)`
- **`DataFrame.zipWithIndex`** — common RDD idiom without dropping to RDD
- **Structured errors over the wire** — SQLSTATE / query context on `PySparkException`
- **Plan compression (zstd)** — why `zstandard` is a hard client dependency now

"Better RDD API compatibility" in the announcement means *DataFrame replacements for RDD
idioms*, not that `df.rdd` works over Connect. It still doesn't — and the demo says so out loud.

## Reel script (~4 min)

`run_demo.py` *is* the storyboard. Use `--pause` for a live take.

1. **Hook (0:00):** connect, print server version. Same `groupBy` you'd write locally.
2. **Thin (0:45):** no `jars/` under the installed package. "No Spark in this process."
3. **4.2 parse (1:20):** JSON string column → `spark.read.json(df)` → nested schema.
4. **Boundary (2:10):** `df.rdd` raises; `zipWithIndex` as the replacement.
5. **Embed (2:50):** AI tool Q&A via Demo 1's metric. Conversion is 9.2%, not 24%.
6. **Close (3:40):** "Your semantic layer just governed your AI." Tease the server UI plan view.
