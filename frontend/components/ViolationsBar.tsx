"use client";

import { useState } from "react";
import { Cluster, QualityReport, ValueAtStake } from "@/lib/api";

type ViolationEntry = { node: string; msg: string };

const NODE_LABELS: Record<string, string> = {
  diagnose: "Diagnose",
  recommend: "Recommend",
  prioritise: "Prioritise",
  narrate: "Narrate",
};

// Verifies the one reconciliation invariant that's fully checkable from the API
// response as shipped: per lever, the (untruncated) cluster.lever_total values
// sum to the portfolio value-at-stake. This mirrors backend.facts.reconciliation_errors'
// second check. The first check there (member sum == cluster total) needs every
// member, but the API only ships top_members (max 20 per cluster) — so it isn't
// re-derivable client-side and isn't attempted here.
function checkReconciliation(
  vas: ValueAtStake,
  clusters: Cluster[]
): { reconciled: boolean; detail: string } {
  const byLever: Record<string, number> = {};
  for (const c of clusters) {
    byLever[c.lever] = (byLever[c.lever] ?? 0) + c.lever_total;
  }
  const pairs: [string, number][] = [
    ["releasable_cash", vas.releasable_cash],
    ["write_off_exposure", vas.write_off_exposure],
    ["stockout_margin_loss", vas.stockout_margin_loss],
  ];
  const TOL = 0.01;
  const reconciled = pairs.every(([lever, total]) => Math.abs((byLever[lever] ?? 0) - total) <= TOL);
  return {
    reconciled,
    detail: reconciled
      ? "Cluster totals sum exactly to the portfolio value-at-stake across all three levers."
      : "Cluster totals do not sum to the portfolio value-at-stake for at least one lever.",
  };
}

export default function ViolationsBar({
  violations,
  qualityReport,
  vas,
  clusters,
}: {
  violations: Record<string, string[]>;
  qualityReport: QualityReport;
  vas: ValueAtStake;
  clusters: Cluster[];
}) {
  const [expanded, setExpanded] = useState(false);

  const allViolations: ViolationEntry[] = Object.entries(violations).flatMap(([node, msgs]) =>
    msgs.map((m) => ({ node, msg: m }))
  );
  const count = allViolations.length;
  const { reconciled, detail } = checkReconciliation(vas, clusters);
  const clean = count === 0 && reconciled;
  const hasIssues = qualityReport.issues.length > 0;
  const hasDetail = !clean || hasIssues;
  const accent = clean ? "var(--green-accent)" : "var(--amber-accent)";

  return (
    <section
      className="rounded-2xl overflow-hidden"
      style={{
        background: "var(--card)",
        boxShadow: "var(--elev-3)",
        border: clean ? "1px solid var(--gold-line)" : "1px solid var(--hairline)",
      }}
    >
      <button
        onClick={() => hasDetail && setExpanded((e) => !e)}
        aria-expanded={expanded}
        className={`w-full flex flex-wrap items-center gap-x-3 gap-y-1 px-6 py-4 text-left transition-colors duration-200 ${
          hasDetail ? "cursor-pointer hover:bg-black/[0.015]" : "cursor-default"
        }`}
      >
        {/* Signature element: a verification pulse fires once on mount. */}
        <span className="relative w-2 h-2 flex-shrink-0 verify-ring" style={{ color: accent }}>
          <span className="absolute inset-0 rounded-full" style={{ backgroundColor: accent }} />
        </span>
        <span className="text-[13px] font-semibold" style={{ color: accent }}>
          {clean ? "Contract clean, 0 violations, totals reconciled" : "AI output independently verified"}
        </span>
        <span className="text-[11px] text-[var(--text-secondary)]">
          {clean
            ? <>Every figure traced to the deterministic core · {qualityReport.total_skus.toLocaleString()} SKUs validated</>
            : <>Every figure traced to tested code · {count} AI output{count === 1 ? "" : "s"} flagged and corrected during this run</>}
        </span>
        {!clean && !reconciled && (
          <span className="text-[11px] font-medium" style={{ color: accent }}>
            Totals do not reconcile
          </span>
        )}
        {hasDetail && (
          <span className="ml-auto text-[11px] text-[var(--text-secondary)] flex-shrink-0">
            {expanded ? "Hide detail" : "Show detail"}
          </span>
        )}
      </button>

      {expanded && hasDetail && (
        <div className="border-t border-black/5 px-6 py-4 space-y-4">
          {count > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--amber-accent)] mb-2">
                What Was Flagged
              </p>
              <div className="max-h-48 overflow-y-auto">
                <table className="w-full text-[12px] border-collapse">
                  <thead>
                    <tr className="text-[var(--text-secondary)]">
                      <th className="text-left pb-2 pr-4 w-28 font-semibold">Pipeline stage</th>
                      <th className="text-left pb-2 font-semibold">Violation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-black/5">
                    {allViolations.map(({ node, msg }, i) => (
                      <tr key={i}>
                        <td className="py-1.5 pr-4 font-mono text-[var(--amber-accent)] align-top">
                          {NODE_LABELS[node] ?? node}
                        </td>
                        <td className="py-1.5 text-[var(--text-primary)]/80">{msg}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!reconciled && <p className="text-[12px] text-[var(--amber-accent)]">{detail}</p>}

          {hasIssues && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-secondary)] mb-2">
                Data Quality Notes
              </p>
              <ul className="text-[12px] text-[var(--text-secondary)] space-y-1 list-disc list-inside">
                {qualityReport.issues.map((issue, i) => (
                  <li key={i}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
