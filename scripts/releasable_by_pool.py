#!/usr/bin/env python3
"""Diagnostic: break releasable cash down by planted pool, and measure how much
of the 'normal' FMCG base is being flagged as excess. Not a permanent tool.

    DATABASE_URL=postgresql://... python scripts/releasable_by_pool.py
"""

import os
import sys
from collections import defaultdict
from datetime import date

from sqlalchemy import create_engine

from analytics.ingest import load_portfolio
from analytics.metrics import dead_stock_value, excess_value, is_dead

REFERENCE_DATE = date(2025, 6, 2)

# SKU-code prefix -> pool label (matches data/generate.py).
PREFIX = {
    "GF": "FMCG general",
    "SL": "SLOW high-value",
    "PE": "EXPIRY pharma",
    "SR": "STOCKOUT fast",
    "NP": "PHARMA normal",
}


def pool_of(sku_code: str) -> str:
    return PREFIX.get(sku_code.split("-")[0], "OTHER")


def aed(x: float) -> str:
    return f"AED {x:,.0f}"


def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set.")
    portfolio = load_portfolio(create_engine(url), REFERENCE_DATE)

    releasable = defaultdict(float)      # releasable cash counted per pool
    inv_value = defaultdict(float)       # total inventory value per pool
    flagged_excess_units = defaultdict(int)   # SKUs in pool flagged with any excess
    sku_count = defaultdict(int)
    dead_count = defaultdict(int)

    for s in portfolio:
        pool = pool_of(s.sku_code)
        sku_count[pool] += 1
        inv_value[pool] += s.on_hand * s.unit_cost

        if is_dead(s.recent_weekly_sales, s.dead_window_weeks):
            releasable[pool] += dead_stock_value(s.on_hand, s.unit_cost)
            dead_count[pool] += 1
        else:
            exc = excess_value(s.on_hand, s.avg_weekly_demand, s.target_coverage_days, s.unit_cost)
            releasable[pool] += exc
            if exc > 0:
                flagged_excess_units[pool] += 1

    pools = ["FMCG general", "SLOW high-value", "EXPIRY pharma",
             "STOCKOUT fast", "PHARMA normal"]

    print(f"{'Pool':18}{'SKUs':>6}{'InvValue':>16}{'Releasable':>16}"
          f"{'%ofInv':>9}{'#dead':>7}{'#excess':>9}")
    print("-" * 81)
    tot_inv = tot_rel = 0.0
    for p in pools:
        inv = inv_value[p]
        rel = releasable[p]
        tot_inv += inv
        tot_rel += rel
        pct = (rel / inv * 100) if inv else 0.0
        print(f"{p:18}{sku_count[p]:>6}{aed(inv):>16}{aed(rel):>16}"
              f"{pct:>8.1f}%{dead_count[p]:>7}{flagged_excess_units[p]:>9}")
    print("-" * 81)
    print(f"{'TOTAL':18}{sum(sku_count.values()):>6}{aed(tot_inv):>16}"
          f"{aed(tot_rel):>16}{tot_rel / tot_inv * 100:>8.1f}%")

    # The critical number: share of the normal FMCG base flagged as releasable.
    fmcg_share = releasable["FMCG general"] / inv_value["FMCG general"] * 100
    print(f"\nFMCG general: {aed(releasable['FMCG general'])} of "
          f"{aed(inv_value['FMCG general'])} flagged excess "
          f"= {fmcg_share:.1f}% of the normal base.")
    print(f"FMCG SKUs with ANY excess: {flagged_excess_units['FMCG general']} "
          f"of {sku_count['FMCG general']}")


if __name__ == "__main__":
    main()
