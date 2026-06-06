"""Inventory health metrics — the deterministic analytics core.

Every figure the product reports is computed here and is reproducible by hand;
tests/test_metrics.py is the answer key. No LLM, no database access.

Conventions (approved):
  * avg_daily_demand = avg_weekly_demand / 7
  * DAYS_PER_MONTH = 30 for months of cover
  * stockout is a snapshot exposure: reorder today, run out at days-of-cover,
    replenishment lands at lead time, so you are out for (lead - cover) days
  * value-at-stake de-dups dead vs excess: a dead SKU counts once, at full value
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from analytics.models import Batch, Sku

DAYS_PER_WEEK = 7
DAYS_PER_MONTH = 30


@dataclass
class ValueAtStake:
    releasable_cash: float
    write_off_exposure: float
    stockout_margin_loss: float
    total: float


# ── Demand and coverage ──────────────────────────────────────────────────────
def avg_daily_demand(avg_weekly_demand: float) -> float:
    return avg_weekly_demand / DAYS_PER_WEEK


def days_of_cover(on_hand: float, avg_weekly_demand: float) -> float | None:
    """Days of stock at current velocity (unit-based DIO).

    Returns ``None`` when there is no demand — coverage is undefined (infinite),
    not zero, and callers must handle that explicitly rather than divide by zero.
    """
    daily = avg_daily_demand(avg_weekly_demand)
    if daily <= 0:
        return None
    return on_hand / daily


def months_of_cover(on_hand: float, avg_weekly_demand: float) -> float | None:
    doc = days_of_cover(on_hand, avg_weekly_demand)
    return None if doc is None else doc / DAYS_PER_MONTH


# ── Excess ───────────────────────────────────────────────────────────────────
def excess_units(on_hand: float, avg_weekly_demand: float, target_coverage_days: float) -> float:
    """Units held above target coverage (clamped at zero)."""
    target_stock = avg_daily_demand(avg_weekly_demand) * target_coverage_days
    return max(0.0, on_hand - target_stock)


def excess_value(
    on_hand: float, avg_weekly_demand: float, target_coverage_days: float, unit_cost: float
) -> float:
    return excess_units(on_hand, avg_weekly_demand, target_coverage_days) * unit_cost


# ── Dead stock ───────────────────────────────────────────────────────────────
def is_dead(recent_weekly_sales: list[float], window_weeks: int) -> bool:
    """Dead if zero units moved across the most recent ``window_weeks`` weeks.

    The window is inclusive of the oldest week in it: a sale exactly
    ``window_weeks`` weeks ago keeps the SKU alive.
    """
    recent = recent_weekly_sales[-window_weeks:]
    return sum(recent) == 0


def dead_stock_value(on_hand: float, unit_cost: float) -> float:
    return on_hand * unit_cost


# ── Expiry risk (FEFO across batches) ────────────────────────────────────────
def expiry_at_risk_by_batch(batches: list[Batch], avg_weekly_demand: float) -> list[float]:
    """At-risk units per batch under first-expiry-first-out consumption.

    Demand drains the earliest-expiring batch first. A batch starts selling only
    once the previous batch is exhausted *or* has expired; whatever it still
    holds at its own expiry is at risk. Returns at-risk units in the same order
    as ``batches``.
    """
    daily = avg_daily_demand(avg_weekly_demand)
    indexed = list(enumerate(batches))
    ordered = sorted(indexed, key=lambda pair: pair[1].days_to_expiry)

    at_risk: dict[int, float] = {}

    if daily <= 0:
        # No demand: every perishable unit expires unsold.
        for i, b in indexed:
            at_risk[i] = b.quantity_on_hand
        return [at_risk[i] for i in range(len(batches))]

    t = 0.0  # time at which the next batch begins selling
    for i, b in ordered:
        if b.days_to_expiry <= t:
            consumed = 0.0
        else:
            available_demand = daily * (b.days_to_expiry - t)
            consumed = min(b.quantity_on_hand, available_demand)
        at_risk[i] = b.quantity_on_hand - consumed
        # This batch ends when it sells out or expires, whichever comes first.
        sellout_time = t + b.quantity_on_hand / daily
        t = min(sellout_time, b.days_to_expiry)

    return [at_risk[i] for i in range(len(batches))]


def sku_expiry_at_risk_units(sku: Sku) -> float:
    """Total units of a SKU that will expire unsold. Non-perishable SKUs: 0."""
    if not sku.is_perishable:
        return 0.0
    perishable = [b for b in sku.batches if b.days_to_expiry is not None]
    if not perishable:
        return 0.0
    return sum(expiry_at_risk_by_batch(perishable, sku.avg_weekly_demand))


def sku_expiry_writeoff(sku: Sku) -> float:
    return sku_expiry_at_risk_units(sku) * sku.unit_cost


# ── Stockout risk ────────────────────────────────────────────────────────────
def stockout_shortfall_days(
    on_hand: float, avg_weekly_demand: float, lead_time_days: float
) -> float:
    """Days the SKU will be out of stock before a reorder placed today arrives."""
    cover = days_of_cover(on_hand, avg_weekly_demand)
    if cover is None:
        return 0.0
    return max(0.0, lead_time_days - cover)


def stockout_margin_loss(
    on_hand: float,
    avg_weekly_demand: float,
    lead_time_days: float,
    unit_cost: float,
    selling_price: float,
) -> float:
    """Lost margin over the stockout window = demand x days out x unit margin."""
    daily = avg_daily_demand(avg_weekly_demand)
    shortfall = stockout_shortfall_days(on_hand, avg_weekly_demand, lead_time_days)
    lost_units = daily * shortfall
    margin = selling_price - unit_cost
    return lost_units * margin


# ── ABC-XYZ classification ───────────────────────────────────────────────────
WEEKS_PER_YEAR = 52
XYZ_X_MAX_CV = 0.5   # CV at or below this is stable (X)
XYZ_Y_MAX_CV = 1.0   # CV at or below this is variable (Y); above is erratic (Z)
ABC_A_MAX_SHARE = 0.80   # cumulative value share at or below this is A
ABC_B_MAX_SHARE = 0.95   # ...then B; the rest is C


def demand_cv(weekly_sales: list[float]) -> float | None:
    """Coefficient of variation of weekly demand: population std / mean.

    Descriptive (divide by N), so it is hand-checkable. ``None`` when there is no
    demand (mean 0) — variability is undefined, not zero.
    """
    if not weekly_sales:
        return None
    n = len(weekly_sales)
    mean = sum(weekly_sales) / n
    if mean == 0:
        return None
    variance = sum((x - mean) ** 2 for x in weekly_sales) / n
    return math.sqrt(variance) / mean


def xyz_class(cv: float | None) -> str | None:
    """Demand-variability class. Bands are upper-inclusive (0.5 -> X, 1.0 -> Y)."""
    if cv is None:
        return None
    if cv <= XYZ_X_MAX_CV:
        return "X"
    if cv <= XYZ_Y_MAX_CV:
        return "Y"
    return "Z"


def annual_usage_value(sku: Sku) -> float:
    """Annual value flowing through a SKU. Reuses the ingestion-computed
    ``avg_weekly_demand`` (the 52-week window average) — does not recompute it."""
    return sku.avg_weekly_demand * WEEKS_PER_YEAR * sku.unit_cost


def classify_abc(skus: list[Sku]) -> list[Sku]:
    """Assign A/B/C by cumulative share of annual usage value (Pareto). Mutates
    each SKU's ``abc_class`` in place and returns the list."""
    total = sum(annual_usage_value(s) for s in skus)
    if total <= 0:
        for s in skus:
            s.abc_class = None
        return skus

    cumulative = 0.0
    for s in sorted(skus, key=annual_usage_value, reverse=True):
        cumulative += annual_usage_value(s)
        share = cumulative / total
        if share <= ABC_A_MAX_SHARE:
            s.abc_class = "A"
        elif share <= ABC_B_MAX_SHARE:
            s.abc_class = "B"
        else:
            s.abc_class = "C"
    return skus


# ── Service-level release guardrail ──────────────────────────────────────────
def order_up_to_units(avg_weekly_demand: float, target_coverage_days: float) -> float:
    """The order-up-to stock level in units = the most you should hold."""
    return avg_daily_demand(avg_weekly_demand) * target_coverage_days


def safe_to_release(on_hand: float, avg_weekly_demand: float, target_coverage_days: float) -> bool:
    """True iff the SKU sits above its order-up-to level, i.e. it carries excess.

    Releasing only that excess leaves stock at the order-up-to level, which still
    embeds the lead-time cover and service-level safety buffer — so the service
    level cannot be breached. A SKU at or below the level (e.g. a stockout) is
    never safe to release.
    """
    return on_hand > order_up_to_units(avg_weekly_demand, target_coverage_days)


def releasable_candidates(skus: list[Sku]) -> list[Sku]:
    """The deterministic guardrail the Prioritise node uses: only SKUs that are
    safe to release. The reasoning layer may never re-admit one this drops."""
    return [
        s for s in skus
        if safe_to_release(s.on_hand, s.avg_weekly_demand, s.target_coverage_days)
    ]


# ── Value at stake (portfolio roll-up) ───────────────────────────────────────
def is_sku_dead(sku: Sku) -> bool:
    if sku.recent_weekly_sales is None:
        return False
    return is_dead(sku.recent_weekly_sales, sku.dead_window_weeks)


_is_sku_dead = is_sku_dead  # backwards-compatible alias


def releasable_cash_contribution(sku: Sku) -> float:
    """A SKU's contribution to the releasable-cash lever, with the dead/excess
    de-dup applied: dead stock counts at full value, otherwise excess only.
    Shared by ``value_at_stake`` and the Compute node so totals reconcile."""
    if is_sku_dead(sku):
        return dead_stock_value(sku.on_hand, sku.unit_cost)
    return excess_value(sku.on_hand, sku.avg_weekly_demand, sku.target_coverage_days, sku.unit_cost)


def value_at_stake(skus: list[Sku]) -> ValueAtStake:
    """Aggregate the three value levers across a portfolio.

    Releasable cash is at cost; write-off exposure is at cost; stockout loss is
    at margin. Dead and excess are de-duped: a dead SKU contributes its full
    on-hand value once (via the dead path) and is excluded from excess, so a SKU
    that qualifies as both is never counted twice.
    """
    releasable = 0.0
    write_off = 0.0
    stockout = 0.0

    for s in skus:
        releasable += releasable_cash_contribution(s)
        write_off += sku_expiry_writeoff(s)
        stockout += stockout_margin_loss(
            s.on_hand, s.avg_weekly_demand, s.lead_time_days, s.unit_cost, s.selling_price
        )

    total = releasable + write_off + stockout
    return ValueAtStake(releasable, write_off, stockout, total)
