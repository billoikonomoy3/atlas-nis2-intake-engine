"""NL · Cbw jurisdiction overlay — named routing, honest TBD, duties, registratieplicht."""

from __future__ import annotations

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
