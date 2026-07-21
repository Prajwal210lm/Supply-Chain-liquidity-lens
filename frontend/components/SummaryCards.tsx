"use client";

import { Cluster, ValueAtStake, fmtCompact } from "@/lib/api";
import { useInView } from "@/lib/useInView";
import { useCountUp } from "@/lib/useCountUp";

// ── Shared section heading ────────────────────────────────────────────────────

// Kept for backward compatibility (string className).
export const sectionHeader =
  "text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--navy-800)] border-b border-black/10 pb-2.5 mb-5";

export function SectionHeading({
  children,
  right,
}: {
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-3 pb-2.5 mb-5 border-b border-black/10">
      <h2 className="flex items-center gap-2.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--navy-800)]">
        <span className="w-3.5 h-px bg-[var(--gold)] flex-shrink-0" aria-hidden="true" />
        {children}
      </h2>
      {right}
    </div>
  );
}

// ── KPI card ──────────────────────────────────────────────────────────────────

type CardProps = {
  label: string;
  value: number;
  count: number;
  accentColor: string;
  isTotal?: boolean;
  denominator?: string;
};

function Card({ label, value, count, accentColor, isTotal, denominator }: CardProps) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const animated = useCountUp(value, inView);

  return (
    <div
      ref={ref}
      className={`group relative rounded-2xl p-5 overflow-hidden transition-[transform,box-shadow] duration-300 ease-out hover:-translate-y-1 ${
        isTotal
          ? "shadow-[var(--elev-3)] hover:shadow-[var(--elev-4)]"
          : "shadow-[var(--elev-2)] hover:shadow-[var(--elev-3)]"
      }`}
      style={
        isTotal
          ? { background: "linear-gradient(155deg, var(--navy-900), var(--navy-800))", border: "1px solid var(--gold-line)" }
          : { background: "var(--card)", border: "1px solid var(--hairline)" }
      }
    >
      {/* Top accent line */}
      <span
        className="absolute inset-x-0 top-0 h-[3px] transition-[background] duration-300"
        style={{
          background: isTotal
            ? "linear-gradient(90deg, var(--gold-deep), var(--gold-soft))"
            : `linear-gradient(90deg, ${accentColor}, ${accentColor}44)`,
        }}
      />

      <p
        className="text-[10px] font-semibold uppercase tracking-[0.14em] mb-3"
        style={{ color: isTotal ? "var(--gold-soft)" : "var(--text-secondary)" }}
      >
        {label}
      </p>

      <p
        className="font-display text-[28px] sm:text-[34px] lg:text-[42px] leading-none mb-1.5 tnum flex flex-wrap items-baseline gap-x-1.5"
        style={{ color: isTotal ? "var(--text-on-dark)" : accentColor }}
      >
        <span>{fmtCompact(animated)}</span>
        <span
          className="font-sans text-[12px] sm:text-[13px] lg:text-[14px] font-normal"
          style={{ color: isTotal ? "var(--text-on-dark-muted)" : "var(--text-secondary)" }}
        >
          AED
        </span>
      </p>

      <p
        className="text-[12px] tnum"
        style={{ color: isTotal ? "var(--text-on-dark-secondary)" : "var(--text-secondary)" }}
      >
        {count.toLocaleString()} SKUs
      </p>

      {denominator && (
        <p
          className="text-[11px] mt-1 tnum"
          style={{ color: isTotal ? "var(--text-on-dark-muted)" : "var(--text-secondary)" }}
        >
          {denominator}
        </p>
      )}
    </div>
  );
}

// AED on-hand inventory value for the synthetic 600-SKU portfolio. Not part of
// the API response (value_at_stake has no on-hand total), so it's a fixed
// reference figure matching the dataset's known on-hand value.
const ON_HAND_INVENTORY_AED = 106_000_000;

function pct(value: number, denominator: number): number {
  return denominator > 0 ? Math.round((value / denominator) * 100) : 0;
}

const ON_HAND_LABEL = "AED 106M on-hand";

// ── Main export ───────────────────────────────────────────────────────────────

export default function SummaryCards({
  vas,
  clusters,
}: {
  vas: ValueAtStake;
  clusters: Cluster[];
}) {
  const byId = Object.fromEntries(clusters.map((c) => [c.cluster_id, c]));
  const flaggedPct =
    vas.sku_count > 0 ? Math.round((vas.flagged_sku_count / vas.sku_count) * 100) : 0;

  return (
    <section>
      <SectionHeading
        right={
          <span className="text-[11px] text-[var(--text-secondary)] tnum">
            Portfolio: {vas.sku_count.toLocaleString()} SKUs · {ON_HAND_LABEL} ·{" "}
            {vas.flagged_sku_count.toLocaleString()} flagged ({flaggedPct}%)
          </span>
        }
      >
        Value at Stake
      </SectionHeading>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          label="Releasable Cash"
          value={vas.releasable_cash}
          count={byId["slow_excess"]?.member_count ?? 0}
          accentColor="var(--green-accent)"
          denominator={`${pct(vas.releasable_cash, vas.total)}% of total at stake`}
        />
        <Card
          label="Write-Off Exposure"
          value={vas.write_off_exposure}
          count={byId["expiry"]?.member_count ?? 0}
          accentColor="var(--amber-accent)"
          denominator={`${pct(vas.write_off_exposure, vas.total)}% of total at stake`}
        />
        <Card
          label="Stockout Risk"
          value={vas.stockout_margin_loss}
          count={byId["stockout"]?.member_count ?? 0}
          accentColor="var(--red-accent)"
          denominator={`${pct(vas.stockout_margin_loss, vas.total)}% of total at stake`}
        />
        <Card
          label="Total at Stake"
          value={vas.total}
          count={vas.flagged_sku_count}
          accentColor="var(--navy-900)"
          isTotal
          denominator={`= ${pct(vas.total, ON_HAND_INVENTORY_AED)}% of ${ON_HAND_LABEL} inventory`}
        />
      </div>

      <p className="mt-3 text-[11px] text-[var(--text-secondary)] leading-[1.6]">
        Totals are not strictly additive across the three dimensions: a SKU that is both
        overstocked and near-expiry counts toward releasable cash and write-off exposure,
        since each names a distinct action on the same units. The total is an upper bound.
      </p>
    </section>
  );
}
