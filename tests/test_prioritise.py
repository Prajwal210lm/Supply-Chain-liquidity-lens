"""Prioritise node tests — deterministic mock + skip-by-default integration.
Includes the load-bearing guardrail check: a non-excluded stockout item is rejected.
"""

import copy
import os
from datetime import date
from types import SimpleNamespace

import pytest

from analytics.models import Sku
from backend.contract import validate_release_plan
from backend.nodes import compute
from backend.prioritise import PRIORITISE_TOOL_NAME, prioritise

REF = date(2025, 6, 2)


def _run():
    portfolio = [
        Sku("S1", on_hand=900, avg_weekly_demand=70, unit_cost=50,
            target_coverage_days=50, lead_time_days=30),
        Sku("SR1", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
    ]
    return compute(portfolio, REF, run_id="prio-test")


class _MockMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _MockClient:
    def __init__(self, response):
        self.messages = _MockMessages(response)


_CANNED = {
    "guardrail": "Only excess above the order-up-to level is released; stockout items are excluded.",
    "ranked": [
        {
            "rank": 1,
            "cluster_id": "slow_excess",
            "cash_impact": "clusters[0].lever_total",
            "feasibility_rationale": "Supplier returns and clearance are straightforward.",
            "excluded_for_guardrail": False,
        },
        {
            "rank": 2,
            "cluster_id": "stockout",
            "cash_impact": "clusters[2].lever_total",
            "feasibility_rationale": "Not a release — needs replenishment to protect sales.",
            "excluded_for_guardrail": True,
        },
    ],
}


def _mock_client():
    block = SimpleNamespace(type="tool_use", name=PRIORITISE_TOOL_NAME, input=_CANNED)
    return _MockClient(SimpleNamespace(content=[block]))


def test_prioritise_mock_wiring():
    run = _run()
    client = _mock_client()
    prioritise(run, recommendations=[], client=client, model="mock-model")

    call = client.messages.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": PRIORITISE_TOOL_NAME}
    assert call["tools"][0]["name"] == PRIORITISE_TOOL_NAME
    assert "RECOMMENDATIONS" in call["messages"][0]["content"]


def test_prioritise_mock_wraps_cash_impact_and_passes_validator():
    run = _run()
    plan = prioritise(run, recommendations=[], client=_mock_client(), model="mock-model")

    assert plan["ranked"][0]["cash_impact"] == {"ref": "clusters[0].lever_total"}
    assert validate_release_plan(plan, run) == []


def test_prioritise_guardrail_rejects_unexcluded_stockout():
    # Load-bearing: if the stockout item is NOT excluded, the guardrail must fire.
    run = _run()
    plan = prioritise(run, recommendations=[], client=_mock_client(), model="mock-model")
    assert validate_release_plan(plan, run) == []          # clean as-is

    breached = copy.deepcopy(plan)
    breached["ranked"][1]["excluded_for_guardrail"] = False  # stockout now ranked as a release
    violations = validate_release_plan(breached, run)
    assert violations != []
    assert any("guardrail" in v for v in violations)


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_prioritise_integration_real_api():
    from backend.diagnose import diagnose
    from backend.recommend import recommend

    run = _run()
    plan = prioritise(run, recommend(run, diagnose(run)))
    violations = validate_release_plan(plan, run)
    print(f"\nguardrail: {plan['guardrail']}")
    for item in plan["ranked"]:
        print(f"  #{item['rank']} {item['cluster_id']} "
              f"(excluded={item['excluded_for_guardrail']}) impact={item['cash_impact']['ref']}")
        print(f"      {item['feasibility_rationale']}")
    if violations:
        print(f"  !! VIOLATIONS: {violations}")
    assert violations == []
