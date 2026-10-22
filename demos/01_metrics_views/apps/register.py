"""Register metric views from YAML files.

    python apps/register.py metrics/*.yaml [--remote sc://localhost:15002]

Each file is one definition. The view is named after the file (metrics/delivery_metrics.yaml
becomes default.delivery_metrics), replaced if it exists, and described afterwards so the types
Spark inferred are visible. The source tables the definitions name are registered first if they
are missing, as external tables over the Parquet files mounted into the server.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pyspark.sql import SparkSession

TABLES = ("sessions", "orders", "users")


def ensure_tables(spark: SparkSession, data: str) -> None:
    for table in TABLES:
        spark.sql(
            f"CREATE TABLE IF NOT EXISTS default.{table} USING parquet "
            f"LOCATION '{data}/{table}.parquet'"
        )


def register(spark: SparkSession, path: Path) -> None:
    name = f"default.{path.stem}"
    body = path.read_text()
    # CREATE OR REPLACE does not replace a metric view in the session catalog on 4.2.0
    # (SPARK-60177), so drop first.
    spark.sql(f"DROP VIEW IF EXISTS {name}")
    spark.sql(f"CREATE VIEW {name} WITH METRICS LANGUAGE YAML AS $${body}$$")
    print(f"{name}  <-  {path}")
    for row in spark.sql(f"DESCRIBE TABLE {name}").collect():
        print(f"    {row.col_name:<20} {row.data_type}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", type=Path, help="YAML definitions")
    parser.add_argument("--remote", default=os.environ.get("SPARK_REMOTE", "sc://localhost:15002"))
    parser.add_argument("--data", default="/demo/data", help="dataset directory on the server")
    args = parser.parse_args()
    spark = SparkSession.builder.remote(args.remote).getOrCreate()
    ensure_tables(spark, args.data)
    for path in args.paths:
        register(spark, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
