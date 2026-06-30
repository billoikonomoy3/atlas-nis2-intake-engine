"""Deterministic supply-chain coverage map — evidence-item presence -> coverage. NO model.

A model (in the extraction layer) LOCATES + QUOTES + TAGS each fact with the registry
evidence_item it addresses. Everything here is pure code: bucket the provenance-verified
facts by evidence_item id, mark each item present / ambiguous / absent against the
registry's confidence threshold, then derive each control's coverage state with the
decisive-item rule — the load-bearing item (per ``signals.present``) must be present, or
the control is at best 'ambiguous'; raw count alone is never enough.

Same facts -> byte-identical map (registry order, sorted evidence, no clock/randomness).
The model never assigns a status; it only located the evidence this counts.
"""

from __future__ import annotations

from . import ruleset as R
from .models import (AreaCoverage, ControlCoverage, CoverageItem, EvidenceRef,
                     ExtractedFact)
from .veto import evaluate_vetoes

_STATES = ("present", "ambiguous", "absent")


def _dedupe(facts: list[ExtractedFact]) -> list[ExtractedFact]:
    """Drop exact duplicate citations (same item/doc/page/quote), order-stable."""
    seen: set[tuple] = set()
    kept: list[ExtractedFact] = []
    for f in facts:
        if not (f.source_quote and f.source_quote.strip()):
            continue
        key = (f.evidence_item_id, f.doc_id, f.page, f.source_quote.strip())
        if key in seen:
            continue
        seen.add(key)
        kept.append(f)
    return kept


def _item_status(facts: list[ExtractedFact], threshold: float) -> tuple[str, float]:
    """present / ambiguous / absent for one evidence item, deterministically.

    absent = nothing tagged it; present = a tagged fact meets the confidence threshold;
    ambiguous = it was located but every tagging fact is below the threshold (touched,
    not solidly evidenced). The threshold and the inputs are data; the rule is fixed code.
    """
    if not facts:
        return "absent", 0.0
    max_conf = max(f.confidence for f in facts)
    return ("present" if max_conf >= threshold else "ambiguous"), max_conf


def _evidence_refs(facts: list[ExtractedFact]) -> list[EvidenceRef]:
    return [
        EvidenceRef(evidence_kind=f.evidence_kind, claim=f.claim, source_quote=f.source_quote,
                    doc_id=f.doc_id, page=f.page)
        for f in sorted(facts, key=lambda x: (x.evidence_kind, x.doc_id, x.page, x.source_quote))
    ]


def _control_coverage(control: dict, facts: list[ExtractedFact], *, threshold: float,
                      decisive_id: str, article: str) -> ControlCoverage:
    control_id = control["id"]
    by_item: dict[str, list[ExtractedFact]] = {}
    for f in facts:
        if f.evidence_item_id:
            by_item.setdefault(f.evidence_item_id, []).append(f)

    items: list[CoverageItem] = []
    counts = {s: 0 for s in _STATES}
    decisive_status = "absent"
    for ev in control.get("evidence_items", []):
        item_id = ev["id"]
        status, max_conf = _item_status(by_item.get(item_id, []), threshold)
        counts[status] += 1
        if item_id == decisive_id:
            decisive_status = status
        items.append(CoverageItem(
            evidence_item_id=item_id, item=ev["item"], status=status,
            decisive=(item_id == decisive_id), max_confidence=round(max_conf, 4),
            evidence=_evidence_refs(by_item.get(item_id, [])),
        ))

    total = len(items)
    # Decisive-item rule: a control is 'present' only when its load-bearing item is
    # present AND no item is wholly absent; if anything is evidenced but that bar is not
    # met it is 'ambiguous' (partial); nothing evidenced at all is 'absent'.
    if counts["present"] == 0 and counts["ambiguous"] == 0:
        coverage_state = "absent"
    elif decisive_status == "present" and counts["absent"] == 0:
        coverage_state = "present"
    else:
        coverage_state = "ambiguous"

    # Disqualifying findings (pure code, same area/leaf veto data). A live veto means a
    # documented clause DEFEATS the control: it can never read 'present' coverage.
    vetoes = evaluate_vetoes(control_id, facts)
    veto_capped = bool(vetoes)
    if veto_capped and coverage_state == "present":
        coverage_state = "ambiguous"

    rationale = (
        f"{counts['present']}/{total} evidence items present, {counts['ambiguous']} ambiguous, "
        f"{counts['absent']} absent; decisive item {decisive_id} is {decisive_status} "
        f"-> coverage {coverage_state}. Heuristic — model located the evidence, the status is "
        f"deterministic; NIS2 Art 21(1) is outcomes-based."
    )
    if veto_capped:
        refs = ", ".join(sorted({v.defeats_ref for v in vetoes if v.defeats_ref}))
        rationale += (f" VETO — {len(vetoes)} disqualifying finding(s) defeat this control"
                      f"{f' (defeats {refs})' if refs else ''}; coverage cannot read 'present'.")

    return ControlCoverage(
        control_id=control_id, title=control.get("title", ""), nis2_ref=article,
        decisive_item=decisive_id, coverage_state=coverage_state,
        present_count=counts["present"], ambiguous_count=counts["ambiguous"],
        absent_count=counts["absent"], total_items=total,
        coverage_ratio=round(counts["present"] / total, 4) if total else 0.0,
        items=items, vetoes=vetoes, veto_capped=veto_capped, rationale=rationale,
    )


def compute_area_coverage(facts: list[ExtractedFact]) -> AreaCoverage:
    """Build the Art 21(2)(d) coverage map from provenance-verified, item-tagged facts.

    Callers must pass facts that already cleared the verbatim-substring firewall (the
    public API re-verifies before calling this). Pure and deterministic.
    """
    area = R.supply_chain_area()
    article = area.get("article", "")
    decisive = R.decisive_items()
    threshold = R.present_confidence()

    facts = _dedupe(facts)
    by_control: dict[str, list[ExtractedFact]] = {}
    for f in facts:
        by_control.setdefault(f.control_id, []).append(f)

    controls: list[ControlCoverage] = []
    item_summary = {s: 0 for s in _STATES}
    control_summary = {s: 0 for s in _STATES}
    for control in R.supply_chain_controls():
        cid = control["id"]
        cc = _control_coverage(
            control, by_control.get(cid, []), threshold=threshold,
            decisive_id=decisive.get(cid, ""), article=article,
        )
        controls.append(cc)
        control_summary[cc.coverage_state] += 1
        for it in cc.items:
            item_summary[it.status] += 1

    return AreaCoverage(
        area_id=area.get("id", ""), article=article, title=area.get("title", ""),
        registry_sha256=R.supply_chain_registry_sha256(), controls=controls,
        item_summary=item_summary, control_summary=control_summary,
    )
