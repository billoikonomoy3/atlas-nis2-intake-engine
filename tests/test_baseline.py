"""Compliance baseline (heuristic) — required rung per tier, applied to all 16 controls."""

from __future__ import annotations

import pytest

from atlas.engine.baseline import build_bar, evidence_rule_for, required_for_tier


@pytest.mark.parametrize("tier,rung", [
    ("Foundational", 1), ("Standard", 2), ("Enhanced", 3), ("Critical", 4),
])
def test_required_rung_per_tier(tier, rung):
    assert required_for_tier(tier) == rung


def test_bar_covers_all_16_controls():
    bar = build_bar("Enhanced")
    assert bar.required_level == 3
    assert bar.required_name == "Defined (operating)"
    assert len(bar.controls) == 16
    assert all(c.required_level == 3 for c in bar.controls)


def test_operating_critical_partition():
    bar = build_bar("Critical")
    op_crit = {c.control_id for c in bar.controls if c.operating_critical}
    assert op_crit == {
        "RM-21B-01", "RM-21C-01", "RM-21E-01", "RM-21F-01", "RM-21G-01",
        "RM-21I-01", "RM-21J-01", "REP-23-01", "REP-23-02", "REP-23-04",
    }
    assert len(op_crit) == 10
    # The slice control is NOT operating-critical.
    rm21d = next(c for c in bar.controls if c.control_id == "RM-21D-01")
    assert rm21d.operating_critical is False


def test_important_can_sit_at_foundational_l1_policy_artifact():
    # Surfaced, not silently corrected: a Foundational tier yields a required rung of L1
    # even for an in-scope control. This is the documented tunable policy decision.
    bar = build_bar("Foundational")
    assert bar.required_level == 1
    assert all(c.required_level == 1 for c in bar.controls)


def test_evidence_rule_escalates_with_rung():
    assert "design artefact with provenance" in evidence_rule_for(1)
    assert "complete design evidence set" in evidence_rule_for(2)
    assert "operating evidence" in evidence_rule_for(3)
    assert "monitoring" in evidence_rule_for(4)
