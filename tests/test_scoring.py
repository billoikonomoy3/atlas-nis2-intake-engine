"""Deterministic scorer — fixed fact-sets -> exact achieved_level, gap, status.

RM-21D-01 carries 3 design_evidence and 3 operating_evidence items in the ruleset, so
completeness is counted out of 3 each. No model is involved anywhere here.
"""

from __future__ import annotations

from atlas.engine.baseline import build_bar
from atlas.engine.models import ExtractedFact
from atlas.engine.scoring import score_control

DESIGN_QUOTES = ["supplier security policy v3", "criticality rating method", "contract security clause"]
OPERATING_QUOTES = ["supplier register 2025", "executed DPA acme", "annual supplier review log"]


def F(kind, quote, control="RM-21D-01", doc="policy.pdf", page=1, claim="established"):
    return ExtractedFact(control_id=control, evidence_kind=kind, claim=claim,
                         source_quote=quote, doc_id=doc, page=page, confidence=0.9)


def design(n):
    return [F("design", DESIGN_QUOTES[i], page=i + 1) for i in range(n)]


def operating(n):
    return [F("operating", OPERATING_QUOTES[i], page=10 + i) for i in range(n)]


def test_complete_design_no_operating_is_l2_gap_at_enhanced():
    facts = design(3)
    f = score_control("RM-21D-01", facts, build_bar("Enhanced"))  # required 3
    assert f.design_done == 1.0 and f.operating_done == 0.0
    assert f.achieved_level == 2
    assert f.required_level == 3
    assert f.gap == 1
    assert f.status == "gap"
    assert len(f.evidence) == 3


def test_complete_design_with_operating_meets_enhanced():
    facts = design(3) + operating(2)
    f = score_control("RM-21D-01", facts, build_bar("Enhanced"))
    assert f.achieved_level == 3
    assert f.gap == 0
    assert f.status == "meets"
    assert any(e.evidence_kind == "operating" for e in f.evidence)


def test_incomplete_design_is_l1():
    f = score_control("RM-21D-01", design(1), 2)
    assert round(f.design_done, 2) == 0.33
    assert f.achieved_level == 1
    assert f.gap == 1
    assert f.status == "gap"


def test_no_facts_is_insufficient_evidence():
    f = score_control("RM-21D-01", [], build_bar("Standard"))
    assert f.achieved_level == 0
    assert f.status == "insufficient_evidence"
    assert f.gap == 2
    assert f.evidence == []


def test_facts_without_source_quote_are_discarded():
    bad = [ExtractedFact(control_id="RM-21D-01", evidence_kind="design", claim="x",
                         source_quote="   ", doc_id="d", page=1, confidence=0.9)]
    f = score_control("RM-21D-01", bad, 2)
    assert f.evidence == []
    assert f.status == "insufficient_evidence"


def test_facts_for_other_controls_are_ignored():
    facts = design(3) + [F("operating", "unrelated", control="RM-21B-01")]
    f = score_control("RM-21D-01", facts, build_bar("Enhanced"))
    assert f.operating_done == 0.0
    assert f.achieved_level == 2


def test_meets_at_standard_with_documented_design():
    f = score_control("RM-21D-01", design(3), 2)  # Standard requires L2
    assert f.achieved_level == 2 and f.status == "meets" and f.gap == 0


def test_operating_critical_cannot_exceed_l2_without_operating():
    # RM-21B-01 is operating-critical; complete design, no operating -> capped at L2.
    facts = [F("design", q, control="RM-21B-01", page=i + 1)
             for i, q in enumerate(["ir plan", "process doc", "escalation"])]
    f = score_control("RM-21B-01", facts, 4)
    assert f.design_done == 1.0
    assert f.achieved_level == 2
    assert f.gap == 2


def test_evidence_carries_full_provenance():
    f = score_control("RM-21D-01", design(1), 3)
    e = f.evidence[0]
    assert e.source_quote and e.doc_id and e.page is not None and e.claim
