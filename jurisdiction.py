"""Atlas - Netherlands (Cbw) jurisdiction overlay.

The EU NIS2 baseline is not the law any single client is judged against; Atlas
ships into a jurisdiction. This module is the Dutch skin on the same deterministic
gold layer - NOT a new engine. It (1) states the governing law by date (Wbni now,
Cbw on entry), (2) routes each classified entity to its NAMED Dutch supervisor,
(3) splits incident output into a Cbw-meldplicht track and a GDPR datalek track,
and (4) checks the registratieplicht has actually been filed.

Legally precise as of 24 June 2026 and adversarially verified. Where the source
does not name a supervisor, this module says TBD and routes to human review rather
than inventing one - the no-judgment-leakage rule. Pure data + pure functions,
offline, every line re-derivable, DRAFT - REQUIRES REVIEW.
"""

from __future__ import annotations

DRAFT = "DRAFT - REQUIRES REVIEW"

# ---------------------------------------------------------------------------
# Governing law by date (the precise line for the report)
# ---------------------------------------------------------------------------

GOVERNING_LAW = {
    "current_statute": "Wet beveiliging netwerk- en informatiesystemen (Wbni) - the "
        "Dutch NIS1 implementing statute - remains the enforceable law as of 24 June 2026.",
    "future_statute": "Cyberbeveiligingswet (Cbw), Eerste Kamer dossier 36.764 - the "
        "NIS2 transposition; repeals the Wbni on entry into force (prospectively).",
    "status_note": "As of 24 June 2026 the Cbw is NOT YET IN FORCE: passed the Tweede "
        "Kamer 15 April 2026 (with the Wwke/CER transposition), in Eerste Kamer committee "
        "(nota n.a.v. het verslag 17 June 2026; nadere procedure 23 June 2026). Entry is "
        "by koninklijk besluit on a date still to be set, and may be staggered per article.",
    "line_for_report": "Prepared against the Netherlands Cyberbeveiligingswet (Cbw, dossier "
        "36.764); as of 24 June 2026 the Cbw is not yet in force and today's enforceable "
        "liability remains under the Wet beveiliging netwerk- en informatiesystemen "
        "(Wbni / NIS1), which the Cbw repeals on entry into force by koninklijk besluit.",
}

# ---------------------------------------------------------------------------
# Supervisor routing - assert ONLY where the source names a supervisor
# ---------------------------------------------------------------------------

# (supervisor_abbr, supervisor_full). "TBD" => route to human/legal review.
_RDI = ("RDI", "Rijksinspectie Digitale Infrastructuur")
_IGJ = ("IGJ", "Inspectie Gezondheidszorg en Jeugd")
_FIN = ("DNB+AFM", "De Nederlandsche Bank + Autoriteit Financiele Markten")
_TBD = ("TBD", "Not named in the source - route to human/legal review")

SUPERVISOR_ROUTING = {
    # Named in the source:
    "Energy": _RDI,
    "Digital infrastructure": _RDI,
    "Health": _IGJ,
    "Banking": _FIN,
    "Financial market infrastructures": _FIN,
    # Honest gaps (no decentralised supervisor named) - do NOT invent:
    "Transport": _TBD,
    "Drinking water": _TBD,
    "Waste water": _TBD,
    "ICT service management (B2B)": _TBD,
    "Public administration": _TBD,
    "Space": _TBD,
    "Postal and courier services": _TBD,
    "Waste management": _TBD,
    "Manufacture, production and distribution of chemicals": _TBD,
    "Production, processing and distribution of food": _TBD,
    "Manufacturing": _TBD,
    "Digital providers": _TBD,
    "Research": _TBD,
}

_FIN_NOTE = ("DORA (Reg (EU) 2022/2554) is lex specialis for ICT risk in the financial "
             "sector and largely displaces NIS2 substance for in-scope entities - flag the "
             "NIS2/DORA overlap for legal review.")


def supervisor_for(sector: str, *, is_ecomms: bool = False) -> dict:
    """Deterministic supervisor lookup off the classified NIS2 sector.

    Public e-comms / telecom (the ECOMMS flag in scope.py, not a standalone Annex
    label) routes to RDI, which the source names for telecom explicitly.
    """
    if is_ecomms:
        abbr, full = _RDI
        return {"sector": sector or "Public e-comms / telecom", "supervisor_abbr": abbr,
                "supervisor_full": full,
                "note": "Telecom / public e-comms -> RDI (named in source); reached via the "
                        "ECOMMS flag, not a raw Annex-label lookup.",
                "needs_human_review": False, "status": DRAFT}
    abbr, full = SUPERVISOR_ROUTING.get(sector, _TBD)
    note = ""
    if abbr == "DNB+AFM":
        note = _FIN_NOTE
    elif abbr == "TBD":
        note = ("No decentralised supervisor named in the source for this sector; route to "
                "human/legal review against the Cbw implementing regulation. Do not infer one.")
    return {"sector": sector, "supervisor_abbr": abbr, "supervisor_full": full,
            "note": note, "needs_human_review": abbr == "TBD", "status": DRAFT}


# ---------------------------------------------------------------------------
# The three Dutch duties
# ---------------------------------------------------------------------------

THREE_DUTIES = [
    {"duty_nl": "Zorgplicht", "duty_en": "Duty of care (risk-management measures)",
     "nis2_ref": "NIS2 Art 21 (Cbw zorgplicht)",
     "description": "Appropriate and proportionate risk-management measures (Art 21(1)), with "
        "heavy Dutch emphasis on supply-chain dependency mapping (Art 21(2)(d)). Outcomes-based "
        "- not a fixed checklist and not a numeric-maturity threshold.",
     "atlas_check": "The 16-criteria design/operating evidence pass feeds the human "
        "proportionality judgment; it does NOT issue the zorgplicht pass/fail itself. Specific "
        "check: a maintained supply-chain / third-party dependency map exists (RM-21D-01)."},
    {"duty_nl": "Meldplicht", "duty_en": "Incident reporting duty",
     "nis2_ref": "NIS2 Art 23 (Cbw meldplicht; REP-23-01..04)",
     "description": "A Cbw-qualifying incident is reported to the competent sectoral supervisor "
        "AND the national CSIRT/NCSC on the staged Art 23 timeline. A personal-data breach in the "
        "same event triggers a SEPARATE GDPR datalek notification to the Autoriteit "
        "Persoonsgegevens - a different portal.",
     "atlas_check": "Verify a reporting procedure with the staged Art 23 timeline (24h / 72h / "
        "1-month) and correct dual routing, and assess every incident scenario against BOTH the "
        "Cbw track and the AP/GDPR track."},
    {"duty_nl": "Registratieplicht", "duty_en": "Registration duty",
     "nis2_ref": "Cbw registratieplicht (NIS2 register at Art 27 targets specific entity types)",
     "description": "In-scope entities must register THEMSELVES so the supervisor/NCSC know who is "
        "covered; for certain digital providers the data reaches the ENISA register. The obligation "
        "clients most often forget because it is administrative and self-triggering.",
     "atlas_check": "Explicit programmatic check that registration was actually FILED by an "
        "authorised officer (filed boolean + officer identity + dated filing), not merely planned. "
        "See registratieplicht_check()."},
]

INCIDENT_SPLIT = {
    "cbw_track": "Cbw meldplicht (NIS2 Art 23): significant cyber incident -> competent Dutch "
        "sectoral supervisor (per supervisor_for()) AND national CSIRT/NCSC, on the staged timeline "
        "(early warning without undue delay and in any event within 24h; notification within 72h; "
        "intermediate update on request; final report within one month). Driver: impact on continuity "
        "/ security of network and information systems.",
    "datalek_track": "GDPR datalek (Art 33/34): a personal-data breach in the same event -> a "
        "separate notification to the Autoriteit Persoonsgegevens, in principle within 72h, plus "
        "communication to affected individuals where high risk. Distinct legal basis, authority, portal.",
    "note": "ONE EVENT CAN TRIGGER BOTH, down different portals, on parallel-but-distinct clocks; "
        "satisfying one does NOT discharge the other. The Cbw track is prospective (not enforceable "
        "until Cbw entry); the GDPR/AP datalek track is enforceable TODAY.",
}

ART20_LIABILITY = {
    "framing": "An Art 20 finding in a Dutch report is a corporate- AND personal-liability vector, "
        "not a mere technical gap. Art 20 requires the management body to APPROVE the measures, "
        "OVERSEE implementation, and complete mandatory training (Atlas GOV-20-01 / GOV-20-02).",
    "doctrine_nl": "Bestuurdersaansprakelijkheid (director liability). Boards must complete cyber "
        "training and can be held accountable for negligent oversight; in extreme wilful-neglect / "
        "systemic-failure cases, inadequate zorgplicht execution can expose individual board members "
        "to PERSONAL liability under the Dutch Civil Code - enforceable only once the Cbw is in force.",
    "why_it_matters": "Surface a weak GOV-20-* result to the board in board language as a dual "
        "corporate-and-personal exposure, never averaged away among control scores.",
}

CAVEATS = [
    f"{DRAFT}: a deterministic first pass; confirm with a qualified Dutch legal reviewer before reliance.",
    "Cbw NOT in force as of 24 June 2026 (dossier 36.764); today's enforceable liability sits under the Wbni.",
    "Supervisor routing asserts a supervisor only where the source names one (RDI / IGJ / DNB+AFM); all "
        "other sectors are TBD and routed to human/legal review - never inferred.",
    "NIS2 is OUTCOMES-BASED (Art 21(1)); the maturity pass feeds, but does not replace, the proportionality test.",
    "NIS2 prescribes no maturity scale; the 0-4 ladder / tiers are conventions, not a safe harbour.",
    "Financial sector: DORA is lex specialis and largely displaces NIS2 substance for in-scope entities.",
    "Dual incident reporting (Cbw meldplicht + GDPR datalek) are independent obligations; the GDPR track is "
        "enforceable today, the Cbw track only on entry.",
    "Registratieplicht trigger is conservative (fires on in_scope) - confirm the exact Cbw register population.",
    "ISO/IEC 27001:2022 control text is never reproduced; ISO is referenced by clause number only.",
]


def registratieplicht_check(*, in_scope: bool, registration_filed: bool = False,
                            filing_officer: str | None = None,
                            filing_date: str | None = None) -> dict:
    """Deterministic prepare/confirm check: if in scope, registration must be evidenced
    as actually filed (filed + authorised officer + dated). Conservative trigger."""
    if not in_scope:
        return {"applicable": False, "ok": True,
                "message": "Entity not in scope - registratieplicht not triggered.", "status": DRAFT}
    missing = []
    if not registration_filed:
        missing.append("filing confirmation / receipt (not merely a plan)")
    if not filing_officer:
        missing.append("authorised filing officer (authority to bind)")
    if not filing_date:
        missing.append("filing date with provenance (portal, reference, date)")
    if missing:
        return {"applicable": True, "ok": False,
                "message": "registratieplicht NOT evidenced as filed - the obligation clients most "
                           "often forget. Missing: " + "; ".join(missing) + ". Prepare/confirm "
                           "(prospective Cbw duty; confirm exact register population).",
                "status": DRAFT}
    return {"applicable": True, "ok": True,
            "message": f"registratieplicht evidenced as filed by {filing_officer} on {filing_date} "
                       f"(confirm against the Cbw register population).", "status": DRAFT}


if __name__ == "__main__":
    print("Governing law:", GOVERNING_LAW["line_for_report"])
    for s in ("Energy", "Health", "Banking", "Transport", "Manufacturing"):
        r = supervisor_for(s)
        print(f"  {s:38s} -> {r['supervisor_abbr']}")
    print(registratieplicht_check(in_scope=True)["message"])
