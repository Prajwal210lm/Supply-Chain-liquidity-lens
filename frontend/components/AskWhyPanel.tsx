"use client";

import { useState, useCallback } from "react";
import { Cluster, ClusterMember, SkuFacts, CLUSTER_LABELS, fetchAskWhy, fmtFull, fmtDecimal } from "@/lib/api";

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

// ── Key-value row ─────────────────────────────────────────────────────────────

function KV({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-xs text-gray-400 flex-shrink-0 w-44">{label}</span>
      <span className="text-xs text-gray-800 text-right font-medium">{value}</span>
    </div>
  );
}

function FactsBlock({ facts }: { facts: SkuFacts }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">
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
      <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">
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

  if (!skuCode) return null;

  const found = findSku(clusters, skuCode);

  return (
    <>
      {/* Dim backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Panel */}
      <aside className="fixed top-0 right-0 h-full w-[440px] bg-white shadow-2xl z-50 flex flex-col border-l border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-200 flex-shrink-0">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-0.5">
              SKU Detail
            </p>
            <p className="font-mono text-sm font-bold text-gray-900">{skuCode}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {found.length === 0 ? (
            <p className="text-sm text-gray-400 italic">SKU not found in top members.</p>
          ) : (
            found.map(({ member, clusterId, clusterLabel }) => (
              <div key={clusterId} className="space-y-4">
                {/* Cluster badge */}
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 border border-gray-200 bg-gray-50 text-gray-600">
                    {clusterLabel}
                  </span>
                  <span className="text-xs text-gray-400">
                    {fmtFull(member.lever_contribution)} AED at stake
                  </span>
                </div>

                <FactsBlock facts={member.facts} />
                <SpecificsBlock specifics={member.specifics} />
              </div>
            ))
          )}

          {/* AI explanation result */}
          {aiResult && (
            <div className="border border-gray-200 bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">
                AI Explanation
              </p>
              <p className="text-sm text-gray-800 leading-relaxed">{aiResult}</p>
            </div>
          )}

          {aiUnavailable && (
            <p className="text-xs text-gray-400 italic">
              Run a fresh diagnosis to enable AI explanations.
            </p>
          )}
        </div>

        {/* Footer — Ask AI button */}
        <div className="flex-shrink-0 px-6 py-4 border-t border-gray-200">
          <button
            onClick={handleAskAi}
            disabled={aiLoading}
            className="w-full px-4 py-2 bg-gray-900 text-white text-sm font-medium tracking-wide
                       uppercase hover:bg-gray-700 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {aiLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block w-2 h-2 bg-white rounded-full animate-pulse" />
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
