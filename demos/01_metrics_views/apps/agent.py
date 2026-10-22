"""Ask a question in English; a Claude agent answers it with SQL over Spark Connect.

    python apps/agent.py "What was the conversion rate in June, overall and by region?"
    python apps/agent.py --context tables "..."

The agent has one tool, run_sql, and every statement it runs is printed. With
--context metric-view (the default) it is shown the metric views' definitions from the catalog
and told to query them with MEASURE(). With --context tables it is shown only the raw tables and
has to work out every formula itself. Same model, same question, same tool; the only difference
is what the catalog told it.
"""

from __future__ import annotations

import argparse
import os
import sys

import anthropic
from anthropic import beta_tool
from pyspark.sql import SparkSession

MODEL = "claude-opus-5-5"
REMOTE = os.environ.get("SPARK_REMOTE", "sc://localhost:15002")
METRIC_VIEWS = ("default.delivery_metrics", "default.order_metrics")
TABLES = ("default.sessions", "default.orders", "default.users")

spark = SparkSession.builder.remote(REMOTE).getOrCreate()


def describe(name: str) -> str:
    rows = spark.sql(f"DESCRIBE TABLE {name}").collect()
    return f"{name}\n" + "\n".join(f"  {r.col_name} {r.data_type}" for r in rows if r.col_name)


def definition(name: str) -> str:
    info = {r.col_name: r.data_type for r in spark.sql(f"DESCRIBE TABLE EXTENDED {name}").collect()}
    return f"{name}\n{info['View Text']}"


CONTEXTS = {
    "metric-view": lambda: (
        "You answer questions about a food-delivery service's June data by running Spark SQL "
        "with the run_sql tool. The data is exposed through metric views. Query a metric view as "
        "SELECT <dimensions>, MEASURE(<measure>) FROM <view> GROUP BY <dimensions>; with no "
        "GROUP BY a measure is computed over everything. Always ask for a measure at the grain "
        "the answer needs; never aggregate a MEASURE() result again in an outer query, and never "
        "recompute a "
        "measure from other tables. Each metric view's definition, as stored in the catalog:\n\n"
        + "\n\n".join(definition(v) for v in METRIC_VIEWS)
        + "\n\nAnswer briefly, with the numbers."
    ),
    "tables": lambda: (
        "You answer questions about a food-delivery service's June data by running Spark SQL "
        "with the run_sql tool against these tables. Write whatever SQL you need.\n\n"
        + "\n\n".join(describe(t) for t in TABLES)
        + "\n\nsessions.converted is true when the session produced an order; orders.session_id "
        "links an order to its session. Answer briefly, with the numbers."
    ),
}


@beta_tool
def run_sql(sql: str) -> str:
    """Run a Spark SQL statement and return the result as text (at most 50 rows).

    Args:
        sql: The SQL statement to run.
    """
    print(f"\n[sql]\n{sql.strip()}", flush=True)
    try:
        frame = spark.sql(sql)
        rows = frame.limit(50).collect()
        text = (
            " | ".join(frame.columns)
            + "\n"
            + "\n".join(" | ".join(str(v) for v in r) for r in rows)
        )
    except Exception as exc:  # the agent sees the error and can try again
        text = f"ERROR: {str(exc).splitlines()[0]}"
    print(text, flush=True)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question")
    parser.add_argument("--context", choices=CONTEXTS, default="metric-view")
    args = parser.parse_args()

    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=8000,
        output_config={"effort": "medium"},
        system=CONTEXTS[args.context](),
        tools=[run_sql],
        messages=[{"role": "user", "content": args.question}],
    )
    final = None
    for message in runner:
        final = message
    if final is None:
        return 1
    print("\n[answer]")
    for block in final.content:
        if block.type == "text":
            print(block.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
