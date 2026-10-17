"""Dual NDJSON output: stdout (streaming) + rotated files (batch).

Thread-safe queue so emission never blocks the simulation loop.
File rotation by event count or elapsed time.
Manifest file tracks output files for Databricks Auto Loader.
"""

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from typing import Any

from cyberpunk_sim.config import SimConfig
from cyberpunk_sim.kafka_sink import KafkaSink


class EventEmitter:
    """Dual-output event emitter with file rotation and manifest tracking."""

    def __init__(self, config: SimConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._queue: Queue[dict[str, Any] | None] = Queue(maxsize=50000)
        self._lock = threading.Lock()

        # File rotation state
        self._file_seq = 0
        self._current_file: Any = None
        self._current_path: Path | None = None
        self._current_count = 0
        self._file_opened_at = time.monotonic()

        # Manifest tracking
        self._manifest_path = self.output_dir / "_manifest.json"
        self._manifest: dict[str, Any] = {"files": [], "total_events": 0}

        # Optional Kafka output (SIM_KAFKA_BOOTSTRAP)
        self._kafka = KafkaSink()
        self._stdout = config.stdout_events

        # Writer thread
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._running = False

    def start(self):
        """Start the background writer thread."""
        self._running = True
        self._writer_thread.start()

    def stop(self):
        """Signal the writer thread to drain and stop."""
        self._running = False
        self._queue.put(None)  # sentinel
        self._writer_thread.join(timeout=10)
        self._close_current_file()
        self._kafka.flush()

    def emit(self, event: dict[str, Any]):
        """Enqueue an event for writing. Non-blocking."""
        self._queue.put(event)

    def _writer_loop(self):
        """Background loop: dequeue events, write to stdout + file."""
        while True:
            event = self._queue.get()
            if event is None:
                # Drain remaining events
                while not self._queue.empty():
                    remaining = self._queue.get()
                    if remaining is not None:
                        self._write_event(remaining)
                break
            self._write_event(event)

    def _write_event(self, event: dict[str, Any]):
        """Write a single event to stdout and the current output file."""
        line = json.dumps(event, separators=(",", ":"), default=str)

        # Stdout, one JSON line per event (SIM_STDOUT_EVENTS=0 to silence)
        if self._stdout:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()

        # Kafka, keyed by the entity the event is about
        self._kafka.send(event, line)

        # File output with rotation
        self._ensure_file()
        self._current_file.write(line + "\n")
        self._current_count += 1

        if self._should_rotate():
            self._rotate_file()

    def _ensure_file(self):
        """Open a new output file if none is open."""
        if self._current_file is None:
            self._open_new_file()

    def _open_new_file(self):
        """Open a fresh output file."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self._file_seq += 1
        filename = f"events_{ts}_{self._file_seq:06d}.ndjson"
        self._current_path = self.output_dir / filename
        self._current_file = open(self._current_path, "w", buffering=1)
        self._current_count = 0
        self._file_opened_at = time.monotonic()

    def _should_rotate(self) -> bool:
        """Check if the current file should be rotated."""
        if self._current_count >= self.config.file_rotation_count:
            return True
        elapsed_minutes = (time.monotonic() - self._file_opened_at) / 60.0
        if elapsed_minutes >= self.config.file_rotation_minutes:
            return True
        return False

    def _rotate_file(self):
        """Close current file, update manifest, open new file."""
        self._close_current_file()
        self._open_new_file()

    def _close_current_file(self):
        """Close the current file and update the manifest."""
        if self._current_file is not None:
            self._current_file.close()
            if self._current_path and self._current_count > 0:
                self._manifest["files"].append({
                    "path": str(self._current_path.name),
                    "record_count": self._current_count,
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                })
                self._manifest["total_events"] += self._current_count
                self._write_manifest()
            self._current_file = None
            self._current_path = None
            self._current_count = 0

    def _write_manifest(self):
        """Write the manifest file atomically."""
        tmp = self._manifest_path.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(self._manifest, f, indent=2)
        tmp.rename(self._manifest_path)
