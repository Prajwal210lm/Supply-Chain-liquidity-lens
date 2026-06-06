"""Diagnose node — the first LLM node. Attributes a root cause to each flagged
cluster via forced tool use, so the model fills named fields rather than prose.

The model never produces a number: every figure is a {{path}} placeholder and
every quantitative claim is backed by a fact path in `evidence`. The node wraps
each bare evidence path into the contract's {"ref": path} shape before returning;
that wrapping is load-bearing and is verified by the mock test.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict

from backend.facts import Cluster, DiagnosisRun

DEFAULT_MODEL = "claude-sonnet-4-6"          # cheap dev default; swap to claude-opus-4-8 for quality
MODEL_ENV_VAR = "LIQUIDITY_LENS_MODEL"
TOP_MEMBERS_PER_CLUSTER = 8
DIAGNOSE_TOOL_NAME = "submit_cluster_diagnoses"
MAX_TOKENS = 4000

SYSTEM_PROMPT = """\
You are a senior working-capital diagnostician for a GCC distributor. Your job is
to attribute the root cause of each flagged inventory cluster.

ABSOLUTE RULE — you reason and write; you never calculate or state a number.
Every figure already exists in the FACTS you are given. To refer to a number,
insert a placeholder of the form {{path}} — double curly braces around a fact
path — and a renderer will substitute the exact figure afterward. NEVER type a
digit (0-9) yourself, in any field, for any reason, even if you are certain of
the value. A digit written outside a {{...}} placeholder causes your entire
answer to be rejected. Spell quantities in words only when unavoidable; prefer a
placeholder.

REFERENCING FACTS. A fact path walks the FACTS object with dots and [index]:
  - portfolio_value_at_stake.total
  - clusters[0].lever_total
  - clusters[0].members[0].facts.lead_time_days
  - clusters[0].members[2].facts.xyz_class
You may reference only paths that exist in the FACTS given to you, and you may
index members[j] only up to the number of members shown for that cluster.

YOUR TASK. For EACH cluster in the FACTS, attribute the single most likely root
cause, choosing from — and combining where the facts justify it:
  - long lead time
  - lumpy / erratic demand (high demand variability; XYZ class Z)
  - MOQ trap (minimum order quantity forces overstock)
  - stale safety-stock policy / over-ordering
  - supplier unreliability or concentration
  - near-expiry mismatch (stock will not sell before it expires)
  - structural stockout (cover below the lead time)
Ground every attribution in that cluster's facts, and cite the specific fact
paths that support it in `evidence`.

CONFIDENCE is qualitative — exactly one of high, medium, low. high = the facts
unambiguously point to the cause; medium = consistent but with caveats; low =
plausible but the facts are thin or mixed. NEVER express confidence as a
percentage or a number.

OUTPUT. Call the tool submit_cluster_diagnoses with exactly one entry per
cluster_id present in the FACTS. Numbers appear only inside {{...}} placeholders
in root_cause and rationale; supporting fact paths go in evidence. Do not write
any prose outside the tool call."""


# ── Client wrapper ───────────────────────────────────────────────────────────
def get_client():
    """Build a real Anthropic client. Reads ANTHROPIC_API_KEY from the env
    (loaded from .env if python-dotenv is present). Imported lazily so the unit
    tests, which inject a mock client, don't require the anthropic package."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    import anthropic

    return anthropic.Anthropic()


def resolve_model(model: str | None) -> str:
    return model or os.environ.get(MODEL_ENV_VAR, DEFAULT_MODEL)


# ── FACTS serializer ─────────────────────────────────────────────────────────
def serialize_run_for_prompt(run: DiagnosisRun, top_n: int = TOP_MEMBERS_PER_CLUSTER) -> dict:
    """JSON-ready view of the run. ALL clusters are included (so clusters[i]
    indices match the full run the validator resolves against), but each cluster
    shows only its top-N members, already sorted by lever_contribution."""
    return {
        "run_id": run.run_id,
        "reference_date": run.reference_date,
        "currency": run.currency,
        "portfolio_value_at_stake": asdict(run.portfolio_value_at_stake),
        "clusters": [
            {
                "cluster_id": c.cluster_id,
                "kind": c.kind,
                "lever": c.lever,
                "lever_total": c.lever_total,
                "member_count": c.member_count,
                "members_shown": min(top_n, len(c.members)),
                "members": [asdict(m) for m in c.members[:top_n]],
            }
            for c in run.clusters
        ],
    }


def build_user_message(run: DiagnosisRun, flagged: list[Cluster], top_n: int) -> str:
    sample_lines = "\n".join(
        f'  - cluster "{c.cluster_id}": showing top {min(top_n, len(c.members))} '
        f"of {c.member_count} members (sorted by impact)"
        for c in flagged
    )
    facts_json = json.dumps(serialize_run_for_prompt(run, top_n), indent=2, default=str)
    return (
        "FACTS — one diagnosis run. Reference these paths in your placeholders and "
        "evidence; never restate their numbers as digits.\n\n"
        "Each cluster shows only a sample of its members:\n"
        f"{sample_lines}\n\n"
        "Reason about each cluster as a whole using its cluster-level totals and this "
        "representative sample — do NOT assume the sample is the entire cluster.\n\n"
        f"{facts_json}\n\n"
        "Diagnose each cluster above — one entry per cluster_id. Every number is a "
        "{{path}} placeholder, never a digit."
    )


# ── Tool schema ──────────────────────────────────────────────────────────────
def build_tool(flagged: list[Cluster]) -> dict:
    return {
        "name": DIAGNOSE_TOOL_NAME,
        "description": (
            "Submit one root-cause diagnosis per flagged cluster. In every text "
            "field, numbers must be {{path}} placeholders, never digits."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "diagnoses": {
                    "type": "array",
                    "description": "Exactly one entry per cluster_id present in the FACTS.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "cluster_id": {
                                "type": "string",
                                "enum": [c.cluster_id for c in flagged],
                                "description": "Which cluster this diagnosis is for.",
                            },
                            "root_cause": {
                                "type": "string",
                                "description": "Single most likely root cause; numbers as {{path}} placeholders only.",
                            },
                            "confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "Qualitative confidence. Never a number or percentage.",
                            },
                            "rationale": {
                                "type": "string",
                                "description": "Why, grounded in the facts; numbers as {{path}} placeholders only.",
                            },
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Fact paths supporting the attribution, e.g. "
                                    "'clusters[0].members[0].facts.lead_time_days'. Provide at least one."
                                ),
                            },
                        },
                        "required": ["cluster_id", "root_cause", "confidence", "rationale", "evidence"],
                    },
                }
            },
            "required": ["diagnoses"],
        },
    }


# ── Node ─────────────────────────────────────────────────────────────────────
def _extract_tool_input(response) -> dict:
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == DIAGNOSE_TOOL_NAME:
            return block.input
    raise RuntimeError(f"Diagnose: model did not return a '{DIAGNOSE_TOOL_NAME}' tool call")


def _wrap_diagnosis(raw: dict) -> dict:
    """Turn one model-filled diagnosis into a contract-shaped REASON object.

    The model returns evidence as bare path strings; the contract wants
    {"ref": path} dicts. This wrapping is load-bearing — without it the contract
    validator rejects the output (a bare string is not a reference)."""
    return {
        "cluster_id": raw["cluster_id"],
        "root_cause": raw["root_cause"],
        "confidence": raw["confidence"],
        "rationale": raw["rationale"],
        "evidence": [{"ref": path} for path in raw.get("evidence", [])],
    }


def diagnose(
    run: DiagnosisRun,
    *,
    client=None,
    model: str | None = None,
    top_n: int = TOP_MEMBERS_PER_CLUSTER,
    max_tokens: int = MAX_TOKENS,
) -> list[dict]:
    """Diagnose each flagged cluster. Returns a list of contract-shaped diagnosis
    payloads (evidence already wrapped as {"ref": path}). Pass ``client`` to
    inject a mock; otherwise a real Anthropic client is built."""
    flagged = [c for c in run.clusters if c.members]
    if not flagged:
        return []

    tool = build_tool(flagged)
    user_message = build_user_message(run, flagged, top_n)

    if client is None:
        client = get_client()

    response = client.messages.create(
        model=resolve_model(model),
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[tool],
        tool_choice={"type": "tool", "name": DIAGNOSE_TOOL_NAME},
        messages=[{"role": "user", "content": user_message}],
    )

    raw = _extract_tool_input(response)
    return [_wrap_diagnosis(d) for d in raw.get("diagnoses", [])]
