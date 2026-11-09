"""Follow the recommender live: each click a shopper makes, and the picks Spark sends back.

  python bin/watch.py                 # the busiest shopper
  python bin/watch.py --user u0042
"""
import argparse
import json
import sys
import time
from pathlib import Path

from confluent_kafka import Consumer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bookshop.common import BOOTSTRAP, CLICKS, DATA, RECS  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--user", default=None)
ap.add_argument("--seconds", type=float, default=60)
a = ap.parse_args()

import pyarrow.parquet as pq  # noqa: E402
cat = pq.read_table(str(DATA / "catalog"), columns=["book_id", "title", "aisle"]).to_pydict()
books = {b: (t, s) for b, t, s in zip(cat["book_id"], cat["title"], cat["aisle"])}
favs = json.loads((DATA / "shoppers.json").read_text())

con = Console(highlight=False)
W = max(24, con.width - 34)   # title columns that fit beside the action and aisle
c = Consumer({"bootstrap.servers": BOOTSTRAP, "group.id": f"watch-{time.time()}",
              "auto.offset.reset": "latest", "enable.auto.commit": False})
c.subscribe([CLICKS, RECS])
user, sent = a.user, {}
end = time.time() + a.seconds
while time.time() < end:
    m = c.poll(0.5)
    if m is None or m.error():
        continue
    v = json.loads(m.value())
    if user is None:
        user = v["user_id"]
        con.print(f"[bold]following {user}[/]  (favourite aisles, hidden from Spark: {', '.join(favs[user])})\n")
    if v["user_id"] != user:
        continue
    if m.topic() == CLICKS:
        if v["event_id"] in sent:
            continue
        sent[v["event_id"]] = v["ts"]
        t, s = books.get(v["book_id"], ("?", "?"))
        con.print(f"[#E25A1C]{v['action']:>8}[/]  {t[:W]}  [dim]({s})[/]")
    elif v["kind"] == "picks":
        lat = m.timestamp()[1] - v["ts"]
        con.print(f"          [dim]picks after {v['clicks']} clicks, {lat} ms after the click:[/]")
        for p in v["picks"][:3]:
            star = "*" if p["aisle"] in favs[user] else " "
            con.print(f"          {star} {p['title'][:W - 4]}  [dim]{p['aisle'][:18]}[/]")
    else:
        con.print(f"[bold]   nudge[/]  {user} went quiet; email: {v['picks'][0]['title'][:W]}")
