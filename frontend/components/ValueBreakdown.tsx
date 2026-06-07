"use client";

import {
  BarChart,
  Bar,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { ValueAtStake, fmtCompact } from "@/lib/api";

const SEGMENTS = [
  { key: "releasable_cash",     label: "Releasable Cash",   color: "#16a34a" },
  { key: "write_off_exposure",  label: "Write-Off Exposure", color: "#d97706" },
  { key: "stockout_margin_loss",label: "Stockout Risk",      color: "#dc2626" },
] as const;

type TooltipProps = {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: { pct: string } }>;
};

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const { name, value, payload: data } = payload[0];
  return (
    <div className="bg-white border border-gray-200 px-3 py-2 text-xs shadow">
      <p className="font-semibold text-gray-800">{name}</p>
      <p className="text-gray-600">
        {fmtCompact(value)} AED · {data.pct}
      </p>
    </div>
  );
}

export default function ValueBreakdown({ vas }: { vas: ValueAtStake }) {
  const total = vas.total || 1;

  const data = SEGMENTS.map((s) => ({
    name: s.label,
    value: vas[s.key],
    pct: `${((vas[s.key] / total) * 100).toFixed(1)}%`,
    color: s.color,
  }));

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400">
          Value Breakdown
        </h2>
        {/* Legend */}
        <div className="flex items-center gap-5">
          {data.map((d) => (
            <span key={d.name} className="flex items-center gap-1.5 text-xs text-gray-500">
              <span
                className="inline-block w-2.5 h-2.5 flex-shrink-0"
                style={{ backgroundColor: d.color }}
              />
              {d.name} · <strong className="text-gray-700">{fmtCompact(d.value)}</strong>
              <span className="text-gray-400">({d.pct})</span>
            </span>
          ))}
        </div>
      </div>

      <div style={{ height: 80 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={[{ name: "total", ...Object.fromEntries(data.map((d) => [d.name, d.value])) }]}
            margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
            barSize={36}
          >
            <XAxis type="number" hide domain={[0, total]} />
            {SEGMENTS.map((s, i) => (
              <Bar
                key={s.key}
                dataKey={s.label}
                stackId="a"
                fill={s.color}
                radius={i === 0 ? [2, 0, 0, 2] : i === SEGMENTS.length - 1 ? [0, 2, 2, 0] : [0, 0, 0, 0]}
              />
            ))}
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ fill: "rgba(0,0,0,0.04)" }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
