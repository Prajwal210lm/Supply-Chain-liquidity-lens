"""LangGraph state machine: validate → compute → diagnose → recommend →
prioritise → narrate.

Each LLM node's output is validated against the contract after the call.
Violations are accumulated into state but do not abort the pipeline — a
degraded-but-complete brief is always returned. render_prose runs only after
validation passes, since it is not safe for unresolvable placeholders.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import TypedDict

from langgraph.graph import END, StateGraph

from analytics.models import Sku
from backend.contract import (
    render_prose,
    validate_diagnosis,
    validate_narrative,
    validate_recommendation,
    validate_release_plan,
)
from backend.diagnose import diagnose as _diagnose
from backend.facts import DiagnosisRun, QualityReport
from backend.narrate import narrate as _narrate
from backend.nodes import compute as _compute
from backend.nodes import validate as _validate
from backend.prioritise import prioritise as _prioritise
from backend.recommend import recommend as _recommend


class DiagnosisState(TypedDict, total=False):
    # ── Inputs ───────────────────────────────────────────────────────────────
    portfolio: list[Sku]
    reference_date: date

    # ── Deterministic node outputs ────────────────────────────────────────────
    quality_report: QualityReport
    diagnosis_run: DiagnosisRun

    # ── LLM node outputs ({{path}} placeholders intact) ───────────────────────
    cluster_diagnoses: list[dict]
    recommendations: list[dict]
    release_plan: dict
    board_brief: dict                   # raw (model-written placeholders)

    # ── Post-render output ────────────────────────────────────────────────────
    board_brief_rendered: dict          # {"headline": str, "body_markdown": str}

    # ── Contract violations per LLM node ─────────────────────────────────────
    violations: dict[str, list[str]]    # {"diagnose": [...], "recommend": [...], ...}

    # ── Test injection only (never set in production) ─────────────────────────
    _clients: dict                      # {"diagnose": client, "recommend": client, ...}


# ── Node wrappers ─────────────────────────────────────────────────────────────

def _node_validate(state: DiagnosisState) -> dict:
    return {"quality_report": _validate(state["portfolio"], state["reference_date"])}


def _node_compute(state: DiagnosisState) -> dict:
    run = _compute(
        state["portfolio"],
        state["reference_date"],
        run_id=str(uuid.uuid4())[:8],
    )
    return {"diagnosis_run": run}


def _node_diagnose(state: DiagnosisState) -> dict:
    run = state["diagnosis_run"]
    client = (state.get("_clients") or {}).get("diagnose")
    payloads = _diagnose(run, client=client)
    v = [err for p in payloads for err in validate_diagnosis(p, run)]
    return {
        "cluster_diagnoses": payloads,
        "violations": {**(state.get("violations") or {}), "diagnose": v},
    }


def _node_recommend(state: DiagnosisState) -> dict:
    run = state["diagnosis_run"]
    client = (state.get("_clients") or {}).get("recommend")
    payloads = _recommend(run, state["cluster_diagnoses"], client=client)
    v = [err for p in payloads for err in validate_recommendation(p, run)]
    return {
        "recommendations": payloads,
        "violations": {**(state.get("violations") or {}), "recommend": v},
    }


def _node_prioritise(state: DiagnosisState) -> dict:
    run = state["diagnosis_run"]
    client = (state.get("_clients") or {}).get("prioritise")
    plan = _prioritise(run, state["recommendations"], client=client)
    return {
        "release_plan": plan,
        "violations": {
            **(state.get("violations") or {}),
            "prioritise": validate_release_plan(plan, run),
        },
    }


def _node_narrate(state: DiagnosisState) -> dict:
    run = state["diagnosis_run"]
    client = (state.get("_clients") or {}).get("narrate")
    brief = _narrate(run, state["release_plan"], client=client)
    v = validate_narrative(brief, run)
    rendered = (
        {
            "headline": render_prose(brief["headline"], run),
            "body_markdown": render_prose(brief["body_markdown"], run),
        }
        if not v
        else {"headline": brief["headline"], "body_markdown": brief["body_markdown"]}
    )
    return {
        "board_brief": brief,
        "board_brief_rendered": rendered,
        "violations": {**(state.get("violations") or {}), "narrate": v},
    }


# ── Graph construction ────────────────────────────────────────────────────────

def _build_graph():
    builder = StateGraph(DiagnosisState)
    builder.add_sequence([
        ("validate", _node_validate),
        ("compute", _node_compute),
        ("diagnose", _node_diagnose),
        ("recommend", _node_recommend),
        ("prioritise", _node_prioritise),
        ("narrate", _node_narrate),
    ])
    builder.set_entry_point("validate")
    builder.set_finish_point("narrate")
    return builder.compile()


_GRAPH = None


def _get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _build_graph()
    return _GRAPH


def run_diagnosis(engine, reference_date: date) -> DiagnosisState:
    """Load portfolio from the DB and run the full six-node pipeline."""
    from analytics.ingest import load_portfolio
    portfolio = load_portfolio(engine, reference_date)
    return _get_graph().invoke({
        "portfolio": portfolio,
        "reference_date": reference_date,
        "violations": {},
    })
