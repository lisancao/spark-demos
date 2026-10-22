#!/usr/bin/env python3
"""Publish a scoring-weights row to the board's config topic (dynamic configuration, no restart).

    docker compose run --rm tools /app/bin/publish_config.py --bootstrap kafka:9092 --topic losantos.config \
        '{"menace": 30, "destroyed": 20}'
"""
import argparse
import json
import sys

from confluent_kafka import Producer

ap = argparse.ArgumentParser()
ap.add_argument("weights", help="JSON object; missing keys keep their defaults")
ap.add_argument("--bootstrap", default="localhost:29092")
ap.add_argument("--topic", default="losantos.config")
args = ap.parse_args()
json.loads(args.weights)
p = Producer({"bootstrap.servers": args.bootstrap})
p.produce(args.topic, key="weights", value=args.weights)
p.flush(10)
print(f"published to {args.topic}: {args.weights}", file=sys.stderr)
