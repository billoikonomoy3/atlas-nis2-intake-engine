"""Supply-chain coverage map — deterministic bucketing + the decisive-item rule.

The model only LOCATES + QUOTES + TAGS an evidence_item_id; every present/ambiguous/absent
status and every per-control coverage state is computed here in pure code. These tests pin
that behaviour, including that the load-bearing (decisive) item gates the control verdict —
count alone is never enough.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas.engine.coverage import compute_area_coverage
from atlas.engine.models import ExtractedFact


def _F(control, item, kind, quote, conf, *, page=1, doc="d.pdf", claim="located"):
    return ExtractedFact(control_id=control, evidence_kind=kind, claim=claim,
                         source_quote=quote, doc_id=doc, page=page, confidence=conf,
                         evidence_item_id=item)


def _ctrl(cov, control_id):
    return next(c for c in cov.controls if c.control_id == control_id)


def _items(cc):
    return {it.evidence_item_id: it.status for it in cc.items}


# ---------------------------------------------------------------------------
# 1. Per-item bucketing: present (>=threshold) / ambiguous (<threshold) / absent (none).
# ---------------------------------------------------------------------------

def test_item_present_ambiguous_absent_buckets():
    # RM-21D-01 has items a, b, c. a strong, b weak, c not located.
    facts = [
        _F("RM-21D-01", "21D-01-a", "operating", "register maintained in the GRC platform", 0.90),
        _F("RM-21D-01", "21D-01-b", "design", "suppliers classified into criticality tiers", 0.40),
    ]
    cc = _ctrl(compute_area_coverage(facts), "RM-21D-01")
    st = _items(cc)
    assert st["21D-01-a"] == "present"     # >= present_confidence (0.60)
    assert st["21D-01-b"] == "ambiguous"   # located but below the threshold
    assert st["21D-01-c"] == "absent"      # never tagged
    assert cc.present_count == 1 and cc.ambiguous_count == 1 and cc.absent_count == 1


def test_threshold_boundary_is_present_at_exactly_the_threshold():
    facts = [_F("RM-21D-01", "21D-01-a", "design", "register maintained in the GRC platform", 0.60)]
    cc = _ctrl(compute_area_coverage(facts), "RM-21D-01")
    assert _items(cc)["21D-01-a"] == "present"   # confidence == threshold -> present


# ---------------------------------------------------------------------------
# 2. The decisive-item rule — the load-bearing item gates the control verdict.
# ---------------------------------------------------------------------------

def test_decisive_item_absent_makes_control_ambiguous_despite_other_evidence():
    # RM-21D-06 decisive item is 21D-06-b (the exit procedure). Evidence only the
    # NON-decisive 21D-06-d -> count says 1 present, but coverage must stay 'ambiguous'.
    facts = [_F("RM-21D-06", "21D-06-d", "design", "return or destruction of data on exit", 0.95)]
    cc = _ctrl(compute_area_coverage(facts), "RM-21D-06")
    assert cc.present_count == 1
    assert _items(cc)["21D-06-b"] == "absent"
    assert cc.decisive_item == "21D-06-b"
    assert cc.coverage_state == "ambiguous", "decisive item absent => never 'present'"


def test_control_present_requires_decisive_present_and_no_absent_item():
    # RM-21D-01 (a, b, c): decisive a present, b present, c ambiguous (none absent) -> present.
    facts = [
        _F("RM-21D-01", "21D-01-a", "operating", "register maintained in the GRC platform", 0.90),
        _F("RM-21D-01", "21D-01-b", "design", "suppliers classified into criticality tiers", 0.85),
        _F("RM-21D-01", "21D-01-c", "operating", "criticality tier and assessment status recorded", 0.45),
    ]
    cc = _ctrl(compute_area_coverage(facts), "RM-21D-01")
    assert cc.absent_count == 0 and _items(cc)["21D-01-a"] == "present"
    assert cc.coverage_state == "present"


def test_control_absent_when_nothing_located():
    cc = _ctrl(compute_area_coverage([]), "RM-21D-02")
    assert cc.coverage_state == "absent"
    assert all(it.status == "absent" for it in cc.items)


def test_unknown_evidence_item_id_is_not_counted():
    facts = [_F("RM-21D-01", "21D-99-z", "design", "register maintained in the GRC platform", 0.9)]
    cc = _ctrl(compute_area_coverage(facts), "RM-21D-01")
    assert cc.coverage_state == "absent"   # the bogus tag matches no registry item


# ---------------------------------------------------------------------------
# 3. Determinism + area-level summary.
# ---------------------------------------------------------------------------

def test_coverage_is_deterministic():
    facts = [
        _F("RM-21D-03", "21D-03-a", "design", "must include the mandatory Security Schedule", 0.9),
        _F("RM-21D-03", "21D-03-b", "design", "notify within 24 hours of detection", 0.8),
    ]
    a = compute_area_coverage(facts)
    b = compute_area_coverage(facts)
    assert a.model_dump() == b.model_dump()
    assert a.model_dump_json() == b.model_dump_json()


def test_area_covers_all_six_controls_and_summaries_add_up():
    cov = compute_area_coverage([])
    assert [c.control_id for c in cov.controls] == [
        "RM-21D-01", "RM-21D-02", "RM-21D-03", "RM-21D-04", "RM-21D-05", "RM-21D-06"]
    assert cov.area_id == "21D" and cov.registry_sha256
    total_items = sum(c.total_items for c in cov.controls)
    assert sum(cov.item_summary.values()) == total_items
    assert sum(cov.control_summary.values()) == 6


# ---------------------------------------------------------------------------
# 4. End-to-end against the real PowerGrid policy (offline stub), if present.
# ---------------------------------------------------------------------------

def test_pdf_demo_spans_all_three_buckets_with_real_quotes():
    from eval.run_coverage import DEFAULT_DOC, build_coverage

    if not Path(DEFAULT_DOC).exists():
        pytest.skip("sample PowerGrid PDF not present")
    cov, facts = build_coverage(Path(DEFAULT_DOC), live=False)

    s = cov.item_summary
    assert s["present"] > 0 and s["ambiguous"] > 0 and s["absent"] > 0
    # Every non-absent item carries a real, provenance-verified verbatim quote.
    for c in cov.controls:
        for it in c.items:
            if it.status != "absent":
                assert it.evidence and it.evidence[0].source_quote.strip()
    # The compliant 24h doc trips no veto.
    assert all(not c.veto_capped for c in cov.controls)
