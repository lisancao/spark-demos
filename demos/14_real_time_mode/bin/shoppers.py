"""Simulated shoppers -> the `clicks` Kafka topic.

Each shopper has one or two favourite aisles (hidden; written to data/shoppers.json
so step 4 can be graded). Most of a shopper's clicks land in a favourite aisle, the
rest anywhere. A small share of events is sent twice with the same event_id, the way
a retrying mobile client would, so the dedup in step 3 has something to do.

  python bin/shoppers.py --rate 200 --seconds 120
"""
import argparse
import json
import random
import sys
import time
import uuid
from pathlib import Path

import pyarrow.parquet as pq
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bookshop.common import BOOTSTRAP, CATALOG, CLICKS, DATA, ENRICHED, RECS, TRENDING  # noqa: E402

ACTIONS = [("view", 0.85), ("cart", 0.11), ("purchase", 0.04)]


def ensure_topics(partitions: int, reset: bool) -> None:
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})
    names = [CLICKS, ENRICHED, TRENDING, RECS]
    if reset:
        existing = set(admin.list_topics(timeout=10).topics)
        doomed = [t for t in names if t in existing]
        if doomed:
            for f in admin.delete_topics(doomed).values():
                f.result()
            time.sleep(5)   # the broker needs a moment before the same names come back
    existing = set(admin.list_topics(timeout=10).topics)
    # Output topics stamp each record with the broker's append time, so a latency read off them
    # includes Spark's producer and the network hop, not just the moment Spark called send().
    new = [NewTopic(t, partitions, 1,
                    config={} if t == CLICKS else {"message.timestamp.type": "LogAppendTime"})
           for t in names if t not in existing]
    if new:
        for f in admin.create_topics(new).values():
            f.result()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shoppers", type=int, default=200)
    ap.add_argument("--rate", type=float, default=100, help="events per second")
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--fav-share", type=float, default=0.8)
    ap.add_argument("--dup-share", type=float, default=0.02)
    ap.add_argument("--partitions", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--reset", action="store_true", help="delete and recreate the demo topics")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    ensure_topics(a.partitions, a.reset)
    rng = random.Random(a.seed)
    cat = pq.read_table(CATALOG, columns=["book_id", "aisle"]).to_pydict()
    by_aisle: dict[str, list[int]] = {}
    for b, s in zip(cat["book_id"], cat["aisle"]):
        by_aisle.setdefault(s, []).append(b)
    aisles = sorted(by_aisle)
    all_books = cat["book_id"]

    shoppers = {f"u{i:04d}": rng.sample(aisles, rng.choice([1, 2])) for i in range(a.shoppers)}
    (DATA / "shoppers.json").write_text(json.dumps(shoppers, indent=1))

    p = Producer({"bootstrap.servers": BOOTSTRAP, "linger.ms": 0, "acks": 1})
    users = list(shoppers)
    interval = 1.0 / a.rate
    start = time.time()
    sent = dups = 0
    next_at = start
    while time.time() - start < a.seconds:
        user = rng.choice(users)
        if rng.random() < a.fav_share:
            book = rng.choice(by_aisle[rng.choice(shoppers[user])])
        else:
            book = rng.choice(all_books)
        action = rng.choices([x for x, _ in ACTIONS], [w for _, w in ACTIONS])[0]
        ev = {"event_id": uuid.UUID(int=rng.getrandbits(128)).hex, "user_id": user,
              "book_id": book, "action": action, "ts": int(time.time() * 1000)}
        body = json.dumps(ev).encode()
        p.produce(CLICKS, key=user.encode(), value=body)
        sent += 1
        if rng.random() < a.dup_share:
            p.produce(CLICKS, key=user.encode(), value=body)   # same event, sent again
            dups += 1
        p.poll(0)
        next_at += interval
        delay = next_at - time.time()
        if delay > 0:
            time.sleep(delay)
        if not a.quiet and sent % max(1, int(a.rate * 5)) == 0:
            print(f"{sent} events, {dups} resent", flush=True)
    p.flush(10)
    print(f"done: {sent} events, {dups} resent, {a.shoppers} shoppers")


if __name__ == "__main__":
    main()
