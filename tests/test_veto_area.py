"""Area/leaf veto scope — the bug fix: a veto with `control_area` (no single `control_id`)
must actually FIRE across the area, not be silently dropped by the per-control filter.

Before the fix, ``[r for r in veto_rules() if r.get("control_id") == control_id]`` discarded
any rule that scoped itself to the AREA (``control_area: "21D"``), because such a rule has no
``control_id`` and ``None`` never equals a control id — so it silently never fired. The fix
honours ``control_id`` / ``control_ids`` / ``control_area``. These tests assert a crafted
negative-evidence fact DOES trip a veto (not merely that the rule resolves), that the area
scope reaches every RM-21D-* control but no control outside the area, and that every veto rule
in the ruleset resolves to at least one real control (a regression guard for the silent drop).
"""

from __future__ import annotations

from atlas.engine import ruleset as R
from atlas.engine.coverage import compute_area_coverage
from atlas.engine.models import ExtractedFact
from atlas.engine.veto import _rule_applies, evaluate_vetoes

AREA_VETO = "VETO-RM21D-AREA-ACCESS-BEFORE-ASSESSMENT"
# A crafted supply-chain defect: access is granted to the supplier BEFORE the assessment
# that is supposed to gate it. Hits all four context patterns of the area veto.
DEFECT = "Suppliers may be granted production access before the security assessment is completed"


def _F(control, quote, *, item=None, kind="design", page=1, doc="bad_policy.pdf"):
    return ExtractedFact(control_id=control, evidence_kind=kind, claim="located",
                         source_quote=quote, doc_id=doc, page=page, confidence=0.9,
                         evidence_item_id=item)


# ---------------------------------------------------------------------------
# 1. A crafted defect actually fires the area veto (the heart of step 6).
# ---------------------------------------------------------------------------

def test_crafted_defect_fires_the_area_veto():
    vetoes = evaluate_vetoes("RM-21D-03", [_F("RM-21D-03", DEFECT)])
    assert len(vetoes) == 1, "the crafted access-before-assessment defect must fire a veto"
    v = vetoes[0]
    assert v.veto_id == AREA_VETO
    assert v.defeats_ref == "Art 21(2)(d)"
    assert v.matched_quote == DEFECT
    assert "access precedes" in v.rationale


def test_area_veto_reaches_every_rm21d_control_but_nothing_outside_the_area():
    # Same defect under another RM-21D-* control fires too (area scope, not a single id).
    assert len(evaluate_vetoes("RM-21D-05", [_F("RM-21D-05", DEFECT)])) == 1
    # A non-21D control is outside the area -> the area veto must NOT fire.
    assert evaluate_vetoes("RM-21B-01", [_F("RM-21B-01", DEFECT)]) == []


def test_area_scoped_rule_would_have_been_silently_dropped_by_the_old_filter():
    # Re-create the OLD behaviour and show it dropped the area rule; the NEW _rule_applies
    # picks it up. This is the exact silent-never-fires bug the fix closes.
    rule = next(r for r in R.veto_rules() if r["id"] == AREA_VETO)
    assert rule.get("control_id") is None                  # no single control id...
    assert rule.get("control_id") != "RM-21D-03"           # ...so the old `==` filter dropped it
    assert _rule_applies(rule, "RM-21D-03") is True        # the fix resolves it via control_area


# ---------------------------------------------------------------------------
# 2. The fired veto caps the control's coverage (can never read 'present').
# ---------------------------------------------------------------------------

def test_vetoed_control_coverage_is_capped():
    facts = [
        _F("RM-21D-03", "must include the mandatory Security Schedule", item="21D-03-a"),
        _F("RM-21D-03", DEFECT, item="21D-03-a"),
    ]
    cc = next(c for c in compute_area_coverage(facts).controls if c.control_id == "RM-21D-03")
    assert cc.veto_capped is True
    assert cc.coverage_state != "present"
    assert any(v.veto_id == AREA_VETO for v in cc.vetoes)


# ---------------------------------------------------------------------------
# 3. Regression guard: no veto rule is silently un-scoped (the bug class).
# ---------------------------------------------------------------------------

def test_every_veto_rule_resolves_to_at_least_one_control():
    all_ids = (
        [c["id"] for c in R.criteria()] + [c["id"] for c in R.supply_chain_controls()]
    )
    for rule in R.veto_rules():
        resolved = [cid for cid in all_ids if _rule_applies(rule, cid)]
        assert resolved, f"veto {rule.get('id')!r} resolves to NO control — it would never fire"


def test_compliant_access_clause_does_not_fire_the_area_veto():
    # The PowerGrid doc grants access UNTIL the assessment is complete (compliant) — the
    # area veto keys on 'before/prior to/without', not 'until', so it must stay silent.
    compliant = "No supplier may be granted production access until the assessment is complete"
    assert evaluate_vetoes("RM-21D-03", [_F("RM-21D-03", compliant)]) == []
