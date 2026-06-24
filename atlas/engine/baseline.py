"""Compliance baseline — the minimum maturity rung each in-scope control must clear.

HEURISTIC, derived from the proportionality tier (Foundational->L1 ... Critical->L4),
applied to every control in the registry. NIS2 prescribes no numeric scale, so this
is a tunable policy, not a statutory threshold.

Known, surfaced (not silently corrected) policy artefact: an in-scope *important*
entity can land at the Foundational tier and therefore a required rung of L1. That is
flagged as a tunable policy decision in the README; this module does not "fix" it.
"""

from __future__ import annotations

from . import ruleset as R
from .models import Bar, BarControl


def maturity_name(level: int) -> str:
    for lv, name, _desc in R.maturity_ladder():
        if lv == level:
            return name
    return "Unknown"


def required_for_tier(tier: str) -> int:
    return R.required_by_tier().get(tier, 1)


def evidence_rule_for(rung: int) -> str:
    """The kind of evidence a given required rung demands (heuristic guidance)."""
    if rung <= 1:
        return "at least one design artefact with provenance (doc · page · date)."
    if rung == 2:
        return "the control fully documented — the complete design evidence set."
    if rung == 3:
        return "complete design PLUS operating evidence that it actually ran inside the evidence window."
    return "complete design, strong operating evidence, AND active monitoring / metrics on a defined cadence."


def build_bar(tier: str) -> Bar:
    """Build the per-control compliance baseline for a proportionality tier."""
    required = required_for_tier(tier)
    required_name = maturity_name(required)
    op_crit = R.operating_critical()
    controls: list[BarControl] = []
    for c in R.criteria():
        controls.append(BarControl(
            control_id=c["id"],
            ref=c["ref"],
            domain=c["domain"],
            inherent_criticality=c["inherent_criticality"],
            required_level=required,
            required_name=required_name,
            operating_critical=c["id"] in op_crit,
            evidence_rule=evidence_rule_for(required),
        ))
    return Bar(tier=tier, required_level=required, required_name=required_name, controls=controls)
