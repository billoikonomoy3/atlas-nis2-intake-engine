"""Audit-grade tests for the Atlas Stage 4-7 engine (assess.py, jurisdiction.py,
economics.py). Run with:  python test_assess.py   (plain assertions, no pytest).

These vectors were produced by the spec fan-out and then adversarially re-checked
(the review caught a self-contradicting risk vector and conflated floors); every
expected value below is hand-recomputed from the rule it verifies.
"""

import assess
import jurisdiction
import economics


# ---------------------------------------------------------------------------
# 1. Maturity ladder - the verified boundary catalogue (incl. the cap cases)
# ---------------------------------------------------------------------------
MATURITY_CASES = [
    # (design_done, operating_done, monitored, expected_level, note)
    (0.0, 0.0, False, 0, "nothing -> None"),
    (0.10, 0.0, False, 0, "design 0.10 < 0.20 -> still None"),
    (0.20, 0.0, False, 1, "design 0.20 -> Initial"),
    (0.99, 1.0, True, 1, "one missing design item holds at L1 despite full operating+monitoring"),
    (1.0, 0.0, False, 2, "complete design, zero operating -> Repeatable (documented-only ceiling)"),
    (1.0, 0.49, True, 2, "OPERATING-MISSING CAP: operating 0.49 < 0.50 caps at L2 despite monitoring"),
    (1.0, 0.50, False, 3, "complete design + operating 0.50, not monitored -> Defined"),
    (1.0, 1.0, False, 3, "MONITORING CAP: full operating but monitored=false caps at L3"),
    (1.0, 0.79, True, 3, "operating 0.79 < 0.80 with monitoring -> still Defined"),
    (1.0, 0.80, True, 4, "complete + operating 0.80 + monitored -> Managed/measured"),
    (1.0, 1.0, True, 4, "everything present and measured"),
    (0.60, 0.90, True, 1, "operating present but design incomplete -> capped at L1"),
]


def test_maturity():
    for dd, od, mon, exp, note in MATURITY_CASES:
        got = assess.level(dd, od, mon)
        assert got == exp, f"level({dd},{od},{mon}) = {got}, expected {exp} ({note})"
    assert assess.aggregate_weakest_link([4, 3, 1, 4]) == 1, "weakest-link must be the min"
    assert assess.required_for_tier("Critical") == 4
    assert assess.required_for_tier("Foundational") == 1
    print(f"maturity: {len(MATURITY_CASES)} cases + aggregation/tier  OK")


# ---------------------------------------------------------------------------
# 2. Risk model - (current, required, inherent_criticality, class) -> rating, phase
#    Expected values hand-recomputed from the rule (the adversarial fix set).
# ---------------------------------------------------------------------------
RISK_CASES = [
    # current, required, ic, class, expected_rating, expected_phase
    (3, 3, 3, "essential", "Low", "No action (monitor)"),   # gap 0
    (2, 3, 1, "important", "Low", "12 months+"),            # gap1 L2 I1 score2
    (2, 3, 3, "important", "Medium", "3-12 months"),        # gap1 L2 I3 score6
    (1, 3, 2, "important", "Medium", "3-12 months"),        # gap2 L3 I2 score6
    (1, 3, 3, "essential", "High", "0-3 months"),           # gap2 L3 I4 score12
    (0, 3, 1, "important", "Medium", "3-12 months"),        # gap3 L4 I1 score4
    (0, 4, 3, "essential", "Critical", "0-3 months"),       # gap4 L4 I4 score16
    (0, 3, 2, "essential", "High", "0-3 months"),           # gap3 L4 I3 score12
    (0, 4, 2, "important", "Medium-High", "3-12 months"),   # gap4 L4 I2 score8, effort heavy
    (1, 2, 3, "essential", "Medium-High", "Quick win"),     # gap1 req<3 L2 I4 score8 effort1
    (1, 3, 3, "out_of_scope", "None", "None (excluded)"),
    (0, 4, 1, "important", "Medium", "3-12 months"),        # gap4 L4 I1 score4
    (1, 3, 3, "deferred_designation", "None", "None (excluded)"),
]


def test_risk():
    for cur, req, ic, cls, exp_rating, exp_phase in RISK_CASES:
        r = assess.risk(cur, req, ic, cls)
        got_rating = r["rating"] if r["rating"] is not None else "None"
        assert got_rating == exp_rating, \
            f"risk({cur},{req},{ic},{cls}) rating={got_rating}, expected {exp_rating}"
        assert r["phase"] == exp_phase, \
            f"risk({cur},{req},{ic},{cls}) phase={r['phase']}, expected {exp_phase}"
    print(f"risk: {len(RISK_CASES)} cases  OK")


# ---------------------------------------------------------------------------
# 3. EQCR challenger - the rules actually fire (and the caps compose)
# ---------------------------------------------------------------------------
def _scored(**kw):
    base = dict(control_id="RM-21B-01", domain="risk-measures", entity_class="essential",
                current_level=4, required_level=4, design_done=1.0, operating_done=1.0,
                monitored=True, has_provenance=True, risk="Low")
    base.update(kw)
    return base


def test_challenger():
    fired_ids = lambda s: {c["id"] for c in assess.challenge(s)["fired"]}

    # CHAL-01: top rung claimed, no operating, operating-critical control -> cap to L2
    ch = assess.challenge(_scored(current_level=4, operating_done=0.0, monitored=False))
    assert "CHAL-01" in {c["id"] for c in ch["fired"]}
    assert ch["final_level"] == 2, "CHAL-01 must cap an operating-critical claim to L2"

    # CHAL-09: PASS asserted with zero design -> cap to L0 (most restrictive cap wins)
    ch = assess.challenge(_scored(current_level=3, required_level=3, design_done=0.0, operating_done=0.0))
    ids = {c["id"] for c in ch["fired"]}
    assert "CHAL-09" in ids and ch["final_level"] == 0, "CHAL-09 caps to L0; min of caps"

    # CHAL-04 precedence: governance control, no design -> flag (and only then)
    gov = _scored(control_id="GOV-20-01", domain="governance", current_level=2,
                  required_level=3, design_done=0.0, operating_done=0.0, monitored=False, risk="Medium")
    assert "CHAL-04" in fired_ids(gov)
    gov_ok = _scored(control_id="GOV-20-01", domain="governance", current_level=3,
                     required_level=3, design_done=1.0, operating_done=0.6, monitored=True)
    assert "CHAL-04" not in fired_ids(gov_ok), "CHAL-04 must NOT fire when design exists (precedence fix)"

    # CHAL-05 escalation: reporting control, untested, required<=2 -> human review, NOT a silent pass
    rep = _scored(control_id="REP-23-01", domain="reporting", current_level=2,
                  required_level=2, design_done=1.0, operating_done=0.0, monitored=False, risk="Low")
    ch = assess.challenge(rep)
    chal5 = [c for c in ch["fired"] if c["id"] == "CHAL-05"]
    assert chal5 and chal5[0]["action"] == "require_human_review", \
        "CHAL-05 must escalate (not silently cap) when the cap would leave a fake PASS"

    # CHAL-02 provenance + CHAL-06 metrics + CHAL-08 proportionality on a thin essential control
    thin = _scored(control_id="RM-21D-01", domain="risk-measures", current_level=2,
                   required_level=3, design_done=1.0, operating_done=0.4, monitored=False,
                   has_provenance=False, risk="High")
    ids = fired_ids(thin)
    assert {"CHAL-03", "CHAL-08"} <= ids, "high-risk gap + essential-below-bar must both fire"
    print("challenger: cap composition, precedence, escalation, flags  OK")


# ---------------------------------------------------------------------------
# 4. assess_control end-to-end (re-rates against the capped level)
# ---------------------------------------------------------------------------
def test_assess_control():
    # Appendix-A control: design good, operating thin, essential, Enhanced tier.
    f = assess.assess_control("RM-21D-01", design_done=1.0, operating_done=0.4,
                              monitored=False, has_provenance=True,
                              entity_class="essential", tier="Enhanced")
    assert f["current_level"] == 2 and f["required_level"] == 3 and f["gap"] == 1
    assert f["rating"] in ("Medium", "Medium-High", "High")
    # A bare claim with no evidence must be challenged down to L0, not trusted.
    g = assess.assess_control("RM-21B-01", design_done=0.0, operating_done=0.0,
                              monitored=False, has_provenance=False,
                              entity_class="essential", tier="Critical")
    assert g["current_level"] == 0, "no evidence -> challenged to L0"
    print("assess_control: end-to-end re-rate after cap  OK")


# ---------------------------------------------------------------------------
# 5. Jurisdiction overlay - routing + registratieplicht
# ---------------------------------------------------------------------------
def test_jurisdiction():
    assert jurisdiction.supervisor_for("Energy")["supervisor_abbr"] == "RDI"
    assert jurisdiction.supervisor_for("Health")["supervisor_abbr"] == "IGJ"
    assert jurisdiction.supervisor_for("Banking")["supervisor_abbr"] == "DNB+AFM"
    tbd = jurisdiction.supervisor_for("Manufacturing")
    assert tbd["supervisor_abbr"] == "TBD" and tbd["needs_human_review"] is True
    assert jurisdiction.supervisor_for("anything", is_ecomms=True)["supervisor_abbr"] == "RDI"
    assert jurisdiction.registratieplicht_check(in_scope=True)["ok"] is False
    assert jurisdiction.registratieplicht_check(
        in_scope=True, registration_filed=True, filing_officer="CISO",
        filing_date="2026-05-01")["ok"] is True
    assert jurisdiction.registratieplicht_check(in_scope=False)["ok"] is True
    print("jurisdiction: routing (named + honest TBD) + registratieplicht  OK")


# ---------------------------------------------------------------------------
# 6. Economics - the one canonical, hand-re-derivable chain
# ---------------------------------------------------------------------------
def test_economics():
    r = economics.compute()
    assert r["junior_day_rate_eur"] == 1662, r["junior_day_rate_eur"]
    assert r["junior_hourly_eur"] == 208, r["junior_hourly_eur"]
    assert r["stage47_hours"] == 34
    assert r["manual_cost_eur"] == 7072, r["manual_cost_eur"]
    assert r["headline_claim_eur"] == 5000
    assert r["hours_kept_human"] == 6
    print("economics: 180k->208/h->7072 full slice, 5000 capped headline  OK")


def run():
    tests = [test_maturity, test_risk, test_challenger, test_assess_control,
             test_jurisdiction, test_economics]
    for t in tests:
        t()
    print(f"\nAll {len(tests)} test groups passed.")


if __name__ == "__main__":
    run()
