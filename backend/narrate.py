"""Narrate node — writes the board brief for the CFO and COO from the prioritised
plan and value-at-stake totals.

Every figure in the prose is a {{path}} placeholder; the renderer
(contract.render_prose) substitutes the exact fact values at the very end, after
validation. The model never writes a digit.
"""

from __future__ import annotations

import json

from backend.facts import DiagnosisRun
from backend.llm import (
    TOP_MEMBERS_PER_CLUSTER,
    extract_tool_input,
    facts_json,
    get_client,
    resolve_model,
    wrap_refs,
)

NARRATE_TOOL_NAME = "submit_board_brief"
MAX_TOKENS = 4000

SYSTEM_PROMPT = """\
You are writing a board brief for the CFO and COO of a GCC distributor, from the
prioritised release plan and the portfolio value-at-stake totals.

ABSOLUTE RULE — you reason and write; you never calculate or state a number.
Every figure already exists in the FACTS. Write each figure INLINE as a {{path}}
placeholder — e.g. "We can release {{portfolio_value_at_stake.releasable_cash}}
in cash." A renderer substitutes the exact value afterward. NEVER type a digit
(0-9) anywhere in the headline or body. A digit outside a placeholder causes
rejection.

Do not add metadata headers, reference dates, or formatting the brief was not
asked for. If the date is relevant, use the {{reference_date}} placeholder —
never type a date as digits.

Placeholders may reference ONLY the FACTS object — paths beginning
portfolio_value_at_stake or clusters. Do NOT reference the release plan (no
ranked[...]). Express priority or order in words (first, second), never as rank
numbers.

REFERENCING FACTS. Use real paths only, e.g. portfolio_value_at_stake.total,
portfolio_value_at_stake.releasable_cash, clusters[0].lever_total.

TOTAL IS AN UPPER BOUND. The three dimensions are not strictly additive: a SKU
that is both overstocked and near-expiry contributes to releasable cash AND
write-off exposure, because each names a distinct action on the same units. When
you state the total, note in words that it is an upper bound across the three
dimensions, not a simple sum of independent amounts.

YOUR TASK. Write a concise, board-ready brief:
- headline: one line stating the total value at stake (as a placeholder).
- body_markdown: a short markdown brief covering the total value at stake, the
  largest release opportunity, expiry write-off exposure, and stockout risk —
  every figure a {{path}} placeholder, in CFO/COO language. Include the
  upper-bound caveat when presenting the total.
- figures_cited: the list of fact paths you referenced.

OUTPUT. Call submit_board_brief. No digits anywhere; numbers are placeholders
only. Do not write prose outside the tool call."""


def build_tool() -> dict:
    return {
        "name": NARRATE_TOOL_NAME,
        "description": (
            "Submit the board brief. Numbers in headline/body must be {{path}} "
            "placeholders, never digits. figures_cited lists the referenced paths."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "headline": {
                    "type": "string",
                    "description": "One-line headline; numbers as {{path}} placeholders only.",
                },
                "body_markdown": {
                    "type": "string",
                    "description": "Markdown board brief; every figure a {{path}} placeholder.",
                },
                "figures_cited": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fact paths referenced in the brief. Provide at least one.",
                },
            },
            "required": ["headline", "body_markdown", "figures_cited"],
        },
    }


def build_user_message(run: DiagnosisRun, release_plan: dict, top_n: int) -> str:
    return (
        "FACTS — the diagnosis run. Reference these paths; never restate numbers as digits.\n\n"
        f"{facts_json(run, top_n)}\n\n"
        "RELEASE PLAN (ranked, from the previous step):\n"
        f"{json.dumps(release_plan, indent=2)}\n\n"
        "Write the board brief. Every figure is an inline {{path}} placeholder; "
        "list the paths you cited in figures_cited."
    )


def _wrap_brief(raw: dict) -> dict:
    return {
        "headline": raw["headline"],
        "body_markdown": raw["body_markdown"],
        "figures_cited": wrap_refs(raw.get("figures_cited", [])),
    }


def narrate(
    run: DiagnosisRun,
    release_plan: dict,
    *,
    client=None,
    model: str | None = None,
    top_n: int = TOP_MEMBERS_PER_CLUSTER,
    max_tokens: int = MAX_TOKENS,
) -> dict:
    """Write the board brief. Returns a contract-shaped dict (figures_cited wrapped
    as references). The prose carries {{path}} placeholders; render with
    contract.render_prose after validation."""
    if client is None:
        client = get_client()

    response = client.messages.create(
        model=resolve_model(model),
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        tools=[build_tool()],
        tool_choice={"type": "tool", "name": NARRATE_TOOL_NAME},
        messages=[{"role": "user", "content": build_user_message(run, release_plan, top_n)}],
    )

    raw = extract_tool_input(response, NARRATE_TOOL_NAME)
    return _wrap_brief(raw)
