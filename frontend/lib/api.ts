const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Response types ────────────────────────────────────────────────────────────

export type SkuFacts = {
  sku_code: string;
  name: string | null;
  category_name: string | null;
  unit_cost: number;
  selling_price: number;
  unit_margin: number;
  on_hand_units: number;
  inventory_value: number;
  avg_weekly_demand: number;
  avg_daily_demand: number;
  months_of_cover: number | null;
  days_of_cover: number | null;
  target_coverage_days: number;
  lead_time_days: number;
  abc_class: string | null;
  xyz_class: string | null;
  demand_cv: number | null;
  moq: number;
  moq_weeks_of_cover: number | null;
  weeks_since_last_sale: number | null;
  supplier_name: string | null;
  supplier_country: string | null;
  supplier_reliability: number | null;
  service_level_target: number | null;
  safe_to_release: boolean;
};

export type ClusterMember = {
  sku_code: string;
  lever_contribution: number;
  facts: SkuFacts;
  specifics: Record<string, unknown>;
};

export type ClusterId = "slow_excess" | "expiry" | "stockout";

export type Cluster = {
  cluster_id: ClusterId;
  kind: string;
  lever: string;
  lever_total: number;
  member_count: number;
  top_members: ClusterMember[];
};

export type ValueAtStake = {
  releasable_cash: number;
  write_off_exposure: number;
  stockout_margin_loss: number;
  total: number;
  sku_count: number;
  flagged_sku_count: number;
};

export type QualityReport = {
  total_skus: number;
  total_batches: number;
  skus_missing_cost: number;
  skus_missing_lead_time: number;
  skus_without_supplier: number;
  skus_with_no_recent_sales: number;
  perishable_without_expiry: number;
  batches_already_expired: number;
  negative_stock_skus: number;
  issues: string[];
};

export type DiagnoseResponse = {
  brief: { headline: string; body_markdown: string };
  value_at_stake: ValueAtStake;
  clusters: Cluster[];
  quality_report: QualityReport;
  violations: Record<string, string[]>;
};

export type AskWhyResponse = {
  sku_code: string;
  explanation: string;
  cluster_memberships: string[];
  violations: string[];
};

// ── Fetch helpers ─────────────────────────────────────────────────────────────

export async function runDiagnosis(): Promise<DiagnoseResponse> {
  // Try the live backend first.
  try {
    const res = await fetch(`${API_BASE}/api/diagnose`, { method: "POST" });
    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`Diagnosis failed (${res.status}): ${text}`);
    }
    return res.json();
  } catch {
    // Backend unavailable (e.g. static deploy on Vercel) — fall back to the
    // pre-computed result shipped in /public.
    const cached = await fetch("/cached-diagnosis.json");
    if (!cached.ok) {
      throw new Error(`Diagnosis failed: backend unavailable and no cached result (${cached.status})`);
    }
    return cached.json();
  }
}

export async function fetchAskWhy(skuCode: string): Promise<AskWhyResponse> {
  const res = await fetch(
    `${API_BASE}/api/ask-why/${encodeURIComponent(skuCode)}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Ask-why failed (${res.status}): ${text}`);
  }
  return res.json();
}

// ── Formatting ────────────────────────────────────────────────────────────────

export function fmtCompact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${Math.round(value / 1_000)}K`;
  return Math.round(value).toLocaleString("en-US");
}

export function fmtFull(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

export function fmtDecimal(
  value: number | null | undefined,
  decimals = 1
): string {
  if (value == null) return "N/A";
  return value.toFixed(decimals);
}

export const CLUSTER_LABELS: Record<ClusterId, string> = {
  slow_excess: "Slow-Moving Excess",
  expiry: "Expiry Risk",
  stockout: "Stockout Risk",
};

export const LEVER_LABELS: Record<string, string> = {
  releasable_cash: "Releasable Cash",
  write_off_exposure: "Write-Off Exposure",
  stockout_margin_loss: "Margin at Risk",
};

// ── Cluster accent (single source) ───────────────────────────────────────────
// Every component that colors a cluster badge/bar/spine reads from here, so
// the same cluster always renders the same color everywhere — previously
// ClusterTable/SupplierAnalysis and AskWhyPanel each hand-typed their own
// (slightly different) hex values for the same three clusters.
export type ClusterAccent = { color: string; bg: string };

export const CLUSTER_ACCENT: Record<ClusterId, ClusterAccent> = {
  slow_excess: { color: "var(--green-accent)", bg: "var(--green-accent-bg)" },
  expiry: { color: "var(--amber-accent)", bg: "var(--amber-accent-bg)" },
  stockout: { color: "var(--red-accent)", bg: "var(--red-accent-bg)" },
};

export const CLUSTER_ACCENT_FALLBACK: ClusterAccent = {
  color: "var(--text-secondary)",
  bg: "var(--slate-accent-bg)",
};
