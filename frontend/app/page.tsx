"use client";

import { useState, useCallback, useEffect } from "react";
import { DiagnoseResponse, runDiagnosis } from "@/lib/api";
import { loadCachedDiagnosis } from "@/lib/static-data";
import RunButton from "@/components/RunButton";
import SummaryCards from "@/components/SummaryCards";
import ValueBreakdown from "@/components/ValueBreakdown";
import BoardBrief from "@/components/BoardBrief";
import ClusterTable from "@/components/ClusterTable";
import SupplierAnalysis from "@/components/SupplierAnalysis";
import CategoryBreakdown from "@/components/CategoryBreakdown";
import AskWhyPanel from "@/components/AskWhyPanel";
import ViolationsBar from "@/components/ViolationsBar";

type RunStatus = "idle" | "loading" | "done" | "error";

export default function Home() {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [runError, setRunError] = useState<string | null>(null);
  const [data, setData] = useState<DiagnoseResponse | null>(null);
  const [selectedSku, setSelectedSku] = useState<string | null>(null);

  // Auto-load cached data on mount
  useEffect(() => {
    loadCachedDiagnosis()
      .then((result) => {
        setData(result);
        setStatus("done");
      })
      .catch(() => {
        // Cached file unavailable — leave in idle state, user can run live
      });
  }, []);

  const handleRunDiagnosis = useCallback(async () => {
    setStatus("loading");
    setRunError(null);
    setData(null);
    setSelectedSku(null);
    try {
      const result = await runDiagnosis();
      setData(result);
      setStatus("done");
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }, []);

  const handleSkuClick = useCallback(
    (skuCode: string) => {
      setSelectedSku((prev) => (prev === skuCode ? null : skuCode));
    },
    []
  );

  const handleClosePanel = useCallback(() => setSelectedSku(null), []);

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Top bar */}
      <header className="border-b border-gray-200 bg-white sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900 tracking-tight">
              Liquidity Lens
            </h1>
            <p className="text-xs text-gray-400 mt-0.5">
              Working-Capital Diagnostic · GCC Distributor
            </p>
          </div>
          <RunButton status={status} onClick={handleRunDiagnosis} />
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8 space-y-10 pb-20">
        {/* Idle: only shown if cached load fails */}
        {status === "idle" && (
          <div className="text-center py-20 text-gray-400">
            <p className="text-sm">
              Press <strong className="text-gray-600">Run Diagnosis</strong> to
              analyse the portfolio.
            </p>
          </div>
        )}

        {status === "loading" && (
          <div className="text-center py-20 text-gray-400 text-sm">
            Running pipeline — this takes 30–60 seconds…
          </div>
        )}

        {status === "error" && runError && (
          <div className="border border-red-200 bg-red-50 p-5 text-sm text-red-700">
            <strong>Pipeline error:</strong> {runError}
          </div>
        )}

        {status === "done" && data && (
          <>
            {/* 1. KPI cards */}
            <SummaryCards vas={data.value_at_stake} clusters={data.clusters} />

            {/* 2. Value waterfall */}
            <ValueBreakdown vas={data.value_at_stake} />

            {/* 3. Board brief — most important, recruiters see this first */}
            <BoardBrief
              headline={data.brief.headline}
              bodyMarkdown={data.brief.body_markdown}
            />

            {/* 4. Detailed tables */}
            <ClusterTable
              clusters={data.clusters}
              onSkuClick={handleSkuClick}
              selectedSku={selectedSku}
            />
            <SupplierAnalysis clusters={data.clusters} />
            <CategoryBreakdown clusters={data.clusters} />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-5 text-center">
        <p className="text-xs text-gray-400">
          Liquidity Lens · Working-Capital Diagnostic · Built with Python, LangGraph, Claude, Next.js
        </p>
      </footer>

      {/* SKU detail panel */}
      {status === "done" && data && (
        <AskWhyPanel
          skuCode={selectedSku}
          clusters={data.clusters}
          onClose={handleClosePanel}
        />
      )}

      {/* Violations bar */}
      {status === "done" && data && (
        <ViolationsBar violations={data.violations} />
      )}
    </div>
  );
}
