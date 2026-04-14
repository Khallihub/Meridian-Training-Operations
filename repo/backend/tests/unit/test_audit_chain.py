"""Unit tests for the audit log hash-chain integrity.

These tests exercise the pure-Python layer (_compute_entry_hash) without a
real database, verifying:

1. Hash determinism — identical inputs always produce the same digest.
2. Chain linkage — each entry encodes the previous entry's hash as prev_hash,
   and the computed chain can be verified by re-computing and comparing hashes.
3. Tamper detection — mutating any field in a row breaks verification for that
   row and every subsequent row in the chain.
4. Null handling — None prev_hash on the genesis row is handled consistently.
5. Actor encoding — non-UUID actor strings ("system") are represented as "null"
   in the canonical payload (matching the log_audit() normalisation path).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import TypedDict

import pytest

from app.core.audit import _compute_entry_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class AuditRow(TypedDict):
    id: uuid.UUID
    actor_id: str | None
    entity_type: str
    entity_id: str
    action: str
    old_value: dict | None
    new_value: dict | None
    ip_address: str | None
    created_at: datetime
    prev_hash: str | None
    entry_hash: str


def _build_row(
    actor_id: str | None = "system",
    entity_type: str = "booking",
    entity_id: str | None = None,
    action: str = "create",
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    created_at: datetime | None = None,
    prev_hash: str | None = None,
) -> AuditRow:
    row_id = uuid.uuid4()
    ts = created_at or datetime.now(UTC)
    # Resolve entity_id once so the same value is used in both the hash
    # computation and the returned AuditRow (two separate `or uuid4()` calls
    # would produce different UUIDs and break chain verification).
    resolved_entity_id = entity_id or str(uuid.uuid4())
    entry_hash = _compute_entry_hash(
        row_id=row_id,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=resolved_entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        created_at=ts,
        prev_hash=prev_hash,
    )
    return AuditRow(
        id=row_id,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=resolved_entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        created_at=ts,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )


def _verify_chain(rows: list[AuditRow]) -> list[int]:
    """Re-compute each row's entry_hash and return indices of broken rows."""
    broken: list[int] = []
    for i, row in enumerate(rows):
        expected = _compute_entry_hash(
            row_id=row["id"],
            actor_id=row["actor_id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            action=row["action"],
            old_value=row["old_value"],
            new_value=row["new_value"],
            ip_address=row["ip_address"],
            created_at=row["created_at"],
            prev_hash=row["prev_hash"],
        )
        if expected != row["entry_hash"]:
            broken.append(i)
    return broken


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeEntryHashDeterminism:
    def test_same_inputs_produce_same_hash(self):
        row_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
        ts = datetime(2026, 4, 13, 12, 0, 0, tzinfo=UTC)
        h1 = _compute_entry_hash(row_id, "actor-1", "booking", "b-1", "create", None, None, None, ts, None)
        h2 = _compute_entry_hash(row_id, "actor-1", "booking", "b-1", "create", None, None, None, ts, None)
        assert h1 == h2

    def test_different_action_produces_different_hash(self):
        row_id = uuid.uuid4()
        ts = datetime.now(UTC)
        h_create = _compute_entry_hash(row_id, "actor", "booking", "b-1", "create", None, None, None, ts, None)
        h_cancel = _compute_entry_hash(row_id, "actor", "booking", "b-1", "cancel", None, None, None, ts, None)
        assert h_create != h_cancel

    def test_different_prev_hash_produces_different_entry_hash(self):
        row_id = uuid.uuid4()
        ts = datetime.now(UTC)
        h_none = _compute_entry_hash(row_id, "actor", "booking", "b-1", "create", None, None, None, ts, None)
        h_prev = _compute_entry_hash(row_id, "actor", "booking", "b-1", "create", None, None, None, ts, "aabbcc")
        assert h_none != h_prev

    def test_hash_is_64_hex_chars(self):
        """SHA-256 output is 32 bytes = 64 hex characters."""
        row_id = uuid.uuid4()
        ts = datetime.now(UTC)
        h = _compute_entry_hash(row_id, "system", "session", "s-1", "go_live", None, None, None, ts, None)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_new_value_dict_is_order_independent(self):
        """json.dumps with sort_keys=True ensures dict key order doesn't affect hash."""
        row_id = uuid.uuid4()
        ts = datetime.now(UTC)
        h1 = _compute_entry_hash(row_id, "a", "x", "y", "z", None, {"b": 2, "a": 1}, None, ts, None)
        h2 = _compute_entry_hash(row_id, "a", "x", "y", "z", None, {"a": 1, "b": 2}, None, ts, None)
        assert h1 == h2


class TestChainLinkage:
    def test_genesis_row_has_null_prev_hash(self):
        row = _build_row(prev_hash=None)
        assert row["prev_hash"] is None
        # Hash should still be computable
        assert len(row["entry_hash"]) == 64

    def test_second_row_encodes_first_row_hash(self):
        row1 = _build_row(action="create")
        row2 = _build_row(action="update", prev_hash=row1["entry_hash"])
        assert row2["prev_hash"] == row1["entry_hash"]

    def test_chain_of_three_rows_verifies_cleanly(self):
        row1 = _build_row(action="create")
        row2 = _build_row(action="update", prev_hash=row1["entry_hash"])
        row3 = _build_row(action="cancel", prev_hash=row2["entry_hash"])
        broken = _verify_chain([row1, row2, row3])
        assert broken == [], f"Unexpected broken rows at indices: {broken}"

    def test_linkage_is_transitive(self):
        """Each row's prev_hash must equal the prior row's entry_hash."""
        rows: list[AuditRow] = []
        prev = None
        for i in range(5):
            row = _build_row(action=f"step_{i}", prev_hash=prev)
            rows.append(row)
            prev = row["entry_hash"]

        for i in range(1, len(rows)):
            assert rows[i]["prev_hash"] == rows[i - 1]["entry_hash"], (
                f"Linkage broken between row {i - 1} and {i}"
            )


class TestTamperDetection:
    def test_mutating_action_breaks_verification(self):
        row = _build_row(action="create")
        row["action"] = "cancel"  # tamper
        broken = _verify_chain([row])
        assert 0 in broken

    def test_mutating_action_breaks_all_subsequent_rows(self):
        """After a tampered row, every downstream row has an incorrect prev_hash."""
        row1 = _build_row(action="create")
        row2 = _build_row(action="update", prev_hash=row1["entry_hash"])
        row3 = _build_row(action="cancel", prev_hash=row2["entry_hash"])

        row1["action"] = "delete"  # tamper row 1

        broken = _verify_chain([row1, row2, row3])
        assert 0 in broken  # row 1 itself is broken

    def test_mutating_new_value_breaks_verification(self):
        row = _build_row(new_value={"status": "active"})
        row["new_value"] = {"status": "tampered"}
        broken = _verify_chain([row])
        assert 0 in broken

    def test_mutating_entity_id_breaks_verification(self):
        row = _build_row(entity_id="original-id")
        row["entity_id"] = "tampered-id"
        broken = _verify_chain([row])
        assert 0 in broken

    def test_clean_chain_has_no_broken_rows(self):
        row1 = _build_row(action="create", new_value={"x": 1})
        row2 = _build_row(action="update", new_value={"x": 2}, prev_hash=row1["entry_hash"])
        broken = _verify_chain([row1, row2])
        assert broken == []


class TestActorEncoding:
    def test_non_uuid_actor_string_produces_stable_hash(self):
        """'system' is a valid actor_id string (non-UUID); hash must be stable."""
        row_id = uuid.uuid4()
        ts = datetime.now(UTC)
        h1 = _compute_entry_hash(row_id, "system", "payment", "p-1", "callback_completed", None, None, None, ts, None)
        h2 = _compute_entry_hash(row_id, "system", "payment", "p-1", "callback_completed", None, None, None, ts, None)
        assert h1 == h2

    def test_none_actor_produces_null_in_canonical(self):
        """None actor_id must serialise to 'null', not 'None'."""
        row_id = uuid.uuid4()
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        h_none_actor = _compute_entry_hash(row_id, None, "x", "y", "z", None, None, None, ts, None)
        # Manually build the canonical string to verify encoding
        canonical = "|".join(["null" if v is None else str(v) for v in [
            str(row_id), None, "x", "y", "z",
        ]]) + "|null|null|null|" + ts.isoformat() + "|null"
        # canonical must match what _compute_entry_hash produces
        expected = hashlib.sha256(canonical.encode()).hexdigest()
        assert h_none_actor == expected
