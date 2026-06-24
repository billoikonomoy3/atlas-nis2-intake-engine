"""INSUFFICIENT_INPUT regression — malformed numerics must never silently classify.

This pins the known v1 bug fix: a non-finite (NaN/Inf), negative, or missing required
financial must return a distinct INSUFFICIENT_INPUT status, never a confident verdict.
Valid boundary inputs must still classify unchanged.
"""

from __future__ import annotations

import math

import pytest

from atlas.engine.models import EntityInput, GroupNode
from atlas.engine.validate import is_valid, validate_entity
from atlas.service import run_classify


def E(name="t", staff=50, turnover=1_000_000, balance=1_000_000, **kw):
    return GroupNode(name=name, staff=staff, turnover_eur=turnover, balance_sheet_eur=balance, **kw)


def _entity(root):
    return EntityInput(sector_annex="I", root=root)


# --- adversarial: each must be INSUFFICIENT_INPUT, never a verdict -------------

BAD_CASES = [
    ("negative staff", E(staff=-5)),
    ("NaN turnover", E(turnover=float("nan"))),
    ("Inf balance", E(balance=float("inf"))),
    ("missing staff", E(staff=None)),
    ("missing turnover", E(turnover=None)),
    ("-Inf turnover", E(turnover=float("-inf"))),
    ("negative balance in a child", GroupNode(
        name="root", staff=10, turnover_eur=1e6, balance_sheet_eur=1e6,
        related=[E(name="child", balance=-1.0)])),
]


@pytest.mark.parametrize("label,root", BAD_CASES, ids=[c[0] for c in BAD_CASES])
def test_malformed_input_is_insufficient(label, root):
    entity = _entity(root)
    assert not is_valid(entity), f"{label}: should be invalid"
    assert validate_entity(entity), f"{label}: should produce reasons"
    result = run_classify(entity)
    assert result.status == "INSUFFICIENT_INPUT", f"{label}: must not classify"
    assert result.verdict is None, f"{label}: must not emit a verdict"
    assert result.reasons, f"{label}: must explain why"


def test_nan_inf_never_resolve_to_a_band():
    # The exact v1 trap: malformed financials must not resolve to below_medium/out-of-scope.
    entity = _entity(E(staff=None, turnover=float("nan"), balance=float("inf")))
    result = run_classify(entity)
    assert result.status == "INSUFFICIENT_INPUT"
    assert result.verdict is None


# --- valid boundary inputs must still classify --------------------------------

def test_staff_exactly_50_is_medium():
    result = run_classify(_entity(E(staff=50, turnover=1_000_000, balance=1_000_000)))
    assert result.status == "ok"
    assert result.verdict.size_band == "medium"


def test_turnover_exactly_10m_not_greater_is_below_medium():
    # Financials use strict > and need BOTH limbs; turnover == 10e6 (not >) with low
    # staff stays below_medium.
    result = run_classify(_entity(E(staff=10, turnover=10_000_000, balance=20_000_000)))
    assert result.status == "ok"
    assert result.verdict.size_band == "below_medium"


def test_valid_zero_figures_are_allowed():
    # Zero is a finite, non-negative figure — valid input, classifies (below_medium).
    entity = _entity(E(staff=0, turnover=0, balance=0))
    assert is_valid(entity)
    result = run_classify(entity)
    assert result.status == "ok"
    assert result.verdict.size_band == "below_medium"
