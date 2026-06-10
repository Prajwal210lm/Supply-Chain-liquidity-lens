"use client";

import { Cluster, fmtFull } from "@/lib/api";
import { sectionHeader } from "@/components/SummaryCards";

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
      row.clusterCounts.set(
        cluster.cluster_id,
        (row.clusterCounts.get(cluster.cluster_id) ?? 0) + 1
      );
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
  slow_excess: { label: "Slow & Excess", bg: "#0596691a", text: "#059669", barColor: "#059669" },
  expiry:      { label: "Expiry Risk",   bg: "#D977061a", text: "#D97706", barColor: "#D97706" },
  stockout:    { label: "Stockout Risk", bg: "#DC26261a", text: "#DC2626", barColor: "#DC2626" },
};

export default function SupplierAnalysis({ clusters }: { clusters: Cluster[] }) {
  const rows = aggregateSuppliers(clusters);
  if (rows.length === 0) return null;

  const maxVal = Math.max(...rows.map((r) => r.totalValue), 1);

  return (
    <section className="bg-white rounded-xl shadow-sm p-6">
      <h2 className={sectionHeader}>Supplier Exposure</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Supplier
              </th>
              <th className="text-right px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Value at Stake (AED)
              </th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] w-24">
                Exposure
              </th>
              <th className="text-right px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] w-24">
                SKUs
              </th>
              <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                Primary Risk
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const badge = CLUSTER_BADGE[row.primaryCluster] ?? {
                label: row.primaryCluster,
                bg: "#6475801a",
                text: "#64748B",
                barColor: "#64748B",
              };
              const barWidthPct = ((row.totalValue / maxVal) * 100).toFixed(1);
              return (
                <tr
                  key={row.supplier}
                  className={`border-b border-gray-100 ${i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}
                >
                  <td className="px-4 py-3 font-medium text-[var(--text-primary)]">
                    {row.supplier}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-sm text-[var(--text-primary)] font-medium">
                    {fmtFull(row.totalValue)}
                  </td>
                  {/* Inline contribution bar */}
                  <td className="px-4 py-3">
                    <div className="w-16 h-1 rounded-full bg-gray-200 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${barWidthPct}%`, backgroundColor: badge.barColor }}
                      />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--text-secondary)] tabular-nums">
                    {row.skuCount}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-block text-xs px-2.5 py-0.5 rounded-full font-medium"
                      style={{ backgroundColor: badge.bg, color: badge.text }}
                    >
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
