"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";
import { sectionHeader } from "@/components/SummaryCards";

// Reformat large currency values ("18,819,464.91 AED") into rounded forms
// (18.8M AED / 281K AED / 24.6K AED) directly in the markdown/headline prose.
function reformatCurrency(text: string): string {
  return text.replace(/([\d,]+(?:\.\d+)?)\s*AED/g, (match, numStr: string) => {
    const value = parseFloat(numStr.replace(/,/g, ""));
    if (Number.isNaN(value)) return match;
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M AED`;
    if (value >= 100_000) return `${Math.round(value / 1_000)}K AED`;
    if (value >= 10_000) return `${(value / 1_000).toFixed(1)}K AED`;
    return match; // below 10,000: leave as-is
  });
}

export default function BoardBrief({
  headline,
  bodyMarkdown,
}: {
  headline: string;
  bodyMarkdown: string;
}) {
  const formattedHeadline = reformatCurrency(headline);
  const formattedBody = reformatCurrency(bodyMarkdown);
  return (
    <section>
      <h2 className={sectionHeader}>Board Brief</h2>
      <div
        className="bg-white rounded-xl shadow-md border border-gray-100 border-l-4 px-8 py-8"
        style={{ borderLeftColor: "var(--navy-700)" }}
      >
        <h1 className="font-display text-[28px] font-semibold text-gray-900 mb-6 leading-[1.4]">
          {formattedHeadline}
        </h1>
        <div>
          <Markdown
            remarkPlugins={[remarkGfm]}
            components={{
              table: ({ children }: { children?: ReactNode }) => (
                <div className="overflow-x-auto my-4">
                  <table className="w-full text-sm border-collapse border border-gray-200">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }: { children?: ReactNode }) => (
                <thead style={{ background: "rgba(15,26,46,0.04)" }}>{children}</thead>
              ),
              tbody: ({ children }: { children?: ReactNode }) => (
                <tbody className="divide-y divide-gray-100">{children}</tbody>
              ),
              tr: ({ children }: { children?: ReactNode }) => (
                <tr className="border-b border-gray-100">{children}</tr>
              ),
              th: ({ children }: { children?: ReactNode }) => (
                <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.1em] text-gray-400 border border-gray-200">
                  {children}
                </th>
              ),
              td: ({ children }: { children?: ReactNode }) => (
                <td className="px-4 py-2.5 text-sm text-[var(--text-primary)] border border-gray-200 tabular-nums">
                  {children}
                </td>
              ),
              h2: ({ children }: { children?: ReactNode }) => (
                <h2
                  className="text-[10px] font-semibold uppercase tracking-[0.12em] border-b border-gray-200 pb-1 mt-7 mb-2"
                  style={{ color: "var(--navy-600)" }}
                >
                  {children}
                </h2>
              ),
              h3: ({ children }: { children?: ReactNode }) => (
                <h3
                  className="text-sm font-semibold mt-4 mb-1"
                  style={{ color: "var(--navy-800)" }}
                >
                  {children}
                </h3>
              ),
              p: ({ children }: { children?: ReactNode }) => (
                <p className="text-[14px] text-gray-700 leading-[1.8] mb-3">
                  {children}
                </p>
              ),
              ul: ({ children }: { children?: ReactNode }) => (
                <ul className="list-disc list-inside text-sm text-[var(--text-primary)] mb-3 space-y-1">
                  {children}
                </ul>
              ),
              ol: ({ children }: { children?: ReactNode }) => (
                <ol className="list-decimal list-inside text-sm text-[var(--text-primary)] mb-3 space-y-1">
                  {children}
                </ol>
              ),
              li: ({ children }: { children?: ReactNode }) => (
                <li className="leading-relaxed">{children}</li>
              ),
              strong: ({ children }: { children?: ReactNode }) => (
                <strong className="font-display font-semibold tabular-nums text-gray-900">
                  {children}
                </strong>
              ),
              em: ({ children }: { children?: ReactNode }) => (
                <em className="italic text-[var(--text-secondary)]">{children}</em>
              ),
              blockquote: ({ children }: { children?: ReactNode }) => (
                <blockquote
                  className="border-l-4 pl-4 italic my-3 text-sm text-[var(--text-secondary)]"
                  style={{ borderLeftColor: "var(--navy-600)" }}
                >
                  {children}
                </blockquote>
              ),
              hr: () => <hr className="border-gray-200 my-6" />,
            }}
          >
            {formattedBody}
          </Markdown>
        </div>
      </div>
    </section>
  );
}
