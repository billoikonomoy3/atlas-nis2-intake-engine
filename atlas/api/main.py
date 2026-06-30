"""Atlas FastAPI app — the single API the frontend calls (the engine is not duplicated).

Endpoints
  GET  /healthz              liveness
  GET  /version              engine + ruleset version + sha256
  GET  /                     the rewired frontend (calls this API; embeds no engine)
  POST /classify             EntityInput -> {verdict, proportionality, bar} | INSUFFICIENT_INPUT
  POST /extract              multipart (control_id + file(s)) -> ExtractedFact[]   (MODEL)
  POST /score                {control_id, facts[], bar|required_level} -> Finding  (deterministic)
  POST /assess/control       multipart (control_id + entity + file(s)) -> classify + extract -> Finding
  POST /snapshot             EntityInput (+ optional control_id/facts) -> re-derivable Snapshot
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .. import ENGINE_VERSION
from ..engine import ruleset as R
from ..engine.baseline import build_bar
from ..engine.models import (AreaCoverage, Bar, ClassifyResult, EntityInput, ExtractedFact,
                             Finding, ProvenanceChunk, Snapshot, VersionInfo)
from ..engine.scoring import score_control
from ..extraction.extract import (ExtractionError, extract_evidence_facts, extract_facts,
                                  validate_provenance)
from ..extraction.ingest import Chunk, ingest_bytes
from ..jurisdiction import jurisdiction_pack
from ..service import run_area_coverage, run_classify, run_snapshot

app = FastAPI(
    title="Atlas — NIS2 readiness engine",
    version=ENGINE_VERSION,
    description="Deterministic Stage-3 -> compliance-baseline core; a model runs ONLY in /extract.",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "index.html"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ScoreRequest(BaseModel):
    control_id: str
    facts: list[ExtractedFact]
    chunks: Optional[list[ProvenanceChunk]] = None
    bar: Optional[Bar] = None
    required_level: Optional[int] = None


class SnapshotRequest(BaseModel):
    inputs: EntityInput
    control_id: Optional[str] = None
    facts: Optional[list[ExtractedFact]] = None
    chunks: Optional[list[ProvenanceChunk]] = None


class CoverageRequest(BaseModel):
    facts: list[ExtractedFact]
    chunks: Optional[list[ProvenanceChunk]] = None


def _verify_facts_or_422(facts: list[ExtractedFact],
                         chunks: Optional[list[ProvenanceChunk]]) -> list[ExtractedFact]:
    """Public-ingress provenance gate: caller-supplied facts are re-verified against
    their source chunks. Facts without chunks are REFUSED (fail closed) so the public
    /score and /snapshot endpoints can never admit an unverifiable / fabricated fact.
    The safe end-to-end path is /assess/control, which extracts facts from documents."""
    if not facts:
        return []
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail=("facts supplied without their source 'chunks'; this endpoint re-verifies "
                    "provenance and refuses unverifiable facts. Supply chunks [{doc_id,page,text}], "
                    "or use /assess/control to extract+score from documents in one step."),
        )
    src = [Chunk(doc_id=c.doc_id, page=c.page, text=c.text) for c in chunks]
    return validate_provenance(facts, src, strict=True)


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/version", response_model=VersionInfo)
def version() -> VersionInfo:
    return VersionInfo(engine_version=ENGINE_VERSION, ruleset_version=R.ruleset_version(),
                       ruleset_sha256=R.ruleset_sha256())


@app.get("/")
def index():
    if _FRONTEND.exists():
        return FileResponse(_FRONTEND)
    return JSONResponse({"detail": "frontend not built", "version": ENGINE_VERSION})


# ---------------------------------------------------------------------------
# Deterministic endpoints (no model)
# ---------------------------------------------------------------------------

@app.post("/classify", response_model=ClassifyResult)
def classify(entity: EntityInput) -> ClassifyResult:
    return run_classify(entity)


@app.post("/score", response_model=Finding)
def score(req: ScoreRequest) -> Finding:
    if req.bar is not None:
        bar: Bar | int = req.bar
    elif req.required_level is not None:
        bar = req.required_level
    else:
        raise HTTPException(status_code=422, detail="provide either 'bar' or 'required_level'")
    facts = _verify_facts_or_422(req.facts, req.chunks)
    try:
        return score_control(req.control_id, facts, bar)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/coverage", response_model=AreaCoverage)
def coverage(req: CoverageRequest) -> AreaCoverage:
    """Deterministic Art 21(2)(d) coverage map from evidence-item-tagged facts.

    Public-ingress provenance gate applies: caller facts are re-verified against their
    source chunks and unverifiable facts are dropped (same fail-closed rule as /score)."""
    facts = _verify_facts_or_422(req.facts, req.chunks)
    return run_area_coverage(facts)


@app.post("/snapshot", response_model=Snapshot)
def snapshot(req: SnapshotRequest) -> Snapshot:
    facts = req.facts
    if req.control_id and facts:
        facts = _verify_facts_or_422(facts, req.chunks)
    return run_snapshot(req.inputs, _now(), control_id=req.control_id, facts=facts)


@app.get("/jurisdiction")
def jurisdiction(sector: str = "", is_ecomms: bool = False, in_scope: bool = True,
                 entity_class: str = "important") -> dict:
    return jurisdiction_pack(sector=sector, is_ecomms=is_ecomms, in_scope=in_scope,
                             entity_class=entity_class)


# ---------------------------------------------------------------------------
# Extraction endpoints (MODEL — only here)
# ---------------------------------------------------------------------------

async def _ingest_uploads(files: list[UploadFile]) -> list:
    chunks = []
    for f in files:
        name = f.filename or "upload"
        data = await f.read()
        try:
            chunks.extend(ingest_bytes(data, name))
        except ValueError as exc:
            # Unsupported file type (e.g. .json) -> clean JSON 422, never a 500 whose
            # plain-text "Internal Server Error" body makes the frontend's r.json() throw.
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 — unreadable/corrupt doc, still fail cleanly
            raise HTTPException(
                status_code=422, detail=f"could not read {name!r}: {exc}") from exc
    return chunks


@app.post("/extract", response_model=list[ExtractedFact])
async def extract(control_id: str = Form(...), files: list[UploadFile] = File(...)):
    chunks = await _ingest_uploads(files)
    if not chunks:
        raise HTTPException(status_code=422, detail="no readable text in the uploaded document(s)")
    try:
        return extract_facts(control_id, chunks)
    except ExtractionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/assess/control")
async def assess_control(control_id: str = Form(...), entity: str = Form(...),
                         files: list[UploadFile] = File(...)):
    """The RM-21D-01 slice: classify -> extract (model) -> deterministic score."""
    try:
        entity_model = EntityInput.model_validate_json(entity)
    except Exception as exc:  # noqa: BLE001 — surface a clean 422
        raise HTTPException(status_code=422, detail=f"invalid entity JSON: {exc}") from exc

    cr = run_classify(entity_model)
    if cr.status != "ok" or cr.bar is None:
        return {"classification": cr.model_dump(), "finding": None, "facts": []}

    chunks = await _ingest_uploads(files)
    if not chunks:
        raise HTTPException(status_code=422, detail="no readable text in the uploaded document(s)")
    try:
        facts = extract_facts(control_id, chunks)
    except ExtractionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    finding = score_control(control_id, facts, cr.bar)
    return {
        "classification": cr.model_dump(),
        "facts": [f.model_dump() for f in facts],
        "finding": finding.model_dump(),
    }


@app.post("/assess/area")
async def assess_area(files: list[UploadFile] = File(...)):
    """The RM-21D-* supply-chain slice: ingest -> evidence-item extraction (model, per
    control) -> deterministic coverage map for the whole Art 21(2)(d) area."""
    chunks = await _ingest_uploads(files)
    if not chunks:
        raise HTTPException(status_code=422, detail="no readable text in the uploaded document(s)")
    facts: list[ExtractedFact] = []
    try:
        for control in R.supply_chain_controls():
            facts.extend(extract_evidence_facts(control["id"], chunks))
    except ExtractionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    coverage_map = run_area_coverage(facts)
    return {"coverage": coverage_map.model_dump(), "facts": [f.model_dump() for f in facts]}
