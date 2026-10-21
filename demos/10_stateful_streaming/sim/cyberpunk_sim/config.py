"""Env-var-driven simulation configuration."""

import os
from dataclasses import dataclass


@dataclass
class SimConfig:
    seed: int = 42
    tick_ms: int = 100
    agents_per_tick: int = 10
    max_ticks: int = 0  # 0 = infinite
    file_rotation_count: int = 10000
    file_rotation_minutes: int = 5
    log_level: str = "INFO"
    output_dir: str = ""
    stdout_events: bool = True

    @classmethod
    def from_env(cls) -> "SimConfig":
        default_output = "/output" if os.path.isdir("/output") else os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "output"
        )
        return cls(
            seed=int(os.environ.get("SIM_SEED", 42)),
            tick_ms=int(os.environ.get("SIM_TICK_MS", 100)),
            agents_per_tick=int(os.environ.get("SIM_AGENTS_PER_TICK", 10)),
            max_ticks=int(os.environ.get("SIM_MAX_TICKS", 0)),
            file_rotation_count=int(os.environ.get("SIM_FILE_ROTATION_COUNT", 10000)),
            file_rotation_minutes=int(os.environ.get("SIM_FILE_ROTATION_MINUTES", 5)),
            log_level=os.environ.get("SIM_LOG_LEVEL", "INFO"),
            output_dir=os.environ.get("SIM_OUTPUT_DIR", default_output),
            stdout_events=os.environ.get("SIM_STDOUT_EVENTS", "1") not in ("0", "false", "no"),
        )
