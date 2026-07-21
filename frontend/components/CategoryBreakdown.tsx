"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { Cluster, fmtFull } from "@/lib/api";
import { SectionHeading } from "@/components/SummaryCards";
import ScrollFadeX from "@/components/ScrollFadeX";
import { formatAED } from "@/lib/format";

// Sophisticated, considered palette — navy/gold/teal/risk, no purple slop.
// Every entry is a token reference, so re-theming the palette in globals.css
// re-skins this chart automatically.
const COLORS = [
  "var(--navy-700)",
  "var(--green-accent)",
  "var(--gold)",
  "var(--navy-600)",
  "var(--amber-accent)",
  "var(--teal-accent)",
  "var(--text-secondary)",
  "var(--bronze-accent)",
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

type TooltipProps = { active?: boolean; payload?: Array<{ name: string; value: number }> };

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[var(--card)] border border-black/10 rounded-lg px-3 py-2 text-[12px]" style={{ boxShadow: "var(--elev-3)" }}>
      <p className="font-semibold text-[var(--text-primary)]">{payload[0].name}</p>
      <p className="text-[var(--text-secondary)] tnum">{fmtFull(payload[0].value)} AED</p>
    </div>
  );
}

const TH = "pb-2.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)]";

export default function CategoryBreakdown({ clusters }: { clusters: Cluster[] }) {
  const rows = aggregateCategories(clusters);
  if (rows.length === 0) return null;

  const chartData = rows.map((r) => ({ name: r.category, value: r.totalValue, color: r.color }));

  return (
    <section
      className="rounded-2xl p-6"
      style={{ background: "var(--card)", boxShadow: "var(--elev-2)", border: "1px solid var(--hairline)" }}
    >
      <SectionHeading>Category Breakdown</SectionHeading>
      <div className="flex flex-col sm:flex-row items-center gap-8">
        {/* Donut chart */}
        <div className="flex-shrink-0" style={{ width: 200, height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={chartData} cx="50%" cy="50%" innerRadius={62} outerRadius={92} paddingAngle={2} dataKey="value" strokeWidth={0}>
                {chartData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend table */}
        <ScrollFadeX wrapperClassName="relative flex-1 w-full" className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-black/8">
                <th className={`${TH} text-left`}>Category</th>
                <th className={`${TH} text-right`}>Value at Stake</th>
                <th className={`${TH} text-right w-20`}>SKUs</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.category} className="border-b border-black/[0.04] last:border-0 transition-colors duration-150 hover:bg-black/[0.02]">
                  <td className="py-2.5 pr-4">
                    <span className="flex items-center gap-2.5">
                      <span className="inline-block w-2.5 h-2.5 flex-shrink-0 rounded-full" style={{ backgroundColor: row.color }} />
                      <span className="text-[13px] text-[var(--text-primary)]/85">{row.category}</span>
                    </span>
                  </td>
                  <td className="py-2.5 text-right font-mono text-[12.5px] font-medium text-[var(--text-primary)] tnum">{formatAED(row.totalValue)}</td>
                  <td className="py-2.5 text-right text-[13px] text-[var(--text-secondary)] tnum">{row.skuCount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollFadeX>
      </div>
    </section>
  );
}
