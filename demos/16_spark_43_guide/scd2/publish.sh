#!/usr/bin/env bash
# Publish a batch of menu change events to Kafka, one JSON event per line.
docker exec -i s43-kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 --topic menu-changes < "$1"
