"""Contract validator: enforces "the LLM reasons and writes, it never calculates".

Validates a REASON payload (an LLM node's output) against the FACT object it was
derived from. Numbers may only enter via references ({"ref": path}) or prose
placeholders ({{path}}); a bare numeral anywhere in prose is rejected, even when
it matches a real fact value. See tests/test_contract.py for the adversarial set.
"""

from __future__ import annotations

import re

from backend.facts import DiagnosisRun, reconciliation_errors

ALLOWED_CONFIDENCE = {"high", "medium", "low"}

# A prose placeholder: {{ <fact path> }}
PLACEHOLDER_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
# One path segment: name, optionally with a [int] index.
_SEGMENT_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?")


# ── Path resolution ──────────────────────────────────────────────────────────
def resolve_path(run: DiagnosisRun, path: str):
    """Walk a dotted/indexed path against the FACT object. Raises on a bad path.

    Supports attribute access, [int] list indexing, and dict-key lookup (for the
    members' ``specifics`` dict), e.g. 'clusters[0].members[2].facts.lead_time_days'
    or 'clusters[0].members[0].specifics.excess_units'.
    """
    obj = run
    for part in path.split("."):
        m = _SEGMENT_RE.fullmatch(part)
        if not m:
            raise KeyError(f"malformed path segment: {part!r}")
        name, index = m.group(1), m.group(2)
        # ClusterMember.specifics is a plain dict, so a segment may be a dict key
        # rather than an attribute. Prefer key lookup when the object is a dict.
        obj = obj[name] if isinstance(obj, dict) else getattr(obj, name)
        if index is not None:
            obj = obj[int(index)]
    return obj


def path_resolves(run: DiagnosisRun, path: str) -> bool:
    try:
        resolve_path(run, path)
        return True
    except (AttributeError, KeyError, IndexError, TypeError):
        return False


# ── Prose (V1-V4) ────────────────────────────────────────────────────────────
def prose_violations(text: str, run: DiagnosisRun) -> list[str]:
    """A prose field is valid iff every {{placeholder}} resolves AND, once the
    placeholders are removed, no digit characters remain."""
    violations: list[str] = []

    for match in PLACEHOLDER_RE.finditer(text):
        path = match.group(1).strip()
        if not path_resolves(run, path):
            violations.append(f"prose placeholder '{{{{{path}}}}}' does not resolve to a fact")

    # Reject standalone numbers (a token that STARTS with a digit, e.g. "20,000",
    # "146,000", "12%", "2x") but allow identifiers where digits are embedded in an
    # alphanumeric word starting with a letter (e.g. SKU codes "SR1", "S1").
    # Placeholders are blanked first so their paths (which contain digits) aren't seen.
    tokens = re.findall(r"[0-9A-Za-z]+", PLACEHOLDER_RE.sub(" ", text))
    if any(token[0].isdigit() for token in tokens):
        violations.append(f"prose contains a bare numeral (use a {{{{ref}}}} placeholder): {text!r}")

    return violations


# ── References (V5-V8) ───────────────────────────────────────────────────────
def ref_violations(value, run: DiagnosisRun) -> list[str]:
    """A reference must be EXACTLY {"ref": "<resolving path>"} — nothing else."""
    if not isinstance(value, dict) or set(value.keys()) != {"ref"} or not isinstance(value["ref"], str):
        return [f"reference must be exactly {{'ref': <path>}}, got {value!r}"]
    if not path_resolves(run, value["ref"]):
        return [f"reference path '{value['ref']}' does not resolve to a fact"]
    return []


# ── Evidence (V9) ────────────────────────────────────────────────────────────
def evidence_violations(evidence, run: DiagnosisRun) -> list[str]:
    if not evidence:
        return ["reasoning has no citations (evidence is empty)"]
    violations: list[str] = []
    for ref in evidence:
        violations.extend(ref_violations(ref, run))
    return violations


# ── Confidence (V10-V11) ─────────────────────────────────────────────────────
def confidence_violations(value) -> list[str]:
    if value not in ALLOWED_CONFIDENCE:
        return [f"confidence must be one of {sorted(ALLOWED_CONFIDENCE)} (qualitative), got {value!r}"]
    return []


# ── Structural binding (V12) ─────────────────────────────────────────────────
def cluster_id_violations(cluster_id: str, run: DiagnosisRun) -> list[str]:
    if cluster_id not in {c.cluster_id for c in run.clusters}:
        return [f"cluster_id {cluster_id!r} is not present in the run"]
    return []


# ── Guardrail (V13) ──────────────────────────────────────────────────────────
def _find_sku_facts(run: DiagnosisRun, sku_code: str):
    for cluster in run.clusters:
        for member in cluster.members:
            if member.facts.sku_code == sku_code:
                return member.facts
    return None


def guardrail_violations(sku_code: str, run: DiagnosisRun, excluded: bool = False) -> list[str]:
    """A non-excluded ranked release item must reference a SKU that is safe to
    release. Excluded items (flagged by the guardrail) are allowed to remain
    listed for transparency."""
    if excluded:
        return []
    facts = _find_sku_facts(run, sku_code)
    if facts is None:
        return [f"release item references unknown SKU {sku_code!r}"]
    if not facts.safe_to_release:
        return [f"release item {sku_code!r} breaches the service-level guardrail (safe_to_release is False)"]
    return []


# ── Precondition (V14) ───────────────────────────────────────────────────────
def run_precondition_violations(run: DiagnosisRun) -> list[str]:
    """The facts must reconcile before any reasoning over them is trustworthy."""
    return reconciliation_errors(run)


# ── Rendering (post-validation) ──────────────────────────────────────────────
def _format_value(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{int(value):,}" if float(value).is_integer() else f"{value:,.2f}"
    return str(value)


def render_prose(text: str, run: DiagnosisRun) -> str:
    """Substitute each {{path}} with its formatted fact value. Runs only AFTER
    validation; the rendered output legitimately contains digits and is never
    re-validated."""
    return PLACEHOLDER_RE.sub(lambda m: _format_value(resolve_path(run, m.group(1).strip())), text)


# ── Cluster-level release guardrail (Prioritise) ─────────────────────────────
def cluster_release_violations(cluster_id: str, run: DiagnosisRun, excluded: bool = False) -> list[str]:
    """A non-excluded ranked RELEASE item must reference a cluster whose members
    are all safe to release. The stockout cluster (members below their order-up-to
    level) is never safe — it must be marked excluded_for_guardrail."""
    if excluded:
        return []
    cluster = next((c for c in run.clusters if c.cluster_id == cluster_id), None)
    if cluster is None:
        return [f"release item references unknown cluster {cluster_id!r}"]
    unsafe = [m.facts.sku_code for m in cluster.members if not m.facts.safe_to_release]
    if unsafe:
        return [
            f"release item for cluster {cluster_id!r} breaches the guardrail: "
            f"{len(unsafe)} member(s) not safe to release (e.g. {unsafe[:3]})"
        ]
    return []


# ── Composed node validators ─────────────────────────────────────────────────
def validate_diagnosis(payload: dict, run: DiagnosisRun) -> list[str]:
    """Validate a Diagnose-node output object against the run."""
    violations: list[str] = []
    violations.extend(cluster_id_violations(payload.get("cluster_id", ""), run))
    violations.extend(prose_violations(payload.get("root_cause", ""), run))
    violations.extend(prose_violations(payload.get("rationale", ""), run))
    violations.extend(confidence_violations(payload.get("confidence")))
    violations.extend(evidence_violations(payload.get("evidence", []), run))
    return violations


def validate_recommendation(payload: dict, run: DiagnosisRun) -> list[str]:
    """Validate a Recommend-node output object: action/preconditions are prose,
    quantified_impact is a single reference, evidence cites facts."""
    violations: list[str] = []
    violations.extend(cluster_id_violations(payload.get("cluster_id", ""), run))
    violations.extend(prose_violations(payload.get("action", ""), run))
    violations.extend(prose_violations(payload.get("preconditions", ""), run))
    violations.extend(ref_violations(payload.get("quantified_impact"), run))
    violations.extend(evidence_violations(payload.get("evidence", []), run))
    return violations


def validate_release_plan(payload: dict, run: DiagnosisRun) -> list[str]:
    """Validate a Prioritise-node release plan: guardrail note is prose, and each
    ranked item references a cluster + a cash-impact fact, with a prose rationale,
    and obeys the service-level guardrail."""
    violations: list[str] = []
    violations.extend(prose_violations(payload.get("guardrail", ""), run))
    ranked = payload.get("ranked", [])
    if not ranked:
        violations.append("release plan has no ranked items")
    for item in ranked:
        cluster_id = item.get("cluster_id", "")
        violations.extend(cluster_id_violations(cluster_id, run))
        violations.extend(ref_violations(item.get("cash_impact"), run))
        violations.extend(prose_violations(item.get("feasibility_rationale", ""), run))
        violations.extend(
            cluster_release_violations(cluster_id, run, bool(item.get("excluded_for_guardrail", False)))
        )
    return violations


def validate_narrative(payload: dict, run: DiagnosisRun) -> list[str]:
    """Validate a Narrate-node board brief: headline and body are prose whose only
    numbers are {{ref}} placeholders, and figures_cited resolve to facts."""
    violations: list[str] = []
    violations.extend(prose_violations(payload.get("headline", ""), run))
    violations.extend(prose_violations(payload.get("body_markdown", ""), run))
    violations.extend(evidence_violations(payload.get("figures_cited", []), run))
    return violations
