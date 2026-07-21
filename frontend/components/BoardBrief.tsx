"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";
import { SectionHeading } from "@/components/SummaryCards";
import ScrollFadeX from "@/components/ScrollFadeX";

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
      <SectionHeading>Board Brief</SectionHeading>

      <article
        className="relative rounded-2xl overflow-hidden"
        style={{ background: "var(--card)", boxShadow: "var(--elev-3)", border: "1px solid var(--hairline)" }}
      >
        {/* Gold spine */}
        <span className="absolute left-0 inset-y-0 w-[3px]" style={{ background: "linear-gradient(180deg, var(--gold), var(--gold-soft))" }} />

        <div className="px-7 sm:px-10 py-8">
          {/* Letterhead */}
          <div className="flex items-center justify-between gap-4 pb-4 mb-6 border-b" style={{ borderColor: "var(--gold-line)" }}>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--navy-800)]">
              Memorandum · Working Capital
            </p>
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--gold)] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--gold)]" aria-hidden="true" />
              Confidential
            </span>
          </div>

          {/* Headline */}
          <h1 className="font-display text-[27px] sm:text-[30px] font-semibold text-[var(--text-primary)] mb-7 leading-[1.32] tnum">
            {formattedHeadline}
          </h1>

          {/* Body */}
          <div className="board-prose max-w-[68ch]">
            <Markdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({ children }: { children?: ReactNode }) => (
                  <ScrollFadeX className="overflow-x-auto my-5 rounded-xl border border-black/8" fadeClassName="rounded-r-xl">
                    <table className="w-full text-[13.5px] border-collapse">{children}</table>
                  </ScrollFadeX>
                ),
                thead: ({ children }: { children?: ReactNode }) => (
                  <thead style={{ background: "var(--surface)" }}>{children}</thead>
                ),
                tbody: ({ children }: { children?: ReactNode }) => (
                  <tbody className="divide-y divide-black/5">{children}</tbody>
                ),
                tr: ({ children }: { children?: ReactNode }) => <tr>{children}</tr>,
                th: ({ children }: { children?: ReactNode }) => (
                  <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--text-secondary)] border-b border-black/8">
                    {children}
                  </th>
                ),
                td: ({ children }: { children?: ReactNode }) => (
                  <td className="px-4 py-2.5 text-[13.5px] text-[var(--text-primary)] tnum">{children}</td>
                ),
                h2: ({ children }: { children?: ReactNode }) => (
                  <h2 className="flex items-center gap-2.5 text-[10.5px] font-semibold uppercase tracking-[0.16em] text-[var(--navy-700)] mt-8 mb-3">
                    <span className="w-3 h-px bg-[var(--gold)] flex-shrink-0" aria-hidden="true" />
                    {children}
                  </h2>
                ),
                h3: ({ children }: { children?: ReactNode }) => (
                  <h3 className="font-display text-[18px] font-semibold text-[var(--navy-800)] mt-5 mb-2">{children}</h3>
                ),
                p: ({ children }: { children?: ReactNode }) => (
                  <p className="text-[14.5px] text-[var(--text-primary)]/85 leading-[1.85] mb-4">{children}</p>
                ),
                ul: ({ children }: { children?: ReactNode }) => (
                  <ul className="list-disc list-outside ml-5 text-[14.5px] text-[var(--text-primary)]/85 mb-4 space-y-1.5">{children}</ul>
                ),
                ol: ({ children }: { children?: ReactNode }) => (
                  <ol className="list-decimal list-outside ml-5 text-[14.5px] text-[var(--text-primary)]/85 mb-4 space-y-1.5">{children}</ol>
                ),
                li: ({ children }: { children?: ReactNode }) => <li className="leading-[1.7] pl-1">{children}</li>,
                strong: ({ children }: { children?: ReactNode }) => (
                  <strong className="font-display font-semibold text-[var(--text-primary)] tnum">{children}</strong>
                ),
                em: ({ children }: { children?: ReactNode }) => (
                  <em className="italic text-[var(--text-secondary)]">{children}</em>
                ),
                blockquote: ({ children }: { children?: ReactNode }) => (
                  <blockquote className="border-l-2 pl-4 italic my-4 text-[14px] text-[var(--text-secondary)]" style={{ borderColor: "var(--gold)" }}>
                    {children}
                  </blockquote>
                ),
                hr: () => <hr className="border-black/8 my-7" />,
              }}
            >
              {formattedBody}
            </Markdown>
          </div>

          {/* Provenance footer */}
        </div>
      </article>
    </section>
  );
}
