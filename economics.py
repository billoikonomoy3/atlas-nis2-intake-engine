"""Atlas - the pyramid economics (the story a partner wants to hear).

Quantifies the cost Atlas collapses, honestly. The Big-4 leveraged model assumes
the evidence-gathering and assessment layer (Stages 4-7) is labour-intensive;
that is the assumption AI breaks. This module derives, from inlined Big-4
benchmarks, what the Stage 4-7 FIRST PASS costs in junior hours - and shows Atlas
producing it deterministically in ~90 seconds at ~EUR 0 marginal cost.

It is augmentation, not replacement: Stages 1-2 (scoping), the interviews, the
Art 21 proportionality judgment, the EQCR sign-off and the partner signature stay
human. The model collapses COST, not LIABILITY, and produces no legal pass/fail.

Every lever is explicit and adjustable; every EUR figure is hand-re-derivable via
ONE chain (the adversarial review removed three conflicting derivations). Numbers
are a derived RANGE, not a quote.
"""

from __future__ import annotations

# --- All inputs explicit and adjustable (defaults = conservative low-end) -----
DEFAULTS = {
    "manager_month_fee_eur": 180_000,   # low end of the 180k-280k blended sell
    "working_days_per_month": 260 / 12,  # 21.6667
    "hours_per_day": 8,
    "leverage_factor": 5.0,             # SINGLE most adjustable lever: junior day-rate = day-sell / leverage
    "gap_assessment_hours": 40,         # a NIS2 Art 21 gap assessment, billable hours
    "stage47_share": 0.85,              # fraction that is Stage 4-7 first-pass clerical work
    "controls_count": 16,
    "atlas_runtime_seconds": 90,
    "atlas_marginal_cost_eur": 0,
    "atlas_anchor_eur": 5_000,          # partner-safe capped headline
}


def _round_half_up(x: float) -> int:
    from decimal import Decimal, ROUND_HALF_UP
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute(**overrides) -> dict:
    """Derive the cost-collapse numbers via one canonical, hand-re-derivable chain."""
    p = {**DEFAULTS, **overrides}

    day_sell = p["manager_month_fee_eur"] / p["working_days_per_month"]      # 8307.69
    junior_day_rate = _round_half_up(day_sell / p["leverage_factor"])        # 1662
    junior_hourly = _round_half_up(junior_day_rate / p["hours_per_day"])     # 208

    stage47_hours = p["gap_assessment_hours"] * p["stage47_share"]           # 34
    hours_per_control = stage47_hours / p["controls_count"]                  # 2.125
    manual_cost = _round_half_up(stage47_hours * junior_hourly)              # 7072

    cost_collapsed = manual_cost - p["atlas_marginal_cost_eur"]             # 7072
    headline_claim = min(cost_collapsed, p["atlas_anchor_eur"])             # 5000
    hours_freed = stage47_hours                                             # 34
    hours_kept_human = p["gap_assessment_hours"] - stage47_hours           # 6

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
    "AUGMENTATION, NOT REPLACEMENT. Atlas automates only the Stage 4-7 first pass; scoping, "
    "interviews, the Art 21 proportionality judgment, EQCR challenge and the partner signature stay human.",
    "NO LEGAL PASS/FAIL. NIS2 Art 21(1) is outcomes-based; the maturity pass is evidence-gathering "
    "vocabulary only, every output DRAFT - REQUIRES REVIEW.",
    "THE MATURITY SCORE IS NOT A SAFE HARBOUR. NIS2 prescribes no numeric scale; tiers carry no statutory force.",
    "EUR FIGURES ARE A DERIVED RANGE, NOT A QUOTE. One explicit chain off the low-end fee; change any lever "
    "(leverage_factor most of all) and it re-derives by hand. Headline capped at the EUR 5k partner-safe anchor.",
    "~EUR 0 IS MARGINAL, NOT FULLY-LOADED. Offline pure code; excludes one-time build/maintenance.",
    "FREED HOURS ARE A CHOICE. They convert to margin/throughput only if redeployed; the value is pyramid "
    "leverage, not a headcount cut.",
    "COLLAPSES COST, NOT LIABILITY. An Art 20 finding stays a corporate- and personal-director-liability "
    "vector (bestuurdersaansprakelijkheid) however cheaply the first pass was produced.",
]


if __name__ == "__main__":
    r = compute()
    print(f"Junior blended rate: EUR {r['junior_hourly_eur']}/h "
          f"(EUR {r['junior_day_rate_eur']}/day from EUR {r['day_sell_eur']}/day-sell / leverage)")
    print(f"Stage 4-7 first pass: {r['stage47_hours']:g} h x EUR {r['junior_hourly_eur']}/h "
          f"= EUR {r['manual_cost_eur']:,} of mostly junior hours")
    print(f"Atlas does it in ~{r['atlas_minutes']:g} min at ~EUR 0 -> headline claim EUR "
          f"{r['headline_claim_eur']:,} (full slice EUR {r['cost_collapsed_eur']:,})")
    print(f"{r['hours_freed']:g} h freed for judgment; {r['hours_kept_human']:g} h stay human.")
