"""Input validation — no silent classification on bad input.

NIS2 applicability turns on financial figures. A non-finite (NaN/Inf), negative, or
missing figure must NEVER resolve to a confident verdict (the v1 bug let malformed
financials silently land at below_medium / out-of-scope). This module walks the
whole group tree and returns a per-field reason list; a non-empty list means the
caller must return status ``INSUFFICIENT_INPUT`` instead of classifying.
"""

from __future__ import annotations

import math
from typing import Any

from .models import EntityInput, GroupNode

_REQUIRED_NUMERICS = ("staff", "turnover_eur", "balance_sheet_eur")


def _check_number(value: Any, field: str, path: str, reasons: list[str]) -> None:
    if value is None:
        reasons.append(f"{path}: missing required numeric '{field}'")
        return
    try:
        f = float(value)
    except (TypeError, ValueError):
        reasons.append(f"{path}: '{field}' is not a number ({value!r})")
        return
    if math.isnan(f):
        reasons.append(f"{path}: '{field}' is NaN — not a usable figure")
    elif math.isinf(f):
        reasons.append(f"{path}: '{field}' is infinite — not a usable figure")
    elif f < 0:
        reasons.append(f"{path}: '{field}' is negative ({f:g}) — impossible figure")


def _walk(node: GroupNode, path: str, reasons: list[str]) -> None:
    for field in _REQUIRED_NUMERICS:
        _check_number(getattr(node, field), field, path, reasons)

    # holding_pct is required for consolidation arithmetic; guard it too (it has a
    # default of 100.0, so this only fires on an explicitly bad value).
    hp = node.holding_pct
    if hp is None or (isinstance(hp, float) and (math.isnan(hp) or math.isinf(hp))) or hp < 0:
        reasons.append(f"{path}: 'holding_pct' is missing or not a finite, non-negative percentage")

    for child in node.related or []:
        child_path = f"{path} > {child.name}" if child.name else f"{path} > (unnamed)"
        _walk(child, child_path, reasons)


def validate_entity(entity: EntityInput) -> list[str]:
    """Return a list of per-field reasons. Empty list == input is usable."""
    reasons: list[str] = []
    root = entity.root
    if root is None:
        return ["root: missing entity (no figures supplied)"]
    _walk(root, root.name or "(root)", reasons)
    return reasons


def is_valid(entity: EntityInput) -> bool:
    return not validate_entity(entity)
