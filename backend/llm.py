"""Shared plumbing for the LLM reasoning nodes: client construction, model
resolution, FACTS serialization, tool-call extraction, and reference wrapping.

No node may produce a number — every figure is referenced by fact path. The
helpers here are provider plumbing only; the per-node prompts and tool schemas
live in the node modules.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict

from backend.facts import DiagnosisRun

DEFAULT_MODEL = "claude-sonnet-4-6"   # cheap dev default; swap to claude-opus-4-8 for quality
MODEL_ENV_VAR = "LIQUIDITY_LENS_MODEL"
TOP_MEMBERS_PER_CLUSTER = 8


def get_client():
    """Build a real Anthropic client. Reads ANTHROPIC_API_KEY from the env
    (loaded from .env if python-dotenv is present). Imported lazily so unit tests,
    which inject a mock client, don't require the anthropic package or a key."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    import anthropic

    return anthropic.Anthropic()


def resolve_model(model: str | None) -> str:
    return model or os.environ.get(MODEL_ENV_VAR, DEFAULT_MODEL)


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


def facts_json(run: DiagnosisRun, top_n: int = TOP_MEMBERS_PER_CLUSTER) -> str:
    return json.dumps(serialize_run_for_prompt(run, top_n), indent=2, default=str)


def extract_tool_input(response, tool_name: str) -> dict:
    """Return the input dict of the named forced tool call, or raise."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == tool_name:
            return block.input
    raise RuntimeError(f"LLM node: model did not return a '{tool_name}' tool call")


def wrap_refs(paths) -> list[dict]:
    """Turn bare fact-path strings into the contract's {"ref": path} shape.
    Load-bearing: the contract validator rejects bare-string references."""
    return [{"ref": path} for path in paths]
