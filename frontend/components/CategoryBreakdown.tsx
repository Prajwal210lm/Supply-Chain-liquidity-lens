"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { Cluster, fmtFull, fmtCompact } from "@/lib/api";
import { sectionHeader } from "@/components/SummaryCards";

const COLORS = [
  "#1B3A5C", // navy-700
  "#059669", // green-accent
  "#D97706", // amber-accent
  "#2563EB", // blue-accent
  "#7C3AED", // violet
  "#DB2777", // pink
  "#0891B2", // cyan
  "#65A30D", // lime
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
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="font-semibold text-[var(--text-primary)]">{payload[0].name}</p>
      <p className="text-[var(--text-secondary)]">{fmtFull(payload[0].value)} AED</p>
    </div>
  );
}

export default function CategoryBreakdown({ clusters }: { clusters: Cluster[] }) {
  const rows = aggregateCategories(clusters);
  if (rows.length === 0) return null;

  const chartData = rows.map((r) => ({ name: r.category, value: r.totalValue, color: r.color }));

  return (
    <section className="bg-white rounded-xl shadow-sm p-6">
      <h2 className={sectionHeader}>Category Breakdown</h2>
      <div className="flex flex-col sm:flex-row items-center gap-8">
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
                <th className="text-left pb-2.5 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Category
                </th>
                <th className="text-right pb-2.5 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
                  Value at Stake (AED)
                </th>
                <th className="text-right pb-2.5 text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)] w-20">
                  SKUs
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.category} className="border-b border-gray-100 hover:bg-gray-50/50 transition-colors">
                  <td className="py-2.5 pr-4">
                    <span className="flex items-center gap-2">
                      <span
                        className="inline-block w-2 h-2 flex-shrink-0 rounded-full"
                        style={{ backgroundColor: row.color }}
                      />
                      <span className="text-[var(--text-primary)]">{row.category}</span>
                    </span>
                  </td>
                  <td className="py-2.5 text-right font-mono tabular-nums text-sm font-medium text-[var(--text-primary)]">
                    {fmtFull(row.totalValue)}
                  </td>
                  <td className="py-2.5 text-right tabular-nums text-[var(--text-secondary)]">
                    {row.skuCount}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
