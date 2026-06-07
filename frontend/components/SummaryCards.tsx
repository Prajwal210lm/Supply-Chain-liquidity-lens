"use client";

import { Cluster, ValueAtStake, fmtCompact } from "@/lib/api";

// ── Section header shared style ───────────────────────────────────────────────

export const sectionHeader =
  "text-xs font-semibold uppercase tracking-widest text-gray-400 border-b border-gray-200 pb-2 mb-4";

// ── KPI card ──────────────────────────────────────────────────────────────────

type CardProps = {
  label: string;
  value: number;
  count: number;
  borderColor: string;
  textColor: string;
  isTotal?: boolean;
};

function Card({ label, value, count, borderColor, textColor, isTotal }: CardProps) {
  return (
    <div
      className={`border border-gray-200 border-l-4 p-6 ${borderColor} ${isTotal ? "bg-gray-50" : "bg-white"}`}
    >
      <p className="text-xs font-semibold tracking-widest uppercase text-gray-500 mb-2">
        {label}
      </p>
      <p className={`font-bold ${textColor} ${isTotal ? "text-4xl" : "text-3xl"}`}>
        {fmtCompact(value)}
        <span className="text-lg font-normal text-gray-400 ml-1">AED</span>
      </p>
      <p className="text-sm text-gray-400 mt-1">{count.toLocaleString()} SKUs</p>
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
  const flaggedPct = vas.sku_count > 0
    ? Math.round((vas.flagged_sku_count / vas.sku_count) * 100)
    : 0;

  return (
    <section>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          label="Releasable Cash"
          value={vas.releasable_cash}
          count={byId["slow_excess"]?.member_count ?? 0}
          borderColor="border-l-green-600"
          textColor="text-green-700"
        />
        <Card
          label="Write-Off Exposure"
          value={vas.write_off_exposure}
          count={byId["expiry"]?.member_count ?? 0}
          borderColor="border-l-amber-500"
          textColor="text-amber-700"
        />
        <Card
          label="Stockout Risk"
          value={vas.stockout_margin_loss}
          count={byId["stockout"]?.member_count ?? 0}
          borderColor="border-l-red-600"
          textColor="text-red-700"
        />
        <Card
          label="Total at Stake"
          value={vas.total}
          count={vas.flagged_sku_count}
          borderColor="border-l-gray-500"
          textColor="text-gray-900"
          isTotal
        />
      </div>
      <p className="text-xs text-gray-400 mt-3">
        Portfolio: {vas.sku_count.toLocaleString()} SKUs
        {" · "}AED 106M on-hand inventory
        {" · "}{vas.flagged_sku_count.toLocaleString()} flagged ({flaggedPct}%)
      </p>
    </section>
  );
}
