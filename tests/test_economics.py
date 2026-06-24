"""Economics — the one canonical, hand-re-derivable chain (preserved coverage)."""

from __future__ import annotations

from atlas import economics


def test_canonical_chain():
    r = economics.compute()
    assert r["junior_day_rate_eur"] == 1662
    assert r["junior_hourly_eur"] == 208
    assert r["stage47_hours"] == 34
    assert r["manual_cost_eur"] == 7072
    assert r["headline_claim_eur"] == 5000
    assert r["hours_kept_human"] == 6
