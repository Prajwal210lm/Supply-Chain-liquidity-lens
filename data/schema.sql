-- Liquidity Lens — PostgreSQL schema
-- Step 1 of the build order: the data model the synthetic generator populates
-- and the deterministic analytics core reads.
--
-- Conventions:
--   * Sales are stored at WEEKLY grain (one row per SKU per week).
--   * The analytics core normalises units: average daily demand = weekly qty / 7,
--     while lead time stays in days. Keep that convention everywhere.
--   * ALL stock is held at batch level; non-perishable batches carry a NULL expiry.
--   * Service-level target lives as a column on category, with an optional
--     per-SKU override. No separate target table.
--   * Replenishment timing is derived from lead_time_days; there is no
--     purchase-order table by design.

BEGIN;

-- ---------------------------------------------------------------------------
-- category
-- Reference table of product categories. Holds the default service-level
-- target for every SKU in the category (excess and stockout risk compare
-- against it). A SKU may override the default.
-- ---------------------------------------------------------------------------
CREATE TABLE category (
    category_id           INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                  TEXT    NOT NULL UNIQUE,
    -- Default service level as a fraction in (0, 1], e.g. 0.95 = 95%.
    service_level_target  NUMERIC(4, 3) NOT NULL
        CHECK (service_level_target > 0 AND service_level_target <= 1)
);

-- ---------------------------------------------------------------------------
-- supplier
-- Master list of suppliers. Lead time and MOQ are NOT here — they belong to
-- the SKU-supplier pairing. Reliability supports the reasoning layer's
-- root-cause attribution (supplier unreliability / concentration).
-- ---------------------------------------------------------------------------
CREATE TABLE supplier (
    supplier_id        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name               TEXT NOT NULL,
    country            TEXT,
    -- Optional 0..1 reliability indicator; NULL when unknown.
    reliability_score  NUMERIC(4, 3)
        CHECK (reliability_score IS NULL
               OR (reliability_score >= 0 AND reliability_score <= 1))
);

-- ---------------------------------------------------------------------------
-- sku
-- The product master and the spine every metric hangs off. unit_cost values
-- inventory; (selling_price - unit_cost) is the margin used for stockout loss.
-- is_perishable / shelf_life_days gate the expiry logic. service_level_target
-- overrides the category default when set.
-- ---------------------------------------------------------------------------
CREATE TABLE sku (
    sku_id                INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku_code              TEXT NOT NULL UNIQUE,
    name                  TEXT NOT NULL,
    category_id           INT  NOT NULL REFERENCES category (category_id),
    unit_cost             NUMERIC(12, 2) NOT NULL CHECK (unit_cost >= 0),
    selling_price         NUMERIC(12, 2) NOT NULL CHECK (selling_price >= 0),
    is_perishable         BOOLEAN NOT NULL DEFAULT FALSE,
    -- Required for perishable SKUs; NULL otherwise.
    shelf_life_days       INT CHECK (shelf_life_days IS NULL OR shelf_life_days > 0),
    -- Optional per-SKU override of the category service level.
    service_level_target  NUMERIC(4, 3)
        CHECK (service_level_target IS NULL
               OR (service_level_target > 0 AND service_level_target <= 1)),
    -- A perishable SKU must declare a shelf life.
    CONSTRAINT perishable_has_shelf_life
        CHECK (NOT is_perishable OR shelf_life_days IS NOT NULL)
);

CREATE INDEX idx_sku_category ON sku (category_id);

-- ---------------------------------------------------------------------------
-- sku_supplier
-- The SKU-to-supplier relationship (many-to-many). Lead time and MOQ are
-- facts about the pairing, so they live here. is_primary marks the default
-- source; at most one primary per SKU.
-- ---------------------------------------------------------------------------
CREATE TABLE sku_supplier (
    sku_id          INT NOT NULL REFERENCES sku (sku_id) ON DELETE CASCADE,
    supplier_id     INT NOT NULL REFERENCES supplier (supplier_id) ON DELETE CASCADE,
    lead_time_days  INT NOT NULL CHECK (lead_time_days > 0),
    moq             INT NOT NULL DEFAULT 0 CHECK (moq >= 0),
    is_primary      BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (sku_id, supplier_id)
);

-- At most one primary supplier per SKU.
CREATE UNIQUE INDEX idx_sku_one_primary
    ON sku_supplier (sku_id)
    WHERE is_primary;

-- ---------------------------------------------------------------------------
-- inventory_batch
-- Current stock on hand, held at batch/lot level. Perishable SKUs carry a real
-- expiry_date per lot; non-perishable batches have expiry_date = NULL.
-- On-hand for a SKU = SUM(quantity_on_hand) over its batches.
-- (The generator is responsible for only setting expiry on perishable SKUs.)
-- ---------------------------------------------------------------------------
CREATE TABLE inventory_batch (
    batch_id          INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku_id            INT  NOT NULL REFERENCES sku (sku_id) ON DELETE CASCADE,
    batch_code        TEXT,
    quantity_on_hand  NUMERIC(14, 2) NOT NULL CHECK (quantity_on_hand >= 0),
    received_date     DATE NOT NULL,
    expiry_date       DATE,
    CONSTRAINT expiry_after_received
        CHECK (expiry_date IS NULL OR expiry_date > received_date)
);

CREATE INDEX idx_batch_sku    ON inventory_batch (sku_id);
-- Supports expiry-risk scans over near-dated lots.
CREATE INDEX idx_batch_expiry ON inventory_batch (expiry_date)
    WHERE expiry_date IS NOT NULL;

-- ---------------------------------------------------------------------------
-- sales_history
-- Weekly demand time series: one row per SKU per week. The series (not a
-- total) is what feeds velocity, demand variability, and recency.
-- week_start_date is the Monday of the ISO week.
-- ---------------------------------------------------------------------------
CREATE TABLE sales_history (
    sku_id           INT  NOT NULL REFERENCES sku (sku_id) ON DELETE CASCADE,
    week_start_date  DATE NOT NULL,
    quantity_sold    NUMERIC(14, 2) NOT NULL CHECK (quantity_sold >= 0),
    -- Optional realised revenue for the week; NULL if not tracked.
    revenue          NUMERIC(14, 2) CHECK (revenue IS NULL OR revenue >= 0),
    PRIMARY KEY (sku_id, week_start_date)
);

-- Supports "last N weeks" recency scans for dead-stock detection.
CREATE INDEX idx_sales_week ON sales_history (week_start_date);

COMMIT;
