"""Recommend node tests — deterministic mock + skip-by-default integration."""

import os
from datetime import date
from types import SimpleNamespace

import pytest

from analytics.models import Sku
from backend.contract import validate_recommendation
from backend.nodes import compute
from backend.recommend import RECOMMEND_TOOL_NAME, recommend

REF = date(2025, 6, 2)


def _run():
    portfolio = [
        Sku("S1", on_hand=900, avg_weekly_demand=70, unit_cost=50,
            target_coverage_days=50, lead_time_days=30),
        Sku("SR1", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
    ]
    return compute(portfolio, REF, run_id="rec-test")


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
    "recommendations": [
        {
            "cluster_id": "slow_excess",
            "action": "Return slow movers to suppliers and liquidate the rest to free {{clusters[0].lever_total}}.",
            "quantified_impact": "clusters[0].lever_total",
            "preconditions": "Supplier return windows and a clearance channel.",
            "evidence": ["clusters[0].lever_total", "clusters[0].members[0].facts.months_of_cover"],
        },
        {
            "cluster_id": "stockout",
            "action": "Expedite and dual-source the fast movers to protect sales.",
            "quantified_impact": "clusters[2].lever_total",
            "preconditions": "Air-freight budget; qualify a secondary supplier.",
            "evidence": ["clusters[2].members[0].facts.lead_time_days"],
        },
    ]
}


def _mock_client():
    block = SimpleNamespace(type="tool_use", name=RECOMMEND_TOOL_NAME, input=_CANNED)
    return _MockClient(SimpleNamespace(content=[block]))


def test_recommend_mock_wiring():
    run = _run()
    client = _mock_client()
    recommend(run, diagnoses=[], client=client, model="mock-model")

    call = client.messages.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": RECOMMEND_TOOL_NAME}
    assert call["tools"][0]["name"] == RECOMMEND_TOOL_NAME
    assert "RECOMMENDATIONS" not in call["messages"][0]["content"]  # input is DIAGNOSES, not its own output
    assert "DIAGNOSES" in call["messages"][0]["content"]


def test_recommend_mock_wraps_refs_and_passes_validator():
    run = _run()
    payloads = recommend(run, diagnoses=[], client=_mock_client(), model="mock-model")

    assert len(payloads) == 2
    # quantified_impact and evidence wrapped into {"ref": path}.
    assert payloads[0]["quantified_impact"] == {"ref": "clusters[0].lever_total"}
    assert payloads[0]["evidence"][0] == {"ref": "clusters[0].lever_total"}
    for p in payloads:
        assert validate_recommendation(p, run) == []


def test_recommend_mock_unwrapped_impact_would_fail_validator():
    # Load-bearing: a bare-string quantified_impact must be rejected.
    run = _run()
    unwrapped = {
        "cluster_id": "slow_excess",
        "action": "Return and liquidate.",
        "quantified_impact": "clusters[0].lever_total",   # bare string, not {"ref": ...}
        "preconditions": "None.",
        "evidence": ["clusters[0].lever_total"],
    }
    assert validate_recommendation(unwrapped, run) != []


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_recommend_integration_real_api():
    from backend.diagnose import diagnose

    run = _run()
    diagnoses = diagnose(run)
    payloads = recommend(run, diagnoses)
    assert payloads
    for p in payloads:
        violations = validate_recommendation(p, run)
        print(f"\n[{p['cluster_id']}] {p['action']}")
        print(f"  impact ref: {p['quantified_impact']['ref']}")
        print(f"  evidence  : {[e['ref'] for e in p['evidence']]}")
        if violations:
            print(f"  !! VIOLATIONS: {violations}")
        assert violations == []
