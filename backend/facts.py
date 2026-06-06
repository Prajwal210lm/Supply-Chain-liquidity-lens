"""FACT objects the deterministic core hands to the reasoning layer.

Everything here is a FACT (computed by analytics/*). The LLM may cite these
fields but never produces or alters them. ``reconciliation_errors`` is the
deterministic audit guard required by the contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Cluster kind -> the single value lever it sums.
LEVER_BY_KIND = {
    "slow_excess": "releasable_cash",
    "expiry": "write_off_exposure",
    "stockout": "stockout_margin_loss",
}


@dataclass
class QualityReport:
    """Validate node output — all FACT."""

    total_skus: int
    total_batches: int
    skus_missing_cost: int
    skus_missing_lead_time: int
    skus_without_supplier: int
    skus_with_no_recent_sales: int
    perishable_without_expiry: int
    batches_already_expired: int
    negative_stock_skus: int
    issues: list[str] = field(default_factory=list)


@dataclass
class ValueAtStakeFacts:
    releasable_cash: float
    write_off_exposure: float
    stockout_margin_loss: float
    total: float
    sku_count: int
    flagged_sku_count: int


@dataclass
class SkuFacts:
    """The common per-SKU fact block (citation identity + computed numbers)."""

    sku_code: str
    name: str | None
    category_name: str | None
    unit_cost: float
    selling_price: float
    unit_margin: float
    on_hand_units: float
    inventory_value: float
    avg_weekly_demand: float
    avg_daily_demand: float
    months_of_cover: float | None
    days_of_cover: float | None
    target_coverage_days: float
    lead_time_days: float
    abc_class: str | None
    xyz_class: str | None
    demand_cv: float | None
    moq: int
    moq_weeks_of_cover: float | None
    weeks_since_last_sale: int | None
    supplier_name: str | None
    supplier_country: str | None
    supplier_reliability: float | None
    service_level_target: float | None
    safe_to_release: bool


@dataclass
class ClusterMember:
    """One SKU's membership in one cluster: its common facts, the cluster-specific
    facts, and its contribution to that cluster's single lever."""

    facts: SkuFacts
    lever_contribution: float
    specifics: dict


@dataclass
class Cluster:
    cluster_id: str
    kind: str            # slow_excess | expiry | stockout
    lever: str           # releasable_cash | write_off_exposure | stockout_margin_loss
    member_count: int
    lever_total: float
    members: list[ClusterMember]


@dataclass
class DiagnosisRun:
    run_id: str
    reference_date: date
    currency: str
    portfolio_value_at_stake: ValueAtStakeFacts
    clusters: list[Cluster]


def reconciliation_errors(run: DiagnosisRun, tol: float = 1e-6) -> list[str]:
    """Return a list of reconciliation failures; empty means the run reconciles.

    Two independent checks:
      1. Each cluster's stated lever_total equals the sum of its members'
         contributions (catches a dropped or moved member).
      2. Per lever, the cluster totals sum to the independently-computed
         portfolio value-at-stake (catches a mis-levered or missing SKU).
    """
    errors: list[str] = []
    by_lever = {"releasable_cash": 0.0, "write_off_exposure": 0.0, "stockout_margin_loss": 0.0}

    for c in run.clusters:
        member_sum = sum(m.lever_contribution for m in c.members)
        if abs(member_sum - c.lever_total) > tol:
            errors.append(
                f"cluster '{c.cluster_id}': members sum to {member_sum} "
                f"but lever_total is {c.lever_total}"
            )
        if c.lever != LEVER_BY_KIND.get(c.kind):
            errors.append(f"cluster '{c.cluster_id}': kind '{c.kind}' mismatched lever '{c.lever}'")
        by_lever[c.lever] = by_lever.get(c.lever, 0.0) + c.lever_total

    vas = run.portfolio_value_at_stake
    for lever, total in (
        ("releasable_cash", vas.releasable_cash),
        ("write_off_exposure", vas.write_off_exposure),
        ("stockout_margin_loss", vas.stockout_margin_loss),
    ):
        if abs(by_lever.get(lever, 0.0) - total) > tol:
            errors.append(
                f"lever '{lever}': clusters total {by_lever.get(lever, 0.0)} "
                f"!= portfolio {total}"
            )
    return errors


def reconciles(run: DiagnosisRun, tol: float = 1e-6) -> bool:
    return not reconciliation_errors(run, tol)
