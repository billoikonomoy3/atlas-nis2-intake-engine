"""Proportionality scorer — HEURISTIC, tunable, NO statutory force.

A transparent additive weighted score (0-100) -> tier, fully re-derivable by hand.
NIS2 Art 21(1) is outcomes-based; this score INFORMS, never replaces, that judgment.
Every weight lives in the ruleset under ``heuristic_weights`` and each one's
justification is an open TODO for a human (see README). The score only ever raises
via floors (essential -> >=60, systemic/sole-national -> >=80); a floor never lowers.
"""

from __future__ import annotations

from . import ruleset as R
from .models import Proportionality, ProportionalityInput, Verdict


def _footprint_points(n_geographies: int, n_entities: int) -> int:
    fp = R.heuristic_weights()["footprint"]

    def ladder(n: int, rungs: list[list[int]]) -> int:
        for threshold, pts in rungs:
            if n >= threshold:
                return pts
        return 0

    g = ladder(n_geographies or 1, fp["geographies"])
    e = ladder(n_entities or 1, fp["entities"])
    return max(g, e)


def tier_for(score: int) -> tuple[str, str]:
    w = R.heuristic_weights()
    for name, lo, hi in w["tiers"]:
        if lo <= score <= hi:
            return name, w["tier_expectation"][name]
    last = w["tiers"][-1][0]
    return last, w["tier_expectation"][last]


def proportionality(
    *,
    size_band: str,
    entity_class: str,
    sector_annex: str,
    cross_border_systemic: str = "none",
    n_geographies: int = 1,
    n_entities: int = 1,
    special_entity: bool = False,
    supply_chain: str = "low",
) -> Proportionality:
    """Transparent additive weighted score (0-100) -> tier. Pure; ruleset-driven."""
    w = R.heuristic_weights()
    pts = {
        "size_band": w["size_points"].get(size_band, 0),
        "entity_class": w["class_points"].get(entity_class, 0),
        "sector_annex": w["annex_points"].get(sector_annex, 0),
        "cross_border_systemic": w["xborder_points"].get(cross_border_systemic, 0),
        "footprint": _footprint_points(n_geographies, n_entities),
        "special_entity": w["special_entity_points"] if special_entity else 0,
        "supply_chain": w["supply_points"].get(supply_chain, 0),
    }
    raw = sum(pts.values())
    score = raw
    floors: list[str] = []
    if entity_class == "essential" and score < w["floors"]["essential_min"]:
        score = w["floors"]["essential_min"]
        floors.append(f"essential -> floored to Enhanced (>={w['floors']['essential_min']})")
    if cross_border_systemic in ("systemic", "sole_national") and score < w["floors"]["systemic_min"]:
        score = w["floors"]["systemic_min"]
        floors.append(f"systemic / sole-national provider -> floored to Critical (>={w['floors']['systemic_min']})")
    tier, expectation = tier_for(score)
    return Proportionality(
        points=pts,
        raw_score=raw,
        score=score,
        floors_applied=floors,
        tier=tier,
        tier_expectation=expectation,
    )


def score_from_verdict(verdict: Verdict, pin: ProportionalityInput | None = None) -> Proportionality:
    """Convenience: score directly off a Verdict + heuristic proportionality inputs."""
    pin = pin or ProportionalityInput()
    return proportionality(
        size_band=verdict.size_band,
        entity_class=verdict.entity_class,
        sector_annex=verdict.sector_annex,
        cross_border_systemic=pin.cross_border_systemic,
        n_geographies=pin.n_geographies,
        n_entities=pin.n_entities,
        special_entity=pin.special_entity,
        supply_chain=pin.supply_chain,
    )
