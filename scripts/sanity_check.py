#!/usr/bin/env python3
"""End-to-end wiring check: load the real portfolio, run the metrics, surface the
SKUs each pattern flags. This is a CONNECTEDNESS check, not a correctness proof —
the hand-built tests are what prove the math.

    DATABASE_URL=postgresql://... python scripts/sanity_check.py
"""

import os
import sys
from datetime import date

from sqlalchemy import create_engine

from analytics.ingest import load_portfolio
from analytics.metrics import (
    excess_value,
    months_of_cover,
    sku_expiry_writeoff,
    stockout_margin_loss,
    stockout_shortfall_days,
    value_at_stake,
)

REFERENCE_DATE = date(2025, 6, 2)  # the generator's anchor; never date.today()


def aed(x: float) -> str:
    return f"AED {x:,.0f}"


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set.")
    engine = create_engine(url)

    portfolio = load_portfolio(engine, REFERENCE_DATE)
    print(f"Loaded {len(portfolio)} SKUs as of {REFERENCE_DATE}\n")

    vas = value_at_stake(portfolio)
    print("Portfolio value-at-stake")
    print(f"  releasable cash      : {aed(vas.releasable_cash)}")
    print(f"  write-off exposure   : {aed(vas.write_off_exposure)}")
    print(f"  stockout margin loss : {aed(vas.stockout_margin_loss)}")
    print(f"  TOTAL                : {aed(vas.total)}\n")

    # SLOW / EXCESS — most months of cover, among SKUs that carry excess.
    slow = []
    for s in portfolio:
        moc = months_of_cover(s.on_hand, s.avg_weekly_demand)
        exc = excess_value(s.on_hand, s.avg_weekly_demand, s.target_coverage_days, s.unit_cost)
        if exc > 0 and moc is not None:
            slow.append((s, moc, exc))
    slow.sort(key=lambda t: t[1], reverse=True)
    print("Top SLOW movers (excess cash trapped) — by months of cover")
    for s, moc, exc in slow[:5]:
        print(f"  {s.sku_code:8}  {moc:6.1f} mo cover   excess {aed(exc)}")

    # EXPIRY — most write-off exposure.
    expiry = [(s, sku_expiry_writeoff(s)) for s in portfolio]
    expiry = [t for t in expiry if t[1] > 0]
    expiry.sort(key=lambda t: t[1], reverse=True)
    print("\nTop EXPIRY risk (write-off exposure) — perishable, won't sell in time")
    for s, wo in expiry[:5]:
        print(f"  {s.sku_code:8}  write-off {aed(wo)}")

    # STOCKOUT — most margin loss.
    stockout = []
    for s in portfolio:
        loss = stockout_margin_loss(
            s.on_hand, s.avg_weekly_demand, s.lead_time_days, s.unit_cost, s.selling_price
        )
        short = stockout_shortfall_days(s.on_hand, s.avg_weekly_demand, s.lead_time_days)
        if loss > 0:
            stockout.append((s, short, loss))
    stockout.sort(key=lambda t: t[2], reverse=True)
    print("\nTop STOCKOUT risk (margin at stake) — fast movers vs lead time")
    for s, short, loss in stockout[:5]:
        print(f"  {s.sku_code:8}  out {short:5.1f} days before reorder   loss {aed(loss)}")


if __name__ == "__main__":
    main()
