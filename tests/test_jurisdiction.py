"""NL · Cbw jurisdiction overlay — named routing, honest TBD, duties, registratieplicht."""

from __future__ import annotations

from datetime import date

from atlas import jurisdiction as j


def test_named_supervisors():
    assert j.supervisor_for("Energy")["supervisor_abbr"] == "RDI"
    assert j.supervisor_for("Health")["supervisor_abbr"] == "IGJ"
    assert j.supervisor_for("Banking")["supervisor_abbr"] == "DNB+AFM"


def test_dora_overlap_flagged_for_financial():
    assert "DORA" in j.supervisor_for("Banking")["note"]


def test_unknown_sector_is_tbd_and_routes_to_human():
    r = j.supervisor_for("Manufacturing")
    assert r["supervisor_abbr"] == "TBD" and r["needs_human_review"] is True


def test_ecomms_routes_to_rdi_via_flag():
    assert j.supervisor_for("anything", is_ecomms=True)["supervisor_abbr"] == "RDI"


def test_registratieplicht_requires_actual_filing():
    assert j.registratieplicht_check(in_scope=True)["ok"] is False
    ok = j.registratieplicht_check(in_scope=True, registration_filed=True,
                                   filing_officer="CISO", filing_date="2026-05-01")
    assert ok["ok"] is True
    assert j.registratieplicht_check(in_scope=False)["ok"] is True


def test_pack_surfaces_art20_liability_for_in_scope():
    pack = j.jurisdiction_pack(sector="Energy", is_ecomms=False, in_scope=True, entity_class="essential")
    assert pack["art20_liability"] is not None
    assert pack["reporting_clocks"]["early_warning_hours"] == 24
    assert len(pack["three_duties"]) == 3
    out = j.jurisdiction_pack(sector="x", is_ecomms=False, in_scope=False, entity_class="out_of_scope")
    assert out["art20_liability"] is None


# --- Structural tests for the dated in-force status (gated, time-INDEPENDENT) -----------
# These never read today's date; they assert the SHAPE of IN_FORCE_STATUS. The separate
# tests/test_jurisdiction_freshness.py owns the time-dependent staleness alarm.

_REQUIRED_KEYS = {
    "statute", "dossier", "status", "eerste_kamer_status",
    "governing_statute_until_commencement", "tweede_kamer_passed",
    "targeted_commencement", "as_of", "review_by", "sources", "statutory",
}


def test_in_force_status_has_all_required_keys():
    assert _REQUIRED_KEYS <= set(j.IN_FORCE_STATUS), \
        f"IN_FORCE_STATUS missing keys: {_REQUIRED_KEYS - set(j.IN_FORCE_STATUS)}"


def test_in_force_status_is_a_valid_enum_value():
    assert j.IN_FORCE_STATUS["status"] in j.IN_FORCE_STATUS_ENUM


def test_targeted_commencement_not_before_tweede_kamer_passage():
    passed = date.fromisoformat(j.IN_FORCE_STATUS["tweede_kamer_passed"])
    commencement = date.fromisoformat(j.IN_FORCE_STATUS["targeted_commencement"])
    assert commencement >= passed


def test_status_is_a_statutory_fact_of_law():
    # Law, not a tunable heuristic — must never be flipped to a heuristic tag.
    assert j.IN_FORCE_STATUS["statutory"] is True


def test_all_dated_fields_are_iso_dates_and_sources_present():
    for key in ("tweede_kamer_passed", "targeted_commencement", "as_of", "review_by"):
        date.fromisoformat(j.IN_FORCE_STATUS[key])  # raises ValueError if malformed
    assert j.IN_FORCE_STATUS["sources"] and all(
        s.startswith("https://") for s in j.IN_FORCE_STATUS["sources"])


def test_report_lines_derive_from_the_status_object_no_duplicate_strings():
    # The report line must be built FROM the object: the dossier and the passage date
    # flow through, and "Wbni still governs" reasoning ties back to the object's field.
    line = j.GOVERNING_LAW["line_for_report"]
    assert j.IN_FORCE_STATUS["dossier"] in line
    assert j.IN_FORCE_STATUS["governing_statute_until_commencement"] in j.GOVERNING_LAW["status_note"]
    # Pack surfaces the structured field itself, not just prose.
    pack = j.jurisdiction_pack(sector="Energy", is_ecomms=False, in_scope=True, entity_class="essential")
    assert pack["in_force_status"] is j.IN_FORCE_STATUS
