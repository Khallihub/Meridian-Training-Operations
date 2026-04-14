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
        promos = [make_promo("10% off", PromotionType.percent_off, 10.0)]
        result = compute_best_offer(promos, 100.0, {"course-1"})
        assert len(result) == 1
        assert result[0].discount_amount == pytest.approx(10.0)

    def test_fixed_off_promo(self):
        promos = [make_promo("$25 off", PromotionType.fixed_off, 25.0)]
        result = compute_best_offer(promos, 200.0, {"course-1"})
        assert result[0].discount_amount == pytest.approx(25.0)

    def test_null_group_mutual_exclusion_picks_best(self):
        """Two null-group promos — only the better one applies."""
        p1 = make_promo("5% off", PromotionType.percent_off, 5.0)   # discount = 5
        p2 = make_promo("10% off", PromotionType.percent_off, 10.0)  # discount = 10
        result = compute_best_offer([p1, p2], 100.0, {"c"})
        # Only one should apply (the better one)
        assert len(result) == 1
        assert result[0].discount_amount == pytest.approx(10.0)

    def test_different_named_groups_stack(self):
        """Promos in different named groups should stack."""
        p1 = make_promo("10% off", PromotionType.percent_off, 10.0, stack_group="group_a")
        p2 = make_promo("$20 off", PromotionType.fixed_off, 20.0, stack_group="group_b")
        result = compute_best_offer([p1, p2], 200.0, {"c"})
        total = sum(a.discount_amount for a in result)
        assert total == pytest.approx(40.0)  # 10% of 200 + 20

    def test_same_named_group_mutually_exclusive(self):
        """Two promos in the same named group — only best applies."""
        p1 = make_promo("5% off", PromotionType.percent_off, 5.0, stack_group="summer")
        p2 = make_promo("15% off", PromotionType.percent_off, 15.0, stack_group="summer")
        result = compute_best_offer([p1, p2], 100.0, {"c"})
        assert len(result) == 1
        assert result[0].discount_amount == pytest.approx(15.0)

    def test_exclusive_promo_not_combined(self):
        """Exclusive promo tested alone; if better, wins alone."""
        excl = make_promo("50% exclusive", PromotionType.percent_off, 50.0, is_exclusive=True)
        other = make_promo("10% off", PromotionType.percent_off, 10.0, stack_group="g1")
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
        promo = make_promo("200% off", PromotionType.percent_off, 200.0)
        result = compute_best_offer([promo], 50.0, {"c"})
        total = sum(a.discount_amount for a in result)
        assert total <= 50.0

    def test_no_promos_returns_empty(self):
        result = compute_best_offer([], 100.0, {"c"})
        assert result == []

    def test_explanation_text_present(self):
        promo = make_promo("10% off", PromotionType.percent_off, 10.0)
        result = compute_best_offer([promo], 100.0, {"c"})
        assert "10%" in result[0].explanation


class TestTieBreakDeterminism:
    """Verify that equal-discount promotions always resolve in the same order."""

    def _make_with_priority(
        self,
        name: str,
        value: float,
        priority: int,
        fixed_id: uuid.UUID | None = None,
    ) -> Promotion:
        p = make_promo(name, PromotionType.percent_off, value)
        p.priority = priority
        if fixed_id is not None:
            p.id = fixed_id
        return p

    def test_lower_priority_value_wins_on_equal_discount(self):
        """Priority=1 should beat Priority=2 when discounts are identical."""
        id_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        id_b = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        high_prio = self._make_with_priority("High prio", 10.0, 1, fixed_id=id_a)
        low_prio = self._make_with_priority("Low prio", 10.0, 2, fixed_id=id_b)
        # Regardless of input order, high_prio (priority=1) must win.
        result_ab = compute_best_offer([high_prio, low_prio], 100.0, {"c"})
        result_ba = compute_best_offer([low_prio, high_prio], 100.0, {"c"})
        assert result_ab[0].promotion.name == "High prio"
        assert result_ba[0].promotion.name == "High prio"

    def test_lower_uuid_breaks_tie_when_priority_equal(self):
        """When both discount and priority are equal, lexicographically lower UUID wins."""
        id_low = uuid.UUID("00000000-0000-0000-0000-000000000001")
        id_high = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        p_low_id = self._make_with_priority("Low-ID promo", 10.0, 0, fixed_id=id_low)
        p_high_id = self._make_with_priority("High-ID promo", 10.0, 0, fixed_id=id_high)
        result_fwd = compute_best_offer([p_low_id, p_high_id], 100.0, {"c"})
        result_rev = compute_best_offer([p_high_id, p_low_id], 100.0, {"c"})
        assert result_fwd[0].promotion.id == id_low
        assert result_rev[0].promotion.id == id_low

    def test_named_group_tie_break_deterministic(self):
        """Tie-break applies inside named groups too."""
        id_a = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        id_b = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        p1 = make_promo("P1", PromotionType.percent_off, 10.0, stack_group="grp")
        p2 = make_promo("P2", PromotionType.percent_off, 10.0, stack_group="grp")
        p1.id = id_a
        p1.priority = 0
        p2.id = id_b
        p2.priority = 0
        # id_a < id_b → p1 must always win
        result = compute_best_offer([p2, p1], 100.0, {"c"})
        assert result[0].promotion.id == id_a
