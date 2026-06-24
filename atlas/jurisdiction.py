"""Netherlands (Cbw) jurisdiction overlay — the Dutch skin on the deterministic core.

NOT a second engine: it (1) states the governing law by date (Wbni now, Cbw on entry),
(2) routes a classified entity to its NAMED Dutch supervisor (and says TBD + routes to a
human where the source names none — no judgment leakage), (3) splits incident output into
a Cbw-meldplicht track and a separate GDPR datalek track, and (4) checks the
registratieplicht was actually filed. Pure data + pure functions, offline.

Legally precise as of 25 June 2026. DRAFT — REQUIRES REVIEW.
"""

from __future__ import annotations

DRAFT = "DRAFT — REQUIRES REVIEW"

GOVERNING_LAW = {
    "current_statute": "Wet beveiliging netwerk- en informatiesystemen (Wbni) — the Dutch NIS1 "
        "implementing statute — remains the enforceable law as of 25 June 2026.",
    "future_statute": "Cyberbeveiligingswet (Cbw), Eerste Kamer dossier 36.764 — the NIS2 "
        "transposition; repeals the Wbni on entry into force (prospectively).",
    "status_note": "As of 25 June 2026 the Cbw is NOT YET IN FORCE: passed the Tweede Kamer "
        "15 April 2026, in Eerste Kamer procedure. Entry is by koninklijk besluit on a date "
        "still to be set, and may be staggered per article.",
    "line_for_report": "Prepared against the Netherlands Cyberbeveiligingswet (Cbw, dossier "
        "36.764); as of 25 June 2026 the Cbw is not yet in force and today's enforceable "
        "liability remains under the Wet beveiliging netwerk- en informatiesystemen (Wbni / "
        "NIS1), which the Cbw repeals on entry into force by koninklijk besluit.",
}

_RDI = ("RDI", "Rijksinspectie Digitale Infrastructuur")
_IGJ = ("IGJ", "Inspectie Gezondheidszorg en Jeugd")
_FIN = ("DNB+AFM", "De Nederlandsche Bank + Autoriteit Financiële Markten")
_TBD = ("TBD", "Not named in the source — route to human/legal review")

# Assert a supervisor ONLY where the source names one; everything else is TBD.
SUPERVISOR_ROUTING = {
    "Energy": _RDI,
    "Digital infrastructure": _RDI,
    "Health": _IGJ,
    "Banking": _FIN,
    "Financial market infrastructures": _FIN,
}

_FIN_NOTE = ("DORA (Reg (EU) 2022/2554) is lex specialis for ICT risk in the financial sector and "
             "largely displaces NIS2 substance for in-scope entities — flag the NIS2/DORA overlap.")

REPORTING_CLOCKS = {
    "early_warning_hours": 24,
    "notification_hours": 72,
    "intermediate": "on request of the CSIRT/competent authority",
    "final_report": "within one month of the notification",
}


def supervisor_for(sector: str, *, is_ecomms: bool = False) -> dict:
    """Deterministic supervisor lookup off the classified NIS2 sector."""
    if is_ecomms:
        abbr, full = _RDI
        return {"sector": sector or "Public e-comms / telecom", "supervisor_abbr": abbr,
                "supervisor_full": full,
                "note": "Telecom / public e-comms -> RDI (named in source); reached via the ECOMMS "
                        "flag, not a raw Annex-label lookup.",
                "needs_human_review": False, "status": DRAFT}
    abbr, full = SUPERVISOR_ROUTING.get(sector, _TBD)
    note = ""
    if abbr == "DNB+AFM":
        note = _FIN_NOTE
    elif abbr == "TBD":
        note = ("No decentralised supervisor named in the source for this sector; route to human/"
                "legal review against the Cbw implementing regulation. Do not infer one.")
    return {"sector": sector, "supervisor_abbr": abbr, "supervisor_full": full, "note": note,
            "needs_human_review": abbr == "TBD", "status": DRAFT}


THREE_DUTIES = [
    {"duty_nl": "Zorgplicht", "duty_en": "Duty of care (risk-management measures)",
     "nis2_ref": "NIS2 Art 21 (Cbw zorgplicht)",
     "description": "Appropriate and proportionate risk-management measures (Art 21(1)), with heavy "
        "Dutch emphasis on supply-chain dependency mapping (Art 21(2)(d)). Outcomes-based — not a "
        "fixed checklist and not a numeric-maturity threshold.",
     "atlas_check": "The criteria design/operating evidence pass FEEDS the human proportionality "
        "judgment; it does NOT issue the zorgplicht pass/fail itself. Specific check: a maintained "
        "supply-chain / third-party dependency map exists (RM-21D-01)."},
    {"duty_nl": "Meldplicht", "duty_en": "Incident reporting duty",
     "nis2_ref": "NIS2 Art 23 (Cbw meldplicht; REP-23-01..04)",
     "description": "A Cbw-qualifying incident is reported to the competent sectoral supervisor AND "
        "the national CSIRT/NCSC on the staged Art 23 timeline. A personal-data breach in the same "
        "event triggers a SEPARATE GDPR datalek notification to the Autoriteit Persoonsgegevens.",
     "atlas_check": "Verify a reporting procedure with the staged Art 23 timeline (24h / 72h / "
        "1-month) and correct dual routing, and assess every incident scenario against BOTH the Cbw "
        "track and the AP/GDPR track."},
    {"duty_nl": "Registratieplicht", "duty_en": "Registration duty",
     "nis2_ref": "Cbw registratieplicht (NIS2 Art 27)",
     "description": "In-scope entities must register THEMSELVES so the supervisor/NCSC know who is "
        "covered. The obligation clients most often forget because it is administrative and "
        "self-triggering.",
     "atlas_check": "Explicit programmatic check that registration was actually FILED by an "
        "authorised officer (filed + officer identity + dated filing), not merely planned."},
]

INCIDENT_SPLIT = {
    "cbw_track": "Cbw meldplicht (NIS2 Art 23): significant cyber incident -> competent Dutch "
        "sectoral supervisor AND national CSIRT/NCSC, on the staged timeline (early warning within "
        "24h; notification within 72h; intermediate update on request; final report within one "
        "month). Driver: impact on continuity / security of network and information systems.",
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
        "OVERSEE implementation, and complete mandatory training (GOV-20-01 / GOV-20-02).",
    "doctrine_nl": "Bestuurdersaansprakelijkheid (director liability). Boards must complete cyber "
        "training and can be held accountable for negligent oversight; inadequate zorgplicht "
        "execution can, in extreme cases, expose individual board members to PERSONAL liability "
        "under the Dutch Civil Code — enforceable only once the Cbw is in force.",
    "why_it_matters": "Surface a weak GOV-20-* result to the board in board language as a dual "
        "corporate-and-personal exposure, never averaged away among control scores.",
}


def registratieplicht_check(*, in_scope: bool, registration_filed: bool = False,
                            filing_officer: str | None = None,
                            filing_date: str | None = None) -> dict:
    """If in scope, registration must be evidenced as actually FILED (filed + officer + dated)."""
    if not in_scope:
        return {"applicable": False, "ok": True,
                "message": "Entity not in scope — registratieplicht not triggered.", "status": DRAFT}
    missing = []
    if not registration_filed:
        missing.append("filing confirmation / receipt (not merely a plan)")
    if not filing_officer:
        missing.append("authorised filing officer (authority to bind)")
    if not filing_date:
        missing.append("filing date with provenance (portal, reference, date)")
    if missing:
        return {"applicable": True, "ok": False,
                "message": "registratieplicht NOT evidenced as filed. Missing: " + "; ".join(missing)
                           + ". Prepare/confirm (prospective Cbw duty; confirm exact register population).",
                "status": DRAFT}
    return {"applicable": True, "ok": True,
            "message": f"registratieplicht evidenced as filed by {filing_officer} on {filing_date} "
                       f"(confirm against the Cbw register population).", "status": DRAFT}


def jurisdiction_pack(*, sector: str | None, is_ecomms: bool, in_scope: bool,
                      entity_class: str) -> dict:
    """Assemble the full NL overlay for a classified entity (deterministic)."""
    sup = supervisor_for(sector or "", is_ecomms=is_ecomms)
    liability = entity_class in ("essential", "important")
    return {
        "governing_law": GOVERNING_LAW["line_for_report"],
        "supervisor": sup,
        "reporting_clocks": REPORTING_CLOCKS,
        "three_duties": THREE_DUTIES,
        "incident_split": INCIDENT_SPLIT,
        "art20_liability": ART20_LIABILITY if liability else None,
        "registratieplicht": registratieplicht_check(in_scope=in_scope),
        "status": DRAFT,
    }
