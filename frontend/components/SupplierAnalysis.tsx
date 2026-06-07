"use client";

import { Cluster, CLUSTER_LABELS, fmtFull } from "@/lib/api";

type SupplierRow = {
  supplier: string;
  totalValue: number;
  skuCount: number;
  primaryCluster: string;
};

function aggregateSuppliers(clusters: Cluster[]): SupplierRow[] {
  // supplier → { totalValue, skuCodes, clusterCounts }
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

const CLUSTER_BADGE: Record<string, { label: string; classes: string }> = {
  slow_excess: { label: "Slow & Excess",   classes: "bg-green-50 text-green-700 border-green-200" },
  expiry:      { label: "Expiry Risk",      classes: "bg-amber-50 text-amber-700 border-amber-200" },
  stockout:    { label: "Stockout Risk",    classes: "bg-red-50 text-red-700 border-red-200" },
};

export default function SupplierAnalysis({ clusters }: { clusters: Cluster[] }) {
  const rows = aggregateSuppliers(clusters);
  if (rows.length === 0) return null;

  return (
    <section>
      <h2 className="text-base font-semibold text-gray-500 uppercase tracking-widest mb-4">
        Supplier Exposure
      </h2>
      <div className="border border-gray-200">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide">
                Supplier
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide">
                Value at Stake (AED)
              </th>
              <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide w-28">
                SKUs Affected
              </th>
              <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase tracking-wide">
                Primary Risk
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const badge = CLUSTER_BADGE[row.primaryCluster] ?? {
                label: row.primaryCluster,
                classes: "bg-gray-50 text-gray-600 border-gray-200",
              };
              return (
                <tr
                  key={row.supplier}
                  className={`border-b border-gray-100 ${i % 2 === 0 ? "bg-white" : "bg-gray-50"}`}
                >
                  <td className="px-4 py-3 font-medium text-gray-800">{row.supplier}</td>
                  <td className="px-4 py-3 text-right font-medium text-gray-900">
                    {fmtFull(row.totalValue)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">{row.skuCount}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block text-xs px-2 py-0.5 border ${badge.classes}`}
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
