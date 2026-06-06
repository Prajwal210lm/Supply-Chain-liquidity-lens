# Liquidity Lens

## One-line description

Liquidity Lens reads a distributor's raw inventory, sales, and supplier data and produces a consulting-grade working-capital diagnostic: where cash is trapped, why, what to release first, and the board memo to explain it.

---

## Vision

Most distributors in the GCC carry too much of the wrong inventory and too little of the right inventory at the same time. Cash sits dead on shelves while the business stocks out on fast movers. The diagnosis of this problem is well understood by consultants and almost never available to the operators themselves, because producing it takes a trained analyst two weeks of spreadsheet work per business unit.

Liquidity Lens compresses that diagnostic into minutes. It does not replace the planner. It produces the value-at-stake assessment a consulting team would deliver, denominated in cash, with every number traceable to auditable logic and the reasoning written in language a CFO and COO can act on.

The scope is deliberately narrow. One problem, working capital trapped in inventory, solved with defensible depth, rather than a broad operations platform solved shallowly.

---

## Why this exists (the consulting case)

**Business problem.** Distributors run on working capital. Cash tied up in inventory is cash not funding growth. In the GCC the structural conditions make it worse: long import lead times inflate safety stock, SKU proliferation buries cash in slow movers, and pharma distribution carries hard expiry write-offs.

**Financial impact.** A distributor with 90 days of inventory on hand and 15% excess or dead stock is sitting on a large, releasable cash position. Releasing it funds expansion without new debt. Expiry and obsolescence write-offs hit the P&L directly.

**Operational risk.** The same poor inventory posture that traps cash also causes stockouts on fast movers, eroding service levels and customer trust. Excess and shortage are two symptoms of one broken policy.

**Governance angle.** Inventory obsolescence, expiry exposure, and supplier concentration are reportable risks. The diagnostic surfaces them as a risk register, which connects the work to Risk and Transformation conversations without pretending to be a GRC tool.

**How a consulting firm sells this.** As a working-capital or inventory optimisation diagnostic: a fixed-scope engagement that quantifies value at stake and produces a prioritised release plan. It is a standard S&O offering across Deloitte, Kearney, and A&M in the region.

**Measurable impact.** Value at stake is reported as releasable cash from excess and dead stock, avoided expiry and obsolescence write-offs, and avoided stockout margin loss, each with a confidence band and a service-level guardrail.

---

## Target user and audience

**Primary user:** a working-capital, inventory, or supply-chain planning lead at a GCC distributor or family conglomerate. The person who has the data and is asked "why is so much cash in stock."

**Output audience:** the CFO and COO. The generated brief is written for them, not for analysts.

This is deliberately not "executives and the board" in the abstract. A named user with real data and a named decision-maker who reads the output.

---

## Product architecture

Three layers, kept strictly separated, because the separation is the defensibility.

**1. Deterministic analytics core (Python, no LLM).**
This computes every number. It is auditable, testable, and walkable line by line in an interview.
- Data ingestion and quality validation (missing fields, negative stock, stale records, unit mismatches).
- ABC-XYZ classification (value vs demand variability).
- Inventory health metrics: days inventory outstanding (DIO), cash conversion cycle inputs, coverage vs target.
- Excess detection: stock above target coverage given demand, lead time, and service-level target.
- Dead-stock detection: no movement over N periods.
- Expiry-risk detection (pharma): stock that will not sell before expiry at current velocity.
- Stockout-risk scoring: probability of stockout before next replenishment.
- Value-at-stake computation: releasable cash, write-off exposure, stockout margin loss.

**2. AI reasoning layer (LangGraph + Claude Opus 4.8).**
This reasons over the computed numbers. It never does arithmetic.
- Root-cause attribution for each flagged cluster (long lead time, lumpy demand, MOQ trap, stale safety-stock policy, supplier unreliability, over-ordering on promotion).
- Action recommendation, with the quantified impact pulled from the deterministic core.
- Prioritisation into a short, ranked release plan ordered by cash impact and feasibility.
- Board-brief generation in CFO and COO language.

**3. Interface (Next.js).**
- Inventory health overview and working-capital waterfall.
- Drill-down "ask why" on any flagged item, answered by the reasoning layer over the computed findings.
- Scenario toggles (change service-level target, watch value-at-stake recompute live).
- The generated board brief, exportable.

---

## AI agent architecture

A small, bounded LangGraph state machine. No knowledge graph. No vector database. No document RAG. Those were cut because the data here is structured, not a document corpus, and adding them would be decoration that an experienced reviewer spots immediately.

Nodes:

1. **Validate** — runs data-quality checks, attaches a quality report to state. (Knowing data is dirty is itself a consulting signal.)
2. **Compute** — calls the deterministic analytics core, attaches all metrics and flags to state. No LLM.
3. **Diagnose** — LLM node. Reads flagged clusters plus their features, attributes a root cause to each, with a confidence level.
4. **Recommend** — LLM node. Proposes an action per cluster, retrieves the quantified impact from the computed metrics in state.
5. **Prioritise** — synthesises actions into a ranked release plan by cash impact and feasibility, applies the service-level guardrail so no recommendation breaches the target.
6. **Narrate** — LLM node. Writes the board brief from the prioritised plan and value-at-stake totals.

The "ask why" drill-down is a separate lightweight conversational call scoped to a single flagged item and its computed context. It is grounded in the findings already in state, not a retrieval system.

Design principle enforced everywhere: the LLM reasons and writes; it does not calculate. Every figure in the brief is reproducible from the deterministic core.

---

## MVP scope (30-45 days)

In scope:
- Synthetic but realistic dataset: a few thousand SKUs across FMCG and pharma categories, with seasonality, promotions, lead-time variability, MOQs, and expiry dates. Built to contain a defensible value story.
- Full deterministic analytics core with tests.
- The six-node LangGraph diagnostic flow.
- Next.js dashboard: health overview, working-capital waterfall, drill-down, scenario toggles, board brief.
- An accompanying two-page case study structured as a Deloitte deliverable.

Explicitly out of scope (cut, not deferred-by-accident):
- Risk, governance, and operations modules.
- Knowledge graph, vector DB, document RAG.
- Real ERP connectors and live data feeds.
- Multi-tenant auth and user management.
- Cost-to-serve and customer-margin analytics (this is the named v2 extension).

---

## Technical stack

- **Reasoning orchestration:** LangGraph.
- **LLM:** Claude Opus 4.8 via the Anthropic API.
- **Analytics core:** Python, pandas, plus statsmodels or LightGBM for the demand baseline used in coverage calculations. Keep the forecasting method simple and explainable.
- **API:** FastAPI.
- **Database:** PostgreSQL.
- **Frontend:** Next.js.
- **Build environment:** Claude Code as the primary agentic environment, VS Code. Emergent optional for a first front-end scaffold only. Antigravity not used; three overlapping agentic builders fragment context for no gain.
- **Deployment:** Vercel for the frontend, a single container (Render, Railway, or Azure) for the API, or run locally for the demo. Do not spend MVP time on infrastructure.

---

## Roadmap

**Week 1: foundation and the defensible core.**
Data model in Postgres. Synthetic data generator that produces a believable distributor dataset with a built-in value story. Begin the deterministic analytics core. Write the case study problem statement in parallel.

**Week 2: finish and test the analytics core.**
Complete classification, health metrics, excess/dead/expiry/stockout detection, and value-at-stake computation. Write tests for every metric. This is the most important week; the numbers must be airtight because they are what gets questioned.

**Week 3: AI reasoning layer.**
Build the LangGraph flow: validate, compute, diagnose, recommend, prioritise, narrate. Tune the prompts so root-cause and recommendations are specific and grounded in the computed features.

**Week 4: interface.**
Next.js dashboard, drill-down, scenario toggles, board-brief export. Connect to the API.

**Week 5 (buffer and polish):**
Demo script, the five-minute walkthrough, finish the two-page case study, record a short demo video for networking and applications.

---

## What makes it win

The code is table stakes. The case study and the board brief are the product. Anyone can build a model. Few junior candidates can produce a deliverable that diagnoses a real operation, quantifies the value in cash, and explains it to a CFO. That document, paired with a working tool whose every number is auditable, is what turns a portfolio link into an interview.
