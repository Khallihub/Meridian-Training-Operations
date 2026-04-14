"""
Best-offer promotion engine.

Default behavior: MUTUAL EXCLUSION (per spec).
- null stack_group  → singleton exclusive group; only best one from all null-group promos applies
- same stack_group  → mutually exclusive within group (best one per group)
- different non-null groups → stackable across groups
- is_exclusive=True → cannot combine with anything, even across groups
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.modules.promotions.models import Promotion, PromotionType


@dataclass
class AppliedPromotion:
    promotion: Promotion
    discount_amount: float
    explanation: str


def _calc_discount(
    promo: Promotion,
    subtotal: float,
    course_ids: set[str],
    item_prices: list[float] | None = None,
) -> float:
    """Calculate the discount amount a single promotion provides on the subtotal."""
    # Check minimum order amount
    if promo.min_order_amount and subtotal < float(promo.min_order_amount):
        return 0.0

    # Check course scope
    applies = promo.applies_to or {}
    if not applies.get("all"):
        allowed_course_ids = set(applies.get("course_ids", []))
        if not allowed_course_ids.intersection(course_ids):
            return 0.0

    if promo.type == PromotionType.percent_off:
        return round(subtotal * float(promo.value) / 100, 2)
    elif promo.type == PromotionType.fixed_off:
        return round(min(float(promo.value), subtotal), 2)
    elif promo.type == PromotionType.threshold_fixed_off:
        # Apply a fixed discount only when order meets the minimum amount threshold.
        # min_order_amount acts as the threshold; value is the fixed discount amount.
        threshold = float(promo.min_order_amount or 0)
        if subtotal < threshold:
            return 0.0
        return round(min(float(promo.value), subtotal), 2)
    elif promo.type == PromotionType.bogo_selected_workshops:
        # Buy-one-get-one for every 2 eligible units: cheapest unit in each pair is free.
        # Requires item_prices for accurate calculation; falls back to 50% if unavailable.
        if item_prices and len(item_prices) >= 2:
            sorted_prices = sorted(item_prices)  # cheapest first
            free_count = len(sorted_prices) // 2
            discount = sum(sorted_prices[:free_count])
            return round(min(discount, subtotal), 2)
        # Fallback when item breakdown is unavailable
        return round(subtotal * 0.5, 2)
    return 0.0


def _build_explanation(promo: Promotion, discount: float) -> str:
    if promo.type == PromotionType.percent_off:
        return f"{promo.name}: {promo.value}% off → -${discount:.2f}"
    elif promo.type == PromotionType.fixed_off:
        return f"{promo.name}: ${promo.value:.2f} off → -${discount:.2f}"
    elif promo.type == PromotionType.threshold_fixed_off:
        return f"{promo.name}: ${promo.value:.2f} off (threshold met) → -${discount:.2f}"
    elif promo.type == PromotionType.bogo_selected_workshops:
        return f"{promo.name}: BOGO — cheapest workshop free → -${discount:.2f}"
    return f"{promo.name}: -${discount:.2f}"


def _promo_sort_key(promo: Promotion, discount: float) -> tuple:
    """Deterministic comparison key: best discount first, then lowest priority, then lowest ID."""
    return (-discount, promo.priority, str(promo.id))


def _group_promotions(promotions: list[Promotion]) -> dict[str | None, list[Promotion]]:
    """Group promotions by stack_group. None-keyed = singleton/exclusive group."""
    groups: dict[str | None, list[Promotion]] = {}
    for p in promotions:
        groups.setdefault(p.stack_group, []).append(p)
    return groups


def compute_best_offer(
    promotions: list[Promotion],
    subtotal: float,
    course_ids: set[str],
    item_prices: list[float] | None = None,
) -> list[AppliedPromotion]:
    """
    Returns the combination of promotions that maximises discount.

    Stack rules (mutual exclusion by default):
    - is_exclusive promotions: tested alone only; never combined.
    - null stack_group: only the single best promo from the entire null pool applies.
    - same non-null stack_group: only the best promo from that group.
    - different non-null groups: one from each group may stack.
    """
    now = datetime.now(UTC)
    valid = [
        p for p in promotions
        if p.is_active and p.valid_from <= now <= p.valid_until
    ]

    if not valid:
        return []

    # --- Step 1: separate exclusive promos ---
    exclusive = [p for p in valid if p.is_exclusive]
    non_exclusive = [p for p in valid if not p.is_exclusive]

    def _apply_single(promo: Promotion) -> list[AppliedPromotion]:
        d = _calc_discount(promo, subtotal, course_ids, item_prices)
        if d <= 0:
            return []
        return [AppliedPromotion(promo, d, _build_explanation(promo, d))]

    best: list[AppliedPromotion] = []
    best_total: float = 0.0

    # --- Step 2: test each exclusive promo alone ---
    # Tie-break: discount DESC → priority ASC → promotion_id ASC
    best_key: tuple = (0.0, 0, "")  # (discount, priority, id) — inverted for comparison
    for p in exclusive:
        candidate = _apply_single(p)
        total = sum(a.discount_amount for a in candidate)
        key = _promo_sort_key(p, total)
        if total > best_total or (total == best_total and total > 0 and key < best_key):
            best_total = total
            best = candidate
            best_key = key

    # --- Step 3: group non-exclusive promos ---
    groups = _group_promotions(non_exclusive)

    # Separate null-group (mutually exclusive by default) from named groups
    null_group = groups.pop(None, [])
    named_groups = groups  # dict[str, list[Promotion]]

    # From the null group, pick the single best promo using deterministic tie-break
    best_null: Promotion | None = None
    best_null_discount: float = 0.0
    best_null_key: tuple = (0.0, 0, "")
    for p in null_group:
        d = _calc_discount(p, subtotal, course_ids, item_prices)
        key = _promo_sort_key(p, d)
        if d > best_null_discount or (d == best_null_discount and d > 0 and key < best_null_key):
            best_null_discount = d
            best_null = p
            best_null_key = key

    # For each named group, pick the best promo using deterministic tie-break
    best_per_group: dict[str, tuple[Promotion, float]] = {}
    for group_name, promos in named_groups.items():
        best_p: Promotion | None = None
        best_d: float = 0.0
        best_pg_key: tuple = (0.0, 0, "")
        for p in promos:
            d = _calc_discount(p, subtotal, course_ids, item_prices)
            key = _promo_sort_key(p, d)
            if d > best_d or (d == best_d and d > 0 and key < best_pg_key):
                best_d = d
                best_p = p
                best_pg_key = key
        if best_p and best_d > 0:
            best_per_group[group_name] = (best_p, best_d)

    # --- Step 4: stack best-per-named-group + optional best-null ---
    # Build candidate combination: one from each named group (stackable) + best null
    candidate: list[AppliedPromotion] = []
    for group_name, (p, d) in best_per_group.items():
        candidate.append(AppliedPromotion(p, d, _build_explanation(p, d)))
    if best_null and best_null_discount > 0:
        candidate.append(AppliedPromotion(best_null, best_null_discount, _build_explanation(best_null, best_null_discount)))

    candidate_total = sum(a.discount_amount for a in candidate)
    if candidate_total > best_total:
        best_total = candidate_total
        best = candidate

    # Cap: discount cannot exceed subtotal
    if best_total > subtotal:
        # Scale down proportionally
        factor = subtotal / best_total
        best = [
            AppliedPromotion(a.promotion, round(a.discount_amount * factor, 2), a.explanation)
            for a in best
        ]

    return best
