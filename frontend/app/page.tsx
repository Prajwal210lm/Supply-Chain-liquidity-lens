"use client";

import { useState, useCallback } from "react";
import { DiagnoseResponse, runDiagnosis } from "@/lib/api";
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

// ── Landing page ──────────────────────────────────────────────────────────────

function FeatureCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="border border-gray-200 bg-white p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-800 mb-2">{title}</h3>
      <p className="text-sm text-gray-500 leading-relaxed">{body}</p>
    </div>
  );
}

function LandingSection({ onRun, loading }: { onRun: () => void; loading: boolean }) {
  return (
    <div className="max-w-3xl mx-auto py-16 space-y-10">
      {/* Hero */}
      <div className="space-y-3">
        <h2 className="text-2xl font-bold text-gray-900 tracking-tight">
          Working-Capital Diagnostic
        </h2>
        <p className="text-base text-gray-500">
          AI-powered inventory value-at-stake assessment
        </p>
      </div>

      {/* Description paragraphs */}
      <div className="space-y-4 text-sm text-gray-600 leading-relaxed border-l-4 border-gray-200 pl-5">
        <p>
          Liquidity Lens analyses a portfolio of 600 SKUs across FMCG and pharmaceutical
          categories for a GCC-based distributor. The portfolio holds AED 106M in on-hand
          inventory across multiple suppliers and warehouses.
        </p>
        <p>
          The diagnostic identifies where cash is trapped in excess stock, which pharma
          batches are approaching expiry, and which high-value items face stockout risk.
          It segments SKUs using ABC-XYZ classification and computes target inventory levels
          calibrated to each item&apos;s lead time and demand variability.
        </p>
        <p>
          The output is a board-ready value-at-stake assessment with prioritised actions
          and assigned owners, written by an AI reasoning layer where every number is
          traceable to a deterministic, tested analytics core.
        </p>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <FeatureCard
          title="Releasable Cash"
          body="Identifies excess inventory above order-up-to levels that is safe to release without service-level risk."
        />
        <FeatureCard
          title="Expiry Risk"
          body="Flags near-expiry pharma batches requiring urgent triage to prevent P&L write-offs."
        />
        <FeatureCard
          title="Stockout Protection"
          body="Detects high-value items below reorder point, explicitly excluded from any release action."
        />
      </div>

      {/* CTA */}
      <div className="flex flex-col items-center gap-4 pt-2">
        <button
          onClick={onRun}
          disabled={loading}
          className="px-8 py-3 bg-gray-900 text-white text-sm font-medium tracking-wide uppercase
                     hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 bg-white rounded-full animate-pulse" />
              Running pipeline…
            </span>
          ) : (
            "Run Diagnosis"
          )}
        </button>
        <p className="text-xs text-gray-400">
          Synthetic data modelled on a mid-sized GCC distributor. Analysis runs against pre-computed results.
        </p>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Home() {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [runError, setRunError] = useState<string | null>(null);
  const [data, setData] = useState<DiagnoseResponse | null>(null);
  const [selectedSku, setSelectedSku] = useState<string | null>(null);

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
          {status !== "idle" && (
            <RunButton status={status} onClick={handleRunDiagnosis} />
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8 space-y-10 pb-20">
        {/* Landing */}
        {(status === "idle" || status === "loading") && (
          <LandingSection
            onRun={handleRunDiagnosis}
            loading={status === "loading"}
          />
        )}

        {/* Error */}
        {status === "error" && runError && (
          <>
            <div className="border border-red-200 bg-red-50 p-5 text-sm text-red-700">
              <strong>Pipeline error:</strong> {runError}
            </div>
            <div className="text-center">
              <button
                onClick={handleRunDiagnosis}
                className="px-6 py-2 bg-gray-900 text-white text-sm font-medium tracking-wide uppercase hover:bg-gray-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </>
        )}

        {/* Results */}
        {status === "done" && data && (
          <>
            <SummaryCards vas={data.value_at_stake} clusters={data.clusters} />
            <ValueBreakdown vas={data.value_at_stake} />
            <BoardBrief
              headline={data.brief.headline}
              bodyMarkdown={data.brief.body_markdown}
            />
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
