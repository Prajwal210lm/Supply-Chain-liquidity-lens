"use client";

import { useState, useCallback } from "react";
import { DiagnoseResponse, runDiagnosis } from "@/lib/api";
import RunButton from "@/components/RunButton";
import SummaryCards from "@/components/SummaryCards";
import ViolationsBar from "@/components/ViolationsBar";
import ValueBreakdown from "@/components/ValueBreakdown";
import BoardBrief from "@/components/BoardBrief";
import ClusterTable from "@/components/ClusterTable";
import SupplierAnalysis from "@/components/SupplierAnalysis";
import CategoryBreakdown from "@/components/CategoryBreakdown";
import AskWhyPanel from "@/components/AskWhyPanel";

type RunStatus = "idle" | "loading" | "done" | "error";

// ── Brand + inline SVG icons (Lucide/Heroicons style) ─────────────────────────

function LensMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="12" cy="12" r="3.4" stroke="currentColor" strokeWidth="1.4" />
      <path d="M12 3v3.4M12 17.6V21M3 12h3.4M17.6 12H21" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

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

function ArrowLeftIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M19 12H5M12 5l-7 7 7 7" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3v12m0 0l-4-4m4 4l4-4M4 19h16" />
    </svg>
  );
}

function TableIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <rect x="3" y="4" width="18" height="16" rx="1.5" />
      <path d="M3 9h18M3 14.5h18M9 9v11" />
    </svg>
  );
}

function ComputeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="3.2" />
      <path d="M12 2.5v3M12 18.5v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2.5 12h3M18.5 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
    </svg>
  );
}

function WriteIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}

function ValidateIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3L4 7v5c0 5.25 3.5 10.15 8 11.25C16.5 22.15 20 17.25 20 12V7l-8-4z" />
      <path d="M9 12.2l2 2 4-4.2" />
    </svg>
  );
}

function StepArrow() {
  return (
    <div className="flex items-center justify-center flex-shrink-0 text-white/25 py-1 md:py-0 md:px-2">
      <svg
        width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
        strokeLinecap="round" strokeLinejoin="round" className="rotate-90 md:rotate-0" aria-hidden="true"
      >
        <path d="M5 12h14M13 6l6 6-6 6" />
      </svg>
    </div>
  );
}

function ContractStep({
  index,
  icon,
  title,
  body,
}: {
  index: string;
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="flex-1 rounded-xl border border-white/10 bg-white/[0.035] p-5 text-left">
      <div className="flex items-center gap-2.5 mb-3">
        <span
          className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: "rgba(189,154,74,0.12)", color: "var(--gold-soft)" }}
        >
          {icon}
        </span>
        <span className="font-mono text-[10px] text-white/35 tnum">{index}</span>
      </div>
      <h4 className="text-[14px] font-semibold text-white mb-1.5">{title}</h4>
      <p className="text-[12.5px] text-white/60 leading-[1.6]">{body}</p>
    </div>
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
      className="group relative bg-[var(--card)] rounded-2xl p-6 border border-black/5 overflow-hidden
                 transition-[transform,box-shadow] duration-300 ease-out hover:-translate-y-1"
      style={{ boxShadow: "var(--elev-2)" }}
    >
      <span
        className="absolute inset-x-0 top-0 h-[3px]"
        style={{ background: `linear-gradient(90deg, ${accentColor}, ${accentColor}55)` }}
      />
      <div
        className="w-11 h-11 rounded-xl flex items-center justify-center mb-4 transition-transform duration-300 group-hover:scale-105"
        style={{ backgroundColor: `${accentColor}14`, color: accentColor }}
      >
        {icon}
      </div>
      <h3 className="font-semibold text-[15px] text-[var(--text-primary)] mb-1.5">{title}</h3>
      <p className="text-[13px] text-[var(--text-secondary)] leading-[1.65]">{body}</p>
    </div>
  );
}

// ── Data model — schema preview cards (table name, row count, columns + samples) ─

type Column = { name: string; sample: string; pk?: boolean };
type TableDef = { name: string; description: string; rows: string; columns: Column[] };

const DATA_TABLES: TableDef[] = [
  {
    name: "sku",
    description: "Product master",
    rows: "600 rows",
    columns: [
      { name: "sku_code", sample: "SKU-0428", pk: true },
      { name: "name", sample: "Amoxicillin 500mg" },
      { name: "category_id", sample: "CAT-03" },
      { name: "unit_cost", sample: "12.40" },
      { name: "selling_price", sample: "18.90" },
      { name: "is_perishable", sample: "true" },
      { name: "shelf_life_days", sample: "540" },
      { name: "service_level_target", sample: "0.95" },
    ],
  },
  {
    name: "inventory_batch",
    description: "Stock by lot, with expiry",
    rows: "2,418 rows",
    columns: [
      { name: "batch_id", sample: "BCH-19273", pk: true },
      { name: "sku_id", sample: "SKU-0428" },
      { name: "batch_code", sample: "L24-0917" },
      { name: "quantity_on_hand", sample: "1,240" },
      { name: "received_date", sample: "2025-09-17" },
      { name: "expiry_date", sample: "2027-03-17" },
    ],
  },
  {
    name: "sku_supplier",
    description: "SKU-supplier links",
    rows: "631 rows",
    columns: [
      { name: "sku_id", sample: "SKU-0428" },
      { name: "supplier_id", sample: "SUP-02" },
      { name: "lead_time_days", sample: "21" },
      { name: "moq", sample: "500" },
      { name: "is_primary", sample: "true" },
    ],
  },
  {
    name: "sales_history",
    description: "Weekly sales, 104 weeks",
    rows: "62,400 rows",
    columns: [
      { name: "sku_id", sample: "SKU-0428" },
      { name: "week_start_date", sample: "2026-05-25" },
      { name: "quantity_sold", sample: "84" },
      { name: "revenue", sample: "1,587.60" },
    ],
  },
  {
    name: "supplier",
    description: "Vendor master",
    rows: "8 rows",
    columns: [
      { name: "supplier_id", sample: "SUP-02", pk: true },
      { name: "name", sample: "Gulf Pharma DMCC" },
      { name: "country", sample: "AE" },
      { name: "reliability_score", sample: "0.91" },
    ],
  },
  {
    name: "category",
    description: "Product families",
    rows: "8 rows",
    columns: [
      { name: "category_id", sample: "CAT-03", pk: true },
      { name: "name", sample: "Antibiotics" },
    ],
  },
];

function DataModelCard({ table }: { table: TableDef }) {
  return (
    <div
      className="group rounded-2xl border border-white/10 bg-white/[0.035] overflow-hidden text-left
                 transition-[transform,border-color,background-color] duration-300 ease-out
                 hover:-translate-y-0.5 hover:border-[var(--gold-line)] hover:bg-white/[0.055]"
    >
      {/* Card head */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="text-[var(--gold-soft)]/80 flex-shrink-0">
            <TableIcon />
          </span>
          <span className="font-mono text-[13.5px] font-semibold text-white truncate">{table.name}</span>
        </div>
        <span className="font-mono text-[10.5px] text-white/55 flex-shrink-0 tnum">{table.rows}</span>
      </div>

      {/* Column rows with sample values */}
      <div className="px-4 py-3">
        <p className="text-[11px] text-white/55 mb-2.5">{table.description}</p>
        <div className="space-y-[3px]">
          {table.columns.map((c) => (
            <div key={c.name} className="flex items-baseline justify-between gap-3 group/row">
              <span className="font-mono text-[11.5px] text-white/70 flex items-center gap-1.5 min-w-0">
                {c.pk && (
                  <span className="text-[8px] uppercase tracking-wider text-[var(--gold-soft)] font-sans font-semibold flex-shrink-0">PK</span>
                )}
                <span className="truncate">{c.name}</span>
              </span>
              <span className="font-mono text-[11px] text-white/50 truncate text-right tnum">{c.sample}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Cinematic loading state ───────────────────────────────────────────────────

const PIPELINE_STEPS = [
  "Validating data quality",
  "Computing inventory metrics",
  "Diagnosing root causes",
  "Recommending actions",
  "Prioritising release plan",
  "Drafting the board brief",
];

function DiagnosticLoading() {
  return (
    <div
      className="relative flex flex-col items-center justify-center text-center px-6 py-28 min-h-[70vh]"
      style={{ background: "linear-gradient(160deg, var(--ink-950) 0%, var(--navy-900) 55%, var(--navy-800) 100%)" }}
    >
      <div className="absolute inset-0 tx-dotgrid pointer-events-none opacity-70" />
      {/* Indeterminate gold progress line */}
      <div className="absolute top-0 inset-x-0 h-px overflow-hidden">
        <div className="h-full w-1/3 skeleton" style={{ background: "linear-gradient(90deg, transparent, var(--gold-soft), transparent)" }} />
      </div>

      <div className="relative z-10 w-full max-w-md">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[var(--gold-soft)]/80 mb-3">Diagnostic Pipeline</p>
        <h2 className="font-display text-[28px] text-white mb-8 leading-tight">Analysing the portfolio</h2>

        <ol className="text-left space-y-2.5">
          {PIPELINE_STEPS.map((step, i) => (
            <li
              key={step}
              className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 animate-fade-up"
              style={{ animationDelay: `${i * 110}ms` }}
            >
              <span className="font-mono text-[11px] text-white/35 w-5 flex-shrink-0 tnum">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-[13.5px] text-white/75 flex-1">{step}</span>
              <span
                className="w-1.5 h-1.5 rounded-full bg-[var(--gold-soft)] flex-shrink-0 animate-pulse-dot"
                style={{ animationDelay: `${i * 180}ms` }}
              />
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

// ── Landing page ──────────────────────────────────────────────────────────────

function LandingSection({ onRun }: { onRun: () => void }) {
  return (
    <div>
      {/* Dark hero — PROBLEM / APPROACH / DATA */}
      <div
        className="relative flex flex-col items-center text-center px-6 pt-20 pb-24"
        style={{ background: "linear-gradient(160deg, var(--ink-950) 0%, var(--navy-900) 50%, var(--navy-800) 100%)" }}
      >
        {/* Texture + glow */}
        <div className="absolute inset-0 tx-dotgrid pointer-events-none" />
        <div
          className="absolute inset-x-0 top-0 h-[420px] pointer-events-none"
          style={{ background: "radial-gradient(60% 100% at 50% 0%, rgba(189,154,74,0.10), transparent 70%)" }}
        />

        {/* THE PROBLEM */}
        <div className="relative z-10 w-full max-w-[720px] mx-auto">
          <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--gold-soft)]/75 mb-6">The Problem</p>
          <p className="font-display italic text-[26px] sm:text-[30px] text-white/95 leading-[1.5]">
            Large distributors in the GCC hold tens of millions in on-hand inventory across
            hundreds of SKUs. Cash gets trapped in slow-moving stock. Pharma batches creep
            toward expiry unnoticed. Fast-moving items stock out while excess sits on the shelf
            next to them.
          </p>
          <p className="text-[15px] text-white/60 max-w-[560px] mx-auto mt-6 leading-[1.7]">
            The problem is not that nobody knows this happens. The problem is that by the time
            a manual review surfaces it, the financial damage is already done.
          </p>
        </div>

        <div className="relative z-10 w-full max-w-2xl border-t tx-gold-hairline my-12" />

        {/* THE APPROACH */}
        <div className="relative z-10 w-full max-w-[640px] mx-auto">
          <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--gold-soft)]/75 mb-6">The Approach</p>
          <p className="text-[15px] text-white/72 leading-[1.8]">
            Liquidity Lens reads raw inventory, sales, and supplier data for a portfolio of
            600 SKUs (AED 106M on-hand inventory). It segments every item by ABC-XYZ
            classification, computes target stock levels calibrated to lead time and demand
            variability, and flags where value is at stake.
          </p>
          <p className="text-[15px] text-white/72 mt-4 leading-[1.8]">
            An AI reasoning layer then diagnoses root causes, writes recommendations, and
            produces a board memo with prioritised actions and assigned owners. Every number
            in the output is traceable to a deterministic, tested analytics core.{" "}
            <span className="text-white/90 font-medium">The AI writes prose. It never calculates.</span>
          </p>
        </div>

        <div className="relative z-10 w-full max-w-2xl border-t tx-gold-hairline my-12" />

        {/* THE CONTRACT — the no-fabrication architecture, shown as a 3-step pipeline */}
        <div className="relative z-10 w-full max-w-4xl mx-auto">
          <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--gold-soft)]/75 mb-6">The Contract</p>
          <p className="text-[15px] text-white/72 max-w-[640px] mx-auto leading-[1.8]">
            This is enforced by machine, not by convention. Every figure moves through three
            steps, and a bare digit anywhere it shouldn&apos;t be causes the whole output to be rejected.
          </p>

          <div className="flex flex-col md:flex-row items-stretch mt-10">
            <ContractStep
              index="01"
              icon={<ComputeIcon />}
              title="Compute"
              body="The deterministic Python core calculates every figure — DIO, excess value, expiry risk, stockout loss. No LLM touches a number here."
            />
            <StepArrow />
            <ContractStep
              index="02"
              icon={<WriteIcon />}
              title="Write"
              body="Claude reasons about root causes and drafts the board brief — but every figure is a {{path}} reference, never a typed digit."
            />
            <StepArrow />
            <ContractStep
              index="03"
              icon={<ValidateIcon />}
              title="Validate & Render"
              body="A contract validator rejects any bare digit outside a reference. Only after it passes does a renderer substitute the real, computed values."
            />
          </div>

          <p className="text-[12px] text-white/45 text-center mt-6">
            Run the diagnosis below to see the live contract status, above the board brief.
          </p>
        </div>

        <div className="relative z-10 w-full max-w-2xl border-t tx-gold-hairline my-12" />

        {/* THE DATA */}
        <div className="relative z-10 w-full max-w-5xl mx-auto">
          <p className="text-[11px] uppercase tracking-[0.2em] text-[var(--gold-soft)]/75 mb-6">The Data</p>
          <p className="text-[15px] text-white/72 max-w-[640px] mx-auto leading-[1.8]">
            Liquidity Lens runs on a relational dataset modelled on a real GCC distributor:
            600 SKUs, 8 suppliers, 104 weeks of sales history, and batch-level inventory with
            expiry dates. Six tables, fully normalised.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-10">
            {DATA_TABLES.map((t) => (
              <DataModelCard key={t.name} table={t} />
            ))}
          </div>

          <div className="flex flex-col items-center mt-10">
            <a
              href="/data/liquidity_lens_dataset.zip"
              download
              className="inline-flex items-center gap-2 border tx-gold-hairline text-white/80 hover:text-white
                         hover:border-[var(--gold-soft)]/60 rounded-full px-5 py-2.5 text-[13px] font-medium
                         cursor-pointer transition-colors duration-200"
            >
              <DownloadIcon />
              Download full dataset (CSV)
            </a>
            <p className="text-[11px] text-white/40 mt-3 tnum">6 tables, 600 SKUs, 104 weeks of sales history</p>
          </div>
        </div>

        <p className="relative z-10 text-[11px] uppercase tracking-[0.2em] text-[var(--gold-soft)]/75 mt-20">
          What It Finds
        </p>
      </div>

      {/* Feature cards — overlap hero, explicit z-10 so they never hide behind it */}
      <div className="relative z-10 max-w-5xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 -mt-12">
          <FeatureCard
            icon={<CashIcon />}
            accentColor="var(--green-accent)"
            title="Releasable Cash"
            body="Identifies excess inventory above order-up-to levels that is safe to release without service-level risk."
          />
          <FeatureCard
            icon={<ClockIcon />}
            accentColor="var(--amber-accent)"
            title="Expiry Risk"
            body="Flags near-expiry pharma batches requiring urgent triage to prevent P&L write-offs."
          />
          <FeatureCard
            icon={<ShieldIcon />}
            accentColor="var(--red-accent)"
            title="Stockout Protection"
            body="Detects high-value items below reorder point, explicitly excluded from any release action."
          />
        </div>
      </div>

      {/* RUN IT */}
      <div className="flex flex-col items-center px-6 pt-14 pb-20">
        <p className="text-[14px] text-[var(--text-secondary)] max-w-[480px] text-center mb-5 leading-[1.7]">
          Run the diagnostic against the full 600-SKU portfolio. The analysis loads
          pre-computed results from a completed pipeline run.
        </p>
        <button
          onClick={onRun}
          className="group inline-flex items-center gap-2.5 px-8 py-3.5 text-[13px] font-semibold tracking-[0.08em] uppercase text-white
                     rounded-full cursor-pointer transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-0.5"
          style={{ background: "linear-gradient(180deg, var(--navy-700), var(--navy-800))", boxShadow: "var(--elev-3)" }}
        >
          Run Diagnosis
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform duration-200 group-hover:translate-x-0.5" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
        <p className="text-[11px] text-[var(--text-secondary)]/70 italic mt-6">
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
      {/* Sticky header — z-50, opaque ink, gold hairline */}
      <header
        className="sticky top-0"
        style={{
          zIndex: "var(--z-header)" as React.CSSProperties["zIndex"],
          background: "linear-gradient(180deg, var(--ink-950), var(--navy-900))",
          boxShadow: "0 1px 0 var(--gold-line), 0 6px 24px rgba(6,10,18,0.35)",
        }}
      >
        <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className="w-9 h-9 rounded-xl flex items-center justify-center text-[var(--gold-soft)] flex-shrink-0"
              style={{ background: "rgba(189,154,74,0.10)", border: "1px solid var(--gold-line)" }}
            >
              <LensMark className="w-5 h-5" />
            </span>
            <div className="min-w-0">
              <h1 className="font-display text-[21px] font-semibold text-white leading-none">Liquidity Lens</h1>
              <p className="hidden sm:block text-[11.5px] mt-1 text-white/45 tracking-wide truncate">
                Working-Capital Diagnostic · GCC Distributor
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {status === "done" && (
              <button
                onClick={() => { setData(null); setStatus("idle"); }}
                className="flex items-center gap-1.5 text-[13px] text-white/65 hover:text-white
                           border border-white/15 hover:border-white/30 rounded-full px-4 py-1.5
                           cursor-pointer transition-colors duration-200"
              >
                <ArrowLeftIcon />
                Overview
              </button>
            )}
            {status !== "idle" && status !== "loading" && (
              <span className="hidden sm:inline-flex">
                <RunButton status={status} onClick={handleRunDiagnosis} variant="ghost" />
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-x-hidden">
        {status === "idle" && <LandingSection onRun={handleRunDiagnosis} />}

        {status === "loading" && <DiagnosticLoading />}

        {status === "error" && runError && (
          <div className="max-w-2xl mx-auto px-6 py-16 space-y-5 text-center">
            <div className="border border-[var(--red-accent)]/25 bg-[var(--red-accent)]/[0.06] rounded-2xl p-6 text-[14px] text-[var(--red-accent)]">
              <strong className="font-semibold">Pipeline error.</strong> {runError}
            </div>
            <button
              onClick={handleRunDiagnosis}
              className="px-6 py-2.5 text-[13px] font-semibold tracking-wide uppercase text-white
                         rounded-full cursor-pointer transition-transform duration-200 hover:-translate-y-0.5"
              style={{ background: "linear-gradient(180deg, var(--navy-700), var(--navy-800))", boxShadow: "var(--elev-2)" }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Results */}
        {status === "done" && data && (
          <div className="max-w-7xl mx-auto px-6 py-10 space-y-10 pb-24">
            {[
              <SummaryCards key="s" vas={data.value_at_stake} clusters={data.clusters} />,
              <ViolationsBar
                key="vb"
                violations={data.violations}
                qualityReport={data.quality_report}
                vas={data.value_at_stake}
                clusters={data.clusters}
              />,
              <ValueBreakdown key="v" vas={data.value_at_stake} />,
              <BoardBrief key="b" headline={data.brief.headline} bodyMarkdown={data.brief.body_markdown} />,
              <ClusterTable key="c" clusters={data.clusters} onSkuClick={handleSkuClick} selectedSku={selectedSku} />,
              <SupplierAnalysis key="su" clusters={data.clusters} />,
              <CategoryBreakdown key="ca" clusters={data.clusters} />,
            ].map((node, i) => (
              <section key={i} className="animate-fade-up scroll-mt-24" style={{ animationDelay: `${i * 70}ms` }}>
                {node}
              </section>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-black/5 py-6 text-center bg-[var(--card)]">
        <p className="text-[11px] text-[var(--text-secondary)] tracking-wide">
          Liquidity Lens · Working-Capital Diagnostic · Built with Python, LangGraph, Claude &amp; Next.js
        </p>
      </footer>

      {/* SKU detail panel */}
      {status === "done" && data && (
        <AskWhyPanel skuCode={selectedSku} clusters={data.clusters} onClose={handleClosePanel} />
      )}
    </div>
  );
}
