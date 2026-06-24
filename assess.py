"""Atlas - NIS2 Stage 4-7 assessment engine (deterministic core).

This is the layer the Stage-3 intake (scope.py) hands off to: it turns per-control
EVIDENCE into a maturity level, a gap against the proportionate bar, a risk rating,
a board-ready remediation phase, and an adversarial EQCR challenge - control by
control, exactly as a Big-4 readiness engagement does in Stages 4 (evidence),
5 (assessment), 6 (review) and 7 (reporting).

Everything here is a PURE function of its inputs. No LLM in the judgment path,
no network, standard library only. Every level, gap, rating and challenge note is
hand-re-derivable from the rules below, which is what makes a verdict defensible.

THREE GUARDRAILS travel with every output (they are the whole point):
  1. The 0-4 ladder and the Foundational/Standard/Enhanced/Critical tiers are
     CONSULTING CONVENTIONS (CMMI / NIST CSF tier flavoured). NIS2 prescribes NO
     numeric maturity scale; a high level is NOT a statutory safe harbour and a
     readiness gap is NOT a finding of legal (non-)compliance. Art 21(1)
     proportionality ("appropriate and proportionate" to risk, size, exposure)
     is the regulator's outcomes-based test. design-vs-operating is the right
     vocabulary for GATHERING evidence; it must not harden into the legal gate.
  2. Output keys only to paraphrased NIS2 prose and NIST CSF 2.0 IDs. ISO/IEC
     27001:2022 is referenced by clause number only (in criteria.py), never its text.
  3. Every emitted artefact is DRAFT - REQUIRES REVIEW.

Specs designed by a specialist fan-out and adversarially verified (the review
caught a maturity-ladder legal overclaim, a self-contradicting risk test vector,
an operator-precedence bug in CHAL-04, a CHAL-05 "fake PASS" path, and conflated
score/maturity floors - all fixed here).
"""

from __future__ import annotations

from criteria import CRITERIA

DRAFT = "DRAFT - REQUIRES REVIEW"

# ---------------------------------------------------------------------------
# Stage 5 - the 0-4 maturity ladder
# ---------------------------------------------------------------------------

LEVELS = [
    (0, "None", "No credible design evidence; the control as written does not exist."),
    (1, "Initial / ad hoc", "Partial design only; documented control incomplete, practice ad hoc."),
    (2, "Repeatable (documented)", "Design complete on paper, but no/insufficient proof it ran over the period."),
    (3, "Defined (operating)", "Complete design plus substantive operating evidence, not yet measured on a cadence."),
    (4, "Managed / measured", "Complete design, strong operating evidence, and active monitoring with metrics."),
]

LEVEL_NAME = {lv: name for lv, name, _ in LEVELS}

# Proportionate required rung per proportionality tier (monotonic: each tier one
# rung higher). The essential->Enhanced and systemic->Critical SCORE floors in
# criteria.py therefore actually raise the required rung.
REQUIRED_BY_TIER = {
    "Foundational": 1,
    "Standard": 2,
    "Enhanced": 3,
    "Critical": 4,
}


def _clamp01(x: float) -> float:
    return min(max(float(x), 0.0), 1.0)


def level(design_done: float, operating_done: float, monitored: bool) -> int:
    """Pure maturity rung 0..4 from evidence completeness.

    design_done / operating_done are fractions in [0,1] of the requested DESIGN
    and OPERATING evidence items present (with provenance). `monitored` = live
    metrics + a defined review cadence.

    The rule of sequence is enforced: operating evidence is meaningless until the
    design is complete, and operating evidence is REQUIRED for the top rungs - a
    perfectly written, monitored policy with no proof it ran can never exceed L2.
    """
    d = _clamp01(design_done)
    o = _clamp01(operating_done)
    if d < 0.20:
        return 0
    if d < 1.0:                       # design incomplete -> capped at Initial
        return 1
    if o < 0.50:                      # complete design, no real operating proof
        return 2
    if (not monitored) or o < 0.80:   # operating present but not measured -> Defined
        return 3
    return 4                          # design + strong operating + monitoring


def aggregate_weakest_link(sub_levels: list[int]) -> int:
    """Stage-5 aggregation across sub-criteria: the WEAKEST link, never the mean.

    One neglected duty drags the whole control down; a strong sub-control cannot
    average a weak one away. The result is the minimum, so it is hand-re-derivable.
    """
    if not sub_levels:
        raise ValueError("aggregate_weakest_link needs at least one sub-level")
    return min(sub_levels)


def required_for_tier(tier: str) -> int:
    return REQUIRED_BY_TIER.get(tier, 1)


# ---------------------------------------------------------------------------
# Stage 5 - gap + risk (likelihood x impact)
# ---------------------------------------------------------------------------

_RATING_COLOR = {
    "Low": "#2E7D32", "Medium": "#F9A825", "Medium-High": "#EF6C00",
    "High": "#D84315", "Critical": "#B71C1C", None: None,
}

_LIKELIHOOD_BY_GAP = {0: 1, 1: 2, 2: 3, 3: 4, 4: 4}

_NO_RATING_CLASSES = {"out_of_scope", "deferred_designation"}
_VALID_CLASSES = {"essential", "important"} | _NO_RATING_CLASSES


def _effort(gap: int, required_level: int) -> tuple[int, str | None]:
    """Remediation lift: gap size + a surcharge when the required rung needs an
    operating period (>=3). Zero when nothing is open."""
    if gap == 0:
        return 0, None
    e = gap + (1 if required_level >= 3 else 0)
    band = ("Quick win" if e == 1 else "Light" if e == 2
            else "Moderate" if e == 3 else "Heavy")
    return e, band


def risk(current_level: int, required_level: int, inherent_criticality: int,
         entity_class: str) -> dict:
    """Deterministic gap + risk rating + remediation phase for one control.

    likelihood is driven by the gap; impact by inherent_criticality plus an
    essential-entity weight. score = L x I, banded to a rating; the rating and
    effort band pick the roadmap phase. out_of_scope / deferred_designation
    controls are not rated. A flag for human review, never a legal verdict.
    """
    if entity_class not in _VALID_CLASSES:
        raise ValueError(f"unknown entity_class: {entity_class!r}")
    if entity_class in _NO_RATING_CLASSES:
        return {"rating": None, "color": None, "L": None, "I": None, "score": None,
                "gap": None, "effort_units": None, "effort_band": None,
                "phase": "None (excluded)",
                "note": "control not assessed for this entity class", "status": DRAFT}

    gap = max(0, min(4, int(required_level) - int(current_level)))
    ic = max(1, min(3, int(inherent_criticality)))
    req = max(0, min(4, int(required_level)))

    L = _LIKELIHOOD_BY_GAP[gap]
    I = max(1, min(4, ic + (1 if entity_class == "essential" else 0)))
    e_units, e_band = _effort(gap, req)

    if gap == 0:                       # a satisfied control is never a finding
        return {"rating": "Low", "color": _RATING_COLOR["Low"], "L": 1, "I": I,
                "score": 1 * I, "gap": 0, "effort_units": 0, "effort_band": None,
                "phase": "No action (monitor)",
                "note": "required bar met or exceeded", "status": DRAFT}

    score = L * I
    if L == 4 and I == 4:
        rating = "Critical"            # weakest-link override at 16
    elif score >= 12:
        rating = "High"
    elif score >= 8:
        rating = "Medium-High"
    elif score >= 4:
        rating = "Medium"
    else:
        rating = "Low"

    if rating in ("Critical", "High", "Medium-High") and e_band == "Quick win":
        phase = "Quick win"
    elif rating in ("Critical", "High"):
        phase = "0-3 months"
    elif rating in ("Medium-High", "Medium"):
        phase = "3-12 months"
    else:                              # Low with gap > 0
        phase = "12 months+"

    return {"rating": rating, "color": _RATING_COLOR[rating], "L": L, "I": I,
            "score": score, "gap": gap, "effort_units": e_units,
            "effort_band": e_band, "phase": phase,
            "note": "L x I banded; weakest-link Critical override at L4xI4; "
                    "effort/phase re-derivable from gap + required_level",
            "status": DRAFT}


# ---------------------------------------------------------------------------
# Stage 6 - the deterministic EQCR challenger (tries to BREAK every PASS)
# ---------------------------------------------------------------------------

# Controls whose top rung legitimately needs operating evidence (performance-
# demonstrated + the time-bound Art 23 stages). Disjoint from the 6 controls
# that may reach L3 on design alone. Verified partition over the exact 16 ids.
OPERATING_CRITICAL = {
    "RM-21B-01", "RM-21C-01", "RM-21E-01", "RM-21F-01", "RM-21G-01",
    "RM-21I-01", "RM-21J-01", "REP-23-01", "REP-23-02", "REP-23-04",
}

_RATING_RANK = {"Low": 1, "Medium": 2, "Medium-High": 3, "High": 4, "Critical": 5, None: 0}

_NL_CAVEAT = ("Prepare against the Cbw; today's enforceable liability still sits "
              "under the Wbni (NIS1) - the Cbw (dossier 36.764) is not yet in force.")


def challenge(scored: dict) -> dict:
    """Run the EQCR challenger pipeline over one scored control.

    `scored` carries: control_id, domain, entity_class, current_level,
    required_level, design_done, operating_done, monitored, has_provenance,
    risk (rating string), and optional cross_border_systemic / sub_levels.

    Returns {final_level, gap, fired:[{id,name,action,severity,note}]}.
    Deterministic pipeline: integrity -> sequence -> caps (final = min of all
    caps) -> recompute gap -> flags / human-review on the FINAL level.
    """
    cid = scored["control_id"]
    domain = scored.get("domain", "")
    cls = scored.get("entity_class", "important")
    cur = int(scored["current_level"])
    req = int(scored["required_level"])
    dd = float(scored.get("design_done", 0.0))
    od = float(scored.get("operating_done", 0.0))
    monitored = bool(scored.get("monitored", False))
    has_prov = bool(scored.get("has_provenance", False))
    sub_levels = scored.get("sub_levels") or []
    xborder = scored.get("cross_border_systemic", "none")

    fired: list[dict] = []

    def fire(rid, name, action, severity, note):
        fired.append({"id": rid, "name": name, "action": action,
                      "severity": severity, "note": note + " " + DRAFT})

    # --- integrity (raw input) ---
    if cur > 4 or req > 4 or cur < 0 or req < 0:
        fire("CHAL-10", "Level out of the 0-4 ladder", "require_human_review", "low",
             f"{cid}: level out of range (current={cur}, required={req}); the ladder is 0-4.")
    raw_gap = max(0, req - cur)
    reported_gap = scored.get("gap")
    if reported_gap is not None and int(reported_gap) != raw_gap:
        fire("CHAL-11", "Reported gap inconsistent with levels", "require_human_review", "low",
             f"{cid}: reported gap {reported_gap} != max(0, {req}-{cur})={raw_gap}.")

    # --- rule of sequence ---
    if od >= 1.0 and dd <= 0.0:
        fire("CHAL-07", "Operating tested before design established", "require_human_review", "med",
             f"{cid}: operating evidence present while design is not established - "
             f"you only test operating once the control as written is sound.")

    # --- caps: collect, then final level = min of all applicable caps ---
    caps = [cur]

    if cur >= req and cur >= 1 and dd <= 0.0:
        caps.append(0)
        fire("CHAL-09", "PASS asserted with no design evidence", "cap_level", "high",
             f"{cid}: reported at L{cur} meeting L{req} but no design evidence exists; "
             f"capping to L0 until at least one design artefact with provenance is attached.")

    if cur >= 3 and od <= 0.0 and cid in OPERATING_CRITICAL:
        caps.append(2)
        fire("CHAL-01", "Top rung without operating evidence (operating-critical)", "cap_level", "high",
             f"{cid}: claimed L{cur} but no operating evidence on an operating-critical control; "
             f"capping to L2 until a period sample shows it actually operated.")

    if sub_levels:
        wl = aggregate_weakest_link(sub_levels)
        if cur > wl:
            caps.append(wl)
            fire("CHAL-12", "Sub-criteria not aggregated by weakest link", "cap_level", "med",
                 f"{cid}: rolled up to L{cur} but weakest sub-criterion is L{wl}; capping to the weakest link.")

    # reporting control claiming compliance with no tested/exercised evidence
    is_reporting = domain == "reporting" or cid.startswith("REP-")
    if is_reporting and cur >= req and od <= 0.0:
        if req <= 2:   # capping to L2 would NOT create a gap -> escalate, never a silent fake PASS
            fire("CHAL-05", "Reporting control unexercised but reads as met", "require_human_review", "med",
                 f"{cid}: claims it meets L{req} with no tested/exercised evidence; a documented procedure "
                 f"alone cannot show the 24h/72h/1-month Art 23 deadlines can be met - escalated to human review.")
        else:
            caps.append(2)
            fire("CHAL-05", "Reporting control claiming compliance, untested", "cap_level", "med",
                 f"{cid}: claims L{cur} with no tested/exercised Art 23 evidence; capping to L2 until a drill "
                 f"or real timestamped submission exists. {_NL_CAVEAT}")

    final_level = min(caps)
    gap = max(0, req - final_level)

    # --- flags / human review on the FINAL level ---
    if cur >= req and not has_prov:
        fire("CHAL-02", "PASS asserted but evidence lacks provenance", "require_human_review", "high",
             f"{cid}: meets its required level but evidence lacks provenance (doc/page/date); "
             f"a conclusion that cannot be traced to a dated source fails the four-eyes standard.")

    rating = scored.get("risk")
    if gap >= 1 and rating in ("High", "Critical"):
        fire("CHAL-03", "High/critical risk-rated gap", "require_human_review", "high",
             f"{cid}: open gap of {gap} level(s) risk-rated {rating}; a top-of-report finding that "
             f"needs an explicit management response - cannot be auto-cleared.")

    is_gov = domain == "governance" or cid.startswith("GOV-")
    if is_gov and dd <= 0.0:
        fire("CHAL-04", "Governance control without board sign-off evidence", "flag", "high",
             f"{cid}: no design evidence of management-body approval / oversight. Under NIS2 Art 20 this is "
             f"a corporate AND potential personal-liability vector (Dutch bestuurdersaansprakelijkheid), "
             f"not a technical gap only. {_NL_CAVEAT}")

    if final_level >= 3 and not monitored:
        fire("CHAL-06", "L3+ asserted without monitoring / metrics", "flag", "med",
             f"{cid}: assessed at L{final_level} but no metrics/KPIs/cadence evidenced; supply monitoring "
             f"evidence or reduce to the rung the evidence supports.")

    systemic = xborder in ("systemic", "sole_national")
    if (cls == "essential" or systemic) and final_level < req:
        sysnote = " (systemic / sole-national)" if systemic else ""
        fire("CHAL-08", "Core control below its proportionate expectation", "require_human_review", "high",
             f"{cid}: entity is {cls}{sysnote} and the control sits at L{final_level}, below its required L{req}. "
             f"This is a CHALLENGER PROMPT for human proportionality review, not an automatic finding - NIS2 is "
             f"outcomes-based and a maturity rung is evidence for, never a substitute for or safe harbour against, "
             f"the Art 21(1) judgment. {_NL_CAVEAT}")

    return {"final_level": final_level, "gap": gap, "fired": fired}


# ---------------------------------------------------------------------------
# Stage 7 - deterministic finding ordering for the report / roadmap
# ---------------------------------------------------------------------------

def order_findings(findings: list[dict]) -> list[dict]:
    """Total, re-derivable order: rating desc, score desc, effort asc,
    inherent_criticality desc, then id ascending. Unrated controls excluded."""
    rated = [f for f in findings if f.get("rating") is not None]
    return sorted(rated, key=lambda f: (
        -_RATING_RANK.get(f.get("rating"), 0),
        -(f.get("score") or 0),
        (f.get("effort_units") if f.get("effort_units") is not None else 99),
        -(f.get("inherent_criticality") or 0),
        f.get("control_id", ""),
    ))


# ---------------------------------------------------------------------------
# Convenience: assess one control end to end (Stage 4 inputs -> Stage 5/6 output)
# ---------------------------------------------------------------------------

_CRIT_BY_ID = {c["id"]: c for c in CRITERIA}


def assess_control(control_id: str, *, design_done: float, operating_done: float,
                   monitored: bool, has_provenance: bool, entity_class: str,
                   tier: str, cross_border_systemic: str = "none") -> dict:
    """Score one control from evidence completeness to a full Stage 5/6 finding."""
    crit = _CRIT_BY_ID[control_id]
    cur = level(design_done, operating_done, monitored)
    req = required_for_tier(tier)
    r = risk(cur, req, crit["inherent_criticality"], entity_class)
    scored = {
        "control_id": control_id, "domain": crit["domain"], "entity_class": entity_class,
        "current_level": cur, "required_level": req, "design_done": design_done,
        "operating_done": operating_done, "monitored": monitored,
        "has_provenance": has_provenance, "risk": r["rating"],
        "cross_border_systemic": cross_border_systemic,
    }
    ch = challenge(scored)
    # if the challenger capped the level, re-rate against the FINAL level
    if ch["final_level"] != cur:
        r = risk(ch["final_level"], req, crit["inherent_criticality"], entity_class)
    return {
        "control_id": control_id, "nis2_ref": crit["nis2_ref"], "domain": crit["domain"],
        "inherent_criticality": crit["inherent_criticality"],
        "raw_level": cur, "current_level": ch["final_level"], "level_name": LEVEL_NAME[ch["final_level"]],
        "required_level": req, "required_name": LEVEL_NAME[req], **r,
        "gap": ch["gap"], "challenges": ch["fired"], "status": DRAFT,
    }


if __name__ == "__main__":
    # The Appendix-A worked control: supply-chain (21(2)(d)) at an essential entity.
    f = assess_control("RM-21D-01", design_done=1.0, operating_done=0.4, monitored=False,
                       has_provenance=True, entity_class="essential", tier="Enhanced")
    print(f"{f['control_id']} ({f['nis2_ref']}): current L{f['current_level']} "
          f"({f['level_name']}) vs required L{f['required_level']} -> gap {f['gap']}, "
          f"risk {f['rating']} -> {f['phase']}")
    for c in f["challenges"]:
        print(f"  [{c['id']} {c['severity']}] {c['name']}")
