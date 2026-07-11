# Demo script (5 minutes)

Rehearse this 3 times before any interview. The goal is not to show every feature. The goal is to land three points: you found AED 21.2M at stake, the AI cannot fabricate a number, and you built it solo.

## Before you start

- Backend running: `uvicorn backend.api:app --reload --port 8000`
- Frontend running: `cd frontend && npm run dev`
- Browser open to `localhost:3000`
- Dashboard in idle state (have not clicked Run Diagnosis yet)

If you are screen-sharing, zoom the browser to 110-125% so text is readable.

## 0:00 - 0:30 | The problem (do not touch the screen yet)

"Large distributors in the GCC typically hold tens of millions in inventory across hundreds of SKUs. Cash gets trapped in slow-moving stock, pharma batches creep toward expiry, and fast movers stock out. The problem is not that nobody knows this happens. The problem is that by the time a manual review surfaces it, the financial damage is already done."

"I built a tool that reads raw inventory, sales, and supplier data and produces a board-ready value-at-stake assessment in minutes."

## 0:30 - 1:00 | Run the diagnosis

Click **Run Diagnosis**. It serves the cached result instantly.

"This ran against a portfolio of 600 SKUs with AED 106 million in on-hand inventory. Synthetic data, but the distribution and value profile are modelled on a real GCC distributor."

Point to the four summary cards as they appear.

"It flagged 280 SKUs with AED 21.2 million at stake. That breaks down into three categories."

## 1:00 - 2:00 | The three clusters (this is the value story)

Point to each cluster in the table as you describe it. Do not click into individual SKUs yet.

**Slow-moving excess (green card, AED 16.5M):** "The largest lever. 173 SKUs carrying 20 to 38 months of cover. All C-Z classification, low value, unpredictable demand. The root cause is supplier MOQs that deliver six to twelve months of stock per order for items that sell a few units a month. Every one of these is confirmed safe to release. Excess sits above the order-up-to level, so drawdown has zero service-level risk."

**Expiry risk (amber card, AED 281K):** "30 pharma SKUs with batches expiring within 27 to 45 days. FEFO enforcement gap. Without action, this converts directly to a P&L write-off."

**Stockout risk (red card, AED 4.4M):** "84 A-X items, high value, stable demand, below their reorder point. The tool explicitly excludes these from any release. You do not free up cash by stocking out your best sellers. This is a replenishment mandate, not a release opportunity."

Pause briefly. "Three action tracks, three different owners, running in parallel."

## 2:00 - 3:00 | The board brief

Scroll down to the Board Brief section.

"The tool generates a board-level memo. This is not a template with numbers dropped in. The AI layer diagnoses root causes per cluster, writes recommendations, and prioritises actions. But here is the important part."

Pause.

"Every number you see in this brief, every AED figure, came from the deterministic analytics core, not from the language model. The AI wrote the prose around placeholder references. A contract validator rejects any AI output that contains a bare digit. The LLM literally cannot put a number in the brief. It has to reference the tested computation."

## 3:00 - 4:00 | Architecture (only if the audience is technical)

If the interviewer is a partner or business-side, skip to 4:00. If they are technical or ask how it works:

"Two layers, strictly separated. A Python analytics core computes every metric: days of inventory, excess above order-up-to, FEFO expiry risk, stockout shortfall. All of that is tested against hand-verified fixtures, 88 automated tests."

"On top of that, a LangGraph state machine with six nodes runs through Claude. Validate the data, compute the diagnosis, attribute root causes, write recommendations, prioritise, and narrate the board brief. The AI reasons and writes. It never calculates."

"The contract validator sits between the two layers and enforces the boundary. If any LLM node produces a digit, even a correct one, the validator rejects it. Numbers enter the output only through placeholder paths that get rendered from the deterministic core."

## 4:00 - 4:30 | The violation bar (quick, builds credibility)

Point to the violations bar at the bottom.

"The tool even reports its own contract violations. There is one here: the expiry cluster has 20 members where safe-to-release is false because their stock is at or below the order-up-to level. The guardrail semantically applies to excess releases, not expiry write-offs. That is a known v2 refinement, documented, not hidden."

"I left this visible because in consulting, showing the client what the tool cannot do yet is as important as showing what it can."

## 4:30 - 5:00 | Close

"I built this solo, from data model to board brief, in about two weeks using Claude Code. The analytics core is hand-tested. The AI layer adds judgment without touching the math. And the output is at the level where you could put it in a Deloitte deck."

Stop talking. Let them ask questions.

## Common questions and answers

**"Is this real client data?"** No, synthetic. But the data generator plants realistic value stories: slow movers with high MOQs, near-expiry pharma, stockout-prone fast movers. The value distribution matches what you would see in a mid-sized GCC distributor.

**"Why not just use a BI tool?"** A BI tool shows you what the data says. This tells you what to do about it, in board-level language, with actions assigned to owners. The AI reasoning layer is what turns a dashboard into a diagnostic.

**"How long would this take to implement at a real client?"** The analytics core generalises immediately to any distributor with SKU-level inventory, sales, and supplier data. The AI layer needs prompt tuning per engagement. Realistic timeline for a pilot: 4-6 weeks with one data engineer and one consultant, assuming clean data feeds from SAP or Oracle.

**"What would you change for v2?"** Three things. First, the expiry guardrail needs refinement so the contract validator distinguishes between release actions and write-off actions. Second, I would add a supplier negotiation module that uses the MOQ-demand mismatch data to generate renegotiation briefs. Third, dynamic reorder points that update weekly instead of using static parameters.
