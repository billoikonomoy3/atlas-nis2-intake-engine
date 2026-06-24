"""NIS2 Stage-3 applicability & classification — the statutory core.

A faithful, ruleset-driven port of the verified engine: recursive Article 6
consolidation, the 2003/361/EC size test (staff hard ceiling >=, financials a single
AND-paired limb read strictly >), the Article 4(2) two-year rule, base sector x size
classification, and the Article 3 / Article 2(2) overrides (which can only RAISE the
class). Pure: depends only on its argument and the loaded ruleset. No model, no clock.

The 32-case oracle in tests/test_classify.py pins every branch; do not change a rule
without changing the oracle (and the oracle is the law here).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ruleset as R
from .models import Consolidated, EntityInput, GroupNode, Verdict


# ---------------------------------------------------------------------------
# Sector mapping
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def annex_of(sector: str) -> str:
    """Map a free-text sector name to 'I', 'II' or 'none' using the ruleset lists."""
    key = _normalize(sector)
    if key in {_normalize(s) for s in R.annex_i_sectors()}:
        return "I"
    if key in {_normalize(s) for s in R.annex_ii_sectors()}:
        return "II"
    return "none"


# ---------------------------------------------------------------------------
# Article 6 recursive consolidation
# ---------------------------------------------------------------------------

@dataclass
class Figures:
    staff: float
    turnover_eur: float
    balance_sheet_eur: float


def link_class(holding_pct: float, control: bool | None) -> tuple[str, float]:
    """Classify a group link per 2003/361 Art 6 (control/linked tested before partner).

    linked -> multiplier 1.0; partner (>=partner_min_pct) -> pro-rata; autonomous -> 0.
    Thresholds are read from the ruleset (statutory, oracle-pinned), not hardcoded.
    """
    gl = R.group_links()
    linked_min, partner_min = gl["linked_min_pct"], gl["partner_min_pct"]
    if control is True or holding_pct > linked_min:
        return "linked", 1.0
    if control is False:
        if holding_pct >= partner_min:
            return "partner", holding_pct / 100.0
        return "autonomous", 0.0
    if holding_pct >= partner_min:
        return "partner", holding_pct / 100.0
    return "autonomous", 0.0


def consolidate(node: GroupNode, _trace: list | None = None, _depth: int = 0) -> tuple[Figures, list]:
    """consolidated(node) = own + SUM over related R of factor(R) * consolidated(R),
    recursively (each child consolidated with its own group first)."""
    trace = _trace if _trace is not None else []
    cs, ct, cb = float(node.staff), float(node.turnover_eur), float(node.balance_sheet_eur)
    if _depth == 0:
        trace.append({
            "node": node.name, "link": "self (root)", "multiplier": 1.0,
            "staff": cs, "turnover": ct, "balance": cb, "depth": _depth,
        })
    for child in node.related or []:
        link, mult = link_class(float(child.holding_pct), child.control)
        child_fig, _ = consolidate(child, trace, _depth + 1)
        contrib_s = mult * child_fig.staff
        contrib_t = mult * child_fig.turnover_eur
        contrib_b = mult * child_fig.balance_sheet_eur
        cs += contrib_s
        ct += contrib_t
        cb += contrib_b
        trace.append({
            "node": child.name, "link": link, "holding_pct": float(child.holding_pct),
            "control": child.control, "multiplier": mult,
            "consolidated_staff_of_node": child_fig.staff,
            "staff": contrib_s, "turnover": contrib_t, "balance": contrib_b,
            "depth": _depth + 1,
        })
    return Figures(cs, ct, cb), trace


# ---------------------------------------------------------------------------
# Size band + two-year rule
# ---------------------------------------------------------------------------

def size_band(fig: Figures) -> str:
    """'large' | 'medium' | 'below_medium' from consolidated figures (ruleset-driven)."""
    t = R.size_thresholds()
    large = fig.staff >= t["large_staff"] or (
        fig.turnover_eur > t["large_turnover_eur"] and fig.balance_sheet_eur > t["large_balance_eur"]
    )
    if large:
        return "large"
    medium = fig.staff >= t["medium_staff"] or (
        fig.turnover_eur > t["medium_turnover_eur"] and fig.balance_sheet_eur > t["medium_balance_eur"]
    )
    if medium:
        return "medium"
    return "below_medium"


def apply_two_year(raw_band: str, prior_band: str | None, years_breached: int) -> tuple[str, str]:
    """Article 4(2): a band CHANGE only takes effect if sustained two consecutive periods."""
    if prior_band is None or raw_band == prior_band:
        return raw_band, "current band applies (no sustained change to test)"
    if years_breached >= 2:
        return raw_band, (
            f"change to '{raw_band}' sustained over {years_breached} consecutive periods (Art 4(2)) — applies")
    return prior_band, (
        f"change to '{raw_band}' seen in only {years_breached} period; Art 4(2) holds the prior band '{prior_band}'")


# ---------------------------------------------------------------------------
# Classification + Article 3 / Article 2(2) overrides
# ---------------------------------------------------------------------------

def classify_entity(entity: EntityInput) -> Verdict:
    """Full NIS2 applicability + classification verdict with audit trail.

    Assumes the input has already passed ``validate.validate_entity`` (no silent
    classification on bad input). Returns a statutory ``Verdict``.
    """
    rank = R.class_rank()
    sf = R.special_flags()
    size_exempt = set(sf["size_exempt_essential"])
    ecomms_flag = sf["ecomms"]
    public_admin = set(sf["public_admin"])

    # Resolve the sector annex: explicit value wins, else derive from the name.
    annex = entity.sector_annex or (annex_of(entity.sector_name) if entity.sector_name else "none")
    flags = list(entity.special_flags or [])
    audit: list[str] = []

    in_i = annex == "I"
    in_ii = annex == "II"
    audit.append(f"Sector: Annex {annex}" + (f" ({entity.sector_name})" if entity.sector_name else ""))

    # Consolidated size (Article 6, recursive).
    fig, agg_trace = consolidate(entity.root)
    if len(agg_trace) > 1:
        audit.append(
            f"Article 6 consolidation over {len(agg_trace)} nodes -> staff={fig.staff:g}, "
            f"turnover=EUR {fig.turnover_eur:,.0f}, balance=EUR {fig.balance_sheet_eur:,.0f}")
    else:
        audit.append(
            f"Standalone figures: staff={fig.staff:g}, turnover=EUR {fig.turnover_eur:,.0f}, "
            f"balance=EUR {fig.balance_sheet_eur:,.0f}")

    # Size band + two-year rule.
    raw_band = size_band(fig)
    band, ty_note = apply_two_year(raw_band, entity.prior_band, entity.years_breached)
    audit.append(f"Size band (2003/361): raw='{raw_band}'. {ty_note}. Effective band='{band}'.")

    # Base classification.
    if in_i and band == "large":
        base, base_reason = "essential", "Annex I (high-criticality) + large => essential"
    elif in_i and band == "medium":
        base, base_reason = "important", "Annex I (high-criticality) + medium => important"
    elif in_ii and band in ("medium", "large"):
        base, base_reason = "important", f"Annex II (other-critical) + {band} => important (never essential by size)"
    else:
        base, base_reason = "out_of_scope", f"sector Annex {annex} + '{band}' => out of scope on size"
    audit.append(f"Base classification: {base} ({base_reason}).")

    result_class = base
    in_scope = base != "out_of_scope"

    def promote(new_class: str, why: str) -> None:
        nonlocal result_class, in_scope
        audit.append(f"Override: {why} => {new_class}.")
        if rank[new_class] >= rank[result_class]:
            result_class = new_class
        in_scope = in_scope or new_class in ("essential", "important")

    exempt = [f for f in flags if f in size_exempt]
    if exempt:
        promote("essential", f"Art 3 - {', '.join(exempt).upper()} is essential regardless of size")

    if ecomms_flag in flags:
        if band in ("medium", "large"):
            promote("essential", "Art 3 - medium/large public e-comms provider is essential (not merely important)")
        else:
            audit.append("Note: e-comms override applies only to medium/large; below-medium provider is NOT rescued.")

    pub_admin = [f for f in flags if f in public_admin]
    if pub_admin:
        promote("essential", "Art 2(2)/Art 3 - public administration body in scope regardless of size")
        flags.append("ASSUMPTION: essential class for sub-medium public administration is "
                     "transposition-dependent (verify Member-State law)")

    if entity.art2_2_designation == "active":
        promote("essential", "Art 2(2) - Member-State designation in force (sole/systemic provider), essential at any size")
    elif entity.art2_2_designation == "pending":
        if result_class == "out_of_scope":
            result_class = "deferred_designation"
            flags.append("DEFERRED: Art 2(2) designation requires a Member-State act not yet made - hold pending the act")
            audit.append("Override: Art 2(2) designation PENDING => deferred_designation (not yet in scope).")
        else:
            audit.append("Note: Art 2(2) designation pending, but entity is already in scope on other grounds.")

    reason = base_reason
    if result_class != base:
        reason = f"{base_reason}; overridden to {result_class} by Article 3/2(2)"
    elif result_class == "deferred_designation":
        reason = "out of scope on size, but a pending Art 2(2) designation may bring it in - human/legal review"

    return Verdict(
        in_scope=in_scope,
        entity_class=result_class,
        size_band=band,
        raw_size_band=raw_band,
        consolidated=Consolidated(staff=fig.staff, turnover_eur=fig.turnover_eur,
                                  balance_sheet_eur=fig.balance_sheet_eur),
        sector_annex=annex,
        reason=reason,
        audit=audit,
        aggregation_trace=agg_trace,
        flags=flags,
    )
