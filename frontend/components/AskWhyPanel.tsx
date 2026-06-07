"use client";

import { AskWhyResponse } from "@/lib/api";

export default function AskWhyPanel({
  skuCode,
  result,
  loading,
  error,
  onClose,
}: {
  skuCode: string | null;
  result: AskWhyResponse | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  if (!skuCode) return null;

  return (
    <>
      {/* Dim backdrop — click to close */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <aside className="fixed top-0 right-0 h-full w-[420px] bg-white shadow-2xl z-50 flex flex-col border-l border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-200">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-0.5">
              Ask Why
            </p>
            <p className="font-mono text-sm font-bold text-gray-900">{skuCode}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading && (
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <span className="inline-block w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
              Analysing…
            </div>
          )}

          {error && !loading && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 p-3">
              {error}
            </p>
          )}

          {result && !loading && (
            <div className="space-y-5">
              {/* Cluster tags */}
              {result.cluster_memberships.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {result.cluster_memberships.map((c) => (
                    <span
                      key={c}
                      className="text-xs px-2 py-1 bg-gray-100 text-gray-600 border border-gray-200"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              )}

              {/* Explanation */}
              <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                {result.explanation}
              </div>

              {/* Violations (if any) */}
              {result.violations.length > 0 && (
                <div className="mt-4 border border-amber-200 bg-amber-50 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-700 mb-2">
                    Contract Warnings
                  </p>
                  <ul className="space-y-1">
                    {result.violations.map((v, i) => (
                      <li key={i} className="text-xs text-amber-700">
                        {v}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
