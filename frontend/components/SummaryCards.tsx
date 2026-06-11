"use client";

import { Cluster, ValueAtStake, fmtCompact } from "@/lib/api";

// ── Section header shared style ───────────────────────────────────────────────

export const sectionHeader =
  "text-[10px] font-semibold uppercase tracking-[0.15em] text-[#1B3A5C] border-b border-gray-200 pb-2 mb-4";

// ── KPI card ──────────────────────────────────────────────────────────────────

type CardProps = {
  label: string;
  value: number;
  count: number;
  accentColor: string;
  valueColor: string;
  isTotal?: boolean;
  animDelay?: number;
};

function Card({ label, value, count, accentColor, valueColor, isTotal, animDelay = 0 }: CardProps) {
  return (
    <div
      className={`relative bg-white rounded-xl shadow-sm overflow-hidden flex hover:shadow-md transition-shadow duration-200 ${isTotal ? "" : ""}`}
      style={
        isTotal
          ? { background: "rgba(15,26,46,0.04)" }
          : {}
      }
    >
      {/* Left accent bar */}
      <div
        className="w-1 flex-shrink-0 self-stretch"
        style={{ backgroundColor: accentColor }}
      />
      {/* Content */}
      <div className="flex-1 p-6">
        <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-gray-500 mb-2">
          {label}
        </p>
        <p
          className="font-display text-[42px] leading-none mb-1"
          style={{ color: valueColor }}
        >
          {fmtCompact(value)}
          <span className="text-[14px] font-normal ml-1.5 text-gray-400">
            AED
          </span>
        </p>
        <p className="text-[12px] text-gray-400">{count.toLocaleString()} SKUs</p>
      </div>
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
    vas.sku_count > 0
      ? Math.round((vas.flagged_sku_count / vas.sku_count) * 100)
      : 0;

  return (
    <section>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          label="Releasable Cash"
          value={vas.releasable_cash}
          count={byId["slow_excess"]?.member_count ?? 0}
          accentColor="var(--green-accent)"
          valueColor="var(--green-accent)"
          animDelay={0}
        />
        <Card
          label="Write-Off Exposure"
          value={vas.write_off_exposure}
          count={byId["expiry"]?.member_count ?? 0}
          accentColor="var(--amber-accent)"
          valueColor="var(--amber-accent)"
          animDelay={50}
        />
        <Card
          label="Stockout Risk"
          value={vas.stockout_margin_loss}
          count={byId["stockout"]?.member_count ?? 0}
          accentColor="var(--red-accent)"
          valueColor="var(--red-accent)"
          animDelay={100}
        />
        <Card
          label="Total at Stake"
          value={vas.total}
          count={vas.flagged_sku_count}
          accentColor="var(--navy-700)"
          valueColor="var(--navy-900)"
          isTotal
          animDelay={150}
        />
      </div>
      <p className="text-xs text-[var(--text-secondary)] mt-3 pt-3 border-t border-gray-200">
        Portfolio: {vas.sku_count.toLocaleString()} SKUs
        {" · "}AED 106M on-hand inventory
        {" · "}{vas.flagged_sku_count.toLocaleString()} flagged ({flaggedPct}%)
      </p>
    </section>
  );
}
