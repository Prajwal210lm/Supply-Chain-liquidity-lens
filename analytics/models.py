"""In-memory input contracts for the analytics core.

These dataclasses are plain inputs — the core never reads the database. The
ingestion layer (later) is responsible for loading rows into these shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
