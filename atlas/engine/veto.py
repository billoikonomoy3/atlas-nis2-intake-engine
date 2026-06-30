"""Deterministic veto (disqualifying-finding) evaluation — pure code, NO model call.

The maturity scorer credits whether a control is *documented*; it cannot see when what
is documented is the very thing that *defeats* the control (presence != conformance).
A veto closes that gap: it fires when a control's OWN cited evidence contains a clause
whose meaning disqualifies the outcome.

Rules are DATA, read from ``ruleset/nis2_v1.yaml › vetoes`` — not hardcoded to one
control. Each rule names the NIS2 reference it defeats and carries a short rationale,
so the Finding can show WHY the rung was capped. Adding a veto is a YAML edit.

Evaluation is pure deterministic code over the already-cited facts (the same facts that
fed the score), so it runs in the offline judgment path with no network and no model.

Seed rule — the supply-chain archetype: a supplier incident-notification window longer
than the entity's own Art 23 cascade (early warning <=24h, notification <=72h) leaves
the entity structurally unable to meet its statutory reporting duty. The window is
parsed from the cited quote and compared, in pure code, against a ceiling carried in
the rule (``max_window_hours``).
"""

from __future__ import annotations

import re

from . import ruleset as R
from .models import ExtractedFact, Veto

# Duration unit -> hours. These are UNITS (arithmetic), not policy, so they live in
# code; the ceiling (max_window_hours) and the context patterns are DATA in the ruleset.
_UNIT_HOURS = {"hour": 1, "hr": 1, "day": 24, "week": 168, "month": 720, "year": 8760}
# A few spelled-out small quantities, so "within one month" / "a week" are not missed.
_WORD_QTY = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3}
_DURATION_RE = re.compile(
    r"\b(\d+|a|an|one|two|three)\s*"
    r"(?:calendar|business|working)?\s*"
    r"(hour|hr|day|week|month|year)s?\b",
    re.IGNORECASE,
)


def _windows_hours(text: str) -> list[int]:
    """Every duration mentioned in ``text``, normalised to hours (deterministic)."""
    out: list[int] = []
    for qty, unit in _DURATION_RE.findall(text):
        n = int(qty) if qty.isdigit() else _WORD_QTY.get(qty.lower())
        if n is None:
            continue
        out.append(n * _UNIT_HOURS[unit.lower()])
    return out


def _all_match(patterns: list[str], text: str) -> bool:
    """True iff every pattern (case-insensitive regex) appears in ``text``."""
    return all(re.search(p, text, re.IGNORECASE) for p in patterns)


def _rule_applies(rule: dict, control_id: str) -> bool:
    """Does this veto rule target ``control_id``?

    A rule may scope itself three ways, any of which counts: ``control_id`` (one
    control), ``control_ids`` (an explicit list), or ``control_area`` (every control in
    an area, e.g. all RM-21D-* for "21D"). The old code matched only ``control_id ==``,
    so an area/leaf rule that set ``control_area`` but no ``control_id`` resolved to None
    and silently NEVER fired. Honouring all three scopes is the fix.
    """
    if rule.get("control_id") == control_id:
        return True
    if control_id in (rule.get("control_ids") or []):
        return True
    area = rule.get("control_area")
    if area is not None and R.area_of(control_id) == area:
        return True
    return False


def evaluate_vetoes(control_id: str, facts: list[ExtractedFact]) -> list[Veto]:
    """Return every active veto for ``control_id``, deterministically, from its facts.

    Pure function: no clock, no randomness, no model. A rule fires per offending fact
    when its ``context_all`` patterns all appear in that fact and (when the rule sets
    ``max_window_hours``) the fact states a window exceeding that ceiling. Results are
    deduped and sorted so the output is byte-stable across runs.
    """
    rules = [r for r in R.veto_rules() if _rule_applies(r, control_id)]
    if not rules:
        return []

    hits: dict[tuple, Veto] = {}
    for fact in facts:
        text = f"{fact.source_quote} {fact.claim}"
        for rule in rules:
            context = rule.get("context_all") or []
            if context and not _all_match(context, text):
                continue

            detail = rule.get("detail", "")
            max_h = rule.get("max_window_hours")
            if max_h is not None:
                breaching = [h for h in _windows_hours(text) if h > max_h]
                if not breaching:
                    continue  # a duration rule with no over-ceiling window does not fire
                worst = max(breaching)
                ref = rule.get("defeats_ref", "")
                detail = (f"stated window of {worst}h exceeds the {max_h}h ceiling"
                          f"{f' ({ref})' if ref else ''}.")

            key = (rule["id"], fact.doc_id, fact.page, fact.source_quote.strip())
            if key in hits:
                continue
            hits[key] = Veto(
                veto_id=rule["id"],
                defeats_ref=rule.get("defeats_ref", ""),
                rationale=rule.get("rationale", ""),
                detail=detail,
                matched_quote=fact.source_quote,
                doc_id=fact.doc_id,
                page=fact.page,
            )

    return [hits[k] for k in sorted(hits)]
