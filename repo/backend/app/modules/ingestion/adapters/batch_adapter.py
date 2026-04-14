"""Batch file ingestion adapter (CSV/JSON)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


def _file_fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _row_fingerprint(row: dict, source_id: str) -> str:
    """Compute the PRD-specified dedup fingerprint.

    Canonical tuple: ``source_id | source_record_id | event_time | payload_sig``

    - ``source_record_id`` is extracted from the first matching field name
      (``source_record_id``, ``record_id``, ``id``, ``_id``).
    - ``event_time`` is extracted from the first matching field name
      (``event_time``, ``timestamp``, ``created_at``, ``updated_at``).
    - ``payload_sig`` is a SHA-256 of the full sorted-JSON row so no field
      is silently dropped from the fingerprint.
    """
    source_record_id = str(
        row.get("source_record_id")
        or row.get("record_id")
        or row.get("id")
        or row.get("_id")
        or ""
    )
    event_time = str(
        row.get("event_time")
        or row.get("timestamp")
        or row.get("created_at")
        or row.get("updated_at")
        or ""
    )
    payload_sig = hashlib.sha256(
        json.dumps(row, sort_keys=True, default=str).encode()
    ).hexdigest()
    canonical = f"{source_id}|{source_record_id}|{event_time}|{payload_sig}"
    return hashlib.sha256(canonical.encode()).hexdigest()


def parse_file(content: bytes, filename: str) -> list[dict[str, Any]]:
    if filename.endswith(".json"):
        data = json.loads(content.decode())
        return data if isinstance(data, list) else [data]
    else:  # CSV
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        return list(reader)


def filter_duplicates(rows: list[dict], source_id: str, redis_client) -> list[dict]:
    """Remove already-seen rows using Redis dedup set.

    Fingerprint uses the PRD-specified tuple:
    ``source_id | source_record_id | event_time | payload_sig``
    """
    fresh = []
    pipe = redis_client.pipeline()
    for row in rows:
        fp = _row_fingerprint(row, source_id)
        key = f"ingest_dedup:{source_id}:{fp}"
        pipe.set(key, "1", ex=604800, nx=True)  # 7-day TTL, only set if not exists
    results = pipe.execute()
    for row, was_new in zip(rows, results):
        if was_new:
            fresh.append(row)
    return fresh


def test_connectivity(config: dict) -> tuple[bool, float | None, str | None]:
    watch_dir = config.get("watch_dir", "/app/uploads")
    t0 = time.monotonic()
    if os.path.isdir(watch_dir):
        return True, round((time.monotonic() - t0) * 1000, 1), None
    return False, None, f"Directory not found: {watch_dir}"
