"""Unit tests for the best-offer promotion engine."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.checkout.best_offer import compute_best_offer
from app.modules.promotions.models import Promotion, PromotionType


def make_promo(
    name: str,
    ptype: PromotionType,
    value: float,
    stack_group: str | None = None,
    is_exclusive: bool = False,
    min_order_amount: float | None = None,
) -> Promotion:
    p = Promotion()
    p.id = uuid.uuid4()
    p.name = name
    p.type = ptype
    p.value = value
    p.stack_group = stack_group
    p.is_exclusive = is_exclusive
    p.min_order_amount = min_order_amount
    p.applies_to = {"all": True}
    p.is_active = True
    p.valid_from = datetime.now(UTC) - timedelta(hours=1)
    p.valid_until = datetime.now(UTC) + timedelta(hours=1)
    return p


class TestBestOfferEngine:
    def test_single_pct_promo(self):
        promos = [make_promo("10% off", PromotionType.pct_off, 10.0)]
        result = compute_best_offer(promos, 100.0, {"course-1"})
        assert len(result) == 1
        assert result[0].discount_amount == pytest.approx(10.0)

    def test_fixed_off_promo(self):
        promos = [make_promo("$25 off", PromotionType.fixed_off, 25.0)]
        result = compute_best_offer(promos, 200.0, {"course-1"})
        assert result[0].discount_amount == pytest.approx(25.0)

    def test_null_group_mutual_exclusion_picks_best(self):
        """Two null-group promos — only the better one applies."""
        p1 = make_promo("5% off", PromotionType.pct_off, 5.0)   # discount = 5
        p2 = make_promo("10% off", PromotionType.pct_off, 10.0)  # discount = 10
        result = compute_best_offer([p1, p2], 100.0, {"c"})
        # Only one should apply (the better one)
        assert len(result) == 1
        assert result[0].discount_amount == pytest.approx(10.0)

    def test_different_named_groups_stack(self):
        """Promos in different named groups should stack."""
        p1 = make_promo("10% off", PromotionType.pct_off, 10.0, stack_group="group_a")
        p2 = make_promo("$20 off", PromotionType.fixed_off, 20.0, stack_group="group_b")
        result = compute_best_offer([p1, p2], 200.0, {"c"})
        total = sum(a.discount_amount for a in result)
        assert total == pytest.approx(40.0)  # 10% of 200 + 20

    def test_same_named_group_mutually_exclusive(self):
        """Two promos in the same named group — only best applies."""
        p1 = make_promo("5% off", PromotionType.pct_off, 5.0, stack_group="summer")
        p2 = make_promo("15% off", PromotionType.pct_off, 15.0, stack_group="summer")
        result = compute_best_offer([p1, p2], 100.0, {"c"})
        assert len(result) == 1
        assert result[0].discount_amount == pytest.approx(15.0)

    def test_exclusive_promo_not_combined(self):
        """Exclusive promo tested alone; if better, wins alone."""
        excl = make_promo("50% exclusive", PromotionType.pct_off, 50.0, is_exclusive=True)
        other = make_promo("10% off", PromotionType.pct_off, 10.0, stack_group="g1")
        result = compute_best_offer([excl, other], 100.0, {"c"})
        assert len(result) == 1
        assert result[0].promotion.name == "50% exclusive"

    def test_min_order_amount_not_met(self):
        """Promo with min_order_amount higher than subtotal should not apply."""
        promo = make_promo("$25 off $200+", PromotionType.fixed_off, 25.0, min_order_amount=200.0)
        result = compute_best_offer([promo], 100.0, {"c"})
        assert len(result) == 0

    def test_discount_capped_at_subtotal(self):
        """Discount can never exceed subtotal."""
        promo = make_promo("200% off", PromotionType.pct_off, 200.0)
        result = compute_best_offer([promo], 50.0, {"c"})
        total = sum(a.discount_amount for a in result)
        assert total <= 50.0

    def test_no_promos_returns_empty(self):
        result = compute_best_offer([], 100.0, {"c"})
        assert result == []

    def test_explanation_text_present(self):
        promo = make_promo("10% off", PromotionType.pct_off, 10.0)
        result = compute_best_offer([promo], 100.0, {"c"})
        assert "10%" in result[0].explanation
