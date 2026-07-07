"""Hand-derived answer key for the analytics core — the seven approved fixtures.

Inputs are in-memory and use simple round numbers; every expected value can be
worked out by hand (see the conversation's fixture approvals). No database.

Conventions (approved):
  * avg_daily_demand = avg_weekly_demand / 7
  * DAYS_PER_MONTH = 30 (months of cover)
  * stockout window = snapshot exposure: out of stock for (lead_time - cover) days
  * value-at-stake de-dups dead vs excess: a dead SKU counts once, at full value
"""

import pytest

from analytics.metrics import (
    days_of_cover,
    dead_stock_value,
    excess_units,
    excess_value,
    is_dead,
    months_of_cover,
    releasable_cash_contribution,
    sku_expiry_at_risk_units,
    sku_expiry_writeoff,
    stockout_margin_loss,
    stockout_shortfall_days,
    value_at_stake,
)
from analytics.models import Batch, Sku


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 1 — DIO / months of cover
#   daily = weekly/7 ; DIO = on_hand/daily ; months = DIO/30
# ─────────────────────────────────────────────────────────────────────────────
def test_fixture1_dio_and_months_of_cover():
    # M1-A: 900 on hand, 70/wk -> daily 10 -> 90 days -> 3.0 months
    assert days_of_cover(900, 70) == pytest.approx(90.0)
    assert months_of_cover(900, 70) == pytest.approx(3.0)

    # M1-B: 150 on hand, 70/wk -> daily 10 -> 15 days -> 0.5 months
    assert days_of_cover(150, 70) == pytest.approx(15.0)
    assert months_of_cover(150, 70) == pytest.approx(0.5)

    # M1-C: 600 on hand, 140/wk -> daily 20 -> 30 days -> 1.0 month
    assert days_of_cover(600, 140) == pytest.approx(30.0)
    assert months_of_cover(600, 140) == pytest.approx(1.0)

    # M1-D: 80 on hand, 0/wk -> daily 0 -> undefined (no demand), reported as None
    assert days_of_cover(80, 0) is None
    assert months_of_cover(80, 0) is None


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 2 — Excess (stock above target coverage)
#   target_stock = daily * target_days ; excess = max(0, on_hand - target_stock)
# ─────────────────────────────────────────────────────────────────────────────
def test_fixture2_excess():
    # E1-A: 900 @ daily 10, target 30 -> target 300 -> excess 600 -> 30,000
    assert excess_units(900, 70, 30) == pytest.approx(600.0)
    assert excess_value(900, 70, 30, 50) == pytest.approx(30_000.0)

    # E1-B: 150 @ daily 10, target 30 -> target 300 -> excess clamped to 0
    assert excess_units(150, 70, 30) == pytest.approx(0.0)
    assert excess_value(150, 70, 30, 50) == pytest.approx(0.0)

    # E1-C: 600 @ daily 20, target 20 -> target 400 -> excess 200 -> 20,000
    assert excess_units(600, 140, 20) == pytest.approx(200.0)
    assert excess_value(600, 140, 20, 100) == pytest.approx(20_000.0)

    # Total across the fixture
    total = (
        excess_value(900, 70, 30, 50)
        + excess_value(150, 70, 30, 50)
        + excess_value(600, 140, 20, 100)
    )
    assert total == pytest.approx(50_000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 3 — Dead stock (no movement in last N=26 weeks)
# ─────────────────────────────────────────────────────────────────────────────
def test_fixture3_dead_stock():
    # D1-A: zero sales in last 26 weeks -> DEAD ; value = 80 * 500 = 40,000
    d1a = [0.0] * 26
    assert is_dead(d1a, 26) is True
    assert dead_stock_value(80, 500) == pytest.approx(40_000.0)

    # D1-B: a sale 8 weeks ago (3 units in window) -> alive
    d1b = [0.0] * 26
    d1b[-8] = 3.0
    assert is_dead(d1b, 26) is False

    # D1-C: steady sales -> alive
    assert is_dead([5.0] * 26, 26) is False

    # D1-D (boundary): one sale EXACTLY 26 weeks ago is inside the window -> alive.
    # The nonzero sits at index -26; a correct window of last-26 includes it.
    d1d = [4.0] + [0.0] * 25  # length 26, nonzero at position -26
    assert is_dead(d1d, 26) is False

    # Total dead value across the fixture = D1-A only
    assert dead_stock_value(80, 500) == pytest.approx(40_000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 4 — Expiry risk (units that won't sell before expiry; FEFO across batches)
# ─────────────────────────────────────────────────────────────────────────────
def test_fixture4_expiry_single_batch():
    # X1-A: 100 units, daily 1, expiry 40d -> sellable 40 -> at risk 60 -> 24,000
    x1a = Sku("X1-A", avg_weekly_demand=7, unit_cost=400, is_perishable=True,
              batches=[Batch(100, 40)])
    assert sku_expiry_at_risk_units(x1a) == pytest.approx(60.0)
    assert sku_expiry_writeoff(x1a) == pytest.approx(24_000.0)

    # X1-B: 30 units, daily 1, expiry 40d -> sellable 40 -> at risk clamped to 0
    x1b = Sku("X1-B", avg_weekly_demand=7, unit_cost=400, is_perishable=True,
              batches=[Batch(30, 40)])
    assert sku_expiry_at_risk_units(x1b) == pytest.approx(0.0)
    assert sku_expiry_writeoff(x1b) == pytest.approx(0.0)

    # X1-C: non-perishable -> not evaluated -> 0
    x1c = Sku("X1-C", avg_weekly_demand=35, unit_cost=400, is_perishable=False,
              batches=[Batch(500, None)])
    assert sku_expiry_at_risk_units(x1c) == pytest.approx(0.0)
    assert sku_expiry_writeoff(x1c) == pytest.approx(0.0)


def test_fixture4_expiry_fefo_multi_batch():
    # X1-D: daily 2. B1: 50 @ day20, B2: 50 @ day100.
    #   FEFO: B1 sells 40 by day20 -> 10 wasted ; B2 sells out by day45 -> 0 at risk.
    #   total at risk 10 -> write-off 10 * 400 = 4,000
    x1d = Sku("X1-D", avg_weekly_demand=14, unit_cost=400, is_perishable=True,
              batches=[Batch(50, 20), Batch(50, 100)])
    assert sku_expiry_at_risk_units(x1d) == pytest.approx(10.0)
    assert sku_expiry_writeoff(x1d) == pytest.approx(4_000.0)

    # Total write-off exposure across the fixture = X1-A + X1-D = 28,000
    x1a = Sku("X1-A", avg_weekly_demand=7, unit_cost=400, is_perishable=True,
              batches=[Batch(100, 40)])
    assert sku_expiry_writeoff(x1a) + sku_expiry_writeoff(x1d) == pytest.approx(28_000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 5 — Stockout risk (days of cover vs lead time)
#   shortfall = max(0, lead - cover) ; loss = daily * shortfall * (sell - cost)
# ─────────────────────────────────────────────────────────────────────────────
def test_fixture5_stockout():
    # S1-A: cover 7, lead 70 -> shortfall 63 -> 20*63 units * 100 margin = 126,000
    assert stockout_shortfall_days(140, 140, 70) == pytest.approx(63.0)
    assert stockout_margin_loss(140, 140, 70, 300, 400) == pytest.approx(126_000.0)

    # S1-B: cover 40, lead 70 -> shortfall 30 -> 20*30 * 100 = 60,000
    assert stockout_shortfall_days(800, 140, 70) == pytest.approx(30.0)
    assert stockout_margin_loss(800, 140, 70, 300, 400) == pytest.approx(60_000.0)

    # S1-C: cover 100, lead 70 -> shortfall clamped to 0 -> no loss
    assert stockout_shortfall_days(2000, 140, 70) == pytest.approx(0.0)
    assert stockout_margin_loss(2000, 140, 70, 300, 400) == pytest.approx(0.0)

    # Total stockout margin loss across the fixture = 186,000
    total = (
        stockout_margin_loss(140, 140, 70, 300, 400)
        + stockout_margin_loss(800, 140, 70, 300, 400)
        + stockout_margin_loss(2000, 140, 70, 300, 400)
    )
    assert total == pytest.approx(186_000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 6 — Value-at-stake portfolio roll-up (integration of fixtures 2–5)
#   releasable 90,000 ; write-off 28,000 ; stockout 186,000 ; total 304,000
# ─────────────────────────────────────────────────────────────────────────────
def _fixture6_portfolio():
    return [
        # Excess (alive, not perishable, lead 0 so no stockout) -> 50,000 releasable
        Sku("E1-A", on_hand=900, avg_weekly_demand=70, unit_cost=50, target_coverage_days=30),
        Sku("E1-B", on_hand=150, avg_weekly_demand=70, unit_cost=50, target_coverage_days=30),
        Sku("E1-C", on_hand=600, avg_weekly_demand=140, unit_cost=100, target_coverage_days=20),
        # Dead (zero demand) -> full value 40,000 releasable, excess suppressed
        Sku("D1-A", on_hand=80, avg_weekly_demand=0, unit_cost=500,
            target_coverage_days=30, recent_weekly_sales=[0.0] * 26),
        # Expiry (perishable; target set so they carry no excess) -> 28,000 write-off
        Sku("X1-A", on_hand=100, avg_weekly_demand=7, unit_cost=400, is_perishable=True,
            target_coverage_days=100, batches=[Batch(100, 40)]),
        Sku("X1-D", on_hand=100, avg_weekly_demand=14, unit_cost=400, is_perishable=True,
            target_coverage_days=50, batches=[Batch(50, 20), Batch(50, 100)]),
        # Stockout (target 100 so no excess; lead 70 drives shortfall) -> 186,000 loss
        Sku("S1-A", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
        Sku("S1-B", on_hand=800, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
        Sku("S1-C", on_hand=2000, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
    ]


def test_fixture6_value_at_stake_portfolio():
    vas = value_at_stake(_fixture6_portfolio())
    assert vas.releasable_cash == pytest.approx(90_000.0)
    assert vas.write_off_exposure == pytest.approx(28_000.0)
    assert vas.stockout_margin_loss == pytest.approx(186_000.0)
    assert vas.total == pytest.approx(304_000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 7 — Overlap: one SKU is BOTH dead and excess, counted ONCE
#   Naive sum would be 220,000; correct de-duped releasable cash is 120,000.
# ─────────────────────────────────────────────────────────────────────────────
def test_fixture7_overlap_dead_and_excess_counted_once():
    ov1 = Sku("OV-1", on_hand=200, avg_weekly_demand=0, unit_cost=500,
              target_coverage_days=30, recent_weekly_sales=[0.0] * 26)
    ov2 = Sku("OV-2", on_hand=600, avg_weekly_demand=140, unit_cost=100,
              target_coverage_days=20)

    # Both flags fire on OV-1 at the function level (the de-dup lives in the roll-up).
    assert is_dead(ov1.recent_weekly_sales, ov1.dead_window_weeks) is True
    assert excess_value(200, 0, 30, 500) == pytest.approx(100_000.0)

    # Roll-up counts OV-1 once (dead path, 100k) + OV-2 excess (20k) = 120,000,
    # NOT the naive 220,000 that double-counts OV-1.
    vas = value_at_stake([ov1, ov2])
    assert vas.releasable_cash == pytest.approx(120_000.0)
    assert vas.releasable_cash != pytest.approx(220_000.0)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 8 — Overlap: one perishable SKU is BOTH excess AND near-expiry.
#   DELIBERATE non-de-dup: the SKU contributes to both releasable_cash and
#   write_off_exposure, because the two levers name mutually exclusive ACTIONS
#   on the same units (return/markdown for cash vs. let it expire). The grand
#   total is therefore an upper bound, not strictly additive. This test locks
#   that decision so it is not silently "fixed" into a de-dup later.
# ─────────────────────────────────────────────────────────────────────────────
def test_fixture8_excess_and_expiry_overlap_is_not_deduped():
    # OV-3: 100 on hand, daily 1 (weekly 7), target 30 -> target_stock 30 ->
    # excess 70. Perishable, one batch of 100 expiring in 40 days -> FEFO
    # sells 40, 60 units at risk (same batch shape as fixture 4's X1-A).
    ov3 = Sku("OV-3", on_hand=100, avg_weekly_demand=7, unit_cost=400,
              is_perishable=True, target_coverage_days=30,
              batches=[Batch(100, 40)])

    assert excess_units(100, 7, 30) == pytest.approx(70.0)
    assert sku_expiry_at_risk_units(ov3) == pytest.approx(60.0)

    # Releasable cash counts the FULL excess (70 * 400 = 28,000) — the at-risk
    # units are NOT subtracted. Write-off counts the at-risk units (24,000).
    assert releasable_cash_contribution(ov3) == pytest.approx(28_000.0)
    assert sku_expiry_writeoff(ov3) == pytest.approx(24_000.0)

    # The roll-up carries both, and total = releasable + write-off = 52,000.
    # This is the upper-bound total, by design (the 60 overlapping units count
    # toward both a potential cash release and a potential write-off).
    vas = value_at_stake([ov3])
    assert vas.releasable_cash == pytest.approx(28_000.0)
    assert vas.write_off_exposure == pytest.approx(24_000.0)
    assert vas.total == pytest.approx(52_000.0)
