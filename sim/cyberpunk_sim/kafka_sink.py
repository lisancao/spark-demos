"""Optional Kafka output for simulation events.

Enabled when SIM_KAFKA_BOOTSTRAP is set. Each event is produced to one topic,
keyed by the entity the event is about (agent, faction, mission, location),
so that a stateful consumer grouping by that entity sees its events in order.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("nightcity.kafka")


def partition_key(event: dict[str, Any]) -> str:
    """Pick the entity id a stateful consumer would key on."""
    for field in ("agent_id", "faction_id", "mission_id", "source_id", "lobby_id", "location_id"):
        value = event.get(field)
        if value:
            return str(value)
    return event.get("event_type", "world")


class KafkaSink:
    """Thin confluent-kafka producer wrapper; no-op when not configured."""

    def __init__(self, bootstrap: str | None = None, topic: str | None = None):
        self.bootstrap = bootstrap or os.environ.get("SIM_KAFKA_BOOTSTRAP", "")
        self.topic = topic or os.environ.get("SIM_KAFKA_TOPIC", "nightcity.events")
        self._producer = None
        if self.bootstrap:
            from confluent_kafka import Producer  # imported lazily: optional dependency

            self._producer = Producer({
                "bootstrap.servers": self.bootstrap,
                "linger.ms": 20,
                "batch.num.messages": 10000,
                "compression.type": "lz4",
                "acks": "all",
                "enable.idempotence": True,
            })
            logger.info("Kafka sink enabled: %s topic=%s", self.bootstrap, self.topic)

    @property
    def enabled(self) -> bool:
        return self._producer is not None

    def send(self, event: dict[str, Any], line: str | None = None):
        if self._producer is None:
            return
        payload = line if line is not None else json.dumps(event, separators=(",", ":"), default=str)
        self._producer.produce(self.topic, key=partition_key(event), value=payload)
        self._producer.poll(0)

    def flush(self, timeout: float = 10.0):
        if self._producer is not None:
            self._producer.flush(timeout)
