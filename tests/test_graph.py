"""End-to-end graph test: all six nodes on a 2-SKU in-memory fixture.

LLM nodes receive mock clients via the ``_clients`` state key, so no real API
call is made. The canned responses are the same clean fixtures used by the
individual node tests — the graph's post-call validators should find zero
violations, and the board brief should render to concrete numbers.
"""

from datetime import date
from types import SimpleNamespace

from analytics.models import Sku
from backend.diagnose import DIAGNOSE_TOOL_NAME
from backend.graph import DiagnosisState, _build_graph
from backend.narrate import NARRATE_TOOL_NAME
from backend.prioritise import PRIORITISE_TOOL_NAME
from backend.recommend import RECOMMEND_TOOL_NAME

REF = date(2025, 6, 2)

PORTFOLIO = [
    Sku("S1", on_hand=900, avg_weekly_demand=70, unit_cost=50,
        target_coverage_days=50, lead_time_days=30),
    Sku("SR1", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
        target_coverage_days=100, lead_time_days=70),
]


# ── Canned model responses ────────────────────────────────────────────────────
# Bare-string evidence/refs — each node's wrapping step converts them to
# {"ref": path} before the contract validator sees them.

_DIAGNOSE_INPUT = {
    "diagnoses": [
        {
            "cluster_id": "slow_excess",
            "root_cause": "Stale safety-stock policy leaves cover far above target.",
            "confidence": "high",
            "rationale": "Releasable cash of {{clusters[0].lever_total}} is trapped in excess stock.",
            "evidence": ["clusters[0].lever_total", "clusters[0].members[0].facts.months_of_cover"],
        },
        {
            "cluster_id": "stockout",
            "root_cause": "Long supplier lead time drives structural stockout risk.",
            "confidence": "medium",
            "rationale": "Top movers run dry before resupply can arrive.",
            "evidence": ["clusters[2].members[0].facts.lead_time_days"],
        },
    ]
}

_RECOMMEND_INPUT = {
    "recommendations": [
        {
            "cluster_id": "slow_excess",
            "action": "Run targeted clearance to release trapped working capital.",
            "preconditions": "Confirm no committed orders before releasing stock.",
            "quantified_impact": "clusters[0].lever_total",
            "evidence": ["clusters[0].lever_total"],
        },
        {
            "cluster_id": "stockout",
            "action": "Expedite replenishment to protect service levels.",
            "preconditions": "Confirm supplier capacity before placing the order.",
            "quantified_impact": "clusters[2].lever_total",
            "evidence": ["clusters[2].members[0].facts.lead_time_days"],
        },
    ]
}

_PRIORITISE_INPUT = {
    "guardrail": "Stockout SKUs excluded from release to protect service levels.",
    "ranked": [
        {
            "rank": 1,
            "cluster_id": "slow_excess",
            "cash_impact": "clusters[0].lever_total",
            "feasibility_rationale": "Clearance via supplier return or markdown is straightforward.",
            "excluded_for_guardrail": False,
        },
        {
            "rank": 2,
            "cluster_id": "stockout",
            "cash_impact": "clusters[2].lever_total",
            "feasibility_rationale": "Cannot release; replenishment required to protect service.",
            "excluded_for_guardrail": True,
        },
    ],
}

_NARRATE_INPUT = {
    "headline": "Working capital: {{portfolio_value_at_stake.total}} at stake across the portfolio.",
    "body_markdown": (
        "## Working-capital diagnostic\n\n"
        "Total value at stake is {{portfolio_value_at_stake.total}}. The largest "
        "release opportunity is {{portfolio_value_at_stake.releasable_cash}} of cash "
        "trapped in slow-moving stock above target coverage. Separately, stockouts "
        "put {{portfolio_value_at_stake.stockout_margin_loss}} of margin at risk."
    ),
    "figures_cited": [
        "portfolio_value_at_stake.total",
        "portfolio_value_at_stake.releasable_cash",
        "portfolio_value_at_stake.stockout_margin_loss",
    ],
}

_INPUTS_BY_TOOL = {
    DIAGNOSE_TOOL_NAME: _DIAGNOSE_INPUT,
    RECOMMEND_TOOL_NAME: _RECOMMEND_INPUT,
    PRIORITISE_TOOL_NAME: _PRIORITISE_INPUT,
    NARRATE_TOOL_NAME: _NARRATE_INPUT,
}


# ── Router mock: dispatches by forced tool name ───────────────────────────────

class _RouterMessages:
    def create(self, **kwargs):
        tool_name = kwargs["tool_choice"]["name"]
        block = SimpleNamespace(type="tool_use", name=tool_name, input=_INPUTS_BY_TOOL[tool_name])
        return SimpleNamespace(content=[block])


class _RouterClient:
    def __init__(self):
        self.messages = _RouterMessages()


def _mock_clients():
    c = _RouterClient()
    return {"diagnose": c, "recommend": c, "prioritise": c, "narrate": c}


def _run_graph() -> DiagnosisState:
    return _build_graph().invoke({
        "portfolio": PORTFOLIO,
        "reference_date": REF,
        "violations": {},
        "_clients": _mock_clients(),
    })


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_graph_all_keys_populated():
    state = _run_graph()
    expected = {
        "quality_report", "diagnosis_run",
        "cluster_diagnoses", "recommendations", "release_plan",
        "board_brief", "board_brief_rendered", "violations",
    }
    assert expected.issubset(state.keys())


def test_graph_brief_is_rendered():
    state = _run_graph()
    rendered = state["board_brief_rendered"]

    assert "{{" not in rendered["headline"]        # all placeholders substituted
    assert "{{" not in rendered["body_markdown"]
    assert "146,000" in rendered["headline"]       # portfolio total at stake
    assert "20,000" in rendered["body_markdown"]   # releasable_cash
    assert "126,000" in rendered["body_markdown"]  # stockout_margin_loss


def test_graph_no_contract_violations():
    state = _run_graph()
    v = state["violations"]

    assert v.get("diagnose", []) == []
    assert v.get("recommend", []) == []
    assert v.get("prioritise", []) == []
    assert v.get("narrate", []) == []
