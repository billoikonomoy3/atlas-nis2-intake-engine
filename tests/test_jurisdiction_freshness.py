"""Freshness canary for the Cbw in-force status — NON-GATING by design.

This is a deliberate staleness alarm, not a correctness test. It asserts that today is
on/before IN_FORCE_STATUS["review_by"]. It is EXPECTED to start failing on/after that
date — that failure is the signal to a human to re-verify the Cyberbeveiligingswet status
against its sources and bump the field.

It is marked `@pytest.mark.freshness` and excluded from the gated CI run
(`pytest -m "not freshness"`), then run separately with continue-on-error so it surfaces
in the logs WITHOUT failing the build or flipping the public badge red.
"""

from __future__ import annotations

from datetime import date

import pytest

from atlas import jurisdiction as j

pytestmark = pytest.mark.freshness


def test_in_force_status_is_not_stale():
    s = j.IN_FORCE_STATUS
    review_by = date.fromisoformat(s["review_by"])
    today = date.today()
    assert today <= review_by, (
        f"\nSTALE LEGAL STATUS: today is {today.isoformat()}, past review_by "
        f"{s['review_by']} (as_of was {s['as_of']}).\n"
        f"ACTION REQUIRED — re-verify the {s['statute']} (dossier {s['dossier']}) status:\n"
        "  has the Eerste Kamer voted? has it commenced (koninklijk besluit)? does the "
        "Wbni still govern?\n"
        f"  Sources: {', '.join(s['sources'])}\n"
        "Then bump atlas/jurisdiction.py › IN_FORCE_STATUS: status / eerste_kamer_status / "
        "as_of / review_by / targeted_commencement (and governing_statute_until_commencement "
        "if the Cbw has commenced). This canary is non-gating; it does not break the build."
    )
