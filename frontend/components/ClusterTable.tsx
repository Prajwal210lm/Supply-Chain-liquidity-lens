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
import { sectionHeader } from "@/components/SummaryCards";

// ── Cluster accent colours ────────────────────────────────────────────────────

const CLUSTER_STYLE: Record<string, { bg: string; text: string; color: string }> = {
  slow_excess: { bg: "#0596691a", text: "#059669", color: "#059669" },
  expiry:      { bg: "#D977061a", text: "#D97706", color: "#D97706" },
  stockout:    { bg: "#DC26261a", text: "#DC2626", color: "#DC2626" },
};

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
    getValue: (m) => fmtDecimal(m.specifics.nearest_days_to_expiry as number | null, 0),
  },
  stockout: {
    header: "Shortfall Days",
    getValue: (m) => fmtDecimal(m.specifics.shortfall_days as number | null, 0),
  },
};

// ── Chevron icon ──────────────────────────────────────────────────────────────

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`transition-transform duration-200 ${open ? "rotate-180" : "rotate-0"}`}
      aria-hidden="true"
    >
      <path d="M4 6l4 4 4-4" />
    </svg>
  );
}

// ── Cluster section ───────────────────────────────────────────────────────────

function ClusterSection({
  cluster,
  onSkuClick,
  selectedSku,
  defaultOpen,
}: {
  cluster: Cluster;
  onSkuClick: (sku: string) => void;
  selectedSku: string | null;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const cover = COVER_CONFIG[cluster.cluster_id];
  const label = CLUSTER_LABELS[cluster.cluster_id];
  const lever = LEVER_LABELS[cluster.lever] ?? cluster.lever;
  const style = CLUSTER_STYLE[cluster.cluster_id] ?? { bg: "#6475801a", text: "#64748B", color: "#64748B" };

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-100">
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors text-left"
        style={{ background: open ? "rgba(15,26,46,0.02)" : undefined }}
      >
        <div className="flex items-center gap-3">
          {/* Coloured cluster badge */}
          <span
            className="inline-block rounded-full px-3 py-0.5 text-xs font-semibold"
            style={{ backgroundColor: style.bg, color: style.text }}
          >
            {label}
          </span>
          <span className="text-xs text-[var(--text-secondary)]">
            {lever} · {cluster.member_count} SKUs
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-display text-xl" style={{ color: "var(--navy-900)" }}>
            {fmtFull(cluster.lever_total)}
            <span className="text-sm font-sans font-normal ml-1.5 text-[var(--text-secondary)]">AED</span>
          </span>
          <span className="text-[var(--text-secondary)]">
            <Chevron open={open} />
          </span>
        </div>
      </button>

      {/* Collapsible table */}
      {open && cluster.top_members.length > 0 && (
        <div className="overflow-x-auto border-t border-gray-100">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] w-28">
                  SKU
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Category
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Value at Stake (AED)
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  {cover.header}
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Supplier
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] w-20">
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
                      ${isSelected
                        ? "bg-blue-50 border-l-2 border-l-blue-500"
                        : "hover:bg-gray-50"
                      }`}
                  >
                    <td className="px-4 py-2.5">
                      <span
                        className="font-mono text-xs hover:underline"
                        style={{ color: "var(--navy-700)" }}
                      >
                        {m.facts.sku_code}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-sm text-[var(--text-primary)]">
                      {m.facts.category_name ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-sm text-[var(--text-primary)] font-medium">
                      {fmtFull(m.lever_contribution)}
                    </td>
                    <td className="px-4 py-2.5 text-center font-mono tabular-nums text-sm text-[var(--text-secondary)]">
                      {cover.getValue(m)}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-[var(--text-secondary)] max-w-32 truncate">
                      {m.facts.supplier_name ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="inline-block rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-[var(--text-secondary)]">
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
        <p className="px-5 py-4 text-sm text-[var(--text-secondary)] italic border-t border-gray-100">
          No flagged SKUs in this cluster.
        </p>
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
      <h2 className={sectionHeader}>Flagged Clusters</h2>
      <div className="space-y-3">
        {clusters.map((c, i) => (
          <ClusterSection
            key={c.cluster_id}
            cluster={c}
            onSkuClick={onSkuClick}
            selectedSku={selectedSku}
            defaultOpen={i === 0}
          />
        ))}
      </div>
    </section>
  );
}
