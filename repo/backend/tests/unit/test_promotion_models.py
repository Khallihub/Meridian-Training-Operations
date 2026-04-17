"""Unit tests for promotion models."""

from app.modules.promotions.models import Promotion, PromotionType


def test_promotion_type_enum():
    expected = {"percent_off", "fixed_off", "threshold_fixed_off", "bogo_selected_workshops"}
    actual = {t.value for t in PromotionType}
    assert expected == actual


def test_promotion_column_defaults():
    table = Promotion.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["is_active"].default.arg is True
    assert cols["is_exclusive"].default.arg is False
    assert cols["stack_group"].nullable is True
    assert cols["min_order_amount"].nullable is True


def test_promotion_exclusive_flag():
    """Exclusive flag column exists and defaults to False."""
    table = Promotion.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["is_exclusive"].default.arg is False
