"""Pydantic schemas — the single source of truth for the API and the tests.

The law/heuristic split is encoded in the schema itself: every field that the LAW
determines carries ``json_schema_extra = STATUTORY``; every proportionality /
maturity field carries ``HEURISTIC`` (``statutory: false, heuristic: true,
tunable: true``). Any consumer (API docs, UI, memo) can therefore mechanically
separate "the law determines" from "our heuristic suggests".
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Field-provenance tags surfaced into the JSON schema.
STATUTORY = {"statutory": True}
HEURISTIC = {"statutory": False, "heuristic": True, "tunable": True}

EntityClass = Literal["essential", "important", "out_of_scope", "deferred_designation"]
SizeBand = Literal["large", "medium", "below_medium"]
Tier = Literal["Foundational", "Standard", "Enhanced", "Critical"]
EvidenceKind = Literal["design", "operating"]
# "vetoed": a disqualifying finding defeats the control regardless of the rung ratios.
FindingStatus = Literal["meets", "gap", "insufficient_evidence", "vetoed"]
# Coverage of one supply-chain evidence item (or a control area as a whole).
CoverageStatus = Literal["present", "ambiguous", "absent"]


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

class GroupNode(BaseModel):
    """A node in the corporate group tree (the root entity is itself a node).

    Numerics are Optional so that a *missing* figure reaches input validation and
    returns INSUFFICIENT_INPUT rather than failing schema parsing with a 422.
    inf/nan are accepted at parse time for the same reason and rejected by
    ``validate.py``.
    """

    model_config = ConfigDict(allow_inf_nan=True)

    name: str = Field(..., json_schema_extra=STATUTORY)
    staff: Optional[float] = Field(None, json_schema_extra=STATUTORY)
    turnover_eur: Optional[float] = Field(None, json_schema_extra=STATUTORY)
    balance_sheet_eur: Optional[float] = Field(None, json_schema_extra=STATUTORY)
    holding_pct: float = Field(100.0, json_schema_extra=STATUTORY)
    control: Optional[bool] = Field(None, json_schema_extra=STATUTORY)
    related: list["GroupNode"] = Field(default_factory=list, json_schema_extra=STATUTORY)


class ProportionalityInput(BaseModel):
    """Heuristic inputs to the proportionality score (NOT statutory facts)."""

    cross_border_systemic: Literal["systemic", "sole_national", "cross_border", "none"] = Field(
        "none", json_schema_extra=HEURISTIC)
    n_geographies: int = Field(1, json_schema_extra=HEURISTIC)
    n_entities: int = Field(1, json_schema_extra=HEURISTIC)
    special_entity: bool = Field(False, json_schema_extra=HEURISTIC)
    supply_chain: Literal["high", "moderate", "low"] = Field("low", json_schema_extra=HEURISTIC)


class EntityInput(BaseModel):
    """Everything the classifier + proportionality need, from user facts only."""

    root: GroupNode = Field(..., json_schema_extra=STATUTORY)
    sector_annex: Optional[Literal["I", "II", "none"]] = Field(None, json_schema_extra=STATUTORY)
    sector_name: Optional[str] = Field(None, json_schema_extra=STATUTORY)
    special_flags: list[str] = Field(default_factory=list, json_schema_extra=STATUTORY)
    art2_2_designation: Optional[Literal["active", "pending"]] = Field(None, json_schema_extra=STATUTORY)
    years_breached: int = Field(2, json_schema_extra=STATUTORY)
    prior_band: Optional[SizeBand] = Field(None, json_schema_extra=STATUTORY)
    proportionality: ProportionalityInput = Field(default_factory=ProportionalityInput,
                                                  json_schema_extra=HEURISTIC)


# ---------------------------------------------------------------------------
# Outputs — statutory
# ---------------------------------------------------------------------------

class Consolidated(BaseModel):
    staff: float = Field(..., json_schema_extra=STATUTORY)
    turnover_eur: float = Field(..., json_schema_extra=STATUTORY)
    balance_sheet_eur: float = Field(..., json_schema_extra=STATUTORY)


class Verdict(BaseModel):
    """The statutory determination — what the LAW determines."""

    in_scope: bool = Field(..., json_schema_extra=STATUTORY)
    entity_class: EntityClass = Field(..., json_schema_extra=STATUTORY)
    size_band: SizeBand = Field(..., json_schema_extra=STATUTORY)
    raw_size_band: SizeBand = Field(..., json_schema_extra=STATUTORY)
    consolidated: Consolidated = Field(..., json_schema_extra=STATUTORY)
    sector_annex: Literal["I", "II", "none"] = Field(..., json_schema_extra=STATUTORY)
    reason: str = Field(..., json_schema_extra=STATUTORY)
    audit: list[str] = Field(default_factory=list, json_schema_extra=STATUTORY)
    aggregation_trace: list[dict] = Field(default_factory=list, json_schema_extra=STATUTORY)
    flags: list[str] = Field(default_factory=list, json_schema_extra=STATUTORY)


# ---------------------------------------------------------------------------
# Outputs — heuristic
# ---------------------------------------------------------------------------

class Proportionality(BaseModel):
    """Heuristic proportionality profile — what OUR HEURISTIC suggests."""

    statutory: bool = Field(False, description="always false — this block is heuristic")
    points: dict[str, int] = Field(..., json_schema_extra=HEURISTIC)
    raw_score: int = Field(..., json_schema_extra=HEURISTIC)
    score: int = Field(..., json_schema_extra=HEURISTIC)
    floors_applied: list[str] = Field(default_factory=list, json_schema_extra=HEURISTIC)
    tier: Tier = Field(..., json_schema_extra=HEURISTIC)
    tier_expectation: str = Field(..., json_schema_extra=HEURISTIC)


class BarControl(BaseModel):
    """The minimum rung one control must clear at this tier (heuristic)."""

    control_id: str = Field(..., json_schema_extra=HEURISTIC)
    ref: str = Field(..., json_schema_extra=STATUTORY)   # the NIS2 article is statutory
    domain: str = Field(..., json_schema_extra=HEURISTIC)
    inherent_criticality: int = Field(..., json_schema_extra=HEURISTIC)
    required_level: int = Field(..., json_schema_extra=HEURISTIC)
    required_name: str = Field(..., json_schema_extra=HEURISTIC)
    operating_critical: bool = Field(..., json_schema_extra=HEURISTIC)
    evidence_rule: str = Field(..., json_schema_extra=HEURISTIC)


class Bar(BaseModel):
    """The compliance baseline derived from the proportionality tier (heuristic)."""

    statutory: bool = Field(False, description="always false — this block is heuristic")
    tier: Tier = Field(..., json_schema_extra=HEURISTIC)
    required_level: int = Field(..., json_schema_extra=HEURISTIC)
    required_name: str = Field(..., json_schema_extra=HEURISTIC)
    controls: list[BarControl] = Field(default_factory=list, json_schema_extra=HEURISTIC)
    note: str = Field(
        "Heuristic minimum bar; NIS2 Art 21(1) is outcomes-based and a rung is not a safe harbour.",
        json_schema_extra=HEURISTIC,
    )


# ---------------------------------------------------------------------------
# Extraction + scoring (the RM-21D-01 slice)
# ---------------------------------------------------------------------------

class ExtractedFact(BaseModel):
    """One fact a model LOCATED + QUOTED from a document. Extraction only.

    The model bridges vocabulary and points at evidence; it assigns NO maturity
    level. ``confidence`` is extraction confidence, never a legal judgment. A fact
    without ``source_quote`` is discarded before scoring (provenance is mandatory).
    """

    control_id: str
    evidence_kind: EvidenceKind
    claim: str
    source_quote: str = Field(..., description="<=25 words, verbatim, for provenance")
    doc_id: str
    page: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    # Which registry evidence_item this fact addresses (e.g. "21D-03-b"). Optional and
    # default None so the existing maturity slice is unchanged; set only by the
    # evidence-item-aware extraction path and read only by the deterministic coverage layer.
    evidence_item_id: Optional[str] = None


class ProvenanceChunk(BaseModel):
    """A source text chunk (doc_id + page + text) used to re-verify a fact's quote.

    Carried on /score and /snapshot so the public API can re-run the anti-fabrication
    provenance check before scoring caller-supplied facts."""

    doc_id: str
    page: int
    text: str


class EvidenceRef(BaseModel):
    """Provenance-carrying evidence attached to a finding."""

    evidence_kind: EvidenceKind
    claim: str
    source_quote: str
    doc_id: str
    page: int


class Veto(BaseModel):
    """A disqualifying ("veto") finding: cited content whose MEANING defeats the control.

    Deterministic — produced by ``atlas/engine/veto.py`` over the cited facts, never by a
    model. It carries the NIS2 reference it defeats (statutory) and a short rationale, plus
    the offending quote + locator, so a reader can see WHY the control was capped. Presence
    of such a clause is a defect, not evidence of conformance.
    """

    veto_id: str = Field(..., json_schema_extra=HEURISTIC)
    defeats_ref: str = Field(..., json_schema_extra=STATUTORY)  # the NIS2 article it defeats
    rationale: str = Field(..., json_schema_extra=HEURISTIC)
    detail: str = Field("", json_schema_extra=HEURISTIC)
    matched_quote: str = Field(..., json_schema_extra=HEURISTIC)
    doc_id: str = Field(..., json_schema_extra=HEURISTIC)
    page: int = Field(..., json_schema_extra=HEURISTIC)


class Finding(BaseModel):
    """A deterministic, cited control finding. No model call produced any of this."""

    control_id: str = Field(..., json_schema_extra=STATUTORY)
    nis2_ref: str = Field(..., json_schema_extra=STATUTORY)
    achieved_level: int = Field(..., json_schema_extra=HEURISTIC)
    achieved_name: str = Field(..., json_schema_extra=HEURISTIC)
    required_level: int = Field(..., json_schema_extra=HEURISTIC)
    required_name: str = Field(..., json_schema_extra=HEURISTIC)
    gap: int = Field(..., json_schema_extra=HEURISTIC)
    status: FindingStatus = Field(..., json_schema_extra=HEURISTIC)
    design_done: float = Field(..., json_schema_extra=HEURISTIC)
    operating_done: float = Field(..., json_schema_extra=HEURISTIC)
    evidence: list[EvidenceRef] = Field(default_factory=list, json_schema_extra=HEURISTIC)
    vetoes: list[Veto] = Field(default_factory=list, json_schema_extra=HEURISTIC)
    veto_capped: bool = Field(False, json_schema_extra=HEURISTIC)
    rationale: str = Field(..., json_schema_extra=HEURISTIC)
    draft: str = Field("DRAFT — REQUIRES REVIEW", json_schema_extra=HEURISTIC)


# ---------------------------------------------------------------------------
# Coverage map (the RM-21D-* evidence-item slice) — heuristic, deterministic.
# A model LOCATES + QUOTES + TAGS evidence items; everything below is computed in
# pure code (atlas/engine/coverage.py). No model assigns any status here.
# ---------------------------------------------------------------------------

class CoverageItem(BaseModel):
    """One registry evidence_item and whether the document evidences it."""

    evidence_item_id: str = Field(..., json_schema_extra=HEURISTIC)
    item: str = Field(..., json_schema_extra=HEURISTIC)             # registry description
    status: CoverageStatus = Field(..., json_schema_extra=HEURISTIC)
    decisive: bool = Field(False, json_schema_extra=HEURISTIC)      # the load-bearing item?
    max_confidence: float = Field(0.0, json_schema_extra=HEURISTIC) # best locating confidence
    evidence: list[EvidenceRef] = Field(default_factory=list, json_schema_extra=HEURISTIC)


class ControlCoverage(BaseModel):
    """Per-control coverage: each evidence item's status + the resulting coverage state."""

    control_id: str = Field(..., json_schema_extra=STATUTORY)
    title: str = Field(..., json_schema_extra=HEURISTIC)
    nis2_ref: str = Field(..., json_schema_extra=STATUTORY)
    decisive_item: str = Field(..., json_schema_extra=HEURISTIC)
    coverage_state: CoverageStatus = Field(..., json_schema_extra=HEURISTIC)
    present_count: int = Field(..., json_schema_extra=HEURISTIC)
    ambiguous_count: int = Field(..., json_schema_extra=HEURISTIC)
    absent_count: int = Field(..., json_schema_extra=HEURISTIC)
    total_items: int = Field(..., json_schema_extra=HEURISTIC)
    coverage_ratio: float = Field(..., json_schema_extra=HEURISTIC)   # present / total
    items: list[CoverageItem] = Field(default_factory=list, json_schema_extra=HEURISTIC)
    vetoes: list[Veto] = Field(default_factory=list, json_schema_extra=HEURISTIC)
    veto_capped: bool = Field(False, json_schema_extra=HEURISTIC)
    rationale: str = Field(..., json_schema_extra=HEURISTIC)


class AreaCoverage(BaseModel):
    """The coverage map for a whole control area (Art 21(2)(d) supply chain)."""

    area_id: str = Field(..., json_schema_extra=HEURISTIC)
    article: str = Field(..., json_schema_extra=STATUTORY)
    title: str = Field(..., json_schema_extra=HEURISTIC)
    registry_sha256: str = Field(..., json_schema_extra=HEURISTIC)
    controls: list[ControlCoverage] = Field(default_factory=list, json_schema_extra=HEURISTIC)
    item_summary: dict[str, int] = Field(default_factory=dict, json_schema_extra=HEURISTIC)
    control_summary: dict[str, int] = Field(default_factory=dict, json_schema_extra=HEURISTIC)
    note: str = Field(
        "Heuristic coverage map; the model only located + quoted + tagged evidence, every "
        "status was computed deterministically. NIS2 Art 21(1) is outcomes-based — coverage "
        "is not a safe harbour.",
        json_schema_extra=HEURISTIC,
    )


# ---------------------------------------------------------------------------
# Composite responses + snapshot
# ---------------------------------------------------------------------------

class InsufficientInput(BaseModel):
    status: Literal["INSUFFICIENT_INPUT"] = "INSUFFICIENT_INPUT"
    reasons: list[str]


class ClassifyResult(BaseModel):
    status: Literal["ok", "INSUFFICIENT_INPUT"] = "ok"
    verdict: Optional[Verdict] = None
    proportionality: Optional[Proportionality] = None
    bar: Optional[Bar] = None
    reasons: list[str] = Field(default_factory=list)


class VersionInfo(BaseModel):
    engine_version: str
    ruleset_version: str
    ruleset_sha256: str


class Snapshot(BaseModel):
    """A fully re-derivable export. ``content_sha256`` is taken over everything
    EXCEPT ``generated_at``, so two runs of the same inputs are byte-identical in
    content and re-derive to the same hash."""

    engine_version: str
    ruleset_version: str
    ruleset_sha256: str
    generated_at: str
    content_sha256: str
    inputs: EntityInput
    verdict: Optional[Verdict] = None
    proportionality: Optional[Proportionality] = None
    bar: Optional[Bar] = None
    findings: list[Finding] = Field(default_factory=list)
    status: Literal["ok", "INSUFFICIENT_INPUT"] = "ok"
    reasons: list[str] = Field(default_factory=list)


GroupNode.model_rebuild()
