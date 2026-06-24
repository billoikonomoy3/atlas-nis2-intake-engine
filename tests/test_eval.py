"""Smoke test for the offline eval harness — keeps the structure green in CI."""

from __future__ import annotations

import json
from pathlib import Path

from eval.run_eval import baseline_runner, score_case

CASES_DIR = Path(__file__).resolve().parents[1] / "eval" / "extraction_cases"


def test_eval_cases_present_and_well_formed():
    cases = list(CASES_DIR.glob("*.json"))
    assert len(cases) >= 3
    for p in cases:
        c = json.loads(p.read_text(encoding="utf-8"))
        assert c["control_id"] == "RM-21D-01"
        assert "snippet" in c and "expected_facts" in c


def test_offline_baseline_scores_perfectly():
    for p in sorted(CASES_DIR.glob("*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        r = score_case(c, live=False)
        assert r["precision"] == 1.0 and r["recall"] == 1.0 and r["provenance"] == 1.0
