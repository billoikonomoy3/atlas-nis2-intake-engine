"""Netherlands (Cbw) jurisdiction overlay — the Dutch skin on the deterministic core.

NOT a second engine: it (1) states the governing law by date (Wbni now, Cbw on entry),
(2) routes a classified entity to its NAMED Dutch supervisor (and says TBD + routes to a
human where the source names none — no judgment leakage), (3) splits incident output into
a Cbw-meldplicht track and a separate GDPR datalek track, and (4) checks the
registratieplicht was actually filed. Pure data + pure functions, offline.

The dated legal "in-force" status is a SINGLE structured fact of law (IN_FORCE_STATUS,
below). Every report line and every "Wbni still governs" clause is DERIVED from it, so the
status lives in exactly one place. Legally precise as of IN_FORCE_STATUS["as_of"].
DRAFT — REQUIRES REVIEW.
"""

from __future__ import annotations

DRAFT = "DRAFT — REQUIRES REVIEW"

# --- The dated legal status: ONE structured, testable fact of law -----------------------
# GIVEN facts as of 2026-06-25 (do NOT invent; re-verify against the sources if as_of moves):
#   - Cbw, Eerste Kamer dossier 36.764.
#   - Tweede Kamer (lower house) adopted it 2026-04-15.
#   - Eerste Kamer (upper house) plenary vote pending as of 2026-06-25.
#   - Targeted commencement 2026-07-01; until commencement the Wbni still governs.
# Sources:
#   https://www.eerstekamer.nl/wetsvoorstel/36764_cyberbeveiligingswet
#   https://www.rijksoverheid.nl/actueel/nieuws/2026/04/15/tweede-kamer-stemt-in-met-wetsvoorstellen-cyberbeveiligingswet-en-wet-weerbaarheid-kritieke-entiteiten
# If Atlas is run on/after review_by, these must NOT be silently trusted — the non-gating
# freshness canary (tests/test_jurisdiction_freshness.py) fails then as a staleness alarm.
IN_FORCE_STATUS_ENUM = (
    "in_progress",
    "adopted_lower_house_pending_upper_house",
    "passed_pending_commencement",
    "in_force",
)

IN_FORCE_STATUS = {
    "statute": "Cyberbeveiligingswet (Cbw)",
    "dossier": "36.764",
    "status": "adopted_lower_house_pending_upper_house",
    "eerste_kamer_status": "pending_plenary_vote",
    "governing_statute_until_commencement": "Wbni",
    "tweede_kamer_passed": "2026-04-15",
    "targeted_commencement": "2026-07-01",
    "as_of": "2026-06-25",
    "review_by": "2026-07-01",
    "sources": [
        "https://www.eerstekamer.nl/wetsvoorstel/36764_cyberbeveiligingswet",
        "https://www.rijksoverheid.nl/actueel/nieuws/2026/04/15/tweede-kamer-stemt-in-met-wetsvoorstellen-cyberbeveiligingswet-en-wet-weerbaarheid-kritieke-entiteiten",
    ],
    "statutory": True,  # a fact of law, not a heuristic
}

# Descriptive expansion of the statute that governs until commencement (a label, NOT a
# status claim — the status itself lives only in IN_FORCE_STATUS).
_GOVERNING_STATUTE_LONG = {
    "Wbni": "Wet beveiliging netwerk- en informatiesystemen (Wbni)",
}

_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def _human_date(iso: str) -> str:
    """'2026-04-15' -> '15 April 2026'. Pure; reads no clock, no locale dependence."""
    y, m, d = (int(part) for part in iso.split("-"))
    return f"{d} {_MONTHS[m - 1]} {y}"


# Present-tense reading of each enum value — the single source of the status phrasing.
_STATUS_PROSE = {
    "in_progress": "is in parliamentary procedure",
    "adopted_lower_house_pending_upper_house":
        "has been adopted by the Tweede Kamer and awaits the Eerste Kamer plenary vote",
    "passed_pending_commencement":
        "has passed both houses and awaits commencement by koninklijk besluit",
    "in_force": "is in force",
}


def _prospective_clause(s: dict) -> str:
    """Derived 'not enforceable until entry' / 'in force' qualifier — never hardcoded twice."""
    if s["status"] == "in_force":
        return f"the {s['statute']} is in force as of {_human_date(s['as_of'])}"
    return (f"the {s['statute']} is prospective — not enforceable until commencement "
            f"(targeted {_human_date(s['targeted_commencement'])}); until then the "
            f"{s['governing_statute_until_commencement']} governs")


def _derive_governing_law(s: dict) -> dict:
    """Build the report lines FROM IN_FORCE_STATUS — the single source of the dated legal
    status. No date or status string is hardcoded a second time."""
    in_force = s["status"] == "in_force"
    governs_long = _GOVERNING_STATUTE_LONG.get(
        s["governing_statute_until_commencement"], s["governing_statute_until_commencement"])
    asof, tk, target = (_human_date(s["as_of"]), _human_date(s["tweede_kamer_passed"]),
                        _human_date(s["targeted_commencement"]))
    status_phrase = _STATUS_PROSE[s["status"]]
    return {
        "current_statute": (
            f"{governs_long} — the Dutch NIS1 implementing statute — "
            f"{'no longer governs' if in_force else 'remains the enforceable law'} "
            f"as of {asof}."),
        "future_statute": (
            f"{s['statute']}, Eerste Kamer dossier {s['dossier']} — the NIS2 transposition; "
            f"repeals the {s['governing_statute_until_commencement']} on entry into force "
            f"(prospectively)."),
        "status_note": (
            f"As of {asof} the {s['statute']} {status_phrase} (dossier {s['dossier']}; "
            f"Tweede Kamer passage {tk}; Eerste Kamer "
            f"{s['eerste_kamer_status'].replace('_', ' ')}; targeted commencement {target} "
            f"by koninklijk besluit, possibly staggered per article). "
            + ("In force." if in_force else
               f"NOT YET IN FORCE — the {s['governing_statute_until_commencement']} still governs.")),
        "line_for_report": (
            f"Prepared against the Netherlands {s['statute']} (dossier {s['dossier']}); "
            f"as of {asof} the Cbw {status_phrase} and "
            + ("the Cbw now governs." if in_force else
               f"today's enforceable liability remains under the {governs_long} / NIS1, which "
               f"the Cbw repeals on entry into force by koninklijk besluit (targeted {target}).")),
    }


GOVERNING_LAW = _derive_governing_law(IN_FORCE_STATUS)

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
    "note": ("ONE EVENT CAN TRIGGER BOTH, down different portals, on parallel-but-distinct "
        "clocks; satisfying one does NOT discharge the other. Cbw track: "
        f"{_prospective_clause(IN_FORCE_STATUS)}. The GDPR/AP datalek track is enforceable "
        "TODAY, independent of the Cbw."),
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
        "in_force_status": IN_FORCE_STATUS,
        "governing_law": GOVERNING_LAW["line_for_report"],
        "supervisor": sup,
        "reporting_clocks": REPORTING_CLOCKS,
        "three_duties": THREE_DUTIES,
        "incident_split": INCIDENT_SPLIT,
        "art20_liability": ART20_LIABILITY if liability else None,
        "registratieplicht": registratieplicht_check(in_scope=in_scope),
        "status": DRAFT,
    }
