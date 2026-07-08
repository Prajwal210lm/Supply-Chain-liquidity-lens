"use client";

import { ValueAtStake, fmtCompact } from "@/lib/api";
import { SectionHeading } from "@/components/SummaryCards";

const SEGMENTS = [
  { key: "releasable_cash", label: "Releasable Cash", color: "var(--green-accent)" },
  { key: "write_off_exposure", label: "Write-Off Exposure", color: "var(--amber-accent)" },
  { key: "stockout_margin_loss", label: "Stockout Risk", color: "var(--red-accent)" },
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
    <section
      className="rounded-2xl p-6"
      style={{ background: "var(--card)", boxShadow: "var(--elev-2)", border: "1px solid var(--hairline)" }}
    >
      <SectionHeading
        right={
          <span className="text-[11px] text-[var(--text-secondary)] tnum">
            Total {fmtCompact(vas.total)} AED
          </span>
        }
      >
        Value Breakdown
      </SectionHeading>

      {/* Stacked pill bar */}
      <div className="h-3.5 rounded-full overflow-hidden flex bg-[var(--surface-2)]">
        {data.map((d, i) => (
          <div
            key={d.name}
            className="animate-bar h-full first:rounded-l-full last:rounded-r-full"
            style={{
              width: `${d.widthPct}%`,
              backgroundColor: d.color,
              animationDelay: `${i * 120}ms`,
              boxShadow: "inset -1px 0 0 rgba(255,255,255,0.25)",
            }}
            title={`${d.name}: ${fmtCompact(d.value)} AED (${d.pct})`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-5">
        {data.map((d) => (
          <div
            key={d.name}
            className="flex items-center justify-between gap-3 rounded-xl px-3.5 py-2.5"
            style={{ background: "var(--surface)", border: "1px solid var(--hairline)" }}
          >
            <span className="flex items-center gap-2 min-w-0">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: d.color }} />
              <span className="text-[12.5px] text-[var(--text-secondary)] truncate">{d.name}</span>
            </span>
            <span className="text-right flex-shrink-0">
              <span className="font-display text-[17px] text-[var(--text-primary)] tnum">{fmtCompact(d.value)}</span>
              <span className="text-[11px] text-[var(--text-muted)] ml-1 tnum">{d.pct}</span>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
