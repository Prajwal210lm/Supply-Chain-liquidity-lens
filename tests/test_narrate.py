"""Narrate node tests — deterministic mock + skip-by-default integration.

The centrepiece is the render round-trip: the model writes prose with {{path}}
placeholders (no digits), the validator passes it, and render_prose substitutes
the exact fact values — proving numbers reach the brief only through the renderer.
"""

import os
from datetime import date
from types import SimpleNamespace

import pytest

from analytics.models import Sku
from backend.contract import render_prose, validate_narrative
from backend.narrate import NARRATE_TOOL_NAME, narrate
from backend.nodes import compute

REF = date(2025, 6, 2)


def _run():
    # releasable_cash 20,000 ; write_off 0 ; stockout 126,000 ; total 146,000.
    portfolio = [
        Sku("S1", on_hand=900, avg_weekly_demand=70, unit_cost=50,
            target_coverage_days=50, lead_time_days=30),
        Sku("SR1", on_hand=140, avg_weekly_demand=140, unit_cost=300, selling_price=400,
            target_coverage_days=100, lead_time_days=70),
    ]
    return compute(portfolio, REF, run_id="narr-test")


class _MockMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _MockClient:
    def __init__(self, response):
        self.messages = _MockMessages(response)


# Canned brief: every figure is an inline {{path}} placeholder — no digits.
_CANNED = {
    "headline": "Working capital: {{portfolio_value_at_stake.total}} at stake across the portfolio.",
    "body_markdown": (
        "## Working-capital diagnostic\n\n"
        "Total value at stake is {{portfolio_value_at_stake.total}}. The largest "
        "opportunity is releasing {{portfolio_value_at_stake.releasable_cash}} of cash "
        "trapped in slow-moving stock. Separately, stockouts on fast movers put "
        "{{portfolio_value_at_stake.stockout_margin_loss}} of margin at risk."
    ),
    "figures_cited": [
        "portfolio_value_at_stake.total",
        "portfolio_value_at_stake.releasable_cash",
        "portfolio_value_at_stake.stockout_margin_loss",
    ],
}


def _mock_client():
    block = SimpleNamespace(type="tool_use", name=NARRATE_TOOL_NAME, input=_CANNED)
    return _MockClient(SimpleNamespace(content=[block]))


def test_narrate_mock_wiring():
    run = _run()
    client = _mock_client()
    narrate(run, release_plan={"guardrail": "", "ranked": []}, client=client, model="mock-model")

    call = client.messages.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": NARRATE_TOOL_NAME}
    assert call["tools"][0]["name"] == NARRATE_TOOL_NAME
    assert "RELEASE PLAN" in call["messages"][0]["content"]


def test_narrate_render_round_trip():
    run = _run()
    brief = narrate(run, release_plan={"guardrail": "", "ranked": []},
                    client=_mock_client(), model="mock-model")

    # figures_cited wrapped into references.
    assert brief["figures_cited"][0] == {"ref": "portfolio_value_at_stake.total"}

    # Validates clean BEFORE render: placeholders resolve, and there are no digits
    # in the prose (every number is a placeholder).
    assert validate_narrative(brief, run) == []

    # Render substitutes each {{path}} with its exact fact value.
    rendered = render_prose(brief["body_markdown"], run)
    assert "{{" not in rendered                 # all placeholders consumed
    assert "146,000" in rendered                # total
    assert "20,000" in rendered                 # releasable_cash
    assert "126,000" in rendered                # stockout_margin_loss

    rendered_headline = render_prose(brief["headline"], run)
    assert rendered_headline == "Working capital: 146,000 at stake across the portfolio."


def test_narrate_digit_in_prose_is_rejected():
    # Load-bearing: a literal number in the brief (even the correct one) is rejected;
    # numbers must arrive via the renderer, not the model.
    run = _run()
    bad = {
        "headline": "Total at stake.",
        "body_markdown": "We can release AED 20,000 of trapped cash.",  # bare digits
        "figures_cited": ["portfolio_value_at_stake.releasable_cash"],
    }
    assert validate_narrative(bad, run) != []


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set")
def test_narrate_integration_real_api():
    from backend.diagnose import diagnose
    from backend.prioritise import prioritise
    from backend.recommend import recommend

    run = _run()
    plan = prioritise(run, recommend(run, diagnose(run)))
    brief = narrate(run, plan)

    # Validate FIRST — only render prose that passed the contract (render is not
    # exception-safe for unresolvable placeholders).
    violations = validate_narrative(brief, run)
    print(f"\nHEADLINE (raw): {brief['headline']}")
    if violations:
        print(f"\n!! VIOLATIONS: {violations}")
    assert violations == []

    print(f"HEADLINE (rendered): {render_prose(brief['headline'], run)}")
    print("\nBODY (rendered):\n" + render_prose(brief["body_markdown"], run))
