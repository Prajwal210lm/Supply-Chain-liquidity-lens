"""API shape tests — no real DB or LLM required.

The diagnose endpoint is tested by mocking run_diagnosis to return a
pre-built state built from the 2-SKU fixture, so the test proves the
serialization and response shape without touching the database or the
Anthropic API.
"""

from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from analytics.models import Sku
from backend.api import app
from backend.contract import render_prose
from backend.nodes import compute, validate

REF = date(2025, 6, 2)

PORTFOLIO = [
    Sku("S1", on_hand=900, avg_weekly_demand=70, unit_cost=50,
        target_coverage_days=50, lead_time_days=30),
    Sku("SR1", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
        target_coverage_days=100, lead_time_days=70),
]


def _mock_state():
    """Build a complete DiagnosisState from the 2-SKU fixture."""
    run = compute(PORTFOLIO, REF, run_id="api-test")
    qr = validate(PORTFOLIO, REF)
    brief = {
        "headline": "Working capital: {{portfolio_value_at_stake.total}} at stake.",
        "body_markdown": "Total at stake: {{portfolio_value_at_stake.total}}.",
        "figures_cited": [{"ref": "portfolio_value_at_stake.total"}],
    }
    return {
        "portfolio": PORTFOLIO,
        "reference_date": REF,
        "quality_report": qr,
        "diagnosis_run": run,
        "cluster_diagnoses": [],
        "recommendations": [],
        "release_plan": {
            "guardrail": "Stockout SKUs excluded.",
            "ranked": [
                {
                    "cluster_id": "slow_excess",
                    "cash_impact": {"ref": "clusters[0].lever_total"},
                    "feasibility_rationale": "Straightforward clearance.",
                    "excluded_for_guardrail": False,
                }
            ],
        },
        "board_brief": brief,
        "board_brief_rendered": {
            "headline": render_prose(brief["headline"], run),
            "body_markdown": render_prose(brief["body_markdown"], run),
        },
        "violations": {"diagnose": [], "recommend": [], "prioritise": [], "narrate": []},
    }


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_cache_path(tmp_path, monkeypatch):
    """Redirect the on-disk diagnosis cache to a temp file for every test in this
    module, so a fresh-run test never overwrites the real data/last_diagnosis.json
    (a git-tracked demo artifact)."""
    import backend.api as api_module

    monkeypatch.setattr(api_module, "_CACHE_PATH", tmp_path / "last_diagnosis.json")


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── Diagnose shape ────────────────────────────────────────────────────────────

def test_diagnose_response_shape():
    with patch("backend.api.run_diagnosis", return_value=_mock_state()):
        r = client.post("/api/diagnose?fresh=true")

    assert r.status_code == 200
    body = r.json()

    # Top-level keys
    assert set(body.keys()) >= {"brief", "value_at_stake", "clusters", "quality_report", "violations"}

    # Brief is rendered (no placeholders)
    assert "{{" not in body["brief"]["headline"]
    assert "{{" not in body["brief"]["body_markdown"]
    assert "146,000" in body["brief"]["headline"]

    # Value-at-stake totals
    vas = body["value_at_stake"]
    assert set(vas.keys()) >= {"releasable_cash", "write_off_exposure", "stockout_margin_loss", "total"}
    assert vas["total"] == pytest.approx(146_000.0)

    # Clusters: three always created, each has expected shape
    assert len(body["clusters"]) == 3
    cluster = body["clusters"][0]
    assert set(cluster.keys()) >= {"cluster_id", "kind", "lever", "lever_total", "member_count", "top_members"}

    # top_members have facts and lever_contribution
    assert len(cluster["top_members"]) >= 1
    member = cluster["top_members"][0]
    assert set(member.keys()) >= {"sku_code", "lever_contribution", "facts", "specifics"}

    # Violations dict present with all four LLM node keys
    v = body["violations"]
    assert set(v.keys()) >= {"diagnose", "recommend", "prioritise", "narrate"}


# ── Ask-why: 404 only when the cache is genuinely absent ─────────────────────

def test_ask_why_404_without_prior_diagnose_or_cache():
    """No in-memory run AND no on-disk cache (isolate_cache_path points at an
    empty tmp_path) -> _get_or_load_run() has nothing to fall back to -> 404."""
    import backend.api as api_module
    original = api_module._last_run
    api_module._last_run = None
    try:
        assert not api_module._CACHE_PATH.exists()
        r = client.post("/api/ask-why/S1")
        assert r.status_code == 404
        assert "diagnose" in r.json()["detail"]
    finally:
        api_module._last_run = original


def test_ask_why_succeeds_from_cache_alone():
    """No in-memory run, but a cached diagnosis exists on disk -> ask-why lazily
    reconstructs the run from the cache and answers without a live pipeline run."""
    import json
    from types import SimpleNamespace

    import backend.api as api_module

    state = _mock_state()
    cached_body = api_module._build_response(state)
    api_module._CACHE_PATH.write_text(json.dumps(cached_body, default=str), encoding="utf-8")

    original = api_module._last_run
    api_module._last_run = None

    mock_text = "SKU S is carrying {{clusters[0].members[0].facts.months_of_cover}} months of cover."

    class _MockMessages:
        def create(self, **kwargs):
            block = SimpleNamespace(type="text", text=mock_text)
            return SimpleNamespace(content=[block])

    class _MockClient:
        def __init__(self):
            self.messages = _MockMessages()

    try:
        with patch("backend.api.get_client", return_value=_MockClient()):
            r = client.post("/api/ask-why/S1")
        assert r.status_code == 200
        body = r.json()
        assert body["sku_code"] == "S1"
        assert body["violations"] == []
        assert "{{" not in body["explanation"]
        # Confirm the run really came from the cache, not a live run.
        assert api_module._last_run is not None
        assert api_module._last_run.run_id == "cached"
    finally:
        api_module._last_run = original


# ── Ask-why: returns expected shape given a seeded run ───────────────────────

def test_ask_why_shape():
    import backend.api as api_module
    from types import SimpleNamespace

    state = _mock_state()
    run = state["diagnosis_run"]
    api_module._last_run = run

    # Mock the LLM call inside _explain_sku to return prose with a valid placeholder.
    mock_text = "SKU S is carrying {{clusters[0].members[0].facts.months_of_cover}} months of cover."

    class _MockMessages:
        def create(self, **kwargs):
            block = SimpleNamespace(type="text", text=mock_text)
            return SimpleNamespace(content=[block])

    class _MockClient:
        def __init__(self):
            self.messages = _MockMessages()

    try:
        with patch("backend.api.get_client", return_value=_MockClient()):
            r = client.post("/api/ask-why/S1")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) >= {"sku_code", "explanation", "cluster_memberships", "violations"}
        assert body["sku_code"] == "S1"
        assert body["violations"] == []
        assert "{{" not in body["explanation"]          # placeholders rendered
        assert "cluster_memberships" in body
        assert "slow_excess" in body["cluster_memberships"]
    finally:
        api_module._last_run = None


# ── Ask-why: fails CLOSED on a contract violation ─────────────────────────────

def test_ask_why_withholds_explanation_on_contract_violation():
    """If the model's prose contains a bare digit (or any other contract
    violation), the raw text must never reach the response — `explanation`
    is withheld (empty) and `violations` is non-empty. This is the one place
    a fabricated/unverifiable number could otherwise reach the screen."""
    import backend.api as api_module
    from types import SimpleNamespace

    state = _mock_state()
    run = state["diagnosis_run"]
    api_module._last_run = run

    # A bare digit outside any {{...}} placeholder — an unambiguous violation.
    fabricated_text = "SKU S is carrying 32 months of cover, well above target."

    class _MockMessages:
        def create(self, **kwargs):
            block = SimpleNamespace(type="text", text=fabricated_text)
            return SimpleNamespace(content=[block])

    class _MockClient:
        def __init__(self):
            self.messages = _MockMessages()

    try:
        with patch("backend.api.get_client", return_value=_MockClient()):
            r = client.post("/api/ask-why/S1")
        assert r.status_code == 200
        body = r.json()
        assert body["violations"] != []
        assert body["explanation"] == ""
        # The fabricated text must not leak into the response anywhere.
        assert "32" not in body["explanation"]
    finally:
        api_module._last_run = None
