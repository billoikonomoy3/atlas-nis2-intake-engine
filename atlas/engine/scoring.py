"""Deterministic maturity scorer — extracted facts -> a cited Finding. NO model call.

This is the judgment path: it turns provenance-carrying ExtractedFacts into a 0-4
maturity level, a gap against the proportionate bar, and a status — by pure rule.
A model never assigns a level here; it only supplied (in the extraction layer) the
facts, each of which must already carry a source_quote + doc_id + page or it is
DISCARDED before it can influence the score.

Level derivation (ladder + ruleset thresholds), weakest-link by construction:
  * design completeness gates everything — incomplete design can never exceed L1;
  * complete design with thin operating evidence is capped at L2 (documented-only);
  * L3 (Defined/operating) needs complete design AND operating evidence in the window;
  * operating-critical controls cannot exceed L2 without any operating evidence;
  * L4 (Managed/measured) needs monitoring/metrics on a cadence — a signal the basic
    extracted-fact schema does not carry, so the facts-only scorer tops out at L3
    (you cannot prove "measured" from policy documents alone). Documented in README.
"""

from __future__ import annotations

from . import ruleset as R
from .baseline import maturity_name
from .models import Bar, EvidenceRef, ExtractedFact, Finding


def _valid_facts(control_id: str, facts: list[ExtractedFact]) -> list[ExtractedFact]:
    """Keep only this control's facts that carry full provenance; dedupe."""
    seen: set[tuple] = set()
    kept: list[ExtractedFact] = []
    for f in facts:
        if f.control_id != control_id:
            continue
        # Provenance is mandatory: a fact without a source_quote / doc_id / page is discarded.
        if not (f.source_quote and f.source_quote.strip()) or not f.doc_id or f.page is None:
            continue
        key = (f.evidence_kind, f.doc_id, f.page, f.source_quote.strip())
        if key in seen:
            continue
        seen.add(key)
        kept.append(f)
    return kept


def _achieved_level(design_done: float, operating_done: float, n_operating: int,
                    operating_critical: bool) -> int:
    th = R.maturity_thresholds()
    if design_done < th["design_min_for_l1"]:
        level = 0
    elif design_done < th["design_complete"]:
        level = 1
    elif operating_done < th["operating_min_for_l3"]:
        level = 2
    else:
        # Complete design + sufficient operating evidence in the window -> Defined.
        # L4 (monitoring/metrics on a cadence) is not derivable from the basic fact
        # schema, so the facts-only scorer tops out at L3.
        level = 3
    # Operating-critical controls cannot exceed L2 without ANY operating evidence.
    if operating_critical and n_operating == 0:
        level = min(level, 2)
    return level


def score_control(control_id: str, facts: list[ExtractedFact], bar: Bar | int) -> Finding:
    """Score one control from cited facts to a deterministic, cited Finding."""
    crit = R.criteria_by_id().get(control_id)
    if crit is None:
        raise KeyError(f"unknown control_id: {control_id!r}")

    op_crit = control_id in R.operating_critical()
    n_design_reqs = max(1, len(crit["design_evidence"]))
    n_operating_reqs = max(1, len(crit["operating_evidence"]))

    kept = _valid_facts(control_id, facts)
    design_facts = [f for f in kept if f.evidence_kind == "design"]
    operating_facts = [f for f in kept if f.evidence_kind == "operating"]

    design_done = min(1.0, len(design_facts) / n_design_reqs)
    operating_done = min(1.0, len(operating_facts) / n_operating_reqs)

    achieved = _achieved_level(design_done, operating_done, len(operating_facts), op_crit)

    # Resolve the required level from the bar.
    if isinstance(bar, int):
        required = bar
    else:
        required = bar.required_level
        for bc in bar.controls:
            if bc.control_id == control_id:
                required = bc.required_level
                break

    gap = max(0, required - achieved)

    if not kept or achieved == 0:
        status = "insufficient_evidence"
    elif achieved >= required:
        status = "meets"
    else:
        status = "gap"

    # Deterministic evidence ordering (no clock, no model).
    evidence = [
        EvidenceRef(evidence_kind=f.evidence_kind, claim=f.claim, source_quote=f.source_quote,
                    doc_id=f.doc_id, page=f.page)
        for f in sorted(kept, key=lambda x: (x.evidence_kind, x.doc_id, x.page, x.source_quote))
    ]

    rationale = (
        f"design {len(design_facts)}/{n_design_reqs} (={design_done:.2f}), "
        f"operating {len(operating_facts)}/{n_operating_reqs} (={operating_done:.2f})"
        f"{' [operating-critical]' if op_crit else ''} -> achieved L{achieved} "
        f"({maturity_name(achieved)}); required L{required} ({maturity_name(required)}); "
        f"gap {gap}; status {status}. Heuristic rung — NIS2 Art 21(1) is outcomes-based."
    )

    return Finding(
        control_id=control_id,
        nis2_ref=crit["ref"],
        achieved_level=achieved,
        achieved_name=maturity_name(achieved),
        required_level=required,
        required_name=maturity_name(required),
        gap=gap,
        status=status,
        design_done=round(design_done, 4),
        operating_done=round(operating_done, 4),
        evidence=evidence,
        rationale=rationale,
    )
