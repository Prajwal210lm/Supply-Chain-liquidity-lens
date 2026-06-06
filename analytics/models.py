"""In-memory input contracts for the analytics core.

Two families live here:
  * Assembled inputs the metric functions consume: ``Sku`` and ``Batch``.
  * Raw-row inputs the ingestion layer consumes: ``SkuRow``, ``SalesRow``,
    ``BatchRow`` — plain shapes mirroring database rows, so ingestion can be
    unit-tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


# ── Assembled inputs (consumed by analytics/metrics.py) ──────────────────────
@dataclass
class Batch:
    """One inventory lot. ``days_to_expiry`` is measured from the reference date.

    ``days_to_expiry is None`` means the batch does not expire (non-perishable);
    the expiry logic skips it.
    """

    quantity_on_hand: float
    days_to_expiry: float | None = None


@dataclass
class Sku:
    """Everything the value-at-stake roll-up needs about a single SKU.

    Per-metric inputs (``avg_weekly_demand``, ``target_coverage_days``,
    ``lead_time_days``) are supplied directly rather than derived, so each metric
    is tested in isolation. ``recent_weekly_sales`` is the trailing window used
    for dead-stock detection; ``None`` means "not evaluated / treated as alive".
    """

    sku_code: str
    on_hand: float = 0.0
    avg_weekly_demand: float = 0.0
    unit_cost: float = 0.0
    selling_price: float = 0.0
    target_coverage_days: float = 0.0
    lead_time_days: float = 0.0
    is_perishable: bool = False
    batches: list[Batch] = field(default_factory=list)
    recent_weekly_sales: list[float] | None = None
    dead_window_weeks: int = 26
    # Reasoning-layer facts surfaced by ingestion (cited by the LLM, never recomputed).
    moq: int = 0
    moq_weeks_of_cover: float | None = None
    weeks_since_last_sale: int | None = None
    supplier_name: str | None = None
    supplier_country: str | None = None
    supplier_reliability: float | None = None
    abc_class: str | None = None        # value class A/B/C (portfolio-relative)
    xyz_class: str | None = None        # demand-variability class X/Y/Z
    demand_cv: float | None = None      # coefficient of variation of weekly demand
    name: str | None = None             # human-readable SKU name (citation identity)
    category_name: str | None = None
    service_level_target: float | None = None


# ── Raw rows (consumed by analytics/ingest.py) ───────────────────────────────
@dataclass
class SkuRow:
    """A SKU master row, with the service level already resolved (SKU override
    or category default) and the primary supplier's lead time attached."""

    sku_code: str
    unit_cost: float
    selling_price: float
    is_perishable: bool
    shelf_life_days: int | None
    service_level_target: float
    lead_time_days: int
    moq: int = 0
    supplier_name: str | None = None
    supplier_country: str | None = None
    supplier_reliability: float | None = None
    name: str | None = None
    category_name: str | None = None


@dataclass
class SalesRow:
    week_start_date: date
    quantity_sold: float


@dataclass
class BatchRow:
    quantity_on_hand: float
    received_date: date
    expiry_date: date | None
