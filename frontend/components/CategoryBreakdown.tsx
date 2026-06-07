"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { Cluster, fmtFull, fmtCompact } from "@/lib/api";
import { sectionHeader } from "@/components/SummaryCards";

// Muted, professional palette — desaturated slate/teal/stone tones
const COLORS = [
  "#64748b", // slate-500
  "#6b7280", // gray-500
  "#78716c", // stone-500
  "#4b6a88", // muted blue-slate
  "#5c7a6e", // muted teal
  "#7c6b7a", // muted mauve
  "#8a7a5a", // muted khaki
  "#6a7a8a", // muted steel
];

type CategoryRow = {
  category: string;
  totalValue: number;
  skuCount: number;
  color: string;
};

function aggregateCategories(clusters: Cluster[]): CategoryRow[] {
  const map = new Map<string, { totalValue: number; skuCodes: Set<string> }>();

  for (const cluster of clusters) {
    for (const member of cluster.top_members) {
      const cat = member.facts.category_name ?? "Uncategorised";
      if (!map.has(cat)) map.set(cat, { totalValue: 0, skuCodes: new Set() });
      const row = map.get(cat)!;
      row.totalValue += member.lever_contribution;
      row.skuCodes.add(member.facts.sku_code);
    }
  }

  return Array.from(map.entries())
    .map(([category, { totalValue, skuCodes }], i) => ({
      category,
      totalValue,
      skuCount: skuCodes.size,
      color: COLORS[i % COLORS.length],
    }))
    .sort((a, b) => b.totalValue - a.totalValue);
}

type TooltipProps = {
  active?: boolean;
  payload?: Array<{ name: string; value: number }>;
};

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 px-3 py-2 text-xs shadow">
      <p className="font-semibold text-gray-800">{payload[0].name}</p>
      <p className="text-gray-600">{fmtFull(payload[0].value)} AED</p>
    </div>
  );
}

export default function CategoryBreakdown({ clusters }: { clusters: Cluster[] }) {
  const rows = aggregateCategories(clusters);
  if (rows.length === 0) return null;

  const chartData = rows.map((r) => ({ name: r.category, value: r.totalValue, color: r.color }));

  return (
    <section>
      <h2 className={sectionHeader}>Category Breakdown</h2>
      <div className="border border-gray-200 bg-white flex items-center gap-8 px-6 py-4">
        {/* Donut chart */}
        <div className="flex-shrink-0" style={{ width: 200, height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
                strokeWidth={0}
              >
                {chartData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend table */}
        <div className="flex-1 overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left pb-2 font-medium text-gray-500 text-xs uppercase tracking-wide">
                  Category
                </th>
                <th className="text-right pb-2 font-medium text-gray-500 text-xs uppercase tracking-wide">
                  Value at Stake (AED)
                </th>
                <th className="text-right pb-2 font-medium text-gray-500 text-xs uppercase tracking-wide w-24">
                  SKUs
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={row.category} className={`border-b border-gray-100 ${i % 2 === 0 ? "" : "bg-gray-50"}`}>
                  <td className="py-2 pr-4">
                    <span className="flex items-center gap-2">
                      <span
                        className="inline-block w-2.5 h-2.5 flex-shrink-0"
                        style={{ backgroundColor: row.color }}
                      />
                      <span className="text-gray-700">{row.category}</span>
                    </span>
                  </td>
                  <td className="py-2 text-right font-medium text-gray-900">
                    {fmtFull(row.totalValue)}
                  </td>
                  <td className="py-2 text-right text-gray-600">{row.skuCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
