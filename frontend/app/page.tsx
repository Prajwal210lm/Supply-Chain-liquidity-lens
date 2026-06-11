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

type RunStatus = "idle" | "loading" | "done" | "error";

// ── Inline SVG icons ──────────────────────────────────────────────────────────

function CashIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <circle cx="12" cy="12" r="3" />
      <path d="M6 12h.01M18 12h.01" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 3" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3L4 7v5c0 5.25 3.5 10.15 8 11.25C16.5 22.15 20 17.25 20 12V7l-8-4z" />
    </svg>
  );
}

// ── Feature card ──────────────────────────────────────────────────────────────

function FeatureCard({
  icon,
  accentColor,
  title,
  body,
}: {
  icon: React.ReactNode;
  accentColor: string;
  title: string;
  body: string;
}) {
  return (
    <div
      className="bg-white rounded-xl shadow-lg p-6 border-t-[3px] transition-all duration-200 hover:shadow-xl hover:translate-y-[-2px]"
      style={{ borderTopColor: accentColor }}
    >
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center mb-4"
        style={{ backgroundColor: `${accentColor}1a`, color: accentColor }}
      >
        {icon}
      </div>
      <h3 className="font-semibold text-[15px] text-gray-900 mb-2">{title}</h3>
      <p className="text-[13px] text-gray-500 leading-[1.6]">{body}</p>
    </div>
  );
}

// ── Landing page ──────────────────────────────────────────────────────────────

function LandingSection({ onRun, loading }: { onRun: () => void; loading: boolean }) {
  return (
    <div>
      {/* Dark hero — THE PROBLEM + THE APPROACH */}
      <div
        className="relative flex flex-col items-center text-center px-6 py-16"
        style={{
          background: "linear-gradient(135deg, var(--navy-900) 0%, var(--navy-800) 100%)",
        }}
      >
        {/* Dot-grid overlay */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.05) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
        />

        {/* THE PROBLEM */}
        <div className="relative z-10 w-full max-w-[700px] mx-auto">
          <p className="text-[11px] uppercase tracking-[0.15em] text-white/40 mb-6">The Problem</p>
          <p className="font-display italic text-2xl text-white/90 leading-[1.6]">
            Large distributors in the GCC hold tens of millions in on-hand inventory across
            hundreds of SKUs. Cash gets trapped in slow-moving stock. Pharma batches creep
            toward expiry unnoticed. Fast-moving items stock out while excess sits on the shelf
            next to them.
          </p>
          <p className="text-base text-white/65 max-w-[580px] mx-auto mt-4 leading-[1.7]">
            The problem is not that nobody knows this happens. The problem is that by the time
            a manual review surfaces it, the financial damage is already done.
          </p>
        </div>

        {/* Divider */}
        <div className="relative z-10 w-full max-w-2xl border-t border-white/10 my-8" />

        {/* THE APPROACH */}
        <div className="relative z-10 w-full max-w-[640px] mx-auto">
          <p className="text-[11px] uppercase tracking-[0.15em] text-white/40 mb-6">The Approach</p>
          <p className="text-[15px] text-white/70 leading-[1.75]">
            Liquidity Lens reads raw inventory, sales, and supplier data for a portfolio of
            600 SKUs (AED 106M on-hand inventory). It segments every item by ABC-XYZ
            classification, computes target stock levels calibrated to lead time and demand
            variability, and flags where value is at stake.
          </p>
          <p className="text-[15px] text-white/70 mt-3 leading-[1.75]">
            An AI reasoning layer then diagnoses root causes, writes recommendations, and
            produces a board memo with prioritised actions and assigned owners. Every number
            in the output is traceable to a deterministic, tested analytics core. The AI
            writes prose. It never calculates.
          </p>
        </div>

        {/* WHAT IT FINDS label — at the bottom of the dark hero, just above the cards */}
        <p className="relative z-10 text-[11px] uppercase tracking-[0.15em] text-white/40 mt-14">
          What It Finds
        </p>
      </div>

      {/* Feature cards — overlapping hero by ~40px */}
      <div className="max-w-5xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 -mt-10">
          <FeatureCard
            icon={<CashIcon />}
            accentColor="#059669"
            title="Releasable Cash"
            body="Identifies excess inventory above order-up-to levels that is safe to release without service-level risk."
          />
          <FeatureCard
            icon={<ClockIcon />}
            accentColor="#D97706"
            title="Expiry Risk"
            body="Flags near-expiry pharma batches requiring urgent triage to prevent P&L write-offs."
          />
          <FeatureCard
            icon={<ShieldIcon />}
            accentColor="#DC2626"
            title="Stockout Protection"
            body="Detects high-value items below reorder point, explicitly excluded from any release action."
          />
        </div>
      </div>

      {/* RUN IT */}
      <div className="flex flex-col items-center px-6 pt-4 pb-16">
        <p className="text-sm text-gray-500 max-w-[480px] text-center mt-6 mb-4 leading-relaxed">
          Click below to run the diagnostic against the full 600-SKU portfolio.
          The analysis loads pre-computed results from a completed pipeline run.
        </p>
        <button
          onClick={onRun}
          disabled={loading}
          className="px-8 py-3 text-sm font-semibold tracking-wide uppercase text-white
                     rounded-full shadow-lg hover:shadow-xl transition-all duration-200
                     bg-[var(--navy-700)] hover:bg-[var(--navy-800)]
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Running pipeline…
            </span>
          ) : (
            "Run Diagnosis"
          )}
        </button>
        <p className="text-xs text-gray-400 italic mt-6">
          Synthetic data modelled on a mid-sized GCC distributor.
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
      window.scrollTo(0, 0);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }, []);

  const handleSkuClick = useCallback((skuCode: string) => {
    setSelectedSku((prev) => (prev === skuCode ? null : skuCode));
  }, []);

  const handleClosePanel = useCallback(() => setSelectedSku(null), []);

  return (
    <div className="min-h-screen bg-[var(--surface)] flex flex-col">
      {/* Dark sticky header */}
      <header
        className="sticky top-0 z-20"
        style={{ background: "var(--navy-900)" }}
      >
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="font-display text-[22px] font-bold text-white">
              Liquidity Lens
            </h1>
            <p className="text-[13px] mt-0.5 text-white/50">
              Working-Capital Diagnostic · GCC Distributor
            </p>
          </div>
          <div className="flex items-center gap-3">
            {status === "done" && (
              <button
                onClick={() => { setData(null); setStatus("idle"); }}
                className="flex items-center gap-1.5 text-sm text-white/60 hover:text-white
                           border border-white/20 rounded-full px-4 py-1.5 transition-colors duration-150"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M19 12H5M12 5l-7 7 7 7" />
                </svg>
                Overview
              </button>
            )}
            {status !== "idle" && (
              <RunButton status={status} onClick={handleRunDiagnosis} variant="ghost" />
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-x-hidden">
        {/* Landing */}
        {(status === "idle" || status === "loading") && (
          <LandingSection onRun={handleRunDiagnosis} loading={status === "loading"} />
        )}

        {/* Error */}
        {status === "error" && runError && (
          <div className="max-w-7xl mx-auto px-6 py-8 space-y-4">
            <div className="border border-red-200 bg-red-50 rounded-xl p-5 text-sm text-red-700">
              <strong>Pipeline error:</strong> {runError}
            </div>
            <div className="text-center">
              <button
                onClick={handleRunDiagnosis}
                className="px-6 py-2.5 text-sm font-semibold tracking-wide uppercase text-white
                           rounded-full shadow-lg hover:shadow-xl transition-all duration-200
                           bg-[var(--navy-700)] hover:bg-[var(--navy-800)]"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {/* Results */}
        {status === "done" && data && (
          <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 pb-20">
            <div className="animate-fade-up" style={{ animationDelay: "0ms" }}>
              <SummaryCards vas={data.value_at_stake} clusters={data.clusters} />
            </div>
            <div className="animate-fade-up" style={{ animationDelay: "60ms" }}>
              <ValueBreakdown vas={data.value_at_stake} />
            </div>
            <div className="animate-fade-up" style={{ animationDelay: "120ms" }}>
              <BoardBrief
                headline={data.brief.headline}
                bodyMarkdown={data.brief.body_markdown}
              />
            </div>
            <div className="animate-fade-up" style={{ animationDelay: "180ms" }}>
              <ClusterTable
                clusters={data.clusters}
                onSkuClick={handleSkuClick}
                selectedSku={selectedSku}
              />
            </div>
            <div className="animate-fade-up" style={{ animationDelay: "240ms" }}>
              <SupplierAnalysis clusters={data.clusters} />
            </div>
            <div className="animate-fade-up" style={{ animationDelay: "300ms" }}>
              <CategoryBreakdown clusters={data.clusters} />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-5 text-center bg-white">
        <p className="text-[11px] text-gray-400">
          Liquidity Lens · Working-Capital Diagnostic · Built with Python, LangGraph, Claude, Next.js
        </p>
      </footer>

      {/* SKU detail panel — always mounted when done, slides in/out */}
      {status === "done" && data && (
        <AskWhyPanel
          skuCode={selectedSku}
          clusters={data.clusters}
          onClose={handleClosePanel}
        />
      )}
    </div>
  );
}
