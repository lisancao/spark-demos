"""Replay a recorded Night City NDJSON event log into Kafka.

Reproducible input for streaming experiments. The replay re-stamps `timestamp`
to the moment the event is (re)emitted, keeps the original value in
`source_timestamp`, and can inject the three things that break naive stream
processors: late arrivals, duplicates, and in-tick reordering.

    python replay.py --bootstrap localhost:29092 ../sim/output/events_*.ndjson \
        --tick-ms 100 --late-fraction 0.05 --late-delay-s 20 --dup-fraction 0.02 --loop

Late events keep the timestamp of when they "happened" and are delivered
after --late-delay-s seconds. Duplicates are the same payload (same event_id)
sent again after --dup-delay-s seconds, the way a retried producer would.
"""

import argparse
import glob
import heapq
import json
import random
import sys
import time
from datetime import datetime, timezone

from confluent_kafka import Producer

from cyberpunk_sim.event_schema import TICKS_PER_DAY, TICKS_PER_PHASE, TIME_PHASES
from cyberpunk_sim.kafka_sink import partition_key


def load_events(paths):
    events = []
    for pattern in paths:
        for path in sorted(glob.glob(pattern)):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
    events.sort(key=lambda e: e["sim_tick"])
    return events


def restamp(event, tick_offset, now):
    e = dict(event)
    tick = event["sim_tick"] + tick_offset
    e["sim_tick"] = tick
    e["sim_day"] = tick // TICKS_PER_DAY + 1
    e["sim_time_phase"] = TIME_PHASES[(tick % TICKS_PER_DAY) // TICKS_PER_PHASE]
    e["sim_phase_tick"] = tick % TICKS_PER_PHASE
    e["source_timestamp"] = event["timestamp"]
    e["timestamp"] = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
    return e


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="NDJSON files or globs")
    ap.add_argument("--bootstrap", default="localhost:29092")
    ap.add_argument("--topic", default="nightcity.events")
    ap.add_argument("--tick-ms", type=int, default=100, help="wall-clock ms between sim ticks")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--late-fraction", type=float, default=0.0)
    ap.add_argument("--late-delay-s", type=float, default=15.0)
    ap.add_argument("--dup-fraction", type=float, default=0.0)
    ap.add_argument("--dup-delay-s", type=float, default=2.0)
    ap.add_argument("--shuffle-within-tick", action="store_true")
    ap.add_argument("--loop", action="store_true", help="replay forever, advancing sim_tick each pass")
    ap.add_argument("--max-ticks", type=int, default=0, help="stop after this many replayed ticks (0 = all)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    events = load_events(args.files)
    if not events:
        sys.exit("no events loaded")
    max_tick = events[-1]["sim_tick"]
    print(f"loaded {len(events)} events, ticks 0..{max_tick}", file=sys.stderr)

    producer = Producer({
        "bootstrap.servers": args.bootstrap,
        "linger.ms": 10,
        "compression.type": "lz4",
        "enable.idempotence": True,
    })

    # Delayed deliveries (late arrivals, duplicates): (due_time, seq, payload, key)
    pending: list[tuple[float, int, str, str]] = []
    seq = 0
    sent = late = dups = 0

    def send(payload: str, key: str):
        producer.produce(args.topic, key=key, value=payload)
        producer.poll(0)

    def flush_due(now: float):
        nonlocal sent
        while pending and pending[0][0] <= now:
            _, _, payload, key = heapq.heappop(pending)
            send(payload, key)
            sent += 1

    tick_offset = 0
    replayed_ticks = 0
    i = 0
    start = time.monotonic()
    try:
        while True:
            # group by tick
            tick_events = []
            tick = events[i]["sim_tick"]
            while i < len(events) and events[i]["sim_tick"] == tick:
                tick_events.append(events[i])
                i += 1
            if args.shuffle_within_tick:
                rng.shuffle(tick_events)

            now_wall = time.time()
            now = time.monotonic()
            for ev in tick_events:
                e = restamp(ev, tick_offset, now_wall)
                payload = json.dumps(e, separators=(",", ":"), default=str)
                key = partition_key(e)
                if args.late_fraction and rng.random() < args.late_fraction:
                    seq += 1
                    heapq.heappush(pending, (now + args.late_delay_s, seq, payload, key))
                    late += 1
                else:
                    send(payload, key)
                    sent += 1
                if args.dup_fraction and rng.random() < args.dup_fraction:
                    seq += 1
                    heapq.heappush(pending, (now + args.dup_delay_s, seq, payload, key))
                    dups += 1
            flush_due(now)

            replayed_ticks += 1
            if args.max_ticks and replayed_ticks >= args.max_ticks:
                break
            if i >= len(events):
                if not args.loop:
                    break
                i = 0
                tick_offset += max_tick + 1
                print(f"loop: tick offset now {tick_offset}", file=sys.stderr)

            # pace: next tick is due at start + replayed_ticks * tick_ms
            due = start + replayed_ticks * args.tick_ms / 1000.0
            sleep = due - time.monotonic()
            if sleep > 0:
                time.sleep(sleep)
            if replayed_ticks % 100 == 0:
                print(f"tick {replayed_ticks}: sent={sent} late_pending={late} dups={dups}", file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        # drain delayed deliveries so late/dup events are not lost on exit
        if pending:
            print(f"draining {len(pending)} delayed events", file=sys.stderr)
            while pending:
                due_at = pending[0][0]
                wait = due_at - time.monotonic()
                if wait > 0:
                    time.sleep(min(wait, 1.0))
                flush_due(time.monotonic())
        producer.flush(30)
        print(f"done: sent={sent} late={late} dups={dups} ticks={replayed_ticks}", file=sys.stderr)


if __name__ == "__main__":
    main()
