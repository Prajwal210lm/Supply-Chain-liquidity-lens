"use client";

import { Cluster, ValueAtStake, fmtCompact } from "@/lib/api";

type CardProps = {
  label: string;
  value: number;
  count: number;
  borderColor: string;
  textColor: string;
};

function Card({ label, value, count, borderColor, textColor }: CardProps) {
  return (
    <div
      className={`bg-white border border-gray-200 border-l-4 p-6 ${borderColor}`}
    >
      <p className="text-xs font-semibold tracking-widest uppercase text-gray-500 mb-2">
        {label}
      </p>
      <p className={`text-3xl font-bold ${textColor}`}>
        {fmtCompact(value)}
        <span className="text-lg font-normal text-gray-400 ml-1">AED</span>
      </p>
      <p className="text-sm text-gray-400 mt-1">{count.toLocaleString()} SKUs</p>
    </div>
  );
}

export default function SummaryCards({
  vas,
  clusters,
}: {
  vas: ValueAtStake;
  clusters: Cluster[];
}) {
  const byId = Object.fromEntries(clusters.map((c) => [c.cluster_id, c]));

  return (
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
        borderColor="border-l-gray-400"
        textColor="text-gray-800"
      />
    </div>
  );
}
