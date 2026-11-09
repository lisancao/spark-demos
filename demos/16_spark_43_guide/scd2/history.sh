#!/usr/bin/env bash
# Print the menu table's full history (JVM startup chatter dropped).
cd "$(dirname "$0")/.." && SPARK_LOCAL_IP=127.0.0.1 .venv/bin/python scd2/history.py 2>/dev/null
