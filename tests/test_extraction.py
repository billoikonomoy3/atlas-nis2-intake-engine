"""Extraction layer — provenance guards, all exercised offline via an injected runner.

The model seam (`runner`) is stubbed so these tests never touch the network. The point
is the CODE-enforced guarantees: a fact with no quote, a fabricated quote, or a quote
citing a non-existent page is DISCARDED before it can ever influence a score.
"""

from __future__ import annotations

from atlas.extraction.extract import extract_facts
from atlas.extraction.ingest import Chunk, ingest_bytes

CHUNKS = [
    Chunk(doc_id="supplier_policy.txt", page=1,
          text="All critical suppliers must sign a data processing agreement. "
               "The supplier register is reviewed quarterly by the vendor risk owner."),
]


def stub(facts):
    def _runner(system, user, tool):
        return facts
    return _runner


def test_good_fact_is_kept_with_provenance():
    runner = stub([{
        "evidence_kind": "design", "claim": "DPA required for critical suppliers",
        "source_quote": "All critical suppliers must sign a data processing agreement",
        "doc_id": "supplier_policy.txt", "page": 1, "confidence": 0.9,
    }])
    facts = extract_facts("RM-21D-01", CHUNKS, runner=runner)
    assert len(facts) == 1
    assert facts[0].control_id == "RM-21D-01"
    assert facts[0].doc_id == "supplier_policy.txt" and facts[0].page == 1


def test_fabricated_quote_is_discarded():
    runner = stub([{
        "evidence_kind": "operating", "claim": "made up",
        "source_quote": "we run continuous third-party penetration testing every hour",
        "doc_id": "supplier_policy.txt", "page": 1, "confidence": 0.99,
    }])
    assert extract_facts("RM-21D-01", CHUNKS, runner=runner) == []


def test_quote_citing_nonexistent_page_is_discarded():
    runner = stub([{
        "evidence_kind": "design", "claim": "real text but wrong page",
        "source_quote": "All critical suppliers must sign a data processing agreement",
        "doc_id": "supplier_policy.txt", "page": 99, "confidence": 0.8,
    }])
    assert extract_facts("RM-21D-01", CHUNKS, runner=runner) == []


def test_empty_quote_is_discarded():
    runner = stub([{
        "evidence_kind": "design", "claim": "no quote", "source_quote": "   ",
        "doc_id": "supplier_policy.txt", "page": 1, "confidence": 0.8,
    }])
    assert extract_facts("RM-21D-01", CHUNKS, runner=runner) == []


def test_model_cannot_emit_a_level_field():
    # Even if the stub tries to smuggle a 'level', the schema-locked ExtractedFact ignores it.
    runner = stub([{
        "evidence_kind": "operating", "claim": "register reviewed quarterly",
        "source_quote": "The supplier register is reviewed quarterly by the vendor risk owner",
        "doc_id": "supplier_policy.txt", "page": 1, "confidence": 0.85, "level": 4,
    }])
    facts = extract_facts("RM-21D-01", CHUNKS, runner=runner)
    assert len(facts) == 1
    assert not hasattr(facts[0], "level")


def test_ingest_txt_bytes_round_trip():
    chunks = ingest_bytes(b"hello world\nsecond line", "note.txt")
    assert chunks and chunks[0].doc_id == "note.txt" and chunks[0].page == 1
