"use client";

import { Cluster, ValueAtStake, fmtCompact } from "@/lib/api";

// ── Shared section heading ────────────────────────────────────────────────────

// Kept for backward compatibility (string className).
export const sectionHeader =
  "text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--navy-800)] border-b border-black/10 pb-2.5 mb-5";

export function SectionHeading({
  children,
  right,
}: {
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-3 pb-2.5 mb-5 border-b border-black/10">
      <h2 className="flex items-center gap-2.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--navy-800)]">
        <span className="w-3.5 h-px bg-[var(--gold)] flex-shrink-0" aria-hidden="true" />
        {children}
      </h2>
      {right}
    </div>
  );
}

// ── KPI card ──────────────────────────────────────────────────────────────────

type CardProps = {
  label: string;
  value: number;
  count: number;
  accentColor: string;
  isTotal?: boolean;
};

function Card({ label, value, count, accentColor, isTotal }: CardProps) {
  return (
    <div
      className="group relative rounded-2xl p-5 overflow-hidden transition-[transform,box-shadow] duration-300 ease-out hover:-translate-y-1"
      style={
        isTotal
          ? {
              background: "linear-gradient(155deg, var(--navy-900), var(--navy-800))",
              boxShadow: "var(--elev-3)",
              border: "1px solid var(--gold-line)",
            }
          : {
              background: "var(--card)",
              boxShadow: "var(--elev-2)",
              border: "1px solid rgba(15,26,46,0.05)",
            }
      }
    >
      {/* Top accent line */}
      <span
        className="absolute inset-x-0 top-0 h-[3px]"
        style={{
          background: isTotal
            ? "linear-gradient(90deg, var(--gold), var(--gold-soft))"
            : `linear-gradient(90deg, ${accentColor}, ${accentColor}44)`,
        }}
      />

      <p
        className="text-[10px] font-semibold uppercase tracking-[0.14em] mb-3"
        style={{ color: isTotal ? "var(--gold-soft)" : "var(--text-secondary)" }}
      >
        {label}
      </p>

      <p
        className="font-display text-[42px] leading-none mb-1.5 tnum"
        style={{ color: isTotal ? "#FFFFFF" : accentColor }}
      >
        {fmtCompact(value)}
        <span
          className="font-sans text-[14px] font-normal ml-1.5"
          style={{ color: isTotal ? "rgba(255,255,255,0.5)" : "var(--text-secondary)" }}
        >
          AED
        </span>
      </p>

      <p
        className="text-[12px] tnum"
        style={{ color: isTotal ? "rgba(255,255,255,0.55)" : "var(--text-secondary)" }}
      >
        {count.toLocaleString()} SKUs
      </p>
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function SummaryCards({
  vas,
  clusters,
}: {
  vas: ValueAtStake;
  clusters: Cluster[];
}) {
  const byId = Object.fromEntries(clusters.map((c) => [c.cluster_id, c]));
  const flaggedPct =
    vas.sku_count > 0 ? Math.round((vas.flagged_sku_count / vas.sku_count) * 100) : 0;

  return (
    <section>
      <SectionHeading
        right={
          <span className="text-[11px] text-[var(--text-secondary)] tnum">
            Portfolio: {vas.sku_count.toLocaleString()} SKUs · AED 106M on-hand ·{" "}
            {vas.flagged_sku_count.toLocaleString()} flagged ({flaggedPct}%)
          </span>
        }
      >
        Value at Stake
      </SectionHeading>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          label="Releasable Cash"
          value={vas.releasable_cash}
          count={byId["slow_excess"]?.member_count ?? 0}
          accentColor="var(--green-accent)"
        />
        <Card
          label="Write-Off Exposure"
          value={vas.write_off_exposure}
          count={byId["expiry"]?.member_count ?? 0}
          accentColor="var(--amber-accent)"
        />
        <Card
          label="Stockout Risk"
          value={vas.stockout_margin_loss}
          count={byId["stockout"]?.member_count ?? 0}
          accentColor="var(--red-accent)"
        />
        <Card
          label="Total at Stake"
          value={vas.total}
          count={vas.flagged_sku_count}
          accentColor="var(--navy-900)"
          isTotal
        />
      </div>
    </section>
  );
}
