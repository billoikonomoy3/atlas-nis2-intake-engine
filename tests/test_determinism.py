"""Determinism + reproducibility — same inputs -> byte-identical outputs & hash.

Every snapshot embeds engine_version + ruleset_version + ruleset_sha256, and the
content hash excludes only generated_at, so a snapshot literally re-derives to the
same hash.
"""

from __future__ import annotations

from atlas import ENGINE_VERSION
from atlas.engine.models import EntityInput, ExtractedFact, GroupNode
from atlas.engine.scoring import score_control
from atlas.service import run_classify, run_snapshot

ENTITY = EntityInput(
    sector_annex="I", sector_name="Energy",
    root=GroupNode(name="Acme Grid", staff=300, turnover_eur=80_000_000, balance_sheet_eur=60_000_000),
)
FACTS = [
    ExtractedFact(control_id="RM-21D-01", evidence_kind="design",
                  claim="supplier security policy exists", source_quote="all suppliers must meet ISO controls",
                  doc_id="policy.pdf", page=2, confidence=0.92),
    ExtractedFact(control_id="RM-21D-01", evidence_kind="operating",
                  claim="supplier register maintained", source_quote="register reviewed quarterly in 2025",
                  doc_id="register.pdf", page=1, confidence=0.88),
]
STAMP = "2026-06-25T00:00:00Z"


def test_finding_is_byte_identical_across_runs():
    cr = run_classify(ENTITY)
    f1 = score_control("RM-21D-01", FACTS, cr.bar)
    f2 = score_control("RM-21D-01", FACTS, cr.bar)
    assert f1.model_dump() == f2.model_dump()
    assert f1.model_dump_json() == f2.model_dump_json()


def test_snapshot_hash_identical_across_runs():
    s1 = run_snapshot(ENTITY, STAMP, control_id="RM-21D-01", facts=FACTS)
    s2 = run_snapshot(ENTITY, STAMP, control_id="RM-21D-01", facts=FACTS)
    assert s1.content_sha256 == s2.content_sha256
    assert s1.model_dump_json() == s2.model_dump_json()


def test_content_hash_excludes_generated_at():
    s1 = run_snapshot(ENTITY, "2026-06-25T00:00:00Z", control_id="RM-21D-01", facts=FACTS)
    s2 = run_snapshot(ENTITY, "2030-01-01T12:00:00Z", control_id="RM-21D-01", facts=FACTS)
    # Different wall-clock stamps, identical content hash.
    assert s1.generated_at != s2.generated_at
    assert s1.content_sha256 == s2.content_sha256


def test_snapshot_re_derives_from_its_inputs():
    snap = run_snapshot(ENTITY, STAMP, control_id="RM-21D-01", facts=FACTS)
    # Re-run from the snapshot's own captured inputs + same stamp -> same hash.
    rederived = run_snapshot(snap.inputs, STAMP, control_id="RM-21D-01", facts=FACTS)
    assert rederived.content_sha256 == snap.content_sha256


def test_snapshot_embeds_versions():
    snap = run_snapshot(ENTITY, STAMP, control_id="RM-21D-01", facts=FACTS)
    assert snap.engine_version == ENGINE_VERSION
    assert snap.ruleset_version == "nis2_v1"
    assert len(snap.ruleset_sha256) == 64  # sha256 hex
    assert snap.content_sha256


def test_insufficient_input_snapshot_is_deterministic():
    bad = EntityInput(sector_annex="I",
                      root=GroupNode(name="bad", staff=None, turnover_eur=1e6, balance_sheet_eur=1e6))
    s1 = run_snapshot(bad, STAMP)
    s2 = run_snapshot(bad, STAMP)
    assert s1.status == "INSUFFICIENT_INPUT"
    assert s1.content_sha256 == s2.content_sha256
    assert s1.verdict is None
