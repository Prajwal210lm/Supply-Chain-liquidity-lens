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
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from backend.contract import prose_violations, render_prose
from backend.facts import (
    Cluster,
    ClusterMember,
    DiagnosisRun,
    SkuFacts,
    ValueAtStakeFacts,
)
from backend.graph import DiagnosisState, run_diagnosis
from backend.llm import get_client, resolve_model

app = FastAPI(title="Liquidity Lens")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Most recent DiagnosisRun, stored after each /api/diagnose call.
_last_run: DiagnosisRun | None = None

_CACHE_PATH = Path(__file__).parent.parent / "data" / "last_diagnosis.json"


# ── Cache reconstruction ──────────────────────────────────────────────────────

def _reconstruct_run_from_cache(cached: dict) -> DiagnosisRun:
    """Build a DiagnosisRun from the cached JSON so ask-why works without a live run.

    Uses only top_members (the 20 stored per cluster); ask-why 404s for SKUs
    outside the top 20, which is expected behaviour.
    """
    from analytics.ingest import REFERENCE_DATE  # noqa: PLC0415

    vas = ValueAtStakeFacts(**cached["value_at_stake"])
    clusters = []
    for c in cached["clusters"]:
        members = [
            ClusterMember(
                facts=SkuFacts(**m["facts"]),
                lever_contribution=float(m["lever_contribution"]),
                specifics=m["specifics"],
            )
            for m in c["top_members"]
        ]
        clusters.append(Cluster(
            cluster_id=c["cluster_id"],
            kind=c["kind"],
            lever=c["lever"],
            member_count=c["member_count"],
            lever_total=float(c["lever_total"]),
            members=members,
        ))
    return DiagnosisRun(
        run_id="cached",
        reference_date=REFERENCE_DATE,
        currency="AED",
        portfolio_value_at_stake=vas,
        clusters=clusters,
    )


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
def diagnose_endpoint(fresh: bool = Query(default=False)) -> dict:
    """Run the full six-node pipeline and return the board brief with supporting data.

    Pass ?fresh=true to force a live pipeline run even when a cached response exists.
    Without ?fresh=true, returns the cached response from data/last_diagnosis.json if present.
    """
    global _last_run

    if not fresh and _CACHE_PATH.exists():
        cached = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        _last_run = _reconstruct_run_from_cache(cached)
        return cached

    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    from analytics.ingest import REFERENCE_DATE

    engine = create_engine(database_url)
    state = run_diagnosis(engine, REFERENCE_DATE)
    _last_run = state["diagnosis_run"]

    response = jsonable_encoder(_build_response(state))
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    return response


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
