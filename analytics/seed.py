#!/usr/bin/env python3
"""analytics/seed.py — Create tables and populate the Liquidity Lens database.

Drops and recreates all six tables, then generates and inserts the full
600-SKU synthetic dataset (seed=42, reference date 2025-06-02).

Usage:
    python -m analytics.seed
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).parent.parent / ".env")


# ── DDL ────────────────────────────────────────────────────────────────────────

_DDL = """
DROP TABLE IF EXISTS inventory_batch CASCADE;
DROP TABLE IF EXISTS sales_history    CASCADE;
DROP TABLE IF EXISTS sku_supplier     CASCADE;
DROP TABLE IF EXISTS sku              CASCADE;
DROP TABLE IF EXISTS supplier         CASCADE;
DROP TABLE IF EXISTS category         CASCADE;

CREATE TABLE category (
    category_id          SERIAL  PRIMARY KEY,
    name                 TEXT    NOT NULL,
    service_level_target NUMERIC NOT NULL
);

CREATE TABLE supplier (
    supplier_id       SERIAL  PRIMARY KEY,
    name              TEXT    NOT NULL,
    country           TEXT,
    reliability_score NUMERIC
);

CREATE TABLE sku (
    sku_id               SERIAL  PRIMARY KEY,
    sku_code             TEXT    UNIQUE NOT NULL,
    name                 TEXT,
    category_id          INTEGER NOT NULL REFERENCES category(category_id),
    unit_cost            NUMERIC NOT NULL,
    selling_price        NUMERIC NOT NULL,
    is_perishable        BOOLEAN NOT NULL DEFAULT FALSE,
    shelf_life_days      INTEGER,
    service_level_target NUMERIC
);

CREATE TABLE sku_supplier (
    sku_id         INTEGER NOT NULL REFERENCES sku(sku_id),
    supplier_id    INTEGER NOT NULL REFERENCES supplier(supplier_id),
    lead_time_days INTEGER NOT NULL,
    moq            INTEGER NOT NULL DEFAULT 0,
    is_primary     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE sales_history (
    sku_id          INTEGER NOT NULL REFERENCES sku(sku_id),
    week_start_date DATE    NOT NULL,
    quantity_sold   NUMERIC NOT NULL,
    revenue         NUMERIC
);

CREATE TABLE inventory_batch (
    batch_id         SERIAL  PRIMARY KEY,
    sku_id           INTEGER NOT NULL REFERENCES sku(sku_id),
    batch_code       TEXT,
    quantity_on_hand NUMERIC NOT NULL,
    received_date    DATE    NOT NULL,
    expiry_date      DATE
);
"""


def _create_tables(conn) -> None:
    conn.execute(text(_DDL))


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("ERROR: DATABASE_URL not set — check .env")

    engine = create_engine(url)

    # Import data-generation helpers from the existing generator.
    # They share a module-level rng seeded at 42; calling them in the same
    # order as the original main() reproduces the identical dataset.
    from data.generate import (  # noqa: PLC0415
        N_SKUS,
        SEED,
        build_inventory_batches,
        build_sales_history,
        build_sku_supplier,
        build_skus,
        insert_categories,
        insert_skus,
        insert_suppliers,
        week_start_dates,
    )
    from analytics.ingest import REFERENCE_DATE  # noqa: PLC0415

    week_dates = week_start_dates()

    print(f"Seed           : {SEED}")
    print(f"Reference date : {REFERENCE_DATE}")
    print(f"Weeks          : {week_dates[0]} to {week_dates[-1]}")
    print(f"Total SKUs     : {N_SKUS}")
    print()

    with engine.begin() as conn:
        print("Creating tables (DROP CASCADE + CREATE)...")
        _create_tables(conn)
        print("  ok: all tables created")

        print("Inserting categories...")
        cat_ids = insert_categories(conn)
        print(f"  -> {len(cat_ids)} rows")

        print("Inserting suppliers...")
        sup_ids = insert_suppliers(conn)
        print(f"  -> {len(sup_ids)} rows")

        print("Building and inserting SKU master...")
        sku_df = build_skus(cat_ids)
        sku_df = insert_skus(conn, sku_df)
        print(f"  -> {len(sku_df)} rows")

        print("Building and inserting SKU-supplier links...")
        ss_df = build_sku_supplier(sku_df, sup_ids)
        ss_df.to_sql("sku_supplier", conn, if_exists="append", index=False, method="multi")
        print(f"  -> {len(ss_df)} rows")

        print("Building and inserting sales history...")
        sales_df = build_sales_history(sku_df, week_dates)
        for i in range(0, len(sales_df), 5_000):
            sales_df.iloc[i : i + 5_000].to_sql(
                "sales_history", conn, if_exists="append", index=False, method="multi"
            )
        print(f"  -> {len(sales_df):,} rows")

        print("Building and inserting inventory batches...")
        batch_df = build_inventory_batches(sku_df, sales_df)
        batch_df.to_sql(
            "inventory_batch", conn, if_exists="append", index=False, method="multi"
        )
        print(f"  -> {len(batch_df):,} rows")

    # Summary
    total_inv = float((sku_df["unit_cost"] * batch_df.groupby("sku_id")["quantity_on_hand"].sum().reindex(sku_df["sku_id"]).fillna(0).values).sum())
    pool_counts = sku_df["pool"].value_counts().to_dict()

    print("\n-- Summary --------------------------------------------------")
    print(f"  Total inventory value : AED {total_inv:,.0f}")
    print(f"  SKU pools             : {pool_counts}")
    print(f"  Sales rows            : {len(sales_df):,}")
    print(f"  Batch rows            : {len(batch_df):,}")
    print("-------------------------------------------------------------")
    print("Done.")


if __name__ == "__main__":
    main()
