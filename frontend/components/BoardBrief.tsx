"use client";

import Markdown from "react-markdown";
import type { ReactNode } from "react";

export default function BoardBrief({
  headline,
  bodyMarkdown,
}: {
  headline: string;
  bodyMarkdown: string;
}) {
  return (
    <section>
      <h2 className="text-base font-semibold text-gray-500 uppercase tracking-widest mb-4">
        Board Brief
      </h2>
      <div className="border border-gray-200 bg-white px-8 py-7">
        <h1 className="text-xl font-bold text-gray-900 mb-5 leading-snug">
          {headline}
        </h1>
        <div className="prose-brief">
          <Markdown
            components={{
              h2: ({ children }: { children?: ReactNode }) => (
                <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mt-6 mb-2">
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
              li: ({ children }: { children?: ReactNode }) => <li className="leading-relaxed">{children}</li>,
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
