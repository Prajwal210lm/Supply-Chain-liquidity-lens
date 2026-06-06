"""Prioritise node — synthesises the recommended actions into a ranked release
plan ordered by cash impact and feasibility, applying the service-level guardrail.

The model ranks and explains; cash impact is a fact reference. The guardrail is
enforced deterministically by the contract validator: a non-excluded ranked item
must reference a cluster whose members are all safe to release (the stockout
cluster must be marked excluded_for_guardrail).
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
)

PRIORITISE_TOOL_NAME = "submit_release_plan"
MAX_TOKENS = 4000

SYSTEM_PROMPT = """\
You are a senior working-capital advisor. You synthesise the recommended actions
into a ranked release plan: which actions free the most cash, soonest, without
breaching service levels.

ABSOLUTE RULE — you reason and write; you never calculate or state a number.
Every figure already exists in the FACTS. Refer to a number only via a {{path}}
placeholder; NEVER type a digit (0-9) in any field.

SERVICE-LEVEL GUARDRAIL. Releasing excess or dead stock (the slow_excess cluster)
is always safe — those units sit above the order-up-to level. Stock at or below
its order-up-to level (the stockout cluster) must NEVER be ranked as a release:
include it only with excluded_for_guardrail = true. Releasing it would breach
service levels.

REFERENCING FACTS. cash_impact must be a fact path quantifying the item's value,
e.g. "clusters[0].lever_total". Reference only paths that exist.

YOUR TASK. Rank the actions by cash impact and feasibility (rank 1 = act first).
For each item give: cluster_id, cash_impact (a fact path), a one-line
feasibility_rationale, and excluded_for_guardrail. Add a short guardrail note
describing how the plan preserves service levels.

OUTPUT. Call submit_release_plan. Numbers appear only as {{path}} placeholders.
Do not write prose outside the tool call."""


def build_tool(flagged: list[Cluster]) -> dict:
    return {
        "name": PRIORITISE_TOOL_NAME,
        "description": (
            "Submit the ranked release plan. cash_impact is a fact path; numbers in "
            "text must be {{path}} placeholders, never digits. Unsafe-to-release "
            "clusters must set excluded_for_guardrail = true."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "guardrail": {
                    "type": "string",
                    "description": "How the plan preserves service levels; numbers as {{path}} placeholders only.",
                },
                "ranked": {
                    "type": "array",
                    "description": "Actions ordered by cash impact and feasibility (rank 1 first).",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "rank": {"type": "integer", "description": "1-based priority order."},
                            "cluster_id": {
                                "type": "string",
                                "enum": [c.cluster_id for c in flagged],
                                "description": "Which cluster's action this is.",
                            },
                            "cash_impact": {
                                "type": "string",
                                "description": "Fact path for the cash impact, e.g. 'clusters[0].lever_total'.",
                            },
                            "feasibility_rationale": {
                                "type": "string",
                                "description": "One line on feasibility; numbers as {{path}} placeholders only.",
                            },
                            "excluded_for_guardrail": {
                                "type": "boolean",
                                "description": "True if this is NOT a safe release (e.g. a stockout cluster).",
                            },
                        },
                        "required": [
                            "rank", "cluster_id", "cash_impact",
                            "feasibility_rationale", "excluded_for_guardrail",
                        ],
                    },
                },
            },
            "required": ["guardrail", "ranked"],
        },
    }


def build_user_message(run: DiagnosisRun, recommendations: list[dict], top_n: int) -> str:
    return (
        "FACTS — the diagnosis run. Reference these paths; never restate numbers as digits.\n\n"
        f"{facts_json(run, top_n)}\n\n"
        "RECOMMENDATIONS (one action per cluster, from the previous step):\n"
        f"{json.dumps(recommendations, indent=2)}\n\n"
        "Rank these into a release plan by cash impact and feasibility. Mark any "
        "cluster that is not safe to release with excluded_for_guardrail = true. "
        "cash_impact must be a fact path; every number is a {{path}} placeholder."
    )


def _wrap_item(raw: dict) -> dict:
    return {
        "rank": raw["rank"],
        "cluster_id": raw["cluster_id"],
        "cash_impact": {"ref": raw["cash_impact"]},
        "feasibility_rationale": raw["feasibility_rationale"],
        "excluded_for_guardrail": bool(raw["excluded_for_guardrail"]),
    }


def prioritise(
    run: DiagnosisRun,
    recommendations: list[dict],
    *,
    client=None,
    model: str | None = None,
    top_n: int = TOP_MEMBERS_PER_CLUSTER,
    max_tokens: int = MAX_TOKENS,
) -> dict:
    """Produce the ranked release plan. Returns a contract-shaped dict with a
    guardrail note and ranked items (cash_impact wrapped as a reference)."""
    flagged = [c for c in run.clusters if c.members]
    if not flagged:
        return {"guardrail": "No flagged clusters; nothing to release.", "ranked": []}

    if client is None:
        client = get_client()

    response = client.messages.create(
        model=resolve_model(model),
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[build_tool(flagged)],
        tool_choice={"type": "tool", "name": PRIORITISE_TOOL_NAME},
        messages=[{"role": "user", "content": build_user_message(run, recommendations, top_n)}],
    )

    raw = extract_tool_input(response, PRIORITISE_TOOL_NAME)
    return {
        "guardrail": raw.get("guardrail", ""),
        "ranked": [_wrap_item(item) for item in raw.get("ranked", [])],
    }
