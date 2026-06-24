"""Ruleset loader — the engine reads its constants from here, hardcodes none.

Loads ``ruleset/nis2_v1.yaml`` once, computes its sha256 over the raw bytes, and
exposes the version + hash that every exported snapshot embeds. Because the hash is
taken over the file bytes, any change to a threshold, weight or criterion changes
the ruleset identity — which is what makes "re-derivable from the snapshot" literal.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# ruleset/nis2_v1.yaml lives at the repo root, two parents up from this file
# (atlas/engine/ruleset.py -> atlas/ -> <root>).
_RULESET_PATH = Path(__file__).resolve().parents[2] / "ruleset" / "nis2_v1.yaml"


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, Any], str]:
    raw = _RULESET_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = yaml.safe_load(raw.decode("utf-8"))
    return data, sha


def ruleset() -> dict[str, Any]:
    """The full parsed ruleset (cached)."""
    return _load()[0]


def ruleset_sha256() -> str:
    """sha256 of the raw ruleset bytes — the ruleset identity for snapshots."""
    return _load()[1]


def ruleset_version() -> str:
    return ruleset()["ruleset_version"]


def ruleset_path() -> Path:
    return _RULESET_PATH


# Convenience accessors (read-only views into the loaded data) -----------------

def statutory() -> dict[str, Any]:
    return ruleset()["statutory"]


def size_thresholds() -> dict[str, float]:
    return statutory()["size_thresholds"]


def class_rank() -> dict[str, int]:
    return statutory()["class_rank"]


def group_links() -> dict[str, float]:
    return statutory()["group_links"]


def annex_i_sectors() -> list[str]:
    return statutory()["annex_i_sectors"]


def annex_ii_sectors() -> list[str]:
    return statutory()["annex_ii_sectors"]


def special_flags() -> dict[str, Any]:
    return statutory()["special_flags"]


def heuristic_weights() -> dict[str, Any]:
    return ruleset()["heuristic_weights"]


def baseline() -> dict[str, Any]:
    return ruleset()["baseline"]


def required_by_tier() -> dict[str, int]:
    return baseline()["required_by_tier"]


def operating_critical() -> set[str]:
    return set(baseline()["operating_critical"])


def maturity_ladder() -> list[list[Any]]:
    return ruleset()["maturity_ladder"]


def maturity_thresholds() -> dict[str, float]:
    return ruleset()["maturity_thresholds"]


def criteria() -> list[dict[str, Any]]:
    return ruleset()["criteria"]


@lru_cache(maxsize=1)
def criteria_by_id() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in criteria()}


def copyright_note() -> str:
    return ruleset()["copyright_note"]


# Module-level convenience constants (read once at import).
RULESET_VERSION = ruleset_version()
RULESET_SHA256 = ruleset_sha256()
