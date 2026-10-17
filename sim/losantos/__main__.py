"""Run the Los Santos lobby sim: python -m losantos  (env: SIM_SEED, SIM_TICK_MS, SIM_MAX_TICKS, SIM_OUTPUT_DIR,
SIM_KAFKA_BOOTSTRAP, SIM_KAFKA_TOPIC, LS_PLAYERS, LS_LOBBIES, LS_CAPACITY)."""

import json
import logging
import os
import sys
import time
from pathlib import Path

from cyberpunk_sim.config import SimConfig
from cyberpunk_sim.event_emitter import EventEmitter
from losantos.engine import LobbySim


def main():
    cfg = SimConfig.from_env()
    logging.basicConfig(level=cfg.log_level, format="%(asctime)s %(name)s %(message)s", stream=sys.stderr)
    log = logging.getLogger("losantos")
    n_players = int(os.environ.get("LS_PLAYERS", 150))
    n_lobbies = int(os.environ.get("LS_LOBBIES", 6))
    capacity = int(os.environ.get("LS_CAPACITY", 30))
    emitter = EventEmitter(cfg)
    emitter.start()
    sim = LobbySim(cfg.seed, n_players, n_lobbies, capacity, emitter.emit)
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "players.jsonl", "w") as f:
        for p in sim.players.values():
            f.write(json.dumps(p.public_profile()) + "\n")
    with open(out / "players_truth.jsonl", "w") as f:
        for p in sim.players.values():
            f.write(json.dumps(p.truth()) + "\n")
    with open(out / "lobbies.json", "w") as f:
        json.dump(sorted(sim.lobbies), f)
    log.info("roster: %d players, %d lobbies of %d; seed %d", n_players, n_lobbies, capacity, cfg.seed)
    start = time.monotonic()
    try:
        while not cfg.max_ticks or sim.tick < cfg.max_ticks:
            sim.step()
            if sim.tick % 100 == 0:
                log.info("tick %d: in session %d", sim.tick, sum(1 for p in sim.players.values() if p.in_session))
            due = start + sim.tick * cfg.tick_ms / 1000.0
            sleep = due - time.monotonic()
            if sleep > 0:
                time.sleep(sleep)
    except KeyboardInterrupt:
        pass
    finally:
        sim.drain()
        emitter.stop()
        log.info("stopped at tick %d", sim.tick)


if __name__ == "__main__":
    main()
