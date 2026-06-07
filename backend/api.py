"""FastAPI routes for Liquidity Lens.

Three endpoints:
  GET  /api/health               — liveness probe
  POST /api/diagnose             — run the full six-node pipeline, return board brief
  POST /api/ask-why/{sku_code}   — lightweight drill-down on a single flagged SKU

The most recently computed DiagnosisRun is kept in app state so ask-why can
resolve fact paths without re-running the pipeline.
"""
from __future__ import annotations

import dataclasses
import os
from dataclasses import asdict
from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder

from backend.contract import prose_violations, render_prose
from backend.facts import DiagnosisRun
from backend.graph import DiagnosisState, run_diagnosis
from backend.llm import get_client, resolve_model

app = FastAPI(title="Liquidity Lens")

# Most recent DiagnosisRun, stored after each /api/diagnose call.
_last_run: DiagnosisRun | None = None


# ── Serialization helpers ─────────────────────────────────────────────────────

def _serialize_member(member, max_members: int = 20) -> dict:
    return {
        "sku_code": member.facts.sku_code,
        "lever_contribution": member.lever_contribution,
        "facts": asdict(member.facts),
        "specifics": member.specifics,
    }


def _serialize_cluster(cluster, max_members: int = 20) -> dict:
    return {
        "cluster_id": cluster.cluster_id,
        "kind": cluster.kind,
        "lever": cluster.lever,
        "lever_total": cluster.lever_total,
        "member_count": cluster.member_count,
        "top_members": [_serialize_member(m) for m in cluster.members[:max_members]],
    }


def _build_response(state: DiagnosisState) -> dict:
    run = state["diagnosis_run"]
    qr = state["quality_report"]
    rendered = state.get("board_brief_rendered", {})
    violations = state.get("violations", {})

    return {
        "brief": rendered,
        "value_at_stake": asdict(run.portfolio_value_at_stake),
        "clusters": [_serialize_cluster(c) for c in run.clusters],
        "quality_report": asdict(qr),
        "violations": violations,
    }


# ── ask-why helpers ───────────────────────────────────────────────────────────

_ASK_WHY_SYSTEM = """\
You are explaining a flagged inventory item to a CFO. Write one short paragraph
(three to five sentences) in plain business English.

ABSOLUTE RULE: every number must be a {{path}} placeholder — never type a digit
(0-9) anywhere in your response. Use ONLY the fact paths listed in the context
provided. Write plain prose — no headings, no bullet points, no tool calls."""


def _ask_why_context(run: DiagnosisRun, sku_code: str) -> tuple[str, list[str]]:
    """Build the prompt context for the given SKU and return (context_text, cluster_ids)."""
    memberships: list[tuple[int, int, object]] = []
    for ci, cluster in enumerate(run.clusters):
        for mi, member in enumerate(cluster.members):
            if member.facts.sku_code == sku_code:
                memberships.append((ci, mi, cluster))

    if not memberships:
        raise ValueError(f"SKU {sku_code!r} not found in any cluster")

    lines = [f'Fact paths for SKU "{sku_code}":']
    cluster_ids = []
    for ci, mi, cluster in memberships:
        base = f"clusters[{ci}].members[{mi}]"
        cluster_ids.append(cluster.cluster_id)
        lines.append(f"\n{cluster.kind} cluster (clusters[{ci}]):")
        for fname in (
            "months_of_cover",
            "target_coverage_days",
            "on_hand_units",
            "lead_time_days",
            "unit_cost",
            "inventory_value",
        ):
            lines.append(f"  {fname:<30} → {base}.facts.{fname}")
        lines.append(f"  {'lever_contribution':<30} → {base}.lever_contribution")
        lines.append(f"  {'cluster lever_total':<30} → clusters[{ci}].lever_total")

    lines.append("\nPortfolio paths:")
    lines.append("  portfolio_value_at_stake.total")
    lines.append("  portfolio_value_at_stake.releasable_cash")
    lines.append("  portfolio_value_at_stake.write_off_exposure")
    lines.append("  portfolio_value_at_stake.stockout_margin_loss")

    return "\n".join(lines), cluster_ids


def _explain_sku(
    sku_code: str,
    run: DiagnosisRun,
    *,
    client: Any = None,
    model: str | None = None,
) -> tuple[str, list[str]]:
    """Call Claude to explain a single SKU. Returns (rendered_explanation, violations)."""
    try:
        path_context, cluster_ids = _ask_why_context(run, sku_code)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    user_msg = (
        f"{path_context}\n\n"
        f"Explain in plain English why SKU \"{sku_code}\" is flagged "
        f"and what the recommended action is."
    )

    if client is None:
        client = get_client()

    response = client.messages.create(
        model=resolve_model(model),
        max_tokens=1000,
        system=_ASK_WHY_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    violations = prose_violations(text, run)
    rendered = render_prose(text, run) if not violations else text
    return rendered, violations, cluster_ids


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/diagnose")
def diagnose_endpoint() -> dict:
    """Run the full six-node pipeline and return the board brief with supporting data."""
    global _last_run

    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    engine = create_engine(database_url)
    state = run_diagnosis(engine, date.today())
    _last_run = state["diagnosis_run"]

    return jsonable_encoder(_build_response(state))


@app.post("/api/ask-why/{sku_code}")
def ask_why(sku_code: str) -> dict:
    """Explain a single flagged SKU in plain English using the most recent run."""
    if _last_run is None:
        raise HTTPException(
            status_code=404,
            detail="No diagnosis run available; call POST /api/diagnose first.",
        )

    explanation, violations, cluster_ids = _explain_sku(sku_code, _last_run)
    return {
        "sku_code": sku_code,
        "explanation": explanation,
        "cluster_memberships": cluster_ids,
        "violations": violations,
    }
