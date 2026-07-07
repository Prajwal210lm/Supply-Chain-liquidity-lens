"use client";

import { useState, useCallback } from "react";
import { Cluster, ClusterMember, SkuFacts, CLUSTER_LABELS, fetchAskWhy, fmtFull, fmtDecimal } from "@/lib/api";
import { formatAED } from "@/lib/format";

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

type FoundSku = { member: ClusterMember; clusterId: string; clusterLabel: string };

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
  slow_excess: { bg: "rgba(14,159,110,0.14)", text: "#10B981" },
  expiry: { bg: "rgba(217,132,43,0.14)", text: "#E0982C" },
  stockout: { bg: "rgba(214,69,61,0.14)", text: "#EF6B63" },
};

// ── Key-value row ─────────────────────────────────────────────────────────────

function KV({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-black/[0.05] last:border-0">
      <span className="text-[11px] uppercase tracking-[0.08em] text-[var(--text-secondary)] flex-shrink-0 w-44">{label}</span>
      <span className="font-mono text-[12px] text-[var(--text-primary)] text-right tnum">{value}</span>
    </div>
  );
}

function BlockLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--navy-700)] mb-2.5">
      <span className="w-3 h-px bg-[var(--gold)] flex-shrink-0" aria-hidden="true" />
      {children}
    </p>
  );
}

function FactsBlock({ facts }: { facts: SkuFacts }) {
  return (
    <div>
      <BlockLabel>SKU Facts</BlockLabel>
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

// Format a cluster-specific value consistently with the rest of the app:
// currency-like fields as X.XM/XXXK AED, counts/days as whole or 2-dp numbers,
// arrays as a count, nested objects skipped.
function formatSpecific(key: string, v: unknown): string | null {
  if (v == null) return null;
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "number") {
    if (/(value|cash|contribution|loss|exposure|revenue)/i.test(key)) return formatAED(v);
    return Number.isInteger(v) ? v.toLocaleString("en-US") : v.toFixed(2);
  }
  if (Array.isArray(v)) return `${v.length} ${v.length === 1 ? "batch" : "batches"}`;
  if (typeof v === "object") return null; // skip nested objects (no "[object Object]")
  return String(v);
}

function SpecificsBlock({ specifics }: { specifics: Record<string, unknown> }) {
  const entries = Object.entries(specifics)
    .map(([k, v]) => [k, formatSpecific(k, v)] as const)
    .filter((e): e is readonly [string, string] => e[1] !== null);
  if (entries.length === 0) return null;
  return (
    <div>
      <BlockLabel>Cluster Specifics</BlockLabel>
      {entries.map(([k, v]) => (
        <KV key={k} label={k.replace(/_/g, " ")} value={v} />
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
  const [aiFailedContract, setAiFailedContract] = useState(false);

  const handleAskAi = useCallback(async () => {
    if (!skuCode) return;
    setAiLoading(true);
    setAiResult(null);
    setAiUnavailable(false);
    setAiFailedContract(false);
    try {
      const res = await fetchAskWhy(skuCode);
      // Backend fails closed: on a contract violation, `explanation` is
      // withheld (empty) and `violations` is non-empty. Never render an
      // empty/fabricated explanation as if it were a normal AI answer.
      if (res.violations.length > 0) {
        setAiFailedContract(true);
      } else {
        setAiResult(res.explanation);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      // Backend down (network error) or no live run available → show a clean
      // "needs a live run" message rather than a raw fetch error.
      const networkish = err instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(msg);
      if (networkish || msg.includes("404") || msg.includes("No diagnosis run")) {
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
    setAiFailedContract(false);
    setAiLoading(false);
  }

  const isOpen = skuCode !== null;
  const found = skuCode ? findSku(clusters, skuCode) : [];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 transition-opacity duration-300"
        style={{
          background: "rgba(6,10,18,0.45)",
          backdropFilter: "blur(2px)",
          opacity: isOpen ? 1 : 0,
          pointerEvents: isOpen ? "auto" : "none",
          zIndex: "var(--z-backdrop)" as React.CSSProperties["zIndex"],
        }}
        onClick={onClose}
      />

      {/* Slide-in panel */}
      <aside
        className="fixed top-0 right-0 h-full w-full sm:w-[480px] flex flex-col overflow-hidden rounded-l-2xl"
        style={{
          transform: isOpen ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.32s cubic-bezier(0.16, 1, 0.3, 1)",
          background: "var(--card)",
          boxShadow: "var(--elev-4)",
          zIndex: "var(--z-panel)" as React.CSSProperties["zIndex"],
        }}
        aria-hidden={!isOpen}
        inert={!isOpen || undefined}
      >
        {/* Dark header with gold hairline */}
        <div
          className="flex items-center justify-between px-6 py-5 flex-shrink-0"
          style={{ background: "linear-gradient(160deg, var(--ink-950), var(--navy-900))", boxShadow: "0 1px 0 var(--gold-line)" }}
        >
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] mb-1 text-[var(--gold-soft)]/85">SKU Detail</p>
            <p className="font-mono text-[15px] font-semibold text-white tnum">{skuCode ?? "—"}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-white/70 hover:text-white hover:bg-white/10 cursor-pointer transition-colors duration-200"
            aria-label="Close panel"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M3 3l10 10M13 3L3 13" />
            </svg>
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {isOpen && found.length === 0 && (
            <p className="text-[13px] text-[var(--text-secondary)] italic">SKU not found in top members.</p>
          )}

          {isOpen && found.map(({ member, clusterId, clusterLabel }) => {
            const style = CLUSTER_STYLE[clusterId] ?? { bg: "rgba(81,97,122,0.14)", text: "#51617A" };
            return (
              <div key={clusterId} className="space-y-4">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[11.5px] px-2.5 py-0.5 rounded-full font-semibold" style={{ backgroundColor: style.bg, color: style.text }}>
                    {clusterLabel}
                  </span>
                  <span className="text-[12px] text-[var(--text-secondary)] tnum">{fmtFull(member.lever_contribution)} AED at stake</span>
                </div>
                <FactsBlock facts={member.facts} />
                <SpecificsBlock specifics={member.specifics} />
              </div>
            );
          })}

          {aiResult && (
            <div className="rounded-xl p-4 border" style={{ background: "var(--surface)", borderColor: "var(--gold-line)" }}>
              <BlockLabel>AI Explanation</BlockLabel>
              <p className="text-[13.5px] text-[var(--text-primary)]/90 leading-[1.7]">{formatLargeNumbers(aiResult)}</p>
            </div>
          )}

          {aiFailedContract && (
            <div
              className="rounded-xl p-4 border"
              style={{ background: "rgba(217,132,43,0.06)", borderColor: "var(--amber-accent)" }}
            >
              <p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--amber-accent)] mb-2.5">
                <span className="w-3 h-px bg-[var(--amber-accent)] flex-shrink-0" aria-hidden="true" />
                AI Explanation Withheld
              </p>
              <p className="text-[13px] text-[var(--amber-accent)] leading-[1.6]">
                This explanation failed the numbers contract and has been withheld.
              </p>
            </div>
          )}

          {aiUnavailable && (
            <p className="text-[12px] text-[var(--text-secondary)] italic">AI explanations require a live diagnosis run.</p>
          )}
        </div>

        {/* Ask AI footer */}
        <div className="flex-shrink-0 px-6 py-4 border-t border-black/8">
          <button
            onClick={handleAskAi}
            disabled={aiLoading || !isOpen}
            className="w-full px-4 py-2.5 text-[13px] font-semibold uppercase tracking-[0.06em] text-white rounded-xl
                       cursor-pointer transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5
                       disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
            style={{ background: "linear-gradient(180deg, var(--navy-700), var(--navy-800))", boxShadow: "var(--elev-2)" }}
          >
            {aiLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analysing…
              </span>
            ) : (
              "Ask AI why this is flagged"
            )}
          </button>
        </div>
      </aside>
    </>
  );
}
