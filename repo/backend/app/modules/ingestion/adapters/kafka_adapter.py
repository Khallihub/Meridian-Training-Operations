"""Kafka ingestion adapter."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def test_connectivity(config: dict) -> tuple[bool, float | None, str | None]:
    try:
        from confluent_kafka import Consumer, KafkaException
        t0 = time.monotonic()
        c = Consumer({
            "bootstrap.servers": config["bootstrap_servers"],
            "group.id": config.get("group_id", "meridian-test"),
            "auto.offset.reset": "latest",
            "session.timeout.ms": 3000,
        })
        c.subscribe([config["topic"]])
        c.poll(timeout=2.0)
        c.close()
        latency = (time.monotonic() - t0) * 1000
        return True, round(latency, 1), None
    except Exception as e:
        return False, None, str(e)


def consume_batch(config: dict, max_messages: int = 100, source_id: str | None = None, redis_client=None) -> tuple[list[dict[str, Any]], int]:
    from confluent_kafka import Consumer, KafkaException
    c = Consumer({
        "bootstrap.servers": config["bootstrap_servers"],
        "group.id": config.get("group_id", "meridian-ingest"),
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })
    c.subscribe([config["topic"]])
    messages: list[dict] = []
    try:
        deadline = time.monotonic() + 10.0
        while len(messages) < max_messages and time.monotonic() < deadline:
            msg = c.poll(timeout=1.0)
            if msg is None:
                break
            if msg.error():
                logger.warning("Kafka error: %s", msg.error())
                continue
            try:
                messages.append(json.loads(msg.value().decode("utf-8")))
            except Exception:
                pass
    finally:
        c.close()

    if source_id and redis_client and messages:
        from app.modules.ingestion.adapters.batch_adapter import filter_duplicates
        messages = filter_duplicates(messages, source_id, redis_client)

    return messages, len(messages)
