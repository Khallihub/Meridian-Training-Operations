"""Unit tests for checkout schemas and order model."""

import uuid

from app.modules.checkout.models import Order, OrderItem, OrderStatus
from app.modules.checkout.schemas import CartCreate


def test_order_status_enum():
    expected = {"awaiting_payment", "paid", "closed_unpaid", "canceled",
                "refund_pending", "refunded_partial", "refunded_full"}
    actual = {s.value for s in OrderStatus}
    assert expected == actual


def test_order_column_defaults():
    table = Order.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["status"].default.arg == OrderStatus.awaiting_payment
    assert cols["currency"].default.arg == "USD"
    assert cols["discount_total"].default.arg == 0
    assert cols["paid_at"].nullable is True


def test_cart_create_schema():
    cart = CartCreate(items=[{"session_id": str(uuid.uuid4()), "quantity": 1}])
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 1


def test_order_item_column_defaults():
    table = OrderItem.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["quantity"].default.arg == 1
