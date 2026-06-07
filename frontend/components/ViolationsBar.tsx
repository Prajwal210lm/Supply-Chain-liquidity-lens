"use client";

import { useState } from "react";

export default function ViolationsBar({
  violations,
}: {
  violations: Record<string, string[]>;
}) {
  const [expanded, setExpanded] = useState(false);

  const allViolations = Object.entries(violations).flatMap(([node, msgs]) =>
    msgs.map((m) => ({ node, msg: m }))
  );
  const count = allViolations.length;
  const clean = count === 0;

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-30 border-t text-sm
        ${clean ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-300"}`}
    >
      {/* Collapsed bar */}
      <button
        onClick={() => !clean && setExpanded((e) => !e)}
        className={`w-full flex items-center gap-3 px-6 py-3 text-left
          ${clean ? "cursor-default" : "hover:bg-amber-100 transition-colors"}`}
      >
        <span
          className={`inline-block w-2 h-2 rounded-full flex-shrink-0
            ${clean ? "bg-green-500" : "bg-amber-500"}`}
        />
        <span
          className={`font-medium ${clean ? "text-green-700" : "text-amber-700"}`}
        >
          {clean
            ? "0 contract violations"
            : `${count} contract violation${count > 1 ? "s" : ""}`}
        </span>
        {!clean && (
          <span className="ml-auto text-amber-500 text-xs">
            {expanded ? "▲ hide" : "▼ show"}
          </span>
        )}
      </button>

      {/* Expanded list */}
      {expanded && !clean && (
        <div className="border-t border-amber-200 px-6 py-4 max-h-48 overflow-y-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-amber-600 font-semibold">
                <th className="text-left pb-2 w-28">Node</th>
                <th className="text-left pb-2">Violation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-amber-100">
              {allViolations.map(({ node, msg }, i) => (
                <tr key={i}>
                  <td className="py-1.5 pr-4 font-mono text-amber-700 align-top">
                    {node}
                  </td>
                  <td className="py-1.5 text-amber-800">{msg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
