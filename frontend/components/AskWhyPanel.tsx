"use client";

import { useState, useCallback } from "react";
import { Cluster, ClusterMember, SkuFacts, CLUSTER_LABELS, fetchAskWhy, fmtFull, fmtDecimal } from "@/lib/api";

// Round large comma-formatted numbers in AI prose (18,819,464.91 -> 18.8M,
// 344,093.90 -> 344K, 24,600 -> 24.6K). Numbers under 10,000 are left as-is.
function formatLargeNumbers(text: string): string {
  return text.replace(/\d{1,3}(?:,\d{3})+(?:\.\d+)?/g, (match) => {
    const value = parseFloat(match.replace(/,/g, ""));
    if (Number.isNaN(value)) return match;
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 100_000) return `${Math.round(value / 1_000)}K`;
    if (value >= 10_000) return `${(value / 1_000).toFixed(1)}K`;
    return match; // below 10,000: leave as-is
  });
}

// ── Fact lookup ───────────────────────────────────────────────────────────────

type FoundSku = {
  member: ClusterMember;
  clusterId: string;
  clusterLabel: string;
};

function findSku(clusters: Cluster[], skuCode: string): FoundSku[] {
  const results: FoundSku[] = [];
  for (const cluster of clusters) {
    for (const member of cluster.top_members) {
      if (member.facts.sku_code === skuCode) {
        results.push({
          member,
          clusterId: cluster.cluster_id,
          clusterLabel: CLUSTER_LABELS[cluster.cluster_id] ?? cluster.cluster_id,
        });
      }
    }
  }
  return results;
}

const CLUSTER_STYLE: Record<string, { bg: string; text: string }> = {
  slow_excess: { bg: "#0596691a", text: "#059669" },
  expiry:      { bg: "#D977061a", text: "#D97706" },
  stockout:    { bg: "#DC26261a", text: "#DC2626" },
};

// ── Key-value row ─────────────────────────────────────────────────────────────

function KV({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-xs uppercase tracking-wider text-[var(--text-secondary)] flex-shrink-0 w-44">
        {label}
      </span>
      <span className="font-mono text-xs text-[var(--text-primary)] text-right">{value}</span>
    </div>
  );
}

function FactsBlock({ facts }: { facts: SkuFacts }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-widest text-[var(--text-secondary)] mb-2">
        SKU Facts
      </p>
      <KV label="Category" value={facts.category_name ?? "—"} />
      <KV label="Supplier" value={facts.supplier_name ?? "—"} />
      <KV label="Supplier Reliability" value={facts.supplier_reliability != null ? `${(facts.supplier_reliability * 100).toFixed(0)}%` : "—"} />
      <KV label="ABC · XYZ Class" value={`${facts.abc_class ?? "?"} · ${facts.xyz_class ?? "?"}`} />
      <KV label="Unit Cost (AED)" value={fmtFull(facts.unit_cost)} />
      <KV label="Selling Price (AED)" value={fmtFull(facts.selling_price)} />
      <KV label="Unit Margin (AED)" value={fmtFull(facts.unit_margin)} />
      <KV label="On Hand (units)" value={fmtDecimal(facts.on_hand_units, 1)} />
      <KV label="Inventory Value (AED)" value={fmtFull(facts.inventory_value)} />
      <KV label="Avg Weekly Demand" value={fmtDecimal(facts.avg_weekly_demand, 2)} />
      <KV label="Months of Cover" value={fmtDecimal(facts.months_of_cover, 1)} />
      <KV label="Target Coverage (days)" value={fmtDecimal(facts.target_coverage_days, 0)} />
      <KV label="Lead Time (days)" value={fmtDecimal(facts.lead_time_days, 0)} />
      <KV label="MOQ" value={fmtFull(facts.moq)} />
      <KV label="Safe to Release" value={facts.safe_to_release ? "Yes" : "No"} />
    </div>
  );
}

function SpecificsBlock({ specifics }: { specifics: Record<string, unknown> }) {
  const entries = Object.entries(specifics).filter(([, v]) => v != null);
  if (entries.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-widest text-[var(--text-secondary)] mb-2">
        Cluster Specifics
      </p>
      {entries.map(([k, v]) => (
        <KV
          key={k}
          label={k.replace(/_/g, " ")}
          value={
            typeof v === "number"
              ? fmtDecimal(v, 2)
              : typeof v === "boolean"
              ? v ? "Yes" : "No"
              : String(v)
          }
        />
      ))}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function AskWhyPanel({
  skuCode,
  clusters,
  onClose,
}: {
  skuCode: string | null;
  clusters: Cluster[];
  onClose: () => void;
}) {
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);
  const [aiUnavailable, setAiUnavailable] = useState(false);

  const handleAskAi = useCallback(async () => {
    if (!skuCode) return;
    setAiLoading(true);
    setAiResult(null);
    setAiUnavailable(false);
    try {
      const res = await fetchAskWhy(skuCode);
      setAiResult(res.explanation);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("404") || msg.includes("No diagnosis run")) {
        setAiUnavailable(true);
      } else {
        setAiResult(`Error: ${msg}`);
      }
    } finally {
      setAiLoading(false);
    }
  }, [skuCode]);

  // Reset AI state when SKU changes
  const [prevSku, setPrevSku] = useState<string | null>(null);
  if (skuCode !== prevSku) {
    setPrevSku(skuCode);
    setAiResult(null);
    setAiUnavailable(false);
    setAiLoading(false);
  }

  const isOpen = skuCode !== null;
  const found = skuCode ? findSku(clusters, skuCode) : [];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 transition-opacity duration-200"
        style={{
          background: "rgba(0,0,0,0.2)",
          opacity: isOpen ? 1 : 0,
          pointerEvents: isOpen ? "auto" : "none",
        }}
        onClick={onClose}
      />

      {/* Slide-in panel */}
      <aside
        className="fixed top-0 right-0 h-full w-full sm:w-[480px] z-50 flex flex-col shadow-2xl rounded-l-2xl overflow-hidden"
        style={{
          transform: isOpen ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.25s ease-out",
          background: "#ffffff",
        }}
      >
        {/* Dark header */}
        <div
          className="flex items-center justify-between px-6 py-5 flex-shrink-0"
          style={{ background: "var(--navy-900)" }}
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest mb-0.5" style={{ color: "rgba(255,255,255,0.5)" }}>
              SKU Detail
            </p>
            <p className="font-mono text-sm font-bold text-white">{skuCode ?? "—"}</p>
          </div>
          <button
            onClick={onClose}
            className="transition-opacity hover:opacity-100 opacity-60"
            style={{ color: "white" }}
            aria-label="Close"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M3 3l10 10M13 3L3 13" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {isOpen && found.length === 0 && (
            <p className="text-sm text-[var(--text-secondary)] italic">SKU not found in top members.</p>
          )}

          {isOpen && found.map(({ member, clusterId, clusterLabel }) => {
            const style = CLUSTER_STYLE[clusterId] ?? { bg: "#6475801a", text: "#64748B" };
            return (
              <div key={clusterId} className="space-y-4">
                <div className="flex items-center gap-2">
                  <span
                    className="text-xs px-2.5 py-0.5 rounded-full font-semibold"
                    style={{ backgroundColor: style.bg, color: style.text }}
                  >
                    {clusterLabel}
                  </span>
                  <span className="text-xs text-[var(--text-secondary)]">
                    {fmtFull(member.lever_contribution)} AED at stake
                  </span>
                </div>
                <FactsBlock facts={member.facts} />
                <SpecificsBlock specifics={member.specifics} />
              </div>
            );
          })}

          {aiResult && (
            <div
              className="rounded-xl p-4 border"
              style={{ background: "rgba(15,26,46,0.03)", borderColor: "rgba(27,58,92,0.15)" }}
            >
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--navy-700)] mb-2">
                AI Explanation
              </p>
              <p className="text-sm text-[var(--text-primary)] leading-relaxed">{formatLargeNumbers(aiResult)}</p>
            </div>
          )}

          {aiUnavailable && (
            <p className="text-xs text-[var(--text-secondary)] italic">
              Run a fresh diagnosis to enable AI explanations.
            </p>
          )}
        </div>

        {/* Ask AI footer */}
        <div className="flex-shrink-0 px-6 py-4 border-t border-gray-100">
          <button
            onClick={handleAskAi}
            disabled={aiLoading || !isOpen}
            className="w-full px-4 py-2.5 text-sm font-semibold uppercase tracking-wide text-white
                       rounded-lg transition-all duration-200
                       disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: "var(--navy-700)" }}
          >
            {aiLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analysing…
              </span>
            ) : (
              "Ask AI"
            )}
          </button>
        </div>
      </aside>
    </>
  );
}
