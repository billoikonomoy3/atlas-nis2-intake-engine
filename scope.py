"""Atlas - NIS2 Stage-3 applicability & classification engine (deterministic core).

Decides, from user-provided facts only, whether an entity is in scope of the
NIS2 Directive (EU) 2022/2555 and whether it is an 'essential' or 'important'
entity. This is the audit-grade replacement for the naive v1 classifier.

What v1 got wrong (and this fixes), per the engagement Stage-3 notes:
  * Size was "staff OR turnover" shorthand. The real test (Commission
    Recommendation 2003/361/EC) is: headcount is a HARD CEILING (a standalone
    >= trigger), while the two financial figures are a SINGLE limb read in the
    entity's favour - you only breach it by exceeding BOTH annual turnover AND
    balance-sheet total (strict >). The 40-staff / EUR 15m turnover / EUR 5m
    balance firm is therefore SMALL and OUT OF SCOPE; the shorthand wrongly
    pulled it in.
  * No group aggregation. Article 6 requires CONSOLIDATED figures: +100% of any
    linked (controlled) enterprise and a pro-rata share of partner (25-50%)
    enterprises - and that consolidation is RECURSIVE down the group tree, so a
    subsidiary of a multinational is never a microenterprise.
  * No two-year rule. Article 4(2): a size change only takes effect once a
    ceiling is crossed in TWO CONSECUTIVE accounting periods; a single anomalous
    year does not flip scope.
  * Article 3 carve-outs were silently deferred. They are now ENCODED: QTSP /
    TLD registry / DNS provider are essential at ANY size; medium-or-large public
    e-comms providers are essential (not merely important); an Article 2(2)
    designation forces essential at any size (or is held pending the act); and
    central-government bodies (and, under the Dutch transposition, local) are in
    scope regardless of size.

No LLM, no network, no external calls, standard library only. Every public
function is PURE and returns a full audit trail so each verdict is defensible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Sectors (VERIFY against NIS2 Annex I and Annex II)
# ---------------------------------------------------------------------------

ANNEX_I_SECTORS = [
    "Energy", "Transport", "Banking", "Financial market infrastructures",
    "Health", "Drinking water", "Waste water", "Digital infrastructure",
    "ICT service management (B2B)", "Public administration", "Space",
]

ANNEX_II_SECTORS = [
    "Postal and courier services", "Waste management",
    "Manufacture, production and distribution of chemicals",
    "Production, processing and distribution of food", "Manufacturing",
    "Digital providers", "Research",
]

# ---------------------------------------------------------------------------
# Size thresholds (Commission Recommendation 2003/361/EC)
# Staff: hard ceiling, inclusive (>=). Financials: strict (>) and AND-paired.
# ---------------------------------------------------------------------------

MEDIUM_STAFF = 50
MEDIUM_TURNOVER_EUR = 10_000_000
MEDIUM_BALANCE_EUR = 10_000_000

LARGE_STAFF = 250
LARGE_TURNOVER_EUR = 50_000_000
LARGE_BALANCE_EUR = 43_000_000

# Article 3 / Article 2(2) special-entity flags.
SIZE_EXEMPT_ESSENTIAL = {"qtsp", "tld", "dns"}        # essential at ANY size
ECOMMS = "ecomms"                                      # medium/large -> essential
PUBLIC_ADMIN = {"public_admin_central", "public_admin_local"}


def _normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


_ANNEX_I_LOOKUP = {_normalize(s): s for s in ANNEX_I_SECTORS}
_ANNEX_II_LOOKUP = {_normalize(s): s for s in ANNEX_II_SECTORS}


def annex_of(sector: str) -> str:
    """Map a free-text sector name to 'I', 'II' or 'none'."""
    key = _normalize(sector)
    if key in _ANNEX_I_LOOKUP:
        return "I"
    if key in _ANNEX_II_LOOKUP:
        return "II"
    return "none"


# ---------------------------------------------------------------------------
# Group model + Article 6 recursive aggregation
# ---------------------------------------------------------------------------


@dataclass
class Enterprise:
    """A node in the corporate group tree.

    `holding_pct` is the percentage of THIS enterprise held by its parent
    (ignored for the root entity). `control` explicitly overrides the
    percentage-based link test (control can exist at <=50% via voting rights /
    board majority / consolidated accounts, or be absent above 50%).
    `related` are sub-enterprises held by this node (recursion handles tiers).
    """
    name: str
    staff: float
    turnover_eur: float
    balance_sheet_eur: float
    holding_pct: float = 100.0
    control: Optional[bool] = None
    related: list["Enterprise"] = field(default_factory=list)


@dataclass
class Figures:
    staff: float
    turnover_eur: float
    balance_sheet_eur: float


def _link_class(holding_pct: float, control: Optional[bool]) -> tuple[str, float]:
    """Classify a link per 2003/361 Art 6, testing CONTROL/LINKED before PARTNER.

    Returns (class, multiplier): linked -> 100%, partner -> pro-rata, autonomous -> 0.
    """
    if control is True or holding_pct > 50:
        return "linked", 1.0
    if control is False:
        # Control explicitly disclaimed: fall back to the percentage bands but
        # can never be 'linked' on percentage alone below the threshold.
        if holding_pct >= 25:
            return "partner", holding_pct / 100.0
        return "autonomous", 0.0
    if holding_pct >= 25:
        return "partner", holding_pct / 100.0
    return "autonomous", 0.0


def consolidate(node: Enterprise, _trace: Optional[list] = None,
                _depth: int = 0) -> tuple[Figures, list]:
    """Recursively consolidate a group per Article 6.

    consolidated(node) = own(node)
                       + SUM over related R of factor(R) * consolidated(R)
    where each related enterprise is itself consolidated with ITS group first
    (the recursive step that the flat formula missed) and factor is 100% for
    linked, the holding fraction for partner, and 0 for autonomous.
    """
    trace = _trace if _trace is not None else []
    cs, ct, cb = node.staff, node.turnover_eur, node.balance_sheet_eur
    if _depth == 0:
        trace.append({
            "node": node.name, "link": "self (root)", "multiplier": 1.0,
            "staff": node.staff, "turnover": node.turnover_eur,
            "balance": node.balance_sheet_eur, "depth": _depth,
        })
    for child in node.related:
        link, mult = _link_class(child.holding_pct, child.control)
        child_fig, _ = consolidate(child, trace, _depth + 1)
        contrib_s = mult * child_fig.staff
        contrib_t = mult * child_fig.turnover_eur
        contrib_b = mult * child_fig.balance_sheet_eur
        cs += contrib_s
        ct += contrib_t
        cb += contrib_b
        trace.append({
            "node": child.name, "link": link, "holding_pct": child.holding_pct,
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
    """'large' | 'medium' | 'below_medium' from consolidated figures.

    large first (it implies medium). Staff inclusive (>=); financials strict (>)
    and only breached when BOTH turnover and balance exceed the threshold.
    """
    large = fig.staff >= LARGE_STAFF or (
        fig.turnover_eur > LARGE_TURNOVER_EUR and fig.balance_sheet_eur > LARGE_BALANCE_EUR
    )
    if large:
        return "large"
    medium = fig.staff >= MEDIUM_STAFF or (
        fig.turnover_eur > MEDIUM_TURNOVER_EUR and fig.balance_sheet_eur > MEDIUM_BALANCE_EUR
    )
    if medium:
        return "medium"
    return "below_medium"


def apply_two_year(raw_band: str, prior_band: Optional[str],
                   years_breached: int) -> tuple[str, str]:
    """Article 4(2): a band CHANGE only takes effect if sustained two consecutive
    accounting periods. `years_breached` = consecutive periods in the new band
    (reset to 0 on any non-consecutive year)."""
    if prior_band is None or raw_band == prior_band:
        return raw_band, "current band applies (no sustained change to test)"
    if years_breached >= 2:
        return raw_band, (
            f"change to '{raw_band}' sustained over {years_breached} consecutive "
            f"periods (Art 4(2)) - applies")
    return prior_band, (
        f"change to '{raw_band}' seen in only {years_breached} period; Art 4(2) "
        f"holds the prior band '{prior_band}'")


# ---------------------------------------------------------------------------
# Classification + Article 3 / Article 2(2) overrides
# ---------------------------------------------------------------------------

_CLASS_RANK = {"out_of_scope": 0, "deferred_designation": 0, "important": 1, "essential": 2}


def classify_entity(
    *,
    sector_annex: str,
    root: Enterprise,
    sector_name: Optional[str] = None,
    special_flags: Optional[list] = None,
    art2_2_designation: Optional[str] = None,   # None | 'active' | 'pending'
    years_breached: int = 2,
    prior_band: Optional[str] = None,
) -> dict:
    """Full NIS2 applicability + classification verdict with audit trail.

    Returns a dict: in_scope, entity_class, size_band, consolidated figures,
    reason, audit (ordered list of steps), flags (assumptions / human-review).
    Pure: depends only on its arguments and the module constants.
    """
    flags = list(special_flags or [])
    audit: list[str] = []

    # 1. Sector
    in_i = sector_annex == "I"
    in_ii = sector_annex == "II"
    audit.append(f"Sector: Annex {sector_annex}"
                 + (f" ({sector_name})" if sector_name else ""))

    # 2. Consolidated size (Article 6, recursive)
    fig, agg_trace = consolidate(root)
    multi_node = len(agg_trace) > 1
    if multi_node:
        audit.append(
            f"Article 6 consolidation over {len(agg_trace)} nodes -> "
            f"staff={fig.staff:g}, turnover=EUR {fig.turnover_eur:,.0f}, "
            f"balance=EUR {fig.balance_sheet_eur:,.0f}")
    else:
        audit.append(
            f"Standalone figures: staff={fig.staff:g}, "
            f"turnover=EUR {fig.turnover_eur:,.0f}, balance=EUR {fig.balance_sheet_eur:,.0f}")

    # 3. Size band + two-year rule
    raw_band = size_band(fig)
    band, ty_note = apply_two_year(raw_band, prior_band, years_breached)
    audit.append(f"Size band (2003/361): raw='{raw_band}'. {ty_note}. Effective band='{band}'.")

    # 4. Base classification from sector x size
    if in_i and band == "large":
        base, base_reason = "essential", "Annex I (high-criticality) + large => essential"
    elif in_i and band == "medium":
        base, base_reason = "important", "Annex I (high-criticality) + medium => important"
    elif in_ii and band in ("medium", "large"):
        base, base_reason = "important", f"Annex II (other-critical) + {band} => important (never essential by size)"
    else:
        base, base_reason = "out_of_scope", f"sector Annex {sector_annex} + '{band}' => out of scope on size"
    audit.append(f"Base classification: {base} ({base_reason}).")

    result_class = base
    in_scope = base != "out_of_scope"

    # 5. Article 3 / Article 2(2) overrides (can only raise the verdict)
    def promote(new_class: str, why: str):
        nonlocal result_class, in_scope
        audit.append(f"Override: {why} => {new_class}.")
        if _CLASS_RANK[new_class] >= _CLASS_RANK[result_class]:
            result_class = new_class
        in_scope = in_scope or new_class in ("essential", "important")

    exempt = [f for f in flags if f in SIZE_EXEMPT_ESSENTIAL]
    if exempt:
        promote("essential", f"Art 3 - {', '.join(exempt).upper()} is essential regardless of size")

    if ECOMMS in flags:
        if band in ("medium", "large"):
            promote("essential", "Art 3 - medium/large public e-comms provider is essential (not merely important)")
        else:
            audit.append("Note: e-comms override applies only to medium/large; below-medium provider is NOT rescued.")

    pub_admin = [f for f in flags if f in PUBLIC_ADMIN]
    if pub_admin:
        promote("essential", "Art 2(2)/Art 3 - public administration body in scope regardless of size")
        flags.append("ASSUMPTION: essential class for sub-medium public administration is transposition-dependent (verify Member-State law)")

    if art2_2_designation == "active":
        promote("essential", "Art 2(2) - Member-State designation in force (sole/systemic provider), essential at any size")
    elif art2_2_designation == "pending":
        if result_class == "out_of_scope":
            result_class = "deferred_designation"
            flags.append("DEFERRED: Art 2(2) designation requires a Member-State act not yet made - hold pending the act")
            audit.append("Override: Art 2(2) designation PENDING => deferred_designation (not yet in scope).")
        else:
            audit.append("Note: Art 2(2) designation pending, but entity is already in scope on other grounds.")

    # 6. Final reason
    reason = base_reason
    if result_class != base:
        reason = f"{base_reason}; overridden to {result_class} by Article 3/2(2)"
    elif result_class == "deferred_designation":
        reason = "out of scope on size, but a pending Art 2(2) designation may bring it in - human/legal review"

    return {
        "in_scope": in_scope,
        "entity_class": result_class,
        "size_band": band,
        "raw_size_band": raw_band,
        "consolidated": {
            "staff": fig.staff,
            "turnover_eur": fig.turnover_eur,
            "balance_sheet_eur": fig.balance_sheet_eur,
        },
        "sector_annex": sector_annex,
        "reason": reason,
        "audit": audit,
        "aggregation_trace": agg_trace,
        "flags": flags,
    }


def classify_simple(sector: str, staff: float, turnover_eur: float,
                    balance_sheet_eur: float, **kwargs) -> dict:
    """Convenience wrapper for a single, autonomous entity (no group)."""
    return classify_entity(
        sector_annex=annex_of(sector),
        sector_name=sector,
        root=Enterprise(name=sector or "entity", staff=staff,
                        turnover_eur=turnover_eur, balance_sheet_eur=balance_sheet_eur),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Tiny manual demo (the full interactive tool is atlas_nis2_intake.html)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # The canonical false-positive trap: must be OUT OF SCOPE.
    trap = classify_simple("Energy", staff=40, turnover_eur=15_000_000,
                           balance_sheet_eur=5_000_000)
    print("Trap (40 staff / EUR15m turnover / EUR5m balance, Annex I):")
    print(f"  in_scope={trap['in_scope']}  class={trap['entity_class']}  band={trap['size_band']}")
    print(f"  reason: {trap['reason']}")
    print()

    # Microenterprise subsidiary of a multinational: linked aggregation -> large.
    sub = Enterprise(
        name="EU subsidiary", staff=20, turnover_eur=2_000_000, balance_sheet_eur=1_000_000,
        related=[Enterprise(name="Global parent", staff=5_000,
                            turnover_eur=1_800_000_000, balance_sheet_eur=1_200_000_000,
                            holding_pct=100.0)],
    )
    res = classify_entity(sector_annex="I", root=sub, sector_name="Energy")
    print("Subsidiary of multinational (20 staff, parent 5,000):")
    print(f"  in_scope={res['in_scope']}  class={res['entity_class']}  "
          f"consolidated_staff={res['consolidated']['staff']:g}  band={res['size_band']}")
    print(f"  reason: {res['reason']}")
