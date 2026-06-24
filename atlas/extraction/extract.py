"""Cited extraction — a model LOCATES + QUOTES evidence for one control. Model only.

Hard rules enforced in code (not left to the prompt):
  * the model returns schema-locked facts via tool use — no free-text parsing;
  * the model assigns NO maturity level and makes NO legal judgment (no such field
    exists in the tool schema);
  * every returned fact must carry a ``source_quote`` and cite a (doc_id, page) that
    EXISTS in the ingested chunks, and (strict mode) the quote must actually appear in
    that chunk's text — otherwise the fact is DISCARDED. Provenance is mandatory.

The ``runner`` seam lets callers inject a deterministic stub so the eval harness and
CI run fully offline; the default runner calls the Anthropic API (the only network
dependency in the whole system, and only here).
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from ..engine import ruleset as R
from ..engine.models import ExtractedFact
from .ingest import Chunk, chunks_to_prompt_block

EXTRACTION_MODEL = os.environ.get("ATLAS_EXTRACTION_MODEL", "claude-sonnet-4-6")

# runner(system: str, user: str, tool: dict) -> list[fact-dict]
Runner = Callable[[str, str, dict], list[dict]]


class ExtractionError(RuntimeError):
    pass


FACT_TOOL: dict[str, Any] = {
    "name": "record_evidence_facts",
    "description": (
        "Record facts you LOCATED in the supplied documents that evidence the given "
        "control. Only record a fact you can back with a short verbatim quote from the "
        "text. Do NOT assess maturity, compliance, or a level — only locate and quote."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "evidence_kind": {"type": "string", "enum": ["design", "operating"],
                                          "description": "design = the control as written; operating = proof it ran."},
                        "claim": {"type": "string", "description": "what the document establishes (paraphrase)."},
                        "source_quote": {"type": "string",
                                         "description": "<=25 words, VERBATIM from the cited chunk, for provenance."},
                        "doc_id": {"type": "string", "description": "doc_id from the [doc_id=... page=...] tag."},
                        "page": {"type": "integer", "description": "page from the [doc_id=... page=...] tag."},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1,
                                       "description": "extraction confidence (how sure the quote supports the claim) — NOT a legal judgment."},
                    },
                    "required": ["evidence_kind", "claim", "source_quote", "doc_id", "page", "confidence"],
                },
            }
        },
        "required": ["facts"],
    },
}


def build_prompt(control_id: str, chunks: list[Chunk]) -> tuple[str, str]:
    crit = R.criteria_by_id().get(control_id)
    if crit is None:
        raise ExtractionError(f"unknown control_id: {control_id!r}")
    design = "\n".join(f"  - {d}" for d in crit["design_evidence"])
    operating = "\n".join(f"  - {o}" for o in crit["operating_evidence"])
    system = (
        "You are an evidence-location assistant for a NIS2 readiness assessment. Your ONLY "
        "job is to find passages in the supplied documents that evidence a specific control, "
        "label each as design (the control as written) or operating (proof it ran), and quote "
        "them verbatim with their doc_id and page. You DO NOT assign a maturity level, you DO "
        "NOT decide compliance, and you DO NOT judge sufficiency — a separate deterministic "
        "engine does all of that. Never invent a quote: every source_quote must appear verbatim "
        "in the cited chunk. If you find nothing, record an empty list."
    )
    user = (
        f"Control {control_id} — {crit['ref']}: {crit['objective']}\n\n"
        f"DESIGN evidence this control would have:\n{design}\n\n"
        f"OPERATING evidence this control would have:\n{operating}\n\n"
        f"Documents (each chunk tagged with its doc_id and page):\n\n"
        f"{chunks_to_prompt_block(chunks)}\n\n"
        f"Call record_evidence_facts with the facts you can quote. Quotes must be <=25 words "
        f"and copied verbatim from the chunk you cite."
    )
    return system, user


def _anthropic_runner(system: str, user: str, tool: dict) -> list[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ExtractionError(
            "ANTHROPIC_API_KEY is not set. The deterministic core runs offline, but the "
            "extraction layer needs a model API key. Set ANTHROPIC_API_KEY or pass a runner."
        )
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise ExtractionError("the 'anthropic' package is required for live extraction") from exc

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=EXTRACTION_MODEL,
        max_tokens=2048,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool["name"]:
            data = block.input
            if isinstance(data, str):
                data = json.loads(data)
            return data.get("facts", [])
    return []


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def validate_provenance(facts: list[ExtractedFact], chunks: list[Chunk], *,
                        strict: bool = True) -> list[ExtractedFact]:
    """Keep only facts whose provenance checks out against the source chunks.

    A fact is KEPT only if it has a non-empty source_quote, cites a (doc_id, page)
    that EXISTS in ``chunks``, and (strict) its quote actually appears in that chunk's
    text. This is the single anti-fabrication gate — it is invoked both inside
    extraction AND at the public API boundary so no untrusted, unverifiable fact can
    reach scoring (a quote that was never in any document is dropped, not scored).
    """
    by_locator = {(c.doc_id, c.page): _normalize(c.text) for c in chunks}
    kept: list[ExtractedFact] = []
    for fact in facts:
        if not fact.source_quote or not fact.source_quote.strip():
            continue
        chunk_text = by_locator.get((fact.doc_id, fact.page))
        if chunk_text is None:
            continue  # cited a doc/page that does not exist -> drop
        if strict and _normalize(fact.source_quote) not in chunk_text:
            continue  # quote not actually in the cited chunk -> drop (anti-hallucination)
        kept.append(fact)
    return kept


def extract_facts(control_id: str, chunks: list[Chunk], *, runner: Runner | None = None,
                  strict: bool = True) -> list[ExtractedFact]:
    """Extract schema-locked, provenance-checked facts for one control.

    The model returns raw facts; each is schema-locked into an ExtractedFact and then
    passed through ``validate_provenance`` — no fact without verifiable provenance scores.
    """
    runner = runner or _anthropic_runner
    system, user = build_prompt(control_id, chunks)
    raw = runner(system, user, FACT_TOOL)

    built: list[ExtractedFact] = []
    for item in raw:
        try:
            built.append(ExtractedFact(
                control_id=control_id,
                evidence_kind=item["evidence_kind"],
                claim=item["claim"],
                source_quote=item["source_quote"],
                doc_id=item["doc_id"],
                page=int(item["page"]),
                confidence=float(item["confidence"]),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return validate_provenance(built, chunks, strict=strict)
