"use client";

import { Cluster } from "@/lib/api";
import { SectionHeading } from "@/components/SummaryCards";
import { formatAED } from "@/lib/format";

type SupplierRow = {
  supplier: string;
  totalValue: number;
  skuCount: number;
  primaryCluster: string;
};

function aggregateSuppliers(clusters: Cluster[]): SupplierRow[] {
  const map = new Map<
    string,
    { totalValue: number; skuCodes: Set<string>; clusterCounts: Map<string, number> }
  >();

  for (const cluster of clusters) {
    for (const member of cluster.top_members) {
      const name = member.facts.supplier_name ?? "Unknown";
      if (!map.has(name)) {
        map.set(name, { totalValue: 0, skuCodes: new Set(), clusterCounts: new Map() });
      }
      const row = map.get(name)!;
      row.totalValue += member.lever_contribution;
      row.skuCodes.add(member.facts.sku_code);
      row.clusterCounts.set(cluster.cluster_id, (row.clusterCounts.get(cluster.cluster_id) ?? 0) + 1);
    }
  }

  return Array.from(map.entries())
    .map(([supplier, { totalValue, skuCodes, clusterCounts }]) => {
      const primaryCluster = [...clusterCounts.entries()].sort((a, b) => b[1] - a[1])[0][0];
      return { supplier, totalValue, skuCount: skuCodes.size, primaryCluster };
    })
    .sort((a, b) => b.totalValue - a.totalValue)
    .slice(0, 8);
}

const CLUSTER_BADGE: Record<string, { label: string; bg: string; text: string; barColor: string }> = {
  slow_excess: { label: "Slow & Excess", bg: "rgba(14,159,110,0.12)", text: "#0E9F6E", barColor: "#0E9F6E" },
  expiry: { label: "Expiry Risk", bg: "rgba(217,132,43,0.12)", text: "#D9842B", barColor: "#D9842B" },
  stockout: { label: "Stockout Risk", bg: "rgba(214,69,61,0.12)", text: "#D6453D", barColor: "#D6453D" },
};

const TH = "px-4 py-3 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-secondary)]/80";

export default function SupplierAnalysis({ clusters }: { clusters: Cluster[] }) {
  const rows = aggregateSuppliers(clusters);
  if (rows.length === 0) return null;

  const maxVal = Math.max(...rows.map((r) => r.totalValue), 1);

  return (
    <section
      className="rounded-2xl p-6"
      style={{ background: "var(--card)", boxShadow: "var(--elev-2)", border: "1px solid rgba(15,26,46,0.05)" }}
    >
      <SectionHeading>Supplier Exposure</SectionHeading>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-black/8">
              <th className={`${TH} text-left`}>Supplier</th>
              <th className={`${TH} text-right`}>Value at Stake</th>
              <th className={`${TH} text-left w-32`}>Exposure</th>
              <th className={`${TH} text-right w-20`}>SKUs</th>
              <th className={`${TH} text-left`}>Primary Risk</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const badge = CLUSTER_BADGE[row.primaryCluster] ?? {
                label: row.primaryCluster, bg: "rgba(81,97,122,0.12)", text: "#51617A", barColor: "#51617A",
              };
              const barWidthPct = ((row.totalValue / maxVal) * 100).toFixed(1);
              return (
                <tr key={row.supplier} className="border-b border-black/[0.04] last:border-0 transition-colors duration-150 hover:bg-black/[0.02]">
                  <td className="px-4 py-3 text-[13.5px] font-medium text-[var(--text-primary)]">{row.supplier}</td>
                  <td className="px-4 py-3 text-right font-mono text-[12.5px] text-[var(--text-primary)] font-medium tnum">
                    {formatAED(row.totalValue)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="w-24 h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden">
                      <div className="h-full rounded-full animate-bar" style={{ width: `${barWidthPct}%`, backgroundColor: badge.barColor }} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-[13px] text-[var(--text-secondary)] tnum">{row.skuCount}</td>
                  <td className="px-4 py-3">
                    <span className="inline-block text-[11.5px] px-2.5 py-0.5 rounded-full font-medium" style={{ backgroundColor: badge.bg, color: badge.text }}>
                      {badge.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
