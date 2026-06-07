"use client";

import { useState } from "react";
import {
  Cluster,
  ClusterMember,
  ClusterId,
  CLUSTER_LABELS,
  LEVER_LABELS,
  fmtFull,
  fmtDecimal,
} from "@/lib/api";

// ── Per-cluster column configuration ─────────────────────────────────────────

type CoverConfig = {
  header: string;
  getValue: (m: ClusterMember) => string;
};

const COVER_CONFIG: Record<ClusterId, CoverConfig> = {
  slow_excess: {
    header: "Months Cover",
    getValue: (m) => fmtDecimal(m.facts.months_of_cover, 1),
  },
  expiry: {
    header: "Days to Expiry",
    getValue: (m) =>
      fmtDecimal(m.specifics.nearest_days_to_expiry as number | null, 0),
  },
  stockout: {
    header: "Shortfall Days",
    getValue: (m) =>
      fmtDecimal(m.specifics.shortfall_days as number | null, 0),
  },
};

// ── Cluster section ───────────────────────────────────────────────────────────

function ClusterSection({
  cluster,
  onSkuClick,
  selectedSku,
}: {
  cluster: Cluster;
  onSkuClick: (sku: string) => void;
  selectedSku: string | null;
}) {
  const [open, setOpen] = useState(true);
  const cover = COVER_CONFIG[cluster.cluster_id];
  const label = CLUSTER_LABELS[cluster.cluster_id];
  const lever = LEVER_LABELS[cluster.lever] ?? cluster.lever;

  return (
    <div className="border border-gray-200">
      {/* Section header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-4">
          <span className="text-sm font-semibold text-gray-800">{label}</span>
          <span className="text-xs text-gray-400">
            {lever} · {cluster.member_count} SKUs
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold text-gray-900">
            {fmtFull(cluster.lever_total)}{" "}
            <span className="font-normal text-gray-400 text-xs">AED</span>
          </span>
          <span className="text-gray-400 text-sm">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* Table */}
      {open && cluster.top_members.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-200 bg-white">
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide w-28">
                  SKU
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide">
                  Category
                </th>
                <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide">
                  Value at Stake (AED)
                </th>
                <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide">
                  {cover.header}
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide">
                  Supplier
                </th>
                <th className="text-center px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide w-20">
                  ABC·XYZ
                </th>
              </tr>
            </thead>
            <tbody>
              {cluster.top_members.map((m, i) => {
                const isSelected = m.facts.sku_code === selectedSku;
                return (
                  <tr
                    key={`${m.facts.sku_code}-${i}`}
                    onClick={() => onSkuClick(m.facts.sku_code)}
                    className={`border-b border-gray-100 cursor-pointer transition-colors
                      ${i % 2 === 0 ? "bg-white" : "bg-gray-50"}
                      ${isSelected ? "bg-blue-50 border-l-2 border-l-blue-500" : "hover:bg-blue-50"}`}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-gray-800">
                      {m.facts.sku_code}
                    </td>
                    <td className="px-4 py-3 text-gray-700">
                      {m.facts.category_name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">
                      {fmtFull(m.lever_contribution)}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {cover.getValue(m)}
                    </td>
                    <td className="px-4 py-3 text-gray-700 max-w-32 truncate">
                      {m.facts.supplier_name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-xs font-mono text-gray-600">
                        {m.facts.abc_class ?? "?"}·{m.facts.xyz_class ?? "?"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {open && cluster.top_members.length === 0 && (
        <p className="px-5 py-4 text-sm text-gray-400 italic">No flagged SKUs in this cluster.</p>
      )}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function ClusterTable({
  clusters,
  onSkuClick,
  selectedSku,
}: {
  clusters: Cluster[];
  onSkuClick: (sku: string) => void;
  selectedSku: string | null;
}) {
  return (
    <section>
      <h2 className="text-base font-semibold text-gray-500 uppercase tracking-widest mb-4">
        Flagged Clusters
      </h2>
      <div className="space-y-3">
        {clusters.map((c) => (
          <ClusterSection
            key={c.cluster_id}
            cluster={c}
            onSkuClick={onSkuClick}
            selectedSku={selectedSku}
          />
        ))}
      </div>
    </section>
  );
}
