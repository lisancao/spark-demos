"""End-to-end latency of an output topic: the Kafka record timestamp (LogAppendTime: when
the broker appended Spark's output record) minus the click's own `ts` (set by the shopper
when it produced the click). Both clocks are this machine's. For `trending`, the click is the
newest one counted into the row (`last_ts`).

  python bin/latency.py enriched --warmup 10
"""
import argparse
import json
import sys
from pathlib import Path

from confluent_kafka import Consumer, TopicPartition

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bookshop.common import BOOTSTRAP  # noqa: E402


def read_all(topic: str) -> list[tuple[int, dict]]:
    c = Consumer({"bootstrap.servers": BOOTSTRAP, "group.id": f"lat-{topic}-{id(object())}",
                  "enable.auto.commit": False, "auto.offset.reset": "earliest"})
    md = c.list_topics(topic, timeout=10).topics[topic]
    parts = [TopicPartition(topic, p) for p in md.partitions]
    ends = {p.partition: c.get_watermark_offsets(p, timeout=10)[1] for p in parts}
    c.assign([TopicPartition(topic, p.partition, 0) for p in parts])
    out, done = [], {p for p, e in ends.items() if e == 0}
    while len(done) < len(parts):
        m = c.poll(2.0)
        if m is None:
            break
        if m.error():
            continue
        out.append((m.timestamp()[1], json.loads(m.value())))
        if m.offset() + 1 >= ends[m.partition()]:
            done.add(m.partition())
    c.close()
    return out


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--field", default=None, help="click timestamp field (default ts, or last_ts)")
    ap.add_argument("--warmup", type=float, default=10, help="skip the first N seconds of output")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = read_all(a.topic)
    if not rows:
        sys.exit(f"{a.topic}: no records")
    rows = [(t, v) for t, v in rows if v.get("kind", "picks") == "picks"]   # nudges are timer output, not click-driven
    field = a.field or ("last_ts" if "last_ts" in rows[0][1] else "ts")
    first = min(t for t, _ in rows)
    lat = [t - v[field] for t, v in rows if t - first >= a.warmup * 1000]
    res = {"topic": a.topic, "records": len(lat), "p50_ms": pct(lat, .5), "p90_ms": pct(lat, .9),
           "p99_ms": pct(lat, .99), "max_ms": max(lat)}
    if a.json:
        print(json.dumps(res))
    else:
        print(f"{a.topic}: {res['records']} records after {a.warmup:g}s warmup  "
              f"p50 {res['p50_ms']} ms  p90 {res['p90_ms']} ms  p99 {res['p99_ms']} ms  max {res['max_ms']} ms")


if __name__ == "__main__":
    main()
