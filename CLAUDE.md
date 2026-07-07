# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Liquidity Lens is a working-capital diagnostic tool for GCC distributors. It reads raw inventory, sales, and supplier data and produces a consulting-grade output: where cash is trapped, why, what to release first, and a board memo explaining it.

## Planned directory structure

```
liquidity-lens/
├── frontend/        # Next.js dashboard
├── backend/         # FastAPI server
├── analytics/       # Deterministic Python core (no LLM)
├── data/            # Synthetic dataset generator
├── tests/           # Test suite (analytics core is most critical)
├── docs/            # Two-page case study (Deloitte-style deliverable)
└── scripts/         # Demo and utility scripts
```

## Commands

### Python (analytics + backend)
```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run a single test file
pytest tests/path/to/test_file.py

# Lint
ruff check .
ruff format .
```

### Next.js (frontend)
```bash
cd frontend
npm install
npm run dev        # development server
npm run build      # production build
```

## Architecture

Three strictly separated layers — the separation is the defensibility.

### 1. Deterministic analytics core (`analytics/`)
Python only, **no LLM**. Computes every number that appears anywhere in the output. Must be fully auditable and testable.

Responsibilities:
- Data ingestion and quality validation
- ABC-XYZ classification (value vs demand variability)
- Inventory health metrics: DIO, coverage vs target
- Excess detection (stock above target coverage)
- Dead-stock detection (no movement over N periods)
- Expiry-risk detection for pharma SKUs
- Stockout-risk scoring
- Value-at-stake computation: releasable cash, write-off exposure, stockout margin loss

Forecasting: statsmodels or LightGBM for the demand baseline. Keep the method simple and explainable.

### 2. AI reasoning layer (`backend/`, LangGraph)
Reasons over the computed numbers. **Never does arithmetic.** Uses Claude Opus 4.8 via the Anthropic API.

Six-node LangGraph state machine:
1. **Validate** — data quality checks, attaches quality report to state
2. **Compute** — calls the deterministic core, attaches all metrics/flags to state (no LLM)
3. **Diagnose** — LLM: attributes root cause to each flagged cluster (long lead time, MOQ trap, lumpy demand, stale safety-stock policy, etc.)
4. **Recommend** — LLM: proposes action per cluster, pulling quantified impact from computed metrics in state
5. **Prioritise** — LLM: synthesises into a ranked release plan ordered by cash impact and feasibility; applies service-level guardrail
6. **Narrate** — LLM: writes the board brief from the prioritised plan and value-at-stake totals

The "ask why" drill-down is a separate lightweight conversational call scoped to a single flagged item and its computed context — not a retrieval system.

### 3. Interface (`frontend/`, Next.js)
- Inventory health overview and working-capital waterfall
- Drill-down "ask why" on flagged items (calls reasoning layer)
- Scenario toggles with live recomputation
- Exportable board brief

### Database
PostgreSQL. The data model lives here; the synthetic generator populates it.

## Critical design principle

**The LLM reasons and writes; it does not calculate.** Every figure in the board brief must be reproducible from the deterministic core. This principle must be enforced in every node, every prompt, and every API boundary.

No knowledge graph, vector DB, or document RAG — the data is structured, not a document corpus, and those additions would be decoration.

## Out of scope for MVP

Do not add: risk/governance/operations modules, ERP connectors, multi-tenant auth, cost-to-serve analytics, or infrastructure beyond local/single-container demo.

## Source of truth

Context.md is the full project specification and the single source of truth.
This file is the operating summary. If scope or architecture changes, update
Context.md first, then reconcile this file. The two must always agree.

## How to work in this repo

- Before writing code, propose a short plan and wait for my approval. Do not
  edit files until I approve the approach.
- Build in this fixed order. Do not work ahead:
  1. Database schema and synthetic data
  2. Analytics core, with a passing test for every metric
  3. LangGraph reasoning layer
  4. FastAPI routes
  5. Next.js frontend
  6. Case study and demo
- The analytics core must have a passing test for every metric before we move
  past it. No exceptions.
- After each working step, stop and commit.
- Keep changes small. After making changes, explain what you did in plain English.
- If a request would expand scope beyond Context.md or the "Out of scope" list,
  stop and flag it. Do not build it.
