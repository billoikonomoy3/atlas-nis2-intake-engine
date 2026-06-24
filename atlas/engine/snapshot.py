"""Snapshot assembly + content hashing — "re-derivable from the snapshot", literally.

``content_sha256`` is computed over the canonical JSON of every field EXCEPT
``generated_at`` (and the hash field itself). So two runs of the same inputs produce
byte-identical content and the same hash, while still carrying a wall-clock stamp.
To re-derive: load ``inputs`` from a snapshot, re-run the engine, rebuild with the
same ``generated_at``, and assert the ``content_sha256`` matches.
"""

from __future__ import annotations

import hashlib
import json

from .. import ENGINE_VERSION
from . import ruleset as R
from .models import Bar, EntityInput, Finding, Proportionality, Snapshot, Verdict


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def content_sha256(payload: dict) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def build_snapshot(
    *,
    inputs: EntityInput,
    generated_at: str,
    verdict: Verdict | None = None,
    proportionality: Proportionality | None = None,
    bar: Bar | None = None,
    findings: list[Finding] | None = None,
    status: str = "ok",
    reasons: list[str] | None = None,
) -> Snapshot:
    findings = findings or []
    reasons = reasons or []
    body = {
        "engine_version": ENGINE_VERSION,
        "ruleset_version": R.ruleset_version(),
        "ruleset_sha256": R.ruleset_sha256(),
        "inputs": inputs.model_dump(mode="json"),
        "verdict": verdict.model_dump(mode="json") if verdict else None,
        "proportionality": proportionality.model_dump(mode="json") if proportionality else None,
        "bar": bar.model_dump(mode="json") if bar else None,
        "findings": [f.model_dump(mode="json") for f in findings],
        "status": status,
        "reasons": reasons,
    }
    digest = content_sha256(body)
    return Snapshot(
        engine_version=ENGINE_VERSION,
        ruleset_version=R.ruleset_version(),
        ruleset_sha256=R.ruleset_sha256(),
        generated_at=generated_at,
        content_sha256=digest,
        inputs=inputs,
        verdict=verdict,
        proportionality=proportionality,
        bar=bar,
        findings=findings,
        status=status,
        reasons=reasons,
    )
