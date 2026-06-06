"""Contract validator — adversarial tests.

Every test constructs an object that COMMITS a violation and asserts the
validator rejects it. A validator that only ever sees clean input proves
nothing, so the bulk here is dirty input. Maps to violations V1-V14 plus the
placeholder render round-trip.
"""

from datetime import date

import pytest

from analytics.models import Sku
from backend.contract import (
    cluster_id_violations,
    confidence_violations,
    evidence_violations,
    guardrail_violations,
    prose_violations,
    ref_violations,
    render_prose,
    resolve_path,
    run_precondition_violations,
    validate_diagnosis,
)
from backend.nodes import compute

REF = date(2025, 6, 2)


def _run():
    # S1: excess (safe_to_release True). SR1: stockout (safe_to_release False).
    # VAS: releasable 20,000 ; write-off 0 ; stockout 126,000 ; total 146,000.
    portfolio = [
        Sku("S1", on_hand=900, avg_weekly_demand=70, unit_cost=50,
            target_coverage_days=50, lead_time_days=30),
        Sku("SR1", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
    ]
    return compute(portfolio, REF, run_id="c1")


# ── Path resolution ──────────────────────────────────────────────────────────
def test_resolve_path_valid_and_invalid():
    run = _run()
    assert resolve_path(run, "portfolio_value_at_stake.total") == pytest.approx(146_000.0)
    assert resolve_path(run, "clusters[0].lever_total") == pytest.approx(20_000.0)
    with pytest.raises(Exception):
        resolve_path(run, "clusters[9].lever_total")          # out of range
    with pytest.raises(Exception):
        resolve_path(run, "portfolio_value_at_stake.nope")    # bad attribute


# ── Prose violations (V1-V4) ─────────────────────────────────────────────────
def test_prose_rejects_bare_numeral():            # V1
    assert prose_violations("Cover is 44 months.", _run()) != []


def test_prose_rejects_literal_matching_a_real_fact():   # V2 — the key one
    run = _run()
    # 146,000 IS the true total; a correct literal is still rejected.
    assert prose_violations("We can release AED 146,000 today.", run) != []


def test_prose_rejects_formatted_numbers():        # V3
    run = _run()
    for bad in ["18.8M", "1,234.50", "12%", "2x"]:
        assert prose_violations(f"Impact is {bad}.", run) != [], bad


def test_prose_rejects_unresolvable_placeholder():  # V4
    assert prose_violations("Release {{clusters[9].lever_total}} now.", _run()) != []


def test_prose_accepts_placeholder_only():          # clean
    run = _run()
    assert prose_violations("Release AED {{portfolio_value_at_stake.total}} in cash.", run) == []


# ── Reference violations (V5-V8) ─────────────────────────────────────────────
def test_ref_rejects_bare_number():                # V5
    assert ref_violations(146_000, _run()) != []


def test_ref_rejects_number_as_string():           # V6
    assert ref_violations("146000", _run()) != []


def test_ref_rejects_smuggled_value_alongside_ref():   # V7
    run = _run()
    assert ref_violations({"ref": "portfolio_value_at_stake.total", "value": 146_000}, run) != []


def test_ref_rejects_dangling_path():              # V8
    assert ref_violations({"ref": "clusters[9].lever_total"}, _run()) != []


def test_ref_accepts_valid_reference():            # clean
    assert ref_violations({"ref": "portfolio_value_at_stake.total"}, _run()) == []


# ── Evidence (V9 + V8) ───────────────────────────────────────────────────────
def test_evidence_requires_at_least_one_citation():   # V9
    assert evidence_violations([], _run()) != []


def test_evidence_rejects_dangling_citation():     # V8 via evidence
    assert evidence_violations([{"ref": "nope.gone"}], _run()) != []


def test_evidence_accepts_valid():                 # clean
    assert evidence_violations([{"ref": "clusters[0].lever_total"}], _run()) == []


# ── Confidence (V10-V11) ─────────────────────────────────────────────────────
def test_confidence_rejects_percentage_or_number():   # V10
    run_pct = confidence_violations("85%")
    run_num = confidence_violations(0.9)
    assert run_pct != [] and run_num != []


def test_confidence_rejects_non_enum():            # V11
    assert confidence_violations("very high") != []
    assert confidence_violations("certain") != []


def test_confidence_accepts_enum():                # clean
    for good in ["high", "medium", "low"]:
        assert confidence_violations(good) == []


# ── Structural binding (V12) ─────────────────────────────────────────────────
def test_cluster_id_rejects_unknown():             # V12
    run = _run()
    assert cluster_id_violations("not_a_cluster", run) != []
    assert cluster_id_violations("slow_excess", run) == []


# ── Guardrail (V13) ──────────────────────────────────────────────────────────
def test_guardrail_rejects_unsafe_release():       # V13
    run = _run()
    assert guardrail_violations("SR1", run, excluded=False) != []   # stockout, unsafe
    assert guardrail_violations("SR1", run, excluded=True) == []    # excluded -> allowed
    assert guardrail_violations("S1", run, excluded=False) == []    # excess, safe


# ── Precondition: the run must reconcile (V14) ───────────────────────────────
def test_precondition_rejects_non_reconciling_run():   # V14
    run = _run()
    assert run_precondition_violations(run) == []
    # Drop a member but keep the stated lever_total -> reconciliation breaks.
    run.clusters[0].members = []
    assert run_precondition_violations(run) != []


# ── Placeholder render round-trip ────────────────────────────────────────────
def test_render_substitutes_placeholder_with_fact_value():
    run = _run()
    text = "Release AED {{portfolio_value_at_stake.total}} in cash."
    assert prose_violations(text, run) == []                       # valid before render
    assert render_prose(text, run) == "Release AED 146,000 in cash."  # value substituted


# ── Composed node validation: clean passes, dirty fails ──────────────────────
def test_validate_diagnosis_clean_passes():
    run = _run()
    clean = {
        "cluster_id": "slow_excess",
        "root_cause": "Stale safety-stock policy leaves cover far above target.",
        "confidence": "high",
        "rationale": "Cover greatly exceeds the order-up-to level; see cited fields.",
        "evidence": [{"ref": "clusters[0].lever_total"}],
    }
    assert validate_diagnosis(clean, run) == []


def test_validate_diagnosis_dirty_fails_on_multiple_counts():
    run = _run()
    dirty = {
        "cluster_id": "ghost_cluster",                         # V12
        "root_cause": "Cover is 44 months, way too high.",     # V1
        "confidence": "85%",                                   # V10
        "rationale": "Trust me.",
        "evidence": [],                                        # V9
    }
    violations = validate_diagnosis(dirty, run)
    assert len(violations) >= 4
