"""Atlas — the pyramid economics (preserved from the prior build).

Quantifies, honestly, the Stage 4-7 first-pass cost Atlas collapses. Pure deterministic
code, no LLM, no network: every EUR figure is hand-re-derivable via ONE chain off the
low-end fee. It produces NO legal pass/fail and collapses COST, not LIABILITY. Kept here
(not in the judgment path) so the prior work is not lost in the restructure.
"""

from __future__ import annotations

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
    }


HONESTY_CAVEATS = [
    "AUGMENTATION, NOT REPLACEMENT. Atlas automates only the Stage 4-7 first pass.",
    "NO LEGAL PASS/FAIL. NIS2 Art 21(1) is outcomes-based; every output DRAFT — REQUIRES REVIEW.",
    "THE MATURITY SCORE IS NOT A SAFE HARBOUR. NIS2 prescribes no numeric scale.",
    "EUR FIGURES ARE A DERIVED RANGE, NOT A QUOTE. One explicit chain; headline capped at EUR 5k.",
    "~EUR 0 IS MARGINAL, NOT FULLY-LOADED. Excludes one-time build/maintenance.",
    "COLLAPSES COST, NOT LIABILITY. An Art 20 finding stays a director-liability vector.",
]
