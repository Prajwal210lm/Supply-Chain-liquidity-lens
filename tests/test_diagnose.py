"""Diagnose node tests.

(a) test_diagnose_mock_* — deterministic, no network. Mocks the Anthropic client,
    returns a canned tool-call response with BARE-STRING evidence, and asserts the
    node's output passes the contract validator. Since the validator rejects
    bare-string evidence, a passing result proves the node wrapped each path into
    {"ref": path}. Also asserts the wiring (forced tool choice, FACTS in the user
    message) and that removing the wrapping would fail.

(b) test_diagnose_integration_* — hits the real API, marked `integration` and
    skipped by default (and skipped without an API key). Runs the live output
    through the validator and prints the reasoning for human review.
"""

import os
from datetime import date
from types import SimpleNamespace

import pytest

from analytics.models import Sku
from backend.contract import validate_diagnosis
from backend.diagnose import DIAGNOSE_TOOL_NAME, diagnose
from backend.nodes import compute

REF = date(2025, 6, 2)


def _run():
    # S1 -> slow_excess (releasable 20,000); SR1 -> stockout (loss 126,000).
    # expiry cluster exists but is empty, so clusters[2] is stockout in the full run.
    portfolio = [
        Sku("S1", on_hand=900, avg_weekly_demand=70, unit_cost=50,
            target_coverage_days=50, lead_time_days=30),
        Sku("SR1", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
    ]
    return compute(portfolio, REF, run_id="diag-test")


# ── Mock client that records calls and returns a canned response ─────────────
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


# Canned model output — evidence is BARE STRINGS, exactly as the tool schema yields.
_CANNED = {
    "diagnoses": [
        {
            "cluster_id": "slow_excess",
            "root_cause": "Stale safety-stock policy leaves cover far above target on slow movers.",
            "confidence": "high",
            "rationale": (
                "Releasable cash of AED {{clusters[0].lever_total}} is trapped in stock whose "
                "months of cover far exceed the order-up-to level."
            ),
            "evidence": [
                "clusters[0].lever_total",
                "clusters[0].members[0].facts.months_of_cover",
            ],
        },
        {
            "cluster_id": "stockout",
            "root_cause": "Structural stockout driven by a long supplier lead time.",
            "confidence": "medium",
            "rationale": "Top movers run dry well before a replenishment order can arrive.",
            "evidence": ["clusters[2].members[0].facts.lead_time_days"],
        },
    ]
}


def _mock_client():
    block = SimpleNamespace(type="tool_use", name=DIAGNOSE_TOOL_NAME, input=_CANNED)
    response = SimpleNamespace(content=[block])
    return _MockClient(response)


def test_diagnose_mock_wiring_uses_forced_tool_and_facts():
    run = _run()
    client = _mock_client()

    diagnose(run, client=client, model="mock-model")

    call = client.messages.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": DIAGNOSE_TOOL_NAME}
    assert call["tools"][0]["name"] == DIAGNOSE_TOOL_NAME
    assert call["model"] == "mock-model"
    user_text = call["messages"][0]["content"]
    assert "showing top" in user_text            # the "top N of M" sample disclosure
    assert "slow_excess" in user_text            # FACTS were serialized into the prompt


def test_diagnose_mock_wraps_evidence_and_passes_validator():
    run = _run()
    payloads = diagnose(run, client=_mock_client(), model="mock-model")

    assert len(payloads) == 2

    # Wrapping occurred: bare strings became {"ref": path} dicts.
    assert payloads[0]["evidence"] == [
        {"ref": "clusters[0].lever_total"},
        {"ref": "clusters[0].members[0].facts.months_of_cover"},
    ]
    assert all(
        isinstance(e, dict) and set(e) == {"ref"}
        for p in payloads for e in p["evidence"]
    )

    # Every payload passes the contract validator. This only holds because the
    # node wrapped the evidence — the validator rejects bare-string references.
    for p in payloads:
        assert validate_diagnosis(p, run) == []


def test_diagnose_mock_unwrapped_evidence_would_fail_validator():
    # Proves the wrapping is load-bearing: feed the validator the RAW bare-string
    # evidence and it must reject it. If someone drops the wrapping in the node,
    # the test above flips to failing for exactly this reason.
    run = _run()
    unwrapped = {
        "cluster_id": "slow_excess",
        "root_cause": "Stale safety-stock policy.",
        "confidence": "high",
        "rationale": "Cover far exceeds target.",
        "evidence": ["clusters[0].lever_total"],   # bare string, not {"ref": ...}
    }
    assert validate_diagnosis(unwrapped, run) != []


# ── (b) Integration: real API, skipped by default ────────────────────────────
@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_diagnose_integration_real_api():
    run = _run()
    payloads = diagnose(run)  # real client; model from LIQUIDITY_LENS_MODEL or default

    assert payloads, "expected at least one diagnosis from the model"
    for p in payloads:
        violations = validate_diagnosis(p, run)
        print(f"\n[{p['cluster_id']}]  confidence={p['confidence']}")
        print(f"  root cause: {p['root_cause']}")
        print(f"  rationale : {p['rationale']}")
        print(f"  evidence  : {[e['ref'] for e in p['evidence']]}")
        if violations:
            print(f"  !! CONTRACT VIOLATIONS: {violations}")
        assert violations == [], f"{p['cluster_id']} violated the contract: {violations}"
