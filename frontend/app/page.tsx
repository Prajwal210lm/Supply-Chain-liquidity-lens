"use client";

import { useState, useCallback } from "react";
import {
  DiagnoseResponse,
  AskWhyResponse,
  runDiagnosis,
  fetchAskWhy,
} from "@/lib/api";
import RunButton from "@/components/RunButton";
import SummaryCards from "@/components/SummaryCards";
import ClusterTable from "@/components/ClusterTable";
import BoardBrief from "@/components/BoardBrief";
import AskWhyPanel from "@/components/AskWhyPanel";
import ViolationsBar from "@/components/ViolationsBar";

type RunStatus = "idle" | "loading" | "done" | "error";

export default function Home() {
  // Pipeline state
  const [status, setStatus] = useState<RunStatus>("idle");
  const [runError, setRunError] = useState<string | null>(null);
  const [data, setData] = useState<DiagnoseResponse | null>(null);

  // Ask-why state
  const [selectedSku, setSelectedSku] = useState<string | null>(null);
  const [askWhyLoading, setAskWhyLoading] = useState(false);
  const [askWhyResult, setAskWhyResult] = useState<AskWhyResponse | null>(null);
  const [askWhyError, setAskWhyError] = useState<string | null>(null);

  const handleRunDiagnosis = useCallback(async () => {
    setStatus("loading");
    setRunError(null);
    setData(null);
    setSelectedSku(null);
    setAskWhyResult(null);
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
    async (skuCode: string) => {
      if (skuCode === selectedSku) {
        setSelectedSku(null);
        setAskWhyResult(null);
        return;
      }
      setSelectedSku(skuCode);
      setAskWhyResult(null);
      setAskWhyError(null);
      setAskWhyLoading(true);
      try {
        const result = await fetchAskWhy(skuCode);
        setAskWhyResult(result);
      } catch (err) {
        setAskWhyError(err instanceof Error ? err.message : String(err));
      } finally {
        setAskWhyLoading(false);
      }
    },
    [selectedSku]
  );

  const handleClosePanel = useCallback(() => {
    setSelectedSku(null);
    setAskWhyResult(null);
    setAskWhyError(null);
  }, []);

  return (
    <div className="min-h-screen bg-white pb-16">
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
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-10">
        {/* Idle state */}
        {status === "idle" && (
          <div className="text-center py-20 text-gray-400">
            <p className="text-sm">
              Press <strong className="text-gray-600">Run Diagnosis</strong> to
              analyse the portfolio.
            </p>
          </div>
        )}

        {/* Loading */}
        {status === "loading" && (
          <div className="text-center py-20 text-gray-400 text-sm">
            Running pipeline — this takes 30–60 seconds…
          </div>
        )}

        {/* Error */}
        {status === "error" && runError && (
          <div className="border border-red-200 bg-red-50 p-5 text-sm text-red-700">
            <strong>Pipeline error:</strong> {runError}
          </div>
        )}

        {/* Results */}
        {status === "done" && data && (
          <>
            <SummaryCards vas={data.value_at_stake} clusters={data.clusters} />
            <ClusterTable
              clusters={data.clusters}
              onSkuClick={handleSkuClick}
              selectedSku={selectedSku}
            />
            <BoardBrief
              headline={data.brief.headline}
              bodyMarkdown={data.brief.body_markdown}
            />
          </>
        )}
      </main>

      {/* Ask-why panel */}
      {status === "done" && (
        <AskWhyPanel
          skuCode={selectedSku}
          result={askWhyResult}
          loading={askWhyLoading}
          error={askWhyError}
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
