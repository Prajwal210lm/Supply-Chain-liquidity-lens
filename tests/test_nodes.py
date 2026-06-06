"""Validate and Compute nodes — deterministic, no LLM.

Covers the two contract requirements:
  * Reconciliation PROVEN: per-lever Sigma cluster.lever_total == portfolio lever,
    plus mutation tests that fail loudly if a member is dropped or mis-levered.
  * Multi-cluster rule LOCKED: a SKU drives one cluster per lever it contributes
    to; an overlap SKU appears in two clusters and the totals still reconcile.
"""

from collections import defaultdict
from datetime import date

import pytest

from analytics.models import Batch, Sku
from backend.facts import reconciles, reconciliation_errors
from backend.nodes import compute, validate

REF = date(2025, 6, 2)


# ── helpers ──────────────────────────────────────────────────────────────────
def _cluster(run, kind):
    return next(c for c in run.clusters if c.kind == kind)


def _member(cluster, sku_code):
    return next((m for m in cluster.members if m.facts.sku_code == sku_code), None)


def _diagnosis_portfolio():
    return [
        # Pure slow/excess (alive, overstocked): releasable 400 * 50 = 20,000
        Sku("S1", on_hand=900, avg_weekly_demand=70, unit_cost=50,
            target_coverage_days=50, lead_time_days=30),
        # Pure dead: releasable full value 80 * 500 = 40,000
        Sku("D1", on_hand=80, avg_weekly_demand=0, unit_cost=500,
            target_coverage_days=50, recent_weekly_sales=[0.0] * 26),
        # Pure expiry: write-off 60 * 400 = 24,000 (target high -> no excess)
        Sku("X1", on_hand=100, avg_weekly_demand=7, unit_cost=400, is_perishable=True,
            target_coverage_days=200, lead_time_days=0, batches=[Batch(100, 40)]),
        # Pure stockout: loss 20/day * 63 days * 100 margin = 126,000
        Sku("SR1", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
        # OVERLAP: overstocked AND near-expiry -> releasable 40,000 + write-off 24,000
        Sku("OVER", on_hand=160, avg_weekly_demand=14, unit_cost=400, is_perishable=True,
            target_coverage_days=30, lead_time_days=10, batches=[Batch(100, 20), Batch(60, 200)]),
    ]


# ── Validate node ────────────────────────────────────────────────────────────
def test_validate_counts_data_quality_issues():
    portfolio = [
        Sku("G", on_hand=100, unit_cost=10, lead_time_days=30,
            supplier_name="Apex", weeks_since_last_sale=2),
        Sku("NC", unit_cost=0, lead_time_days=30, supplier_name="Apex",
            weeks_since_last_sale=1),                                   # missing cost
        Sku("NL", unit_cost=10, lead_time_days=0, supplier_name="Apex",
            weeks_since_last_sale=1),                                   # missing lead time
        Sku("NS", unit_cost=10, lead_time_days=30, supplier_name=None,
            weeks_since_last_sale=1),                                   # no supplier
        Sku("DEAD", unit_cost=10, lead_time_days=30, supplier_name="Apex",
            weeks_since_last_sale=None),                                # never sold
        Sku("PE", unit_cost=10, lead_time_days=30, supplier_name="Apex",
            weeks_since_last_sale=1, is_perishable=True, batches=[Batch(5, None)]),  # perishable, no expiry
        Sku("EB", unit_cost=10, lead_time_days=30, supplier_name="Apex",
            weeks_since_last_sale=1, is_perishable=True,
            batches=[Batch(5, -3), Batch(5, 10)]),                     # one already-expired batch
    ]
    q = validate(portfolio, REF)

    assert q.total_skus == 7
    assert q.total_batches == 3            # PE(1) + EB(2)
    assert q.skus_missing_cost == 1
    assert q.skus_missing_lead_time == 1
    assert q.skus_without_supplier == 1
    assert q.skus_with_no_recent_sales == 1
    assert q.perishable_without_expiry == 1
    assert q.batches_already_expired == 1
    assert q.negative_stock_skus == 0
    assert len(q.issues) >= 1              # human-readable lines for a dirty portfolio


# ── Compute node: structure + totals ─────────────────────────────────────────
def test_compute_builds_three_clusters_with_expected_totals():
    run = compute(_diagnosis_portfolio(), REF, run_id="t1")

    assert {c.kind for c in run.clusters} == {"slow_excess", "expiry", "stockout"}
    assert _cluster(run, "slow_excess").lever_total == pytest.approx(100_000.0)
    assert _cluster(run, "expiry").lever_total == pytest.approx(48_000.0)
    assert _cluster(run, "stockout").lever_total == pytest.approx(126_000.0)

    vas = run.portfolio_value_at_stake
    assert vas.releasable_cash == pytest.approx(100_000.0)
    assert vas.write_off_exposure == pytest.approx(48_000.0)
    assert vas.stockout_margin_loss == pytest.approx(126_000.0)
    assert vas.total == pytest.approx(274_000.0)
    assert vas.sku_count == 5
    assert vas.flagged_sku_count == 5      # all five SKUs land in at least one cluster


# ── Reconciliation PROVEN ─────────────────────────────────────────────────────
def test_reconciliation_per_lever_equals_portfolio():
    run = compute(_diagnosis_portfolio(), REF)

    totals = defaultdict(float)
    for c in run.clusters:
        totals[c.lever] += c.lever_total

    vas = run.portfolio_value_at_stake
    assert totals["releasable_cash"] == pytest.approx(vas.releasable_cash)
    assert totals["write_off_exposure"] == pytest.approx(vas.write_off_exposure)
    assert totals["stockout_margin_loss"] == pytest.approx(vas.stockout_margin_loss)

    assert reconciles(run)
    assert reconciliation_errors(run) == []


def test_reconciliation_fails_loudly_if_a_member_is_dropped():
    run = compute(_diagnosis_portfolio(), REF)
    # Drop the OVERLAP SKU from slow/excess but leave the stated lever_total.
    slow = _cluster(run, "slow_excess")
    slow.members = [m for m in slow.members if m.facts.sku_code != "OVER"]

    errs = reconciliation_errors(run)
    assert errs != []                      # loud, not silent
    assert not reconciles(run)


def test_reconciliation_fails_loudly_if_a_sku_is_mis_levered():
    run = compute(_diagnosis_portfolio(), REF)
    # Move the stockout SKU into the slow/excess cluster (wrong lever).
    stockout = _cluster(run, "stockout")
    slow = _cluster(run, "slow_excess")
    moved = _member(stockout, "SR1")
    stockout.members = [m for m in stockout.members if m.facts.sku_code != "SR1"]
    slow.members.append(moved)

    assert not reconciles(run)
    assert reconciliation_errors(run) != []


# ── Multi-cluster rule LOCKED ────────────────────────────────────────────────
def test_overlap_sku_appears_in_two_clusters_and_still_reconciles():
    run = compute(_diagnosis_portfolio(), REF)

    over_in_slow = _member(_cluster(run, "slow_excess"), "OVER")
    over_in_expiry = _member(_cluster(run, "expiry"), "OVER")

    # Same SKU, two clusters, each carrying ITS lever's contribution.
    assert over_in_slow is not None
    assert over_in_expiry is not None
    assert over_in_slow.lever_contribution == pytest.approx(40_000.0)   # excess cash
    assert over_in_expiry.lever_contribution == pytest.approx(24_000.0)  # write-off

    # OVER is NOT in stockout (no shortfall), and the run still reconciles.
    assert _member(_cluster(run, "stockout"), "OVER") is None
    assert reconciles(run)
