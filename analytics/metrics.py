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


# ── Value at stake (portfolio roll-up) ───────────────────────────────────────
def _is_sku_dead(sku: Sku) -> bool:
    if sku.recent_weekly_sales is None:
        return False
    return is_dead(sku.recent_weekly_sales, sku.dead_window_weeks)


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
        if _is_sku_dead(s):
            releasable += dead_stock_value(s.on_hand, s.unit_cost)
        else:
            releasable += excess_value(
                s.on_hand, s.avg_weekly_demand, s.target_coverage_days, s.unit_cost
            )
        write_off += sku_expiry_writeoff(s)
        stockout += stockout_margin_loss(
            s.on_hand, s.avg_weekly_demand, s.lead_time_days, s.unit_cost, s.selling_price
        )

    total = releasable + write_off + stockout
    return ValueAtStake(releasable, write_off, stockout, total)
