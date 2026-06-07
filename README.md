# Suppply Chain Liquidity Lens

AI-powered working-capital diagnostic for GCC FMCG/pharma distributors. Reads raw inventory, sales, and supplier data. Produces a consulting-grade value-at-stake assessment with a board-ready memo.

Built as a portfolio project for supply chain transformation and consulting roles.

## What it does

Analyses a portfolio of SKUs and identifies three categories of value at stake:

- **Releasable cash**: excess inventory above the order-up-to level, confirmed safe to release without service-level risk
- **Write-off exposure**: near-expiry batches requiring urgent triage
- **Stockout margin loss**: high-value items below reorder point, requiring replenishment (explicitly excluded from release)

Outputs a prioritised action plan with assigned owners and a board brief written by AI, where every number is traceable to the deterministic analytics core.

### Sample output (600-SKU synthetic portfolio)

| Risk cluster | Value at stake (AED) | SKUs |
|---|---|---|
| Slow-moving excess | 18,819,465 | 191 |
| Near-expiry pharma | 280,657 | 30 |
| Stockout risk | 4,419,582 | 84 |
| **Total** | **23,519,704** | **294** |

## Architecture

Two layers, strictly separated:

**Deterministic analytics core** (Python). Computes every number: DIO, months of cover, excess above order-up-to level, dead stock, FEFO expiry risk, stockout shortfall, ABC-XYZ classification, and value-at-stake rollup with overlap de-duplication. Tested against hand-verified fixtures. 84 automated tests.

**AI reasoning layer** (LangGraph + Claude). Six-node state machine: validate, compute, diagnose, recommend, prioritise, narrate. The LLM reasons about root causes, writes recommendations, and drafts the board brief. It never calculates. Every number enters the output through `{{path}}` placeholders that reference the deterministic core, enforced by a contract validator that rejects any AI output containing a bare digit.

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│  PostgreSQL  │───>│  Analytics   │───>│  LangGraph   │
│  (inventory, │    │  Core        │    │  Pipeline     │
│   sales,     │    │  (Python,    │    │  (6 nodes,    │
│   suppliers) │    │   tested)    │    │   Claude)     │
└─────────────┘    └─────────────┘    └──────┬───────┘
                                              │
                                     ┌────────▼───────┐
                                     │  Contract       │
                                     │  Validator      │
                                     │  (rejects bare  │
                                     │   digits in AI  │
                                     │   output)       │
                                     └────────┬───────┘
                                              │
                          ┌───────────────────▼──────────┐
                          │  FastAPI + Next.js Dashboard  │
                          │  Board brief, cluster tables, │
                          │  summary cards, SKU drill-down│
                          └──────────────────────────────┘
```

## Tech stack

- Python 3.13, FastAPI, PostgreSQL (Docker)
- LangGraph, Claude (Anthropic API)
- Next.js, Tailwind CSS
- 84 automated tests, 4 integration tests (skip-by-default)

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL)
- Anthropic API key

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/liquidity-lens.git
cd liquidity-lens

# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Environment

Create `.env` in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/liquidity_lens
```

### 3. Database

```bash
docker run -d --name ll-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=liquidity_lens \
  -p 5432:5432 postgres:16

# Run schema and seed data
python -m analytics.seed
```

### 4. Run

```bash
# Terminal 1: backend
uvicorn backend.api:app --reload --port 8000

# Terminal 2: frontend
cd frontend && npm run dev
```

Open `http://localhost:3000` and click **Run Diagnosis**.

The first run calls the full pipeline (requires API key and database). Subsequent runs serve the cached response from `data/last_diagnosis.json` unless you pass `?fresh=true`.

### 5. Tests

```bash
# All unit tests (no API key or database needed)
pytest tests/ -x

# Integration tests (requires API key)
pytest tests/ -x --run-integration
```

## Key design decisions

**The LLM never calculates.** Every figure in the board brief is produced by tested Python code. The contract validator mechanically enforces this, it is not a prompt instruction. This solves the trust problem with AI in consulting: a partner can trace any number from the board brief back to a hand-checked test fixture.

**Service-level guardrails.** Releasing excess cannot breach service levels because excess is defined as inventory above the order-up-to level (which incorporates lead time, review period, and demand variability). Stockout-risk SKUs are explicitly excluded from release actions.

**Overlap de-duplication.** A dead-stock SKU that is also excess is counted once in the value-at-stake rollup, not double-counted. This is tested with a dedicated overlap fixture.

**ABC-XYZ segmentation.** Standard classification by revenue contribution (ABC) and demand coefficient of variation (XYZ). Drives both the target coverage calculation and the cluster attribution.

## Project structure

```
liquidity-lens/
├── analytics/
│   ├── metrics.py       # Deterministic analytics core
│   ├── ingest.py        # Data ingestion from PostgreSQL
│   └── seed.py          # Synthetic data generator
├── backend/
│   ├── api.py           # FastAPI routes
│   ├── graph.py         # LangGraph state machine
│   ├── contract.py      # Contract validator
│   ├── facts.py         # Data classes (DiagnosisRun, Cluster, etc.)
│   └── llm.py           # Claude client wrapper
├── frontend/
│   ├── app/page.tsx     # Main dashboard
│   ├── components/      # React components
│   └── lib/api.ts       # API client
├── tests/               # 84 tests across 8 files
├── data/                # Cached pipeline responses
├── Context.md           # Project spec
├── CLAUDE.md            # Claude Code operating rules
└── .env                 # API key + database URL (gitignored)
```

## Known limitations

1. **Expiry guardrail**: 20 expiry-cluster members have `safe_to_release=false` because their stock is at or below the order-up-to level. The guardrail semantically applies to excess releases, not expiry write-offs. Documented, not hidden. V2 refinement.

2. **Spelled-out numbers**: The digit validator does not catch numbers written as words (e.g. "sixty-three thousand"). Mitigated by prompt design and required evidence references.

3. **Ask-why requires fresh run**: The SKU drill-down AI explanation only works after a live pipeline run, not from cached data.

## License

MIT
