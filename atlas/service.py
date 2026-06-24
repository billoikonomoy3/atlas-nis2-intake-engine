"""Deterministic orchestration — validate -> classify -> proportionality -> bar -> score.

Pure and offline: NO model calls anywhere in this module. The API and the tests both
go through here, so the "no silent classification on bad input" guarantee is exercised
on the real path: malformed numerics short-circuit to INSUFFICIENT_INPUT before any
classification happens.
"""

from __future__ import annotations

from .engine.baseline import build_bar
from .engine.classify import classify_entity
from .engine.models import Bar, ClassifyResult, EntityInput, ExtractedFact, Finding, Snapshot
from .engine.proportionality import score_from_verdict
from .engine.scoring import score_control
from .engine.snapshot import build_snapshot
from .engine.validate import validate_entity


def run_classify(entity: EntityInput) -> ClassifyResult:
    reasons = validate_entity(entity)
    if reasons:
        return ClassifyResult(status="INSUFFICIENT_INPUT", reasons=reasons)
    verdict = classify_entity(entity)
    prop = score_from_verdict(verdict, entity.proportionality)
    bar = build_bar(prop.tier)
    return ClassifyResult(status="ok", verdict=verdict, proportionality=prop, bar=bar)


def assess_control_from_facts(entity: EntityInput, control_id: str,
                              facts: list[ExtractedFact]) -> tuple[ClassifyResult, Finding | None]:
    """Score one control deterministically against this entity's bar."""
    cr = run_classify(entity)
    if cr.status != "ok" or cr.bar is None:
        return cr, None
    return cr, score_control(control_id, facts, cr.bar)


def run_snapshot(entity: EntityInput, generated_at: str, *, control_id: str | None = None,
                 facts: list[ExtractedFact] | None = None) -> Snapshot:
    cr = run_classify(entity)
    if cr.status != "ok":
        return build_snapshot(inputs=entity, generated_at=generated_at,
                              status="INSUFFICIENT_INPUT", reasons=cr.reasons)
    findings: list[Finding] = []
    if control_id and facts is not None:
        findings = [score_control(control_id, facts, cr.bar)]
    return build_snapshot(
        inputs=entity, generated_at=generated_at, verdict=cr.verdict,
        proportionality=cr.proportionality, bar=cr.bar, findings=findings,
    )
