"""Ingestion layer: read raw rows and assemble the ``Sku``/``Batch`` inputs the
metric functions consume.

The pure assembly functions take in-memory rows (``SkuRow``/``SalesRow``/
``BatchRow``) and are fully unit-tested without a database. ``load_portfolio``
is the thin database adapter that runs SQL and feeds those functions.

Conventions:
  * Demand-averaging window = DEMAND_WINDOW_WEEKS (default 52, a full seasonal
    cycle). Dead-stock no-movement window = DEAD_STOCK_WINDOW_WEEKS (default 26).
  * The current partial week (the week containing reference_date) is EXCLUDED
    from both windows; only complete prior weeks are counted.
  * target_coverage_days = lead + REVIEW_PERIOD_DAYS + z(service_level)*sqrt(lead):
    the periodic-review order-up-to level (reorder point plus one replenishment
    cycle of cover). Safety stock is a service-level-scaled simplification — a
    fuller model would use demand standard deviation.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from analytics.models import Batch, BatchRow, SalesRow, Sku, SkuRow

# Named windows / policy parameters — NOT magic numbers.
DEMAND_WINDOW_WEEKS = 52      # demand baseline: a full seasonal cycle
DEAD_STOCK_WINDOW_WEEKS = 26  # no-movement window for dead-stock detection
REVIEW_PERIOD_DAYS = 45       # replenishment cycle in the target-coverage formula

# Standard one-sided normal z-scores for service-level safety stock.
SERVICE_LEVEL_Z = {
    0.80: 0.8416,
    0.85: 1.0364,
    0.90: 1.2816,
    0.92: 1.4051,
    0.95: 1.6449,
    0.97: 1.8808,
    0.98: 2.0537,
    0.99: 2.3263,
}


# ── Week alignment ───────────────────────────────────────────────────────────
def week_start_of(d: date) -> date:
    """Monday of the ISO week containing ``d`` (Monday is weekday 0)."""
    return d - timedelta(days=d.weekday())


def _window_bounds(reference_date: date, window_weeks: int) -> tuple[date, date]:
    """[start, end) of the complete weeks in the window.

    ``end`` is the current (partial) week's Monday — excluded. ``start`` is
    ``window_weeks`` Mondays before that — included.
    """
    end = week_start_of(reference_date)
    start = end - timedelta(weeks=window_weeks)
    return start, end


# ── Demand ───────────────────────────────────────────────────────────────────
def windowed_weekly_sales(
    sales_rows: list[SalesRow], reference_date: date, window_weeks: int
) -> list[float]:
    """Quantities for the complete weeks inside the window, oldest first."""
    start, end = _window_bounds(reference_date, window_weeks)
    in_window = [r for r in sales_rows if start <= r.week_start_date < end]
    in_window.sort(key=lambda r: r.week_start_date)
    return [float(r.quantity_sold) for r in in_window]


def compute_avg_weekly_demand(
    sales_rows: list[SalesRow], reference_date: date, window_weeks: int = DEMAND_WINDOW_WEEKS
) -> float:
    """Mean weekly demand over the weeks present in the window. No rows -> 0."""
    qtys = windowed_weekly_sales(sales_rows, reference_date, window_weeks)
    if not qtys:
        return 0.0
    return sum(qtys) / len(qtys)


# ── Stock on hand ────────────────────────────────────────────────────────────
def compute_on_hand(batch_rows: list[BatchRow]) -> float:
    return sum(float(b.quantity_on_hand) for b in batch_rows)


# ── Expiry ───────────────────────────────────────────────────────────────────
def days_to_expiry(expiry_date: date | None, reference_date: date) -> float | None:
    if expiry_date is None:
        return None
    return float((expiry_date - reference_date).days)


# ── Target coverage ──────────────────────────────────────────────────────────
def service_level_z(service_level: float) -> float:
    """z-score for a service level. Rounds to the nearest tabulated level so DB
    NUMERIC values (e.g. 0.950) resolve cleanly."""
    key = round(float(service_level), 2)
    if key in SERVICE_LEVEL_Z:
        return SERVICE_LEVEL_Z[key]
    nearest = min(SERVICE_LEVEL_Z, key=lambda k: abs(k - key))
    return SERVICE_LEVEL_Z[nearest]


def compute_target_coverage_days(lead_time_days: float, service_level: float) -> float:
    """Periodic-review order-up-to level, in days of cover.

    = cycle stock (lead time) + one replenishment cycle (REVIEW_PERIOD_DAYS)
      + service-level safety buffer (z * sqrt(lead)).

    The review-period term is what stops normal post-replenishment stock from
    being flagged as excess; without it this collapses to a reorder point.
    """
    z = service_level_z(service_level)
    safety_days = z * math.sqrt(lead_time_days)
    return lead_time_days + REVIEW_PERIOD_DAYS + safety_days


# ── Assembly ─────────────────────────────────────────────────────────────────
def assemble_sku(
    sku_row: SkuRow,
    sales_rows: list[SalesRow],
    batch_rows: list[BatchRow],
    reference_date: date,
    demand_window_weeks: int = DEMAND_WINDOW_WEEKS,
    dead_window_weeks: int = DEAD_STOCK_WINDOW_WEEKS,
) -> Sku:
    """Turn one SKU's raw rows into the assembled ``Sku`` the metrics consume."""
    return Sku(
        sku_code=sku_row.sku_code,
        on_hand=compute_on_hand(batch_rows),
        avg_weekly_demand=compute_avg_weekly_demand(
            sales_rows, reference_date, demand_window_weeks
        ),
        unit_cost=float(sku_row.unit_cost),
        selling_price=float(sku_row.selling_price),
        target_coverage_days=compute_target_coverage_days(
            sku_row.lead_time_days, sku_row.service_level_target
        ),
        lead_time_days=float(sku_row.lead_time_days),
        is_perishable=bool(sku_row.is_perishable),
        batches=[
            Batch(
                quantity_on_hand=float(b.quantity_on_hand),
                days_to_expiry=days_to_expiry(b.expiry_date, reference_date),
            )
            for b in batch_rows
        ],
        recent_weekly_sales=windowed_weekly_sales(
            sales_rows, reference_date, dead_window_weeks
        ),
        dead_window_weeks=dead_window_weeks,
    )


# ── Database adapter (not unit-tested with hand fixtures) ─────────────────────
def load_portfolio(engine, reference_date: date) -> list[Sku]:
    """Load every SKU from PostgreSQL and assemble it. Uses the default windows.

    Service level is resolved as the SKU override or the category default; lead
    time is the primary supplier's, falling back to the shortest available.
    """
    from collections import defaultdict

    from sqlalchemy import text

    with engine.connect() as conn:
        sku_rows = conn.execute(text(
            """
            SELECT s.sku_id, s.sku_code, s.unit_cost, s.selling_price,
                   s.is_perishable, s.shelf_life_days,
                   COALESCE(s.service_level_target, c.service_level_target) AS service_level
            FROM sku s
            JOIN category c ON c.category_id = s.category_id
            """
        )).fetchall()

        supplier_rows = conn.execute(text(
            "SELECT sku_id, lead_time_days, is_primary FROM sku_supplier"
        )).fetchall()

        batch_rows = conn.execute(text(
            "SELECT sku_id, quantity_on_hand, received_date, expiry_date FROM inventory_batch"
        )).fetchall()

        sales_rows = conn.execute(text(
            "SELECT sku_id, week_start_date, quantity_sold FROM sales_history"
        )).fetchall()

    # Resolve a single lead time per SKU: primary if present, else the minimum.
    leads_primary: dict[int, int] = {}
    leads_min: dict[int, int] = {}
    for r in supplier_rows:
        leads_min[r.sku_id] = min(leads_min.get(r.sku_id, r.lead_time_days), r.lead_time_days)
        if r.is_primary:
            leads_primary[r.sku_id] = r.lead_time_days

    batches_by_sku: dict[int, list[BatchRow]] = defaultdict(list)
    for r in batch_rows:
        batches_by_sku[r.sku_id].append(
            BatchRow(float(r.quantity_on_hand), r.received_date, r.expiry_date)
        )

    sales_by_sku: dict[int, list[SalesRow]] = defaultdict(list)
    for r in sales_rows:
        sales_by_sku[r.sku_id].append(SalesRow(r.week_start_date, float(r.quantity_sold)))

    portfolio: list[Sku] = []
    for r in sku_rows:
        lead = leads_primary.get(r.sku_id, leads_min.get(r.sku_id, 0))
        sku_row = SkuRow(
            sku_code=r.sku_code,
            unit_cost=float(r.unit_cost),
            selling_price=float(r.selling_price),
            is_perishable=bool(r.is_perishable),
            shelf_life_days=r.shelf_life_days,
            service_level_target=float(r.service_level),
            lead_time_days=int(lead),
        )
        portfolio.append(
            assemble_sku(
                sku_row,
                sales_by_sku.get(r.sku_id, []),
                batches_by_sku.get(r.sku_id, []),
                reference_date,
            )
        )
    return portfolio
