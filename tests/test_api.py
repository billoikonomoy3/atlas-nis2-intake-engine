"""API surface — exercised offline with FastAPI's TestClient (no model, no network).

The /extract path is checked to fail CLOSED (503) when no API key is present, never to
fabricate facts.
"""

from __future__ import annotations

import os

import pytest

from fastapi.testclient import TestClient

from atlas.api.main import app

client = TestClient(app)

VALID_ENTITY = {
    "sector_annex": "I",
    "sector_name": "Energy",
    "root": {"name": "Acme Grid", "staff": 300, "turnover_eur": 80_000_000, "balance_sheet_eur": 60_000_000},
}


def test_healthz_and_version():
    assert client.get("/healthz").json()["status"] == "ok"
    v = client.get("/version").json()
    assert v["ruleset_version"] == "nis2_v1" and len(v["ruleset_sha256"]) == 64


def test_classify_ok():
    r = client.post("/classify", json=VALID_ENTITY)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["verdict"]["entity_class"] == "essential"
    assert body["proportionality"]["tier"]
    assert len(body["bar"]["controls"]) == 16


def test_classify_insufficient_input():
    bad = {"sector_annex": "I",
           "root": {"name": "x", "staff": -5, "turnover_eur": 1e6, "balance_sheet_eur": 1e6}}
    body = client.post("/classify", json=bad).json()
    assert body["status"] == "INSUFFICIENT_INPUT"
    assert body["verdict"] is None and body["reasons"]


def test_score_endpoint_with_verified_provenance():
    facts = [{
        "control_id": "RM-21D-01", "evidence_kind": "design", "claim": "policy exists",
        "source_quote": "supplier security policy", "doc_id": "d.pdf", "page": 1, "confidence": 0.9,
    }]
    chunks = [{"doc_id": "d.pdf", "page": 1, "text": "Our supplier security policy applies to all vendors."}]
    r = client.post("/score", json={"control_id": "RM-21D-01", "facts": facts,
                                     "chunks": chunks, "required_level": 3})
    assert r.status_code == 200
    f = r.json()
    assert f["achieved_level"] == 1 and f["required_level"] == 3 and f["gap"] == 2


def test_score_refuses_facts_without_chunks():
    # Public ingress fails closed: facts cannot be scored without their source chunks.
    facts = [{
        "control_id": "RM-21D-01", "evidence_kind": "design", "claim": "x",
        "source_quote": "supplier security policy", "doc_id": "d.pdf", "page": 1, "confidence": 0.9,
    }]
    r = client.post("/score", json={"control_id": "RM-21D-01", "facts": facts, "required_level": 3})
    assert r.status_code == 422


def test_score_drops_fabricated_fact():
    # A fabricated quote (never in the supplied chunk) is dropped -> insufficient_evidence.
    facts = [{
        "control_id": "RM-21D-01", "evidence_kind": "design", "claim": "made up",
        "source_quote": "WE HAVE A WORLD CLASS SUPPLY CHAIN PROGRAM", "doc_id": "ghost.pdf",
        "page": 99, "confidence": 0.99,
    }]
    chunks = [{"doc_id": "d.pdf", "page": 1, "text": "Unrelated facilities note about parking."}]
    r = client.post("/score", json={"control_id": "RM-21D-01", "facts": facts,
                                     "chunks": chunks, "required_level": 3})
    assert r.status_code == 200
    f = r.json()
    assert f["status"] == "insufficient_evidence" and f["evidence"] == []


def test_snapshot_refuses_fabricated_facts_without_chunks():
    fab = [{
        "control_id": "RM-21D-01", "evidence_kind": "operating", "claim": "fake",
        "source_quote": "fabricated never in any document", "doc_id": "ghost", "page": 9999,
        "confidence": 0.99,
    }]
    r = client.post("/snapshot", json={"inputs": VALID_ENTITY, "control_id": "RM-21D-01", "facts": fab})
    assert r.status_code == 422


def test_snapshot_is_rederivable():
    r = client.post("/snapshot", json={"inputs": VALID_ENTITY})
    body = r.json()
    assert body["content_sha256"] and body["engine_version"]
    # Re-post -> identical content hash (generated_at may differ).
    again = client.post("/snapshot", json={"inputs": VALID_ENTITY}).json()
    assert body["content_sha256"] == again["content_sha256"]


def test_extract_fails_closed_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/extract", data={"control_id": "RM-21D-01"},
                    files={"files": ("doc.txt", b"All suppliers must sign a DPA.", "text/plain")})
    # No key -> 503 (fail closed), never a fabricated 200 with invented facts.
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Supply-chain coverage endpoints (the RM-21D-* slice).
# ---------------------------------------------------------------------------

def test_coverage_endpoint_buckets_a_verified_fact():
    facts = [{
        "control_id": "RM-21D-03", "evidence_kind": "design", "claim": "security schedule",
        "source_quote": "must include the mandatory Security Schedule", "doc_id": "d.pdf",
        "page": 1, "confidence": 0.9, "evidence_item_id": "21D-03-a",
    }]
    chunks = [{"doc_id": "d.pdf", "page": 1,
               "text": "Every contract must include the mandatory Security Schedule and a DPA."}]
    r = client.post("/coverage", json={"facts": facts, "chunks": chunks})
    assert r.status_code == 200
    body = r.json()
    assert body["area_id"] == "21D"
    c03 = next(c for c in body["controls"] if c["control_id"] == "RM-21D-03")
    a = next(i for i in c03["items"] if i["evidence_item_id"] == "21D-03-a")
    assert a["status"] == "present" and a["decisive"] is True


def test_coverage_refuses_facts_without_chunks():
    # Same fail-closed provenance gate as /score: no chunks -> 422, never scored unverified.
    facts = [{
        "control_id": "RM-21D-03", "evidence_kind": "design", "claim": "x",
        "source_quote": "must include the mandatory Security Schedule", "doc_id": "d.pdf",
        "page": 1, "confidence": 0.9, "evidence_item_id": "21D-03-a",
    }]
    r = client.post("/coverage", json={"facts": facts})
    assert r.status_code == 422


def test_coverage_drops_fabricated_fact():
    fab = [{
        "control_id": "RM-21D-03", "evidence_kind": "design", "claim": "made up",
        "source_quote": "WE AUDIT EVERY SUPPLIER IN REAL TIME", "doc_id": "ghost.pdf",
        "page": 9, "confidence": 0.99, "evidence_item_id": "21D-03-c",
    }]
    chunks = [{"doc_id": "d.pdf", "page": 1, "text": "Unrelated note about the cafeteria."}]
    r = client.post("/coverage", json={"facts": fab, "chunks": chunks})
    assert r.status_code == 200
    c03 = next(c for c in r.json()["controls"] if c["control_id"] == "RM-21D-03")
    assert all(i["status"] == "absent" for i in c03["items"])   # the fabricated quote never counts


def test_assess_area_fails_closed_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/assess/area",
                    files={"files": ("doc.txt",
                                     b"Suppliers are classified into three criticality tiers.",
                                     "text/plain")})
    assert r.status_code == 503   # extraction needs a key; never fabricates a map


def test_unsupported_upload_type_is_clean_422_not_500():
    # Regression: a .json (or any non pdf/docx/txt/md) upload used to raise an uncaught
    # ValueError -> 500 with a PLAIN-TEXT "Internal Server Error" body, which made the
    # frontend's r.json() throw "Unexpected token 'I'". It must now be a clean JSON 422.
    import json as _json
    entity = _json.dumps(VALID_ENTITY)
    cases = [
        ("/assess/control", {"control_id": "RM-21D-01", "entity": entity}),
        ("/extract", {"control_id": "RM-21D-01"}),
    ]
    for endpoint, data in cases:
        r = client.post(endpoint, data=data,
                        files={"files": ("data.json", b'{"x":1}', "application/json")})
        assert r.status_code == 422, endpoint
        assert ".json" in r.json()["detail"]   # body is valid JSON (the whole point)

    r = client.post("/assess/area", files={"files": ("x.rtf", b"{\\rtf1}", "application/rtf")})
    assert r.status_code == 422 and ".rtf" in r.json()["detail"]
