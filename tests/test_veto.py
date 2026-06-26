"""Disqualifying ("veto") findings — deterministic, data-driven, no model anywhere.

Regression coverage for the bug where a deliberately non-conformant supply-chain policy
(mock2) scored RM-21D-01 as "meets": 13 design clauses on the topic pushed design_done to
1.00 even though several of those clauses ARE the defects (e.g. a 30-calendar-day supplier
breach-notification window that cannot feed the entity's own Art 23 24h/72h cascade).

The mock2 document itself is not committed; tests/fixtures/mock2_rm21d_facts.json captures
what the extraction layer LOCATES + QUOTES from it (its "extracted findings"), which is the
exact input the deterministic scorer consumes.
"""

from __future__ import annotations

import json
from pathlib import Path

from atlas.engine.models import ExtractedFact
from atlas.engine.scoring import score_control
from atlas.engine.veto import evaluate_vetoes

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mock2_rm21d_facts.json"


def _mock2():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    facts = [ExtractedFact(control_id=data["control_id"], **f) for f in data["facts"]]
    return data["control_id"], facts, data["required_level"]


def _F(kind, quote, page, control="RM-21D-01", doc="policy.pdf", claim="established"):
    return ExtractedFact(control_id=control, evidence_kind=kind, claim=claim,
                         source_quote=quote, doc_id=doc, page=page, confidence=0.9)


# ---------------------------------------------------------------------------
# 1. The regression: mock2's RM-21D-01 is now vetoed, not "meets".
# ---------------------------------------------------------------------------

def test_mock2_rm21d_supplier_window_is_vetoed():
    control_id, facts, required = _mock2()
    f = score_control(control_id, facts, required)

    # Before the veto feature this fact-set scored achieved L2, gap 0, status "meets".
    assert f.design_done == 1.0 and f.operating_done == 0.0  # the presence signal is unchanged
    assert f.achieved_level == 1, "achieved rung must be capped at L1 by the veto"
    assert f.gap > 0, "a capped rung below the required bar must show a gap"
    assert f.status != "meets", "a vetoed control must never read as meets"
    assert f.status == "vetoed"
    assert f.veto_capped is True

    # The veto is surfaced explicitly so a reader sees WHY it failed.
    assert len(f.vetoes) == 1
    v = f.vetoes[0]
    assert v.veto_id == "VETO-RM21D-01-SUPPLIER-NOTIF-WINDOW"
    assert v.defeats_ref == "Art 23(4)(a)"          # an existing NIS2 ref in the ruleset
    assert "30 calendar days" in v.matched_quote     # the offending clause is cited
    assert v.rationale and "Art 23" in v.rationale
    assert "720h" in v.detail and "72h" in v.detail  # 30 days = 720h > the 72h ceiling

    # The rationale string itself carries the veto reason (it appears in the output).
    assert "VETO" in f.rationale and "Art 23(4)(a)" in f.rationale


# ---------------------------------------------------------------------------
# 2. No-veto controls score EXACTLY as before the change (no regression).
# ---------------------------------------------------------------------------

DESIGN_QUOTES = ["supplier security policy v3", "criticality rating method", "contract security clause"]


def test_no_veto_control_scores_identically_to_before():
    # Same fact-set as tests/test_scoring.test_meets_at_standard_with_documented_design.
    facts = [_F("design", DESIGN_QUOTES[i], page=i + 1) for i in range(3)]
    f = score_control("RM-21D-01", facts, 2)  # Standard requires L2

    # Pre-change values (unchanged): complete design, no operating -> L2 meets at Standard.
    assert f.achieved_level == 2
    assert f.required_level == 2
    assert f.gap == 0
    assert f.status == "meets"
    assert f.design_done == 1.0 and f.operating_done == 0.0

    # The new fields are inert when nothing is vetoed.
    assert f.vetoes == []
    assert f.veto_capped is False


def test_compliant_24h_supplier_window_does_not_veto():
    # A supplier-notification clause WITHIN the cascade must not fire the veto.
    facts = [
        _F("design", "Supplier Security Policy governs third parties", 1, doc="mock.docx"),
        _F("design", "Each supplier is assigned a criticality rating", 1, doc="mock.docx"),
        _F("design", "Suppliers must notify us of a security breach within 24 hours", 2, doc="mock.docx"),
    ]
    f = score_control("RM-21D-01", facts, 2)
    assert f.status == "meets"
    assert f.achieved_level == 2
    assert f.vetoes == []


# ---------------------------------------------------------------------------
# 3. The veto evaluator itself — deterministic + boundary behaviour.
# ---------------------------------------------------------------------------

def test_evaluate_vetoes_is_deterministic():
    _, facts, _ = _mock2()
    a = evaluate_vetoes("RM-21D-01", facts)
    b = evaluate_vetoes("RM-21D-01", facts)
    assert [v.model_dump() for v in a] == [v.model_dump() for v in b]


def test_window_exactly_at_ceiling_does_not_veto_but_over_does():
    at_ceiling = [_F("design", "Suppliers must report any breach within 72 hours", 1, doc="m.docx")]
    over = [_F("design", "Suppliers must report any breach within 73 hours", 1, doc="m.docx")]
    assert evaluate_vetoes("RM-21D-01", at_ceiling) == []      # 72h == ceiling -> ok
    assert len(evaluate_vetoes("RM-21D-01", over)) == 1        # 73h > ceiling -> veto


def test_long_window_without_supplier_context_does_not_veto():
    # A long window unrelated to supplier incident notification must not trip the rule.
    facts = [_F("design", "The board reviews the strategy within 30 calendar days", 1, doc="m.docx")]
    assert evaluate_vetoes("RM-21D-01", facts) == []


def test_veto_rules_are_scoped_per_control():
    # The seed rule targets RM-21D-01 only; the same clause under another control is inert.
    clause = "Suppliers must notify us of a security breach within 30 calendar days"
    assert evaluate_vetoes("RM-21B-01", [_F("design", clause, 1, control="RM-21B-01")]) == []
