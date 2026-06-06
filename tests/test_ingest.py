"""Hand-derived answer key for the ingestion layer.

Inputs are a few raw rows with simple round numbers; every assembled value is
derived by hand below. No database, no generated dataset.

Conventions (stated):
  * Demand-averaging window = DEMAND_WINDOW_WEEKS (default 52); dead-stock
    no-movement window = DEAD_STOCK_WINDOW_WEEKS (default 26). Separate.
  * The CURRENT partial week (the week containing reference_date) is EXCLUDED
    from both windows. Only complete prior weeks are counted.
  * avg_weekly_demand = mean of quantity_sold over the weeks present in the
    window. Zero sales rows -> 0.0.
  * target_coverage_days = lead_time_days + z(service_level) * sqrt(lead_time).
    (Cycle stock over the lead time plus a service-level-scaled safety buffer;
    an explainable MVP simplification — real safety stock would use demand std.)
"""

import math
from datetime import date

import pytest

from analytics.ingest import (
    DEAD_STOCK_WINDOW_WEEKS,
    DEMAND_WINDOW_WEEKS,
    assemble_sku,
    compute_avg_weekly_demand,
    compute_on_hand,
    compute_target_coverage_days,
    days_to_expiry,
    service_level_z,
    week_start_of,
    windowed_weekly_sales,
)
from analytics.metrics import days_of_cover, is_dead
from analytics.models import BatchRow, SalesRow, SkuRow

REF = date(2025, 6, 2)  # a Monday; "today" for these fixtures


# ─────────────────────────────────────────────────────────────────────────────
# Named windows are constants, not magic numbers.
# ─────────────────────────────────────────────────────────────────────────────
def test_window_constants_are_named_and_distinct():
    assert DEMAND_WINDOW_WEEKS == 52
    assert DEAD_STOCK_WINDOW_WEEKS == 26


# ─────────────────────────────────────────────────────────────────────────────
# Week alignment: every week is keyed by the Monday of its ISO week.
# ─────────────────────────────────────────────────────────────────────────────
def test_week_start_of_returns_monday():
    assert week_start_of(date(2025, 6, 2)) == date(2025, 6, 2)   # Monday -> itself
    assert week_start_of(date(2025, 6, 4)) == date(2025, 6, 2)   # Wednesday -> Monday
    assert week_start_of(date(2025, 6, 8)) == date(2025, 6, 2)   # Sunday -> same Monday
    assert week_start_of(date(2025, 6, 9)) == date(2025, 6, 9)   # next Monday


# ─────────────────────────────────────────────────────────────────────────────
# avg_weekly_demand: window bound + current partial week excluded.
#   Window = 4 complete weeks before the current week (2025-06-02).
#   Complete weeks: 05-26, 05-19, 05-12, 05-05 with qty 10,20,30,40 -> mean 25.
#   06-02 (current, partial) and 04-28 (out of window) are both excluded.
# ─────────────────────────────────────────────────────────────────────────────
def _demand_sales_rows():
    return [
        SalesRow(date(2025, 6, 2), 999),   # current partial week -> EXCLUDED
        SalesRow(date(2025, 5, 26), 10),
        SalesRow(date(2025, 5, 19), 20),
        SalesRow(date(2025, 5, 12), 30),
        SalesRow(date(2025, 5, 5), 40),
        SalesRow(date(2025, 4, 28), 100),  # older than 4-week window -> EXCLUDED
    ]


def test_avg_weekly_demand_excludes_partial_and_out_of_window():
    avg = compute_avg_weekly_demand(_demand_sales_rows(), REF, window_weeks=4)
    assert avg == pytest.approx(25.0)  # (10+20+30+40)/4


def test_windowed_weekly_sales_returns_only_in_window_quantities():
    qtys = windowed_weekly_sales(_demand_sales_rows(), REF, window_weeks=4)
    assert sorted(qtys) == [10, 20, 30, 40]  # 999 and 100 excluded


def test_avg_weekly_demand_zero_when_no_sales_rows():
    assert compute_avg_weekly_demand([], REF, window_weeks=4) == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# on-hand = sum of batch quantities (multiple batches).
# ─────────────────────────────────────────────────────────────────────────────
def test_on_hand_sums_multiple_batches():
    batches = [
        BatchRow(120.5, date(2025, 4, 1), date(2025, 7, 12)),
        BatchRow(79.5, date(2025, 3, 1), date(2025, 8, 1)),
        BatchRow(100.0, date(2025, 2, 1), None),
    ]
    assert compute_on_hand(batches) == pytest.approx(300.0)


def test_on_hand_zero_when_no_batches():
    assert compute_on_hand([]) == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# days_to_expiry: calendar days from reference; None when non-perishable.
# ─────────────────────────────────────────────────────────────────────────────
def test_days_to_expiry():
    assert days_to_expiry(date(2025, 7, 12), REF) == 40  # 30 (June) + 10
    assert days_to_expiry(None, REF) is None


# ─────────────────────────────────────────────────────────────────────────────
# target coverage = lead + z(service_level) * sqrt(lead).
#   0.95 -> z 1.6449 ; lead 64 -> sqrt 8 -> safety 13.1592 -> target 77.1592
#   0.90 -> z 1.2816 ; lead 36 -> sqrt 6 -> safety  7.6896 -> target 43.6896
# ─────────────────────────────────────────────────────────────────────────────
def test_service_level_z_lookup():
    assert service_level_z(0.95) == pytest.approx(1.6449)
    assert service_level_z(0.90) == pytest.approx(1.2816)


def test_target_coverage_from_lead_and_service_level():
    assert compute_target_coverage_days(64, 0.95) == pytest.approx(64 + 1.6449 * 8)
    assert compute_target_coverage_days(64, 0.95) == pytest.approx(77.1592)
    assert compute_target_coverage_days(36, 0.90) == pytest.approx(43.6896)


# ─────────────────────────────────────────────────────────────────────────────
# assemble_sku integration — a tiny multi-batch SKU.
# ─────────────────────────────────────────────────────────────────────────────
def test_assemble_sku_multi_batch():
    sku_row = SkuRow(
        sku_code="T1", unit_cost=100, selling_price=130, is_perishable=True,
        shelf_life_days=180, service_level_target=0.95, lead_time_days=64,
    )
    sales_rows = _demand_sales_rows()
    batch_rows = [
        BatchRow(120.5, date(2025, 4, 1), date(2025, 7, 12)),  # 40 days out
        BatchRow(79.5, date(2025, 3, 1), date(2025, 8, 1)),    # 60 days out
    ]
    sku = assemble_sku(sku_row, sales_rows, batch_rows, REF,
                       demand_window_weeks=4, dead_window_weeks=4)

    assert sku.sku_code == "T1"
    assert sku.on_hand == pytest.approx(200.0)           # 120.5 + 79.5
    assert sku.avg_weekly_demand == pytest.approx(25.0)  # (10+20+30+40)/4
    assert sku.unit_cost == pytest.approx(100)
    assert sku.selling_price == pytest.approx(130)
    assert sku.is_perishable is True
    assert sku.lead_time_days == pytest.approx(64)
    assert sku.target_coverage_days == pytest.approx(77.1592)

    # Batches assembled with calendar days-to-expiry, order preserved.
    assert len(sku.batches) == 2
    assert sku.batches[0].quantity_on_hand == pytest.approx(120.5)
    assert sku.batches[0].days_to_expiry == 40
    assert sku.batches[1].days_to_expiry == 60

    # Dead-stock window populated (4 complete weeks) and SKU is alive.
    assert sum(sku.recent_weekly_sales) == pytest.approx(100.0)  # 10+20+30+40
    assert is_dead(sku.recent_weekly_sales, sku.dead_window_weeks) is False


# ─────────────────────────────────────────────────────────────────────────────
# assemble_sku edge — a SKU with ZERO sales rows.
#   avg demand 0 -> days_of_cover undefined (None); empty window -> reads as dead.
# ─────────────────────────────────────────────────────────────────────────────
def test_assemble_sku_zero_sales_rows():
    sku_row = SkuRow(
        sku_code="T0", unit_cost=500, selling_price=650, is_perishable=False,
        shelf_life_days=None, service_level_target=0.90, lead_time_days=36,
    )
    batch_rows = [BatchRow(50.0, date(2025, 1, 1), None)]
    sku = assemble_sku(sku_row, [], batch_rows, REF,
                       demand_window_weeks=4, dead_window_weeks=4)

    assert sku.on_hand == pytest.approx(50.0)
    assert sku.avg_weekly_demand == pytest.approx(0.0)
    assert sku.target_coverage_days == pytest.approx(43.6896)  # 36 + 1.2816*6
    assert sku.recent_weekly_sales == []
    # No demand -> coverage is undefined, and no movement -> dead.
    assert days_of_cover(sku.on_hand, sku.avg_weekly_demand) is None
    assert is_dead(sku.recent_weekly_sales, sku.dead_window_weeks) is True

    # Non-perishable batch carries no expiry.
    assert sku.batches[0].days_to_expiry is None
