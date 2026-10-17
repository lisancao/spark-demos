#!/usr/bin/env python3
"""End-to-end latency of a processor's Kafka output: output record append time minus the input record's Kafka append time.

    python bin/latency_report.py --topic nightcity.presence.rtm [--bootstrap localhost:29092]

Each output record carries `source_kafka_ts` (epoch ms of the input record as the Kafka broker stamped it), and the
broker stamps the output record on append (CreateTime from the producer, which Spark's Kafka sink leaves unset, so
the broker fills it in with LogAppendTime only if the topic is configured that way; we use the producer timestamp
Spark sets at send time otherwise). Either way the clock is the same machine's, so the difference is honest.
"""
import argparse
import json
import statistics

from confluent_kafka import Consumer, TopicPartition

ap = argparse.ArgumentParser()
ap.add_argument("--topic", required=True)
ap.add_argument("--bootstrap", default="localhost:29092")
ap.add_argument("--skip-first-s", type=float, default=0.0, help="ignore outputs in the first N seconds (warm-up)")
args = ap.parse_args()

c = Consumer({"bootstrap.servers": args.bootstrap, "group.id": f"latency-{args.topic}", "auto.offset.reset": "earliest", "enable.auto.commit": False})
md = c.list_topics(args.topic, timeout=10)
parts = [TopicPartition(args.topic, p) for p in md.topics[args.topic].partitions]
for tp in parts:
    lo, hi = c.get_watermark_offsets(tp, timeout=10)
    tp.offset = lo
c.assign(parts)
ends = {tp.partition: c.get_watermark_offsets(tp, timeout=10)[1] for tp in parts}

lat = []
first_out = None
done = {p: ends[p] == 0 for p in ends}
while not all(done.values()):
    m = c.poll(2.0)
    if m is None:
        break
    if m.error():
        continue
    _, out_ts = m.timestamp()
    v = json.loads(m.value())
    src = v.get("source_kafka_ts")
    if first_out is None:
        first_out = out_ts
    if src is not None and out_ts - first_out >= args.skip_first_s * 1000:
        lat.append(out_ts - src)
    if m.offset() + 1 >= ends[m.partition()]:
        done[m.partition()] = True
c.close()

if not lat:
    raise SystemExit("no output records with source_kafka_ts")
lat.sort()
q = lambda p: lat[min(len(lat) - 1, int(p * len(lat)))]
print(f"topic {args.topic}: {len(lat)} output records")
print(f"latency ms  p50 {q(0.5)}  p90 {q(0.9)}  p99 {q(0.99)}  max {lat[-1]}  mean {statistics.mean(lat):.0f}")
