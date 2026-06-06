"""Recommend node — proposes one action per flagged cluster, given the computed
facts and the diagnosed root cause. The quantified impact is a fact reference,
never a typed number; supporting facts go in evidence. Forced tool use.
"""

from __future__ import annotations

import json

from backend.facts import Cluster, DiagnosisRun
from backend.llm import (
    TOP_MEMBERS_PER_CLUSTER,
    extract_tool_input,
    facts_json,
    get_client,
    resolve_model,
    wrap_refs,
)

RECOMMEND_TOOL_NAME = "submit_cluster_recommendations"
MAX_TOKENS = 4000

SYSTEM_PROMPT = """\
You are a senior working-capital advisor for a GCC distributor. For each flagged
cluster you propose ONE concrete action that addresses its diagnosed root cause.

ABSOLUTE RULE — you reason and write; you never calculate or state a number.
Every figure already exists in the FACTS. Refer to a number only via a {{path}}
placeholder; NEVER type a digit (0-9) in any field. A digit outside a placeholder
causes rejection.

REFERENCING FACTS. Paths walk the FACTS with dots and [index], e.g.
clusters[0].lever_total, clusters[0].members[0].facts.lead_time_days. Reference
only paths that exist; index members[j] only up to the number shown.

YOUR TASK. For each cluster, propose a specific, feasible action that targets the
diagnosed root cause — e.g. return-to-supplier, markdown / liquidation,
renegotiate MOQ, expedite or dual-source supply, write off near-expiry stock.
- quantified_impact: the single fact path that quantifies the action's value
  (typically the cluster's lever total, e.g. "clusters[0].lever_total").
- preconditions: what must be true to act (approvals, supplier terms, channels).
- evidence: the fact paths that justify the action.

OUTPUT. Call submit_cluster_recommendations with one entry per cluster_id present
in the FACTS. Numbers appear only as {{path}} placeholders in action/preconditions
text. Do not write prose outside the tool call."""


def build_tool(flagged: list[Cluster]) -> dict:
    return {
        "name": RECOMMEND_TOOL_NAME,
        "description": (
            "Submit one action per flagged cluster. quantified_impact is a single "
            "fact path; numbers in text must be {{path}} placeholders, never digits."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "recommendations": {
                    "type": "array",
                    "description": "Exactly one entry per cluster_id present in the FACTS.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "cluster_id": {
                                "type": "string",
                                "enum": [c.cluster_id for c in flagged],
                                "description": "Which cluster this action is for.",
                            },
                            "action": {
                                "type": "string",
                                "description": "The proposed action; numbers as {{path}} placeholders only.",
                            },
                            "quantified_impact": {
                                "type": "string",
                                "description": "A single fact path quantifying the value, e.g. 'clusters[0].lever_total'.",
                            },
                            "preconditions": {
                                "type": "string",
                                "description": "What must be true to act; numbers as {{path}} placeholders only.",
                            },
                            "evidence": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Fact paths justifying the action. Provide at least one.",
                            },
                        },
                        "required": ["cluster_id", "action", "quantified_impact", "preconditions", "evidence"],
                    },
                }
            },
            "required": ["recommendations"],
        },
    }


def build_user_message(run: DiagnosisRun, diagnoses: list[dict], top_n: int) -> str:
    return (
        "FACTS — the diagnosis run. Reference these paths; never restate numbers as digits.\n\n"
        f"{facts_json(run, top_n)}\n\n"
        "DIAGNOSES (root cause per cluster, from the previous step):\n"
        f"{json.dumps(diagnoses, indent=2)}\n\n"
        "Propose one action per cluster_id that addresses its diagnosed root cause. "
        "quantified_impact must be a fact path; every number is a {{path}} placeholder."
    )


def _wrap_recommendation(raw: dict) -> dict:
    """Wrap the model's bare fact paths into the contract's reference shape.
    Load-bearing: the validator rejects bare-string references."""
    return {
        "cluster_id": raw["cluster_id"],
        "action": raw["action"],
        "quantified_impact": {"ref": raw["quantified_impact"]},
        "preconditions": raw["preconditions"],
        "evidence": wrap_refs(raw.get("evidence", [])),
    }


def recommend(
    run: DiagnosisRun,
    diagnoses: list[dict],
    *,
    client=None,
    model: str | None = None,
    top_n: int = TOP_MEMBERS_PER_CLUSTER,
    max_tokens: int = MAX_TOKENS,
) -> list[dict]:
    """Recommend an action per flagged cluster. Returns contract-shaped payloads
    (quantified_impact and evidence already wrapped as references)."""
    flagged = [c for c in run.clusters if c.members]
    if not flagged:
        return []

    if client is None:
        client = get_client()

    response = client.messages.create(
        model=resolve_model(model),
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[build_tool(flagged)],
        tool_choice={"type": "tool", "name": RECOMMEND_TOOL_NAME},
        messages=[{"role": "user", "content": build_user_message(run, diagnoses, top_n)}],
    )

    raw = extract_tool_input(response, RECOMMEND_TOOL_NAME)
    return [_wrap_recommendation(r) for r in raw.get("recommendations", [])]
