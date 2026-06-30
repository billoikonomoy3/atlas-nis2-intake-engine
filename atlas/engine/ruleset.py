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

# The Art 21(2)(d) supply-chain evidence-item registry is a SEPARATE data source,
# loaded alongside the main ruleset. Keeping it separate leaves nis2_v1.yaml's bytes
# (and therefore ruleset_sha256, embedded in every snapshot) untouched, so existing
# determinism holds — this file is purely additive.
_SUPPLY_CHAIN_PATH = _RULESET_PATH.parent / "supply_chain_controls_21D.yaml"


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, Any], str]:
    raw = _RULESET_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = yaml.safe_load(raw.decode("utf-8"))
    return data, sha


@lru_cache(maxsize=1)
def _load_supply_chain() -> tuple[dict[str, Any], str]:
    if not _SUPPLY_CHAIN_PATH.exists():
        return {}, ""
    raw = _SUPPLY_CHAIN_PATH.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = yaml.safe_load(raw.decode("utf-8")) or {}
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


def veto_rules() -> list[dict[str, Any]]:
    """Disqualifying-finding rules (data-driven), aggregated across both data sources.

    The seed rules live in nis2_v1.yaml › vetoes; the Art 21(2)(d) area/leaf rules live
    in supply_chain_controls_21D.yaml › coverage_engine.vetoes. Both are returned here so
    veto.py evaluates them uniformly. Empty if neither file defines any.
    """
    return list(ruleset().get("vetoes", [])) + list(coverage_engine().get("vetoes", []))


@lru_cache(maxsize=1)
def criteria_by_id() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in criteria()}


# Supply-chain (Art 21(2)(d)) evidence-item registry — read-only accessors ------

def supply_chain_registry() -> dict[str, Any]:
    """The full parsed Art 21(2)(d) registry (cached). Empty dict if the file is absent."""
    return _load_supply_chain()[0]


def supply_chain_registry_sha256() -> str:
    """sha256 of the registry bytes — provenance for the coverage map. '' if absent."""
    return _load_supply_chain()[1]


def supply_chain_area() -> dict[str, Any]:
    return supply_chain_registry().get("control_area", {})


def supply_chain_controls() -> list[dict[str, Any]]:
    return supply_chain_registry().get("controls", [])


@lru_cache(maxsize=1)
def supply_chain_control_by_id() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in supply_chain_controls()}


def coverage_engine() -> dict[str, Any]:
    """The deterministic coverage layer's operational data (thresholds, decisive items,
    area vetoes). Empty dict if the registry is absent."""
    return supply_chain_registry().get("coverage_engine", {})


def decisive_items() -> dict[str, str]:
    return coverage_engine().get("decisive_items", {})


def present_confidence() -> float:
    """Heuristic, tunable threshold separating a 'present' item from an 'ambiguous' one."""
    return float(coverage_engine().get("present_confidence", 0.6))


def area_of(control_id: str) -> str | None:
    """The control area a control belongs to ('21D' for RM-21D-*), else None.

    Used by veto.py to fire area-scoped vetoes (``control_area``) for every control in
    the area — the leaf/area scope the per-control filter used to drop silently.
    """
    if control_id in supply_chain_control_by_id():
        return supply_chain_area().get("id")
    return None


def copyright_note() -> str:
    return ruleset()["copyright_note"]


# Module-level convenience constants (read once at import).
RULESET_VERSION = ruleset_version()
RULESET_SHA256 = ruleset_sha256()
