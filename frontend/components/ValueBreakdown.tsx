"use client";

import { ValueAtStake, fmtCompact } from "@/lib/api";
import { sectionHeader } from "@/components/SummaryCards";

const SEGMENTS = [
  { key: "releasable_cash",      label: "Releasable Cash",    color: "#059669" },
  { key: "write_off_exposure",   label: "Write-Off Exposure", color: "#D97706" },
  { key: "stockout_margin_loss", label: "Stockout Risk",      color: "#DC2626" },
] as const;

export default function ValueBreakdown({ vas }: { vas: ValueAtStake }) {
  const total = vas.total || 1;

  const data = SEGMENTS.map((s) => ({
    name: s.label,
    value: vas[s.key],
    pct: `${((vas[s.key] / total) * 100).toFixed(1)}%`,
    color: s.color,
    widthPct: ((vas[s.key] / total) * 100).toFixed(2),
  }));

  return (
    <section className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 pb-3 mb-4">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-[#1B3A5C]">
          Value Breakdown
        </h2>
        <div className="flex flex-wrap items-center gap-5">
          {data.map((d) => (
            <span key={d.name} className="flex items-center gap-1.5 text-xs text-[var(--text-secondary)]">
              <span
                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: d.color }}
              />
              {d.name}
              {" · "}
              <strong className="text-[var(--text-primary)]">{fmtCompact(d.value)}</strong>
              <span className="opacity-60">({d.pct})</span>
            </span>
          ))}
        </div>
      </div>

      {/* 12px pill bar */}
      <div className="h-3 rounded-full overflow-hidden flex">
        {data.map((d) => (
          <div
            key={d.name}
            style={{ width: `${d.widthPct}%`, backgroundColor: d.color }}
            title={`${d.name}: ${fmtCompact(d.value)} AED (${d.pct})`}
          />
        ))}
      </div>
    </section>
  );
}
