"""Deterministic reasoning-layer nodes: Validate and Compute. No LLM.

Validate attaches a data-quality report; Compute calls the analytics core and
assembles the DiagnosisRun FACT object — flagged SKUs grouped into clusters
(one per lever) with reconciling totals. Multi-cluster rule: a SKU is a member
of every cluster whose lever it contributes to (overlap allowed), so per-lever
totals reconcile exactly with the portfolio value-at-stake.
"""

from __future__ import annotations

from datetime import date, timedelta

from analytics.metrics import (
    avg_daily_demand,
    days_of_cover,
    dead_stock_value,
    excess_units,
    excess_value,
    expiry_at_risk_by_batch,
    is_sku_dead,
    months_of_cover,
    releasable_cash_contribution,
    safe_to_release,
    sku_expiry_writeoff,
    stockout_margin_loss,
    stockout_shortfall_days,
    value_at_stake,
)
from analytics.models import Sku
from backend.facts import (
    LEVER_BY_KIND,
    Cluster,
    ClusterMember,
    DiagnosisRun,
    QualityReport,
    SkuFacts,
    ValueAtStakeFacts,
)


# ── Validate ─────────────────────────────────────────────────────────────────
def validate(portfolio: list[Sku], reference_date: date) -> QualityReport:
    """Data-quality checks over the assembled portfolio. All FACT.

    Row-level invariants (negative sales, expiry-before-received) are enforced by
    the database CHECK constraints at ingestion, so this focuses on what is
    observable on the assembled SKUs.
    """
    missing_cost = sum(1 for s in portfolio if s.unit_cost <= 0)
    missing_lead = sum(1 for s in portfolio if s.lead_time_days <= 0)
    no_supplier = sum(1 for s in portfolio if not s.supplier_name)
    no_recent_sales = sum(1 for s in portfolio if s.weeks_since_last_sale is None)
    perishable_no_expiry = sum(
        1 for s in portfolio
        if s.is_perishable and not any(b.days_to_expiry is not None for b in s.batches)
    )
    batches_expired = sum(
        1 for s in portfolio for b in s.batches
        if b.days_to_expiry is not None and b.days_to_expiry <= 0
    )
    negative_stock = sum(1 for s in portfolio if s.on_hand < 0)

    issues: list[str] = []

    def note(count: int, message: str) -> None:
        if count:
            issues.append(f"{count} {message}")

    note(missing_cost, "SKU(s) missing unit cost")
    note(missing_lead, "SKU(s) missing lead time")
    note(no_supplier, "SKU(s) without a supplier")
    note(no_recent_sales, "SKU(s) with no sales on record")
    note(perishable_no_expiry, "perishable SKU(s) without an expiry date")
    note(batches_expired, "batch(es) already past expiry")
    note(negative_stock, "SKU(s) with negative stock")

    return QualityReport(
        total_skus=len(portfolio),
        total_batches=sum(len(s.batches) for s in portfolio),
        skus_missing_cost=missing_cost,
        skus_missing_lead_time=missing_lead,
        skus_without_supplier=no_supplier,
        skus_with_no_recent_sales=no_recent_sales,
        perishable_without_expiry=perishable_no_expiry,
        batches_already_expired=batches_expired,
        negative_stock_skus=negative_stock,
        issues=issues,
    )


# ── Compute: per-SKU fact assembly ───────────────────────────────────────────
def _sku_facts(sku: Sku) -> SkuFacts:
    return SkuFacts(
        sku_code=sku.sku_code,
        name=sku.name,
        category_name=sku.category_name,
        unit_cost=sku.unit_cost,
        selling_price=sku.selling_price,
        unit_margin=sku.selling_price - sku.unit_cost,
        on_hand_units=sku.on_hand,
        inventory_value=sku.on_hand * sku.unit_cost,
        avg_weekly_demand=sku.avg_weekly_demand,
        avg_daily_demand=avg_daily_demand(sku.avg_weekly_demand),
        months_of_cover=months_of_cover(sku.on_hand, sku.avg_weekly_demand),
        days_of_cover=days_of_cover(sku.on_hand, sku.avg_weekly_demand),
        target_coverage_days=sku.target_coverage_days,
        lead_time_days=sku.lead_time_days,
        abc_class=sku.abc_class,
        xyz_class=sku.xyz_class,
        demand_cv=sku.demand_cv,
        moq=sku.moq,
        moq_weeks_of_cover=sku.moq_weeks_of_cover,
        weeks_since_last_sale=sku.weeks_since_last_sale,
        supplier_name=sku.supplier_name,
        supplier_country=sku.supplier_country,
        supplier_reliability=sku.supplier_reliability,
        service_level_target=sku.service_level_target,
        safe_to_release=safe_to_release(sku.on_hand, sku.avg_weekly_demand, sku.target_coverage_days),
    )


def _slow_excess_specifics(sku: Sku) -> dict:
    dead = is_sku_dead(sku)
    return {
        "excess_units": excess_units(sku.on_hand, sku.avg_weekly_demand, sku.target_coverage_days),
        "excess_value": excess_value(
            sku.on_hand, sku.avg_weekly_demand, sku.target_coverage_days, sku.unit_cost),
        "is_dead": dead,
        "dead_stock_value": dead_stock_value(sku.on_hand, sku.unit_cost) if dead else None,
        "weeks_since_last_sale": sku.weeks_since_last_sale,
        "releasable_cash_contribution": releasable_cash_contribution(sku),
    }


def _expiry_specifics(sku: Sku, reference_date: date) -> dict:
    perishable = [b for b in sku.batches if b.days_to_expiry is not None]
    at_risk = expiry_at_risk_by_batch(perishable, sku.avg_weekly_demand) if perishable else []
    at_risk_total = sum(at_risk)
    on_hand_perishable = sum(b.quantity_on_hand for b in perishable)
    nearest = min((b.days_to_expiry for b in perishable), default=None)
    return {
        "nearest_days_to_expiry": nearest,
        "nearest_expiry_date": (reference_date + timedelta(days=nearest)) if nearest is not None else None,
        "sellable_before_expiry_units": on_hand_perishable - at_risk_total,
        "at_risk_units": at_risk_total,
        "write_off_value": sku_expiry_writeoff(sku),
        "batches": [
            {"days_to_expiry": b.days_to_expiry,
             "quantity_on_hand": b.quantity_on_hand,
             "at_risk_units": ar}
            for b, ar in zip(perishable, at_risk)
        ],
    }


def _stockout_specifics(sku: Sku) -> dict:
    shortfall = stockout_shortfall_days(sku.on_hand, sku.avg_weekly_demand, sku.lead_time_days)
    return {
        "shortfall_days": shortfall,
        "lost_units": avg_daily_demand(sku.avg_weekly_demand) * shortfall,
        "stockout_margin_loss": stockout_margin_loss(
            sku.on_hand, sku.avg_weekly_demand, sku.lead_time_days, sku.unit_cost, sku.selling_price),
    }


def compute(portfolio: list[Sku], reference_date: date, run_id: str = "run") -> DiagnosisRun:
    """Assemble the DiagnosisRun. Each cluster sums exactly one lever; a SKU joins
    every cluster whose lever it contributes to, so totals reconcile per lever."""
    cluster_specs = (
        ("slow_excess",
         releasable_cash_contribution,
         _slow_excess_specifics),
        ("expiry",
         sku_expiry_writeoff,
         lambda s: _expiry_specifics(s, reference_date)),
        ("stockout",
         lambda s: stockout_margin_loss(
             s.on_hand, s.avg_weekly_demand, s.lead_time_days, s.unit_cost, s.selling_price),
         _stockout_specifics),
    )

    clusters: list[Cluster] = []
    flagged: set[str] = set()

    for kind, contribution_fn, specifics_fn in cluster_specs:
        members: list[ClusterMember] = []
        for sku in portfolio:
            contribution = contribution_fn(sku)
            if contribution > 0:
                members.append(ClusterMember(
                    facts=_sku_facts(sku),
                    lever_contribution=contribution,
                    specifics=specifics_fn(sku),
                ))
                flagged.add(sku.sku_code)
        members.sort(key=lambda m: m.lever_contribution, reverse=True)
        clusters.append(Cluster(
            cluster_id=kind,
            kind=kind,
            lever=LEVER_BY_KIND[kind],
            member_count=len(members),
            lever_total=sum(m.lever_contribution for m in members),
            members=members,
        ))

    vas = value_at_stake(portfolio)
    portfolio_vas = ValueAtStakeFacts(
        releasable_cash=vas.releasable_cash,
        write_off_exposure=vas.write_off_exposure,
        stockout_margin_loss=vas.stockout_margin_loss,
        total=vas.total,
        sku_count=len(portfolio),
        flagged_sku_count=len(flagged),
    )
    return DiagnosisRun(
        run_id=run_id,
        reference_date=reference_date,
        currency="AED",
        portfolio_value_at_stake=portfolio_vas,
        clusters=clusters,
    )
