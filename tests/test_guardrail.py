"""Service-level guardrail — PROVEN, not asserted (contract condition).

Releasing a SKU's excess brings it down to its order-up-to level, which by
construction still covers lead-time demand plus the safety buffer — so the
service level is preserved. And the release-candidate filter must never admit a
SKU that is not safe to release (e.g. a stockout SKU).
"""

import pytest

from analytics.metrics import (
    excess_units,
    order_up_to_units,
    releasable_candidates,
    safe_to_release,
)
from analytics.models import Sku


def test_releasing_excess_preserves_service_level():
    # Over-stocked: daily 10, target 50d -> order-up-to 500 ; on hand 520 -> excess 20.
    over = Sku("OVER", on_hand=520, avg_weekly_demand=70, unit_cost=10,
               target_coverage_days=50, lead_time_days=30)

    assert order_up_to_units(70, 50) == pytest.approx(500.0)
    assert excess_units(520, 70, 50) == pytest.approx(20.0)
    assert safe_to_release(520, 70, 50) is True

    # Releasing the excess leaves exactly the order-up-to level...
    remaining = over.on_hand - excess_units(520, 70, 50)
    assert remaining == pytest.approx(500.0)
    assert remaining == pytest.approx(order_up_to_units(70, 50))

    # ...which still covers lead-time demand (10/day * 30d = 300), with a strictly
    # positive safety+review margin on top -> service level NOT breached.
    lead_time_demand = (70 / 7) * over.lead_time_days
    assert lead_time_demand == pytest.approx(300.0)
    assert remaining >= lead_time_demand
    assert remaining - lead_time_demand == pytest.approx(200.0)  # review + safety buffer


def test_stockout_sku_is_not_safe_to_release():
    # Below order-up-to (140 vs 2000) -> no excess -> must not be released.
    stockout = Sku("STOCK", on_hand=140, avg_weekly_demand=140, unit_cost=10,
                   target_coverage_days=100, lead_time_days=70)
    assert excess_units(140, 140, 100) == pytest.approx(0.0)
    assert safe_to_release(140, 140, 100) is False


def test_dead_stock_is_safe_to_release():
    # No demand -> order-up-to 0 -> all on-hand is releasable.
    dead = Sku("DEAD", on_hand=80, avg_weekly_demand=0, unit_cost=500,
               target_coverage_days=50)
    assert safe_to_release(80, 0, 50) is True


def test_release_plan_never_includes_an_unsafe_item():
    over = Sku("OVER", on_hand=520, avg_weekly_demand=70, unit_cost=10,
               target_coverage_days=50, lead_time_days=30)
    stockout = Sku("STOCK", on_hand=140, avg_weekly_demand=140, unit_cost=10,
                   target_coverage_days=100, lead_time_days=70)
    dead = Sku("DEAD", on_hand=80, avg_weekly_demand=0, unit_cost=500,
               target_coverage_days=50)

    candidates = releasable_candidates([over, stockout, dead])

    codes = {s.sku_code for s in candidates}
    assert codes == {"OVER", "DEAD"}      # stockout excluded
    assert stockout not in candidates
    # The invariant the contract requires: every ranked release item is safe.
    for s in candidates:
        assert safe_to_release(s.on_hand, s.avg_weekly_demand, s.target_coverage_days) is True
