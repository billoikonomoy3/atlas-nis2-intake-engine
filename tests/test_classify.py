"""The 32-case classification oracle — the law for the deterministic core.

These expected ``in_scope`` / ``entity_class`` values are the oracle: a refactor that
breaks any one of them is wrong. They pin every branch — the canonical false-positive
trap, the staff/financial boundaries, recursive Article 6 aggregation, the Article 4(2)
two-year rule, and the Article 3 / Article 2(2) overrides.
"""

from __future__ import annotations

import pytest

from atlas.engine.classify import classify_entity
from atlas.engine.models import EntityInput, GroupNode


def E(name, staff, turnover, balance, holding_pct=100.0, control=None, related=None):
    return GroupNode(name=name, staff=staff, turnover_eur=turnover, balance_sheet_eur=balance,
                     holding_pct=holding_pct, control=control, related=related or [])


def classify(sector_annex, root, **kwargs):
    return classify_entity(EntityInput(sector_annex=sector_annex, root=root, **kwargs))


# (id, kwargs, expected_in_scope, expected_class)
CASES = [
    ("TC01", dict(sector_annex="I", root=E("t", 40, 15_000_000, 5_000_000)), False, "out_of_scope"),
    ("TC02", dict(sector_annex="I", root=E("t", 49, 9_000_000, 9_000_000)), False, "out_of_scope"),
    ("TC03", dict(sector_annex="I", root=E("t", 50, 1_000_000, 1_000_000)), True, "important"),
    ("TC04", dict(sector_annex="I", root=E("t", 249, 1_000_000, 1_000_000)), True, "important"),
    ("TC05", dict(sector_annex="I", root=E("t", 250, 1_000_000, 1_000_000)), True, "essential"),
    ("TC06", dict(sector_annex="I", root=E("t", 30, 12_000_000, 8_000_000)), False, "out_of_scope"),
    ("TC07", dict(sector_annex="I", root=E("t", 30, 9_000_000, 11_000_000)), False, "out_of_scope"),
    ("TC08", dict(sector_annex="I", root=E("t", 20, 11_000_000, 11_000_000)), True, "important"),
    ("TC09", dict(sector_annex="I", root=E("t", 100, 60_000_000, 40_000_000)), True, "important"),
    ("TC10", dict(sector_annex="I", root=E("t", 100, 60_000_000, 45_000_000)), True, "essential"),
    ("TC11", dict(sector_annex="I", root=E("sub", 10, 1_000_000, 1_000_000,
            related=[E("parent", 5_000, 1_800_000_000, 1_200_000_000, holding_pct=100.0)])),
        True, "essential"),
    ("TC12", dict(sector_annex="I", root=E("t", 30, 2_000_000, 2_000_000,
            related=[E("partner", 100, 1_000_000, 1_000_000, holding_pct=40.0)])),
        True, "important"),
    ("TC13", dict(sector_annex="I", root=E("t", 30, 2_000_000, 2_000_000,
            related=[E("partner", 60, 1_000_000, 1_000_000, holding_pct=25.0)])),
        False, "out_of_scope"),
    ("TC14", dict(sector_annex="I", root=E("t", 55, 1_000_000, 1_000_000),
            years_breached=1, prior_band="below_medium"), False, "out_of_scope"),
    ("TC15", dict(sector_annex="I", root=E("t", 55, 1_000_000, 1_000_000),
            years_breached=2, prior_band="below_medium"), True, "important"),
    ("TC16", dict(sector_annex="I", root=E("t", 120, 30_000_000, 5_000_000), special_flags=["ecomms"]),
        True, "essential"),
    ("TC17", dict(sector_annex="I", root=E("t", 4_000, 800_000_000, 600_000_000), special_flags=["ecomms"]),
        True, "essential"),
    ("TC18", dict(sector_annex="I", root=E("t", 4, 300_000, 200_000), special_flags=["qtsp"]),
        True, "essential"),
    ("TC19", dict(sector_annex="I", root=E("t", 8, 900_000, 400_000), special_flags=["dns"]),
        True, "essential"),
    ("TC20", dict(sector_annex="I", root=E("t", 6, 500_000, 300_000), special_flags=["tld"]),
        True, "essential"),
    ("TC21", dict(sector_annex="I", root=E("t", 15, 2_000_000, 1_000_000), art2_2_designation="pending"),
        False, "deferred_designation"),
    ("TC22", dict(sector_annex="I", root=E("t", 15, 2_000_000, 1_000_000), art2_2_designation="active"),
        True, "essential"),
    ("TC23", dict(sector_annex="I", root=E("t", 20, 1_000_000, 1_000_000), special_flags=["public_admin_central"]),
        True, "essential"),
    ("TC24", dict(sector_annex="II", root=E("t", 5_000, 900_000_000, 700_000_000)), True, "important"),
    ("TC25", dict(sector_annex="II", root=E("t", 80, 20_000_000, 15_000_000)), True, "important"),
    ("TC26", dict(sector_annex="II", root=E("t", 15, 2_000_000, 1_000_000)), False, "out_of_scope"),
    ("TC27", dict(sector_annex="none", root=E("t", 5_000, 900_000_000, 700_000_000)), False, "out_of_scope"),
    ("TC28", dict(sector_annex="I", root=E("t", 300, 80_000_000, 60_000_000)), True, "essential"),
    ("TC29", dict(sector_annex="I", root=E("t", 10, 1_000_000, 800_000,
            related=[E("sibling", 20, 1_000_000, 800_000, holding_pct=100.0)])),
        False, "out_of_scope"),
    ("TC30", dict(sector_annex="I", root=E("t", 30, 12_000_000, 11_000_000), special_flags=["ecomms"]),
        True, "essential"),
    ("TC31", dict(sector_annex="I", root=E("t", 10, 1_000_000, 500_000), special_flags=["ecomms"]),
        False, "out_of_scope"),
    ("TC32", dict(sector_annex="I", root=E("t", 30, 2_000_000, 1_000_000),
            years_breached=1, prior_band="large"), True, "essential"),
]


@pytest.mark.parametrize("tc_id,kwargs,exp_scope,exp_class", CASES, ids=[c[0] for c in CASES])
def test_classification_oracle(tc_id, kwargs, exp_scope, exp_class):
    v = classify(**kwargs)
    assert v.in_scope is exp_scope, f"{tc_id}: in_scope {v.in_scope} != {exp_scope}"
    assert v.entity_class == exp_class, f"{tc_id}: class {v.entity_class!r} != {exp_class!r}"


def test_oracle_has_32_cases():
    assert len(CASES) == 32


def test_trap_audit_and_band():
    v = classify(sector_annex="I", root=E("t", 40, 15_000_000, 5_000_000))
    assert v.audit, "audit trail must be populated"
    assert v.size_band == "below_medium"
    assert v.consolidated.balance_sheet_eur == 5_000_000
