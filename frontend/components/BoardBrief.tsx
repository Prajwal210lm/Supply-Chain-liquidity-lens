"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ReactNode } from "react";
import { sectionHeader } from "@/components/SummaryCards";

export default function BoardBrief({
  headline,
  bodyMarkdown,
}: {
  headline: string;
  bodyMarkdown: string;
}) {
  return (
    <section>
      <h2 className={sectionHeader}>Board Brief</h2>
      <div className="bg-gray-50 border border-gray-200 border-l-4 border-l-blue-800 px-8 py-7">
        <h1 className="text-xl font-bold text-gray-900 mb-5 leading-snug">
          {headline}
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
                <thead className="bg-white">{children}</thead>
              ),
              tbody: ({ children }: { children?: ReactNode }) => (
                <tbody className="divide-y divide-gray-100">{children}</tbody>
              ),
              tr: ({ children }: { children?: ReactNode }) => (
                <tr className="border-b border-gray-100">{children}</tr>
              ),
              th: ({ children }: { children?: ReactNode }) => (
                <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 border border-gray-200 bg-gray-50">
                  {children}
                </th>
              ),
              td: ({ children }: { children?: ReactNode }) => (
                <td className="px-4 py-2 text-sm text-gray-700 border border-gray-200">
                  {children}
                </td>
              ),
              h2: ({ children }: { children?: ReactNode }) => (
                <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 border-b border-gray-200 pb-1 mt-6 mb-2">
                  {children}
                </h2>
              ),
              h3: ({ children }: { children?: ReactNode }) => (
                <h3 className="text-sm font-semibold text-gray-800 mt-4 mb-1">
                  {children}
                </h3>
              ),
              p: ({ children }: { children?: ReactNode }) => (
                <p className="text-sm text-gray-700 leading-relaxed mb-3">
                  {children}
                </p>
              ),
              ul: ({ children }: { children?: ReactNode }) => (
                <ul className="list-disc list-inside text-sm text-gray-700 mb-3 space-y-1">
                  {children}
                </ul>
              ),
              ol: ({ children }: { children?: ReactNode }) => (
                <ol className="list-decimal list-inside text-sm text-gray-700 mb-3 space-y-1">
                  {children}
                </ol>
              ),
              li: ({ children }: { children?: ReactNode }) => (
                <li className="leading-relaxed">{children}</li>
              ),
              strong: ({ children }: { children?: ReactNode }) => (
                <strong className="font-semibold text-gray-900">{children}</strong>
              ),
              em: ({ children }: { children?: ReactNode }) => (
                <em className="italic text-gray-600">{children}</em>
              ),
              blockquote: ({ children }: { children?: ReactNode }) => (
                <blockquote className="border-l-4 border-gray-300 pl-4 text-gray-600 italic my-3">
                  {children}
                </blockquote>
              ),
              hr: () => <hr className="border-gray-200 my-5" />,
            }}
          >
            {bodyMarkdown}
          </Markdown>
        </div>
      </div>
    </section>
  );
}
