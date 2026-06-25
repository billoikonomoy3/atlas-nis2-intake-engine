"""Atlas — the pyramid economics — HEURISTIC, tunable, NO statutory force.

Quantifies, honestly, the Stage 4-7 first-pass cost Atlas collapses. Pure deterministic
code, no LLM, no network: every EUR figure is hand-re-derivable via ONE chain off the
low-end fee. It produces NO legal pass/fail and collapses COST, not LIABILITY. Kept here
(not in the judgment path) so the prior work is not lost in the restructure.

Like the proportionality weights, EVERY constant and EVERY EUR output here is a judgment
call that carries no statutory force and is tunable — it informs, never determines,
anything legal. Each constant's justification is an open item for a human, mirroring the
README open-items section: TODO: REVIEW — justify these constants.
"""

from __future__ import annotations

# Mirror of the law/heuristic split (cf. proportionality.py, README §"law determines vs.
# heuristic suggests"): the economics is ENTIRELY the "our heuristic suggests" side —
# never law. Tag carried on the compute() output so no EUR figure reads as statutory.
STATUTORY_FORCE = False
HEURISTIC_TAG = {"statutory": False, "heuristic": True, "tunable": True,
                 "basis": "internal cost-collapse estimate; no statutory force; not a quote"}

# TODO: REVIEW — justify these constants. Every value below is a tunable HEURISTIC with NO
# statutory force (mirrors ruleset `heuristic_weights`, whose rationale is likewise an open
# README TODO). They drive a cost estimate only — never a legal pass/fail or liability.
DEFAULTS = {
    "manager_month_fee_eur": 180_000,
    "working_days_per_month": 260 / 12,
    "hours_per_day": 8,
    "leverage_factor": 5.0,
    "gap_assessment_hours": 40,
    "stage47_share": 0.85,
    "controls_count": 16,
    "atlas_runtime_seconds": 90,
    "atlas_marginal_cost_eur": 0,
    "atlas_anchor_eur": 5_000,
}


def _round_half_up(x: float) -> int:
    from decimal import Decimal, ROUND_HALF_UP
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute(**overrides) -> dict:
    """Derive the cost-collapse numbers via one canonical, hand-re-derivable chain."""
    p = {**DEFAULTS, **overrides}

    day_sell = p["manager_month_fee_eur"] / p["working_days_per_month"]
    junior_day_rate = _round_half_up(day_sell / p["leverage_factor"])
    junior_hourly = _round_half_up(junior_day_rate / p["hours_per_day"])

    stage47_hours = p["gap_assessment_hours"] * p["stage47_share"]
    hours_per_control = stage47_hours / p["controls_count"]
    manual_cost = _round_half_up(stage47_hours * junior_hourly)

    cost_collapsed = manual_cost - p["atlas_marginal_cost_eur"]
    headline_claim = min(cost_collapsed, p["atlas_anchor_eur"])
    hours_freed = stage47_hours
    hours_kept_human = p["gap_assessment_hours"] - stage47_hours

    return {
        "inputs": p,
        "day_sell_eur": round(day_sell, 2),
        "junior_day_rate_eur": junior_day_rate,
        "junior_hourly_eur": junior_hourly,
        "stage47_hours": stage47_hours,
        "hours_per_control": hours_per_control,
        "manual_cost_eur": manual_cost,
        "atlas_minutes": p["atlas_runtime_seconds"] / 60.0,
        "cost_collapsed_eur": cost_collapsed,
        "headline_claim_eur": headline_claim,
        "hours_freed": hours_freed,
        "hours_kept_human": hours_kept_human,
        # --- Label every EUR output: HEURISTIC / tunable / no statutory force ----------
        # (mirrors how proportionality weights are tagged; see HEURISTIC_TAG above).
        "statutory": False,
        "heuristic": True,
        "tunable": True,
        "eur_outputs": ["day_sell_eur", "junior_day_rate_eur", "junior_hourly_eur",
                        "manual_cost_eur", "cost_collapsed_eur", "headline_claim_eur"],
        "disclaimer": ("Every *_eur figure here is a HEURISTIC, tunable estimate with NO "
                       "statutory force — a derived range, not a quote. "
                       "TODO: REVIEW — justify these constants."),
    }


HONESTY_CAVEATS = [
    "AUGMENTATION, NOT REPLACEMENT. Atlas automates only the Stage 4-7 first pass.",
    "NO LEGAL PASS/FAIL. NIS2 Art 21(1) is outcomes-based; every output DRAFT — REQUIRES REVIEW.",
    "THE MATURITY SCORE IS NOT A SAFE HARBOUR. NIS2 prescribes no numeric scale.",
    "EUR FIGURES ARE A DERIVED RANGE, NOT A QUOTE. One explicit chain; headline capped at EUR 5k.",
    "~EUR 0 IS MARGINAL, NOT FULLY-LOADED. Excludes one-time build/maintenance.",
    "COLLAPSES COST, NOT LIABILITY. An Art 20 finding stays a director-liability vector.",
]
