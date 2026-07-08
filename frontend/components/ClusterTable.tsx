"use client";

import { useState } from "react";
import {
  Cluster,
  ClusterMember,
  ClusterId,
  CLUSTER_LABELS,
  CLUSTER_ACCENT,
  CLUSTER_ACCENT_FALLBACK,
  LEVER_LABELS,
  fmtFull,
  fmtDecimal,
} from "@/lib/api";
import { SectionHeading } from "@/components/SummaryCards";
import { formatAED } from "@/lib/format";

// ── Per-cluster column configuration ─────────────────────────────────────────

type CoverConfig = { header: string; getValue: (m: ClusterMember) => string };

const COVER_CONFIG: Record<ClusterId, CoverConfig> = {
  slow_excess: { header: "Months Cover", getValue: (m) => fmtDecimal(m.facts.months_of_cover, 1) },
  expiry: { header: "Days to Expiry", getValue: (m) => fmtDecimal(m.specifics.nearest_days_to_expiry as number | null, 0) },
  stockout: { header: "Shortfall Days", getValue: (m) => fmtDecimal(m.specifics.shortfall_days as number | null, 0) },
};

// ── Chevron icon ──────────────────────────────────────────────────────────────

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round"
      className={`transition-transform duration-300 ${open ? "rotate-180" : "rotate-0"}`}
      aria-hidden="true"
    >
      <path d="M4 6l4 4 4-4" />
    </svg>
  );
}

const TH = "px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)]";

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
  const accent = CLUSTER_ACCENT[cluster.cluster_id] ?? CLUSTER_ACCENT_FALLBACK;

  return (
    <div
      className="relative rounded-2xl overflow-hidden transition-shadow duration-300"
      style={{ background: "var(--card)", boxShadow: open ? "var(--elev-2)" : "var(--elev-1)", border: "1px solid var(--hairline)" }}
    >
      {/* Left accent spine */}
      <span className="absolute left-0 inset-y-0 w-[3px]" style={{ background: accent.color }} />

      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-4 pl-5 pr-4 py-4 text-left cursor-pointer transition-colors duration-200 hover:bg-black/[0.015]"
        style={open ? { background: "var(--hairline-soft)" } : undefined}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span
            className="inline-block rounded-full px-3 py-1 text-[12px] font-semibold flex-shrink-0"
            style={{ backgroundColor: accent.bg, color: accent.color }}
          >
            {label}
          </span>
          <span className="text-[12px] text-[var(--text-secondary)] truncate">
            {lever} · {cluster.member_count} SKUs
          </span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="font-display text-[21px] tnum" style={{ color: accent.color }}>
            {formatAED(cluster.lever_total)}
          </span>
          <span className="text-[var(--text-secondary)]">
            <Chevron open={open} />
          </span>
        </div>
      </button>

      {/* Collapsible table */}
      {open && cluster.top_members.length > 0 && (
        <div className="overflow-x-auto border-t border-black/5">
          <table className="w-full border-collapse">
            <thead>
              <tr style={{ background: "var(--surface)" }}>
                <th className={`${TH} text-left w-28`}>SKU</th>
                <th className={`${TH} text-left`}>Category</th>
                <th className={`${TH} text-right`}>Value at Stake</th>
                <th className={`${TH} text-center`}>{cover.header}</th>
                <th className={`${TH} text-left`}>Supplier</th>
                <th className={`${TH} text-center w-20`}>ABC·XYZ</th>
              </tr>
            </thead>
            <tbody>
              {cluster.top_members.map((m, i) => {
                const isSelected = m.facts.sku_code === selectedSku;
                return (
                  <tr
                    key={`${m.facts.sku_code}-${i}`}
                    onClick={() => onSkuClick(m.facts.sku_code)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSkuClick(m.facts.sku_code);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    aria-label={`Inspect SKU ${m.facts.sku_code}`}
                    aria-pressed={isSelected}
                    className={`cursor-pointer border-b border-black/[0.04] last:border-0 transition-colors duration-150 ${
                      isSelected ? "bg-[var(--gold)]/[0.07]" : "hover:bg-black/[0.02]"
                    }`}
                  >
                    <td className="px-4 py-2.5 relative">
                      {isSelected && <span className="absolute left-0 inset-y-0 w-[2px] bg-[var(--gold)]" />}
                      <span className="font-mono text-[12.5px] font-medium hover:underline" style={{ color: "var(--navy-700)" }}>
                        {m.facts.sku_code}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-[13px] text-[var(--text-primary)]/80">{m.facts.category_name ?? "—"}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-[12.5px] text-[var(--text-primary)] font-medium tnum">
                      {fmtFull(m.lever_contribution)}
                    </td>
                    <td className="px-4 py-2.5 text-center font-mono text-[12.5px] text-[var(--text-secondary)] tnum">
                      {cover.getValue(m)}
                    </td>
                    <td className="px-4 py-2.5 text-[13px] text-[var(--text-secondary)] max-w-32 truncate">
                      {m.facts.supplier_name ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="inline-block rounded-md bg-[var(--surface-2)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--text-secondary)]">
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
        <p className="px-5 py-4 text-[13px] text-[var(--text-secondary)] italic border-t border-black/5">
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
      <SectionHeading
        right={<span className="text-[11px] text-[var(--text-secondary)]">Click any row to inspect a SKU</span>}
      >
        Flagged Clusters
      </SectionHeading>
      <div className="space-y-3.5">
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
