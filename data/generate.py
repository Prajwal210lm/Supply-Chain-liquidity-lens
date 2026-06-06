#!/usr/bin/env python3
"""
data/generate.py — Liquidity Lens synthetic data generator.

Three deliberate patterns in the dataset:
  1. Slow-moving high-value cluster  (SLOW)    — excess / dead-stock
  2. Near-expiry pharma              (EXPIRY)  — write-off exposure
  3. Fast-moving stockout risk       (STOCKOUT)— margin at stake

Usage:
    DATABASE_URL=postgresql://user:pass@host:5432/dbname python data/generate.py

Idempotent: truncates and repopulates all tables on every run.
All date arithmetic is relative to REFERENCE_DATE — date.today() is never called.
No formulas or constants are shared with the analytics core.
"""

import math
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# ── Constants ──────────────────────────────────────────────────────────────────
SEED           = 42
REFERENCE_DATE = date(2025, 6, 2)   # "today" — never use date.today()
N_WEEKS        = 104                 # weeks of sales history (~2 years)

# Pool sizes (sum = N_SKUS)
N_GENERAL_FMCG    = 360
N_SLOW_HIGH_VALUE = 120  # Pattern 1
N_NEAR_EXPIRY     = 30   # Pattern 2
N_STOCKOUT_RISK   = 60   # Pattern 3
N_NORMAL_PHARMA   = 30

N_SKUS = (N_GENERAL_FMCG + N_SLOW_HIGH_VALUE
          + N_NEAR_EXPIRY + N_STOCKOUT_RISK + N_NORMAL_PHARMA)

rng = np.random.default_rng(SEED)


# ── Database ───────────────────────────────────────────────────────────────────
def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit(
            "ERROR: DATABASE_URL not set.\n"
            "Example: DATABASE_URL=postgresql://user:pass@localhost/liquidity_lens"
        )
    return create_engine(url)


# ── Helpers ────────────────────────────────────────────────────────────────────
def week_start_dates():
    """104 Mondays ending on REFERENCE_DATE (which is itself a Monday)."""
    days_since_monday = REFERENCE_DATE.weekday()
    last_monday = REFERENCE_DATE - timedelta(days=days_since_monday)
    return [last_monday - timedelta(weeks=w) for w in range(N_WEEKS - 1, -1, -1)]


def seasonal_factor(week_date):
    """Gaussian lifts at Ramadan (~ISO week 10) and December (~ISO week 48)."""
    woy = week_date.isocalendar()[1]
    return (1.0
            + 0.30 * math.exp(-0.5 * ((woy - 10) / 6) ** 2)
            + 0.20 * math.exp(-0.5 * ((woy - 48) / 4) ** 2))


def pick(seq):
    """Pick one element from a list; always returns a Python str."""
    return str(rng.choice(seq))


# ── Reference data ─────────────────────────────────────────────────────────────
CATEGORIES = [
    ("FMCG – Beverages",      0.900),
    ("FMCG – Personal Care",  0.900),
    ("FMCG – Food",           0.900),
    ("Pharma – Antibiotics",  0.950),
    ("Pharma – Chronic",      0.970),
    ("Pharma – OTC",          0.920),
]

SUPPLIERS = [
    ("Al-Futtaim Trading",       "UAE",    0.95),
    ("Gulf Pharma Distributors", "Saudi",  0.88),
    ("EuroMed Imports",          "UAE",    0.92),
    ("Levant Supply Co.",        "Jordan", 0.75),
    ("Sino-Gulf Logistics",      "China",  0.70),
    ("Apex FMCG",                "UAE",    0.98),
    ("MedSource International",  "India",  0.82),
    ("Peninsula Consumer Goods", "Qatar",  0.91),
]

FMCG_CATS   = ["FMCG – Beverages", "FMCG – Personal Care", "FMCG – Food"]
PHARMA_CATS = ["Pharma – Antibiotics", "Pharma – Chronic", "Pharma – OTC"]
PHARMA_SUPS = ["Gulf Pharma Distributors", "MedSource International", "EuroMed Imports"]
FMCG_SUPS   = [
    "Al-Futtaim Trading", "Apex FMCG", "Peninsula Consumer Goods",
    "Sino-Gulf Logistics", "Levant Supply Co.",
]


# ── Insert helpers ─────────────────────────────────────────────────────────────
def insert_categories(conn):
    df = pd.DataFrame(CATEGORIES, columns=["name", "service_level_target"])
    df.to_sql("category", conn, if_exists="append", index=False, method="multi")
    rows = conn.execute(text("SELECT category_id, name FROM category")).fetchall()
    return {r.name: r.category_id for r in rows}


def insert_suppliers(conn):
    df = pd.DataFrame(SUPPLIERS, columns=["name", "country", "reliability_score"])
    df.to_sql("supplier", conn, if_exists="append", index=False, method="multi")
    rows = conn.execute(text("SELECT supplier_id, name FROM supplier")).fetchall()
    return {r.name: r.supplier_id for r in rows}


# ── SKU master ─────────────────────────────────────────────────────────────────
def build_skus(cat_ids):
    rows = []
    n = [0]

    def add(prefix, pool, cat, cost, price, perishable=False, shelf=None):
        n[0] += 1
        rows.append({
            "sku_code":             f"{prefix}-{n[0]:04d}",
            "name":                 f"{pool} SKU {n[0]:04d}",
            "pool":                 pool,
            "category_id":          cat_ids[cat],
            "unit_cost":            round(float(cost), 2),
            "selling_price":        round(float(price), 2),
            "is_perishable":        bool(perishable),
            "shelf_life_days":      int(shelf) if shelf is not None else None,
            "service_level_target": None,
        })

    for _ in range(N_GENERAL_FMCG):
        c = rng.uniform(5, 50)
        add("GF", "FMCG", pick(FMCG_CATS), c, c * rng.uniform(1.20, 1.40))

    for _ in range(N_SLOW_HIGH_VALUE):
        c = rng.uniform(500, 5_000)
        add("SL", "SLOW", pick(FMCG_CATS + ["Pharma – OTC"]),
            c, c * rng.uniform(1.15, 1.30))

    for _ in range(N_NEAR_EXPIRY):
        c = rng.uniform(50, 300)
        add("PE", "EXPIRY",
            pick(["Pharma – Antibiotics", "Pharma – Chronic"]),
            c, c * rng.uniform(1.25, 1.40),
            perishable=True, shelf=int(rng.integers(365, 731)))

    for _ in range(N_STOCKOUT_RISK):
        c = rng.uniform(10, 80)
        add("SR", "STOCKOUT", pick(FMCG_CATS), c, c * rng.uniform(1.20, 1.35))

    for _ in range(N_NORMAL_PHARMA):
        c      = rng.uniform(40, 200)
        perish = bool(rng.random() < 0.5)
        add("NP", "PHARMA", pick(PHARMA_CATS),
            c, c * rng.uniform(1.25, 1.40),
            perishable=perish,
            shelf=int(rng.integers(365, 731)) if perish else None)

    df = pd.DataFrame(rows)
    df["shelf_life_days"] = df["shelf_life_days"].astype(pd.Int64Dtype())
    return df


def insert_skus(conn, sku_df):
    cols = ["sku_code", "name", "category_id", "unit_cost", "selling_price",
            "is_perishable", "shelf_life_days", "service_level_target"]
    sku_df[cols].to_sql("sku", conn, if_exists="append", index=False, method="multi")
    rows = conn.execute(text("SELECT sku_id, sku_code FROM sku")).fetchall()
    id_map = {r.sku_code: r.sku_id for r in rows}
    out = sku_df.copy()
    out["sku_id"] = out["sku_code"].map(id_map)
    return out


# ── SKU–supplier links ─────────────────────────────────────────────────────────
def build_sku_supplier(sku_df, sup_ids):
    all_sups = list(sup_ids.keys())
    rows = []

    for _, sku in sku_df.iterrows():
        pool = sku["pool"]
        sid  = int(sku["sku_id"])

        if pool == "SLOW":
            lead, moq, sups = int(rng.integers(60, 91)),  int(rng.integers(50, 201)), FMCG_SUPS
        elif pool == "STOCKOUT":
            lead, moq, sups = int(rng.integers(45, 71)),  int(rng.integers(5, 30)),   FMCG_SUPS
        elif pool in ("EXPIRY", "PHARMA"):
            lead, moq, sups = int(rng.integers(30, 46)),  int(rng.integers(10, 51)),  PHARMA_SUPS
        else:
            lead, moq, sups = int(rng.integers(14, 46)),  int(rng.integers(5, 50)),   FMCG_SUPS

        prim = pick(sups)
        rows.append({"sku_id": sid, "supplier_id": sup_ids[prim],
                     "lead_time_days": lead, "moq": moq, "is_primary": True})

        if rng.random() < 0.30:
            sec = pick([s for s in all_sups if s != prim])
            rows.append({"sku_id": sid, "supplier_id": sup_ids[sec],
                         "lead_time_days": max(7, lead + int(rng.integers(-5, 15))),
                         "moq": moq, "is_primary": False})

    return pd.DataFrame(rows)


# ── Sales history ──────────────────────────────────────────────────────────────
def build_sales_history(sku_df, week_dates):
    seasonal = np.array([seasonal_factor(w) for w in week_dates])
    frames = []

    for _, sku in sku_df.iterrows():
        pool = sku["pool"]
        sid  = int(sku["sku_id"])

        if pool == "SLOW":
            qty = rng.poisson(0.3, N_WEEKS).astype(float)

        elif pool == "EXPIRY":
            qty = rng.poisson(float(rng.uniform(3, 8)), N_WEEKS).astype(float)

        elif pool == "STOCKOUT":
            lam = float(rng.uniform(80, 150))
            qty = rng.poisson(lam, N_WEEKS).astype(float)
            qty = np.maximum(qty * (1.0 + 0.35 * rng.standard_normal(N_WEEKS)), 0.0)

        elif pool == "PHARMA":
            qty = rng.poisson(float(rng.uniform(5, 20)), N_WEEKS).astype(float)

        else:  # FMCG
            lam  = float(rng.uniform(15, 40))
            qty  = rng.poisson(lam, N_WEEKS).astype(float) * seasonal
            promo = rng.random(N_WEEKS) < 0.05
            if promo.any():
                qty[promo] *= rng.uniform(2.0, 3.0, int(promo.sum()))
            qty = np.maximum(qty, 0.0)

        frames.append(pd.DataFrame({
            "sku_id":          sid,
            "week_start_date": week_dates,
            "quantity_sold":   np.round(qty, 2),
            "revenue":         None,
        }))

    return pd.concat(frames, ignore_index=True)


# ── Inventory batches ──────────────────────────────────────────────────────────
def build_inventory_batches(sku_df, sales_df):
    """
    Stock quantities are calibrated in plain weeks/days against avg demand.
    No formulas or constants are shared with the analytics core.
    """
    recent     = sales_df.sort_values("week_start_date").groupby("sku_id").tail(26)
    avg_weekly = recent.groupby("sku_id")["quantity_sold"].mean()

    n = [0]

    def batch(sid, qty, received_days_ago, expiry=None):
        n[0] += 1
        return {
            "sku_id":           sid,
            "batch_code":       f"LOT-{n[0]:06d}",
            "quantity_on_hand": round(max(float(qty), 1.0), 2),
            "received_date":    REFERENCE_DATE - timedelta(days=int(received_days_ago)),
            "expiry_date":      expiry,
        }

    rows = []
    for _, sku in sku_df.iterrows():
        pool  = sku["pool"]
        sid   = int(sku["sku_id"])
        avg_w = float(avg_weekly.get(sid, 1.0))
        avg_d = avg_w / 7.0  # daily demand (weeks / 7 — no formula import)

        if pool == "SLOW":
            # 18–30 months of stock; split across 2–3 batches
            total  = max(avg_w * float(rng.uniform(18, 30)) * 4.33, 20.0)
            splits = rng.dirichlet(np.ones(int(rng.integers(2, 4)))) * total
            for qty in splits:
                rows.append(batch(sid, qty, int(rng.integers(30, 180))))

        elif pool == "EXPIRY":
            # Primary batch: expires in 20–45 days; qty > projected sell-through
            dte    = int(rng.integers(20, 46))
            expiry = REFERENCE_DATE + timedelta(days=dte)
            qty    = max(avg_d * dte * float(rng.uniform(1.5, 2.5)), 10.0)
            shelf  = int(sku["shelf_life_days"])
            rows.append(batch(sid, qty, max(1, shelf - dte), expiry=expiry))
            # 40 % chance of a second batch expiring further out
            if rng.random() < 0.40:
                dte2 = int(rng.integers(60, 91))
                rows.append(batch(
                    sid,
                    max(avg_d * dte2 * float(rng.uniform(0.3, 0.6)), 5.0),
                    max(1, shelf - dte2),
                    expiry=REFERENCE_DATE + timedelta(days=dte2),
                ))

        elif pool == "STOCKOUT":
            # Stock covers only 5–12 days; primary lead time is 45–70 days
            rows.append(batch(
                sid,
                max(avg_d * float(rng.uniform(5, 12)), 1.0),
                int(rng.integers(7, 30)),
            ))

        elif pool == "PHARMA":
            total  = max(avg_w * float(rng.uniform(6, 16)), 5.0)
            splits = rng.dirichlet(np.ones(int(rng.integers(1, 3)))) * total
            for qty in splits:
                rec = int(rng.integers(14, 90))
                exp = None
                if bool(sku["is_perishable"]):
                    exp = (REFERENCE_DATE
                           - timedelta(days=rec)
                           + timedelta(days=int(sku["shelf_life_days"])))
                rows.append(batch(sid, max(float(qty), 1.0), rec, expiry=exp))

        else:  # General FMCG — healthy 4–12 weeks of cover
            total  = max(avg_w * float(rng.uniform(4, 12)), 2.0)
            splits = rng.dirichlet(np.ones(int(rng.integers(1, 4)))) * total
            for qty in splits:
                rows.append(batch(sid, max(float(qty), 1.0),
                                  int(rng.integers(7, 60))))

    return pd.DataFrame(rows)


# ── Truncate ────────────────────────────────────────────────────────────────────
def truncate_all(conn):
    for t in ["inventory_batch", "sales_history", "sku_supplier",
              "sku", "supplier", "category"]:
        conn.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE"))


# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    engine     = get_engine()
    week_dates = week_start_dates()

    print(f"Seed           : {SEED}")
    print(f"Reference date : {REFERENCE_DATE}")
    print(f"Weeks          : {week_dates[0]} → {week_dates[-1]}")
    print(f"Total SKUs     : {N_SKUS}")
    print()

    with engine.begin() as conn:
        print("Truncating tables …")
        truncate_all(conn)

        print("Inserting categories …")
        cat_ids = insert_categories(conn)
        print(f"  → {len(cat_ids)} rows")

        print("Inserting suppliers …")
        sup_ids = insert_suppliers(conn)
        print(f"  → {len(sup_ids)} rows")

        print("Building and inserting SKU master …")
        sku_df = build_skus(cat_ids)
        sku_df = insert_skus(conn, sku_df)
        print(f"  → {len(sku_df)} rows")

        print("Building and inserting SKU–supplier links …")
        ss_df = build_sku_supplier(sku_df, sup_ids)
        ss_df.to_sql("sku_supplier", conn, if_exists="append",
                     index=False, method="multi")
        print(f"  → {len(ss_df)} rows")

        print("Building and inserting sales history …")
        sales_df = build_sales_history(sku_df, week_dates)
        for i in range(0, len(sales_df), 5_000):
            sales_df.iloc[i : i + 5_000].to_sql(
                "sales_history", conn, if_exists="append",
                index=False, method="multi",
            )
        print(f"  → {len(sales_df):,} rows")

        print("Building and inserting inventory batches …")
        batch_df = build_inventory_batches(sku_df, sales_df)
        batch_df.to_sql("inventory_batch", conn, if_exists="append",
                        index=False, method="multi")
        print(f"  → {len(batch_df):,} rows")

    print("\nDone.")


if __name__ == "__main__":
    main()
