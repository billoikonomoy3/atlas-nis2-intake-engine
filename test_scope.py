"""Audit-grade tests for the Atlas NIS2 engine (scope.py).

Run with:  python test_scope.py    (no pytest needed - plain assertions)

These 32 cases are the verified test catalogue for Stage-3 applicability. They
pin down every branch and every trap: the canonical false-positive
(40 staff / EUR 15m / EUR 5m -> SMALL), the staff/financial boundaries, RECURSIVE
Article 6 group aggregation (linked 100% / partner pro-rata), the Article 4(2)
two-year rule, and the Article 3 / Article 2(2) overrides.
"""

from scope import classify_entity, Enterprise


def E(name, staff, turnover, balance, holding_pct=100.0, control=None, related=None):
    return Enterprise(name=name, staff=staff, turnover_eur=turnover,
                      balance_sheet_eur=balance, holding_pct=holding_pct,
                      control=control, related=related or [])


# (id, kwargs for classify_entity, expected_in_scope, expected_class)
CASES = [
    ("TC01 false-positive trap",
     dict(sector_annex="I", root=E("t", 40, 15_000_000, 5_000_000)), False, "out_of_scope"),
    ("TC02 staff 49",
     dict(sector_annex="I", root=E("t", 49, 9_000_000, 9_000_000)), False, "out_of_scope"),
    ("TC03 staff 50",
     dict(sector_annex="I", root=E("t", 50, 1_000_000, 1_000_000)), True, "important"),
    ("TC04 staff 249",
     dict(sector_annex="I", root=E("t", 249, 1_000_000, 1_000_000)), True, "important"),
    ("TC05 staff 250",
     dict(sector_annex="I", root=E("t", 250, 1_000_000, 1_000_000)), True, "essential"),
    ("TC06 medium fin one side (turnover only)",
     dict(sector_annex="I", root=E("t", 30, 12_000_000, 8_000_000)), False, "out_of_scope"),
    ("TC07 medium fin one side (balance only)",
     dict(sector_annex="I", root=E("t", 30, 9_000_000, 11_000_000)), False, "out_of_scope"),
    ("TC08 medium fin both",
     dict(sector_annex="I", root=E("t", 20, 11_000_000, 11_000_000)), True, "important"),
    ("TC09 large fin one side (balance below 43m)",
     dict(sector_annex="I", root=E("t", 100, 60_000_000, 40_000_000)), True, "important"),
    ("TC10 large fin both",
     dict(sector_annex="I", root=E("t", 100, 60_000_000, 45_000_000)), True, "essential"),
    ("TC11 linked subsidiary -> large",
     dict(sector_annex="I", root=E("sub", 10, 1_000_000, 1_000_000,
          related=[E("parent", 5_000, 1_800_000_000, 1_200_000_000, holding_pct=100.0)])),
     True, "essential"),
    ("TC12 partner 40% -> medium",
     dict(sector_annex="I", root=E("t", 30, 2_000_000, 2_000_000,
          related=[E("partner", 100, 1_000_000, 1_000_000, holding_pct=40.0)])),
     True, "important"),
    ("TC13 partner 25% -> stays below",
     dict(sector_annex="I", root=E("t", 30, 2_000_000, 2_000_000,
          related=[E("partner", 60, 1_000_000, 1_000_000, holding_pct=25.0)])),
     False, "out_of_scope"),
    ("TC14 single anomalous year -> no flip up",
     dict(sector_annex="I", root=E("t", 55, 1_000_000, 1_000_000),
          years_breached=1, prior_band="below_medium"), False, "out_of_scope"),
    ("TC15 two consecutive years -> flip up",
     dict(sector_annex="I", root=E("t", 55, 1_000_000, 1_000_000),
          years_breached=2, prior_band="below_medium"), True, "important"),
    ("TC16 medium e-comms -> essential",
     dict(sector_annex="I", root=E("t", 120, 30_000_000, 5_000_000), special_flags=["ecomms"]),
     True, "essential"),
    ("TC17 large e-comms -> essential",
     dict(sector_annex="I", root=E("t", 4_000, 800_000_000, 600_000_000), special_flags=["ecomms"]),
     True, "essential"),
    ("TC18 tiny QTSP -> essential",
     dict(sector_annex="I", root=E("t", 4, 300_000, 200_000), special_flags=["qtsp"]),
     True, "essential"),
    ("TC19 tiny DNS -> essential",
     dict(sector_annex="I", root=E("t", 8, 900_000, 400_000), special_flags=["dns"]),
     True, "essential"),
    ("TC20 tiny TLD -> essential",
     dict(sector_annex="I", root=E("t", 6, 500_000, 300_000), special_flags=["tld"]),
     True, "essential"),
    ("TC21 Art2(2) pending -> deferred",
     dict(sector_annex="I", root=E("t", 15, 2_000_000, 1_000_000), art2_2_designation="pending"),
     False, "deferred_designation"),
    ("TC22 Art2(2) active -> essential",
     dict(sector_annex="I", root=E("t", 15, 2_000_000, 1_000_000), art2_2_designation="active"),
     True, "essential"),
    ("TC23 small central-gov -> essential",
     dict(sector_annex="I", root=E("t", 20, 1_000_000, 1_000_000), special_flags=["public_admin_central"]),
     True, "essential"),
    ("TC24 Annex II large -> important",
     dict(sector_annex="II", root=E("t", 5_000, 900_000_000, 700_000_000)), True, "important"),
    ("TC25 Annex II medium -> important",
     dict(sector_annex="II", root=E("t", 80, 20_000_000, 15_000_000)), True, "important"),
    ("TC26 Annex II below medium -> out",
     dict(sector_annex="II", root=E("t", 15, 2_000_000, 1_000_000)), False, "out_of_scope"),
    ("TC27 non-covered sector -> out",
     dict(sector_annex="none", root=E("t", 5_000, 900_000_000, 700_000_000)), False, "out_of_scope"),
    ("TC28 Annex I large both -> essential",
     dict(sector_annex="I", root=E("t", 300, 80_000_000, 60_000_000)), True, "essential"),
    ("TC29 linked but still below medium",
     dict(sector_annex="I", root=E("t", 10, 1_000_000, 800_000,
          related=[E("sibling", 20, 1_000_000, 800_000, holding_pct=100.0)])),
     False, "out_of_scope"),
    ("TC30 medium-via-fin e-comms -> essential",
     dict(sector_annex="I", root=E("t", 30, 12_000_000, 11_000_000), special_flags=["ecomms"]),
     True, "essential"),
    ("TC31 below-medium e-comms NOT elevated",
     dict(sector_annex="I", root=E("t", 10, 1_000_000, 500_000), special_flags=["ecomms"]),
     False, "out_of_scope"),
    ("TC32 single year down -> no flip down",
     dict(sector_annex="I", root=E("t", 30, 2_000_000, 1_000_000),
          years_breached=1, prior_band="large"), True, "essential"),
]


def run():
    passed = failed = 0
    for label, kwargs, exp_scope, exp_class in CASES:
        r = classify_entity(**kwargs)
        if r["in_scope"] == exp_scope and r["entity_class"] == exp_class:
            passed += 1
        else:
            failed += 1
            print(f"FAIL {label}")
            print(f"   expected: in_scope={exp_scope}, class={exp_class}")
            print(f"   got:      in_scope={r['in_scope']}, class={r['entity_class']} "
                  f"(band={r['size_band']}, consolidated_staff={r['consolidated']['staff']:g})")

    # Spot-check the audit trail is populated and the trap reasoning is explicit.
    trap = classify_entity(sector_annex="I", root=E("t", 40, 15_000_000, 5_000_000))
    assert trap["audit"], "audit trail must be populated"
    assert trap["size_band"] == "below_medium"

    print(f"\n{passed} passed, {failed} failed (out of {len(CASES)} cases).")
    if failed:
        raise SystemExit(1)
    print("All good.")


if __name__ == "__main__":
    run()
