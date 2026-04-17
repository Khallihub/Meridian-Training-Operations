"""Unit tests for payment and refund models."""

from app.modules.payments.models import Payment, PaymentStatus, Refund, RefundStatus, ReconciliationExport


def test_payment_status_enum():
    expected = {"pending", "completed", "failed"}
    actual = {s.value for s in PaymentStatus}
    assert expected == actual


def test_refund_status_enum():
    expected = {"requested", "pending_review", "approved", "processing", "completed", "rejected", "failed", "canceled"}
    actual = {s.value for s in RefundStatus}
    assert expected == actual


def test_payment_column_defaults():
    table = Payment.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["status"].default.arg == PaymentStatus.pending
    assert cols["signature_verified"].default.arg is False
    assert cols["terminal_ref"].nullable is True
    assert cols["external_event_id"].nullable is True


def test_refund_column_defaults():
    table = Refund.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["status"].default.arg == RefundStatus.requested
    assert cols["reason"].nullable is True
    assert cols["processed_at"].nullable is True


def test_reconciliation_export_table():
    assert ReconciliationExport.__tablename__ == "reconciliation_exports"
    table = ReconciliationExport.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["row_count"].default.arg == 0
