"""Extraction eval harness — precision / recall / provenance-correctness per control.

Runs ``atlas.extraction.extract.extract_facts`` over the labelled cases in
``eval/extraction_cases/`` and reports how well it locates the expected evidence and
how well its quotes trace back to the source.

  python eval/run_eval.py            # offline: a deterministic baseline runner (CI-safe)
  python eval/run_eval.py --live     # calls the real model (needs ANTHROPIC_API_KEY)

The offline runner is a literal baseline (it quotes the sentence containing each
expected phrase) so the harness is self-checking and CI-safe; --live measures the
actual model. Seeded with 3 RM-21D-01 cases — drop more JSON files in the folder to extend.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas.extraction.extract import extract_facts  # noqa: E402
from atlas.extraction.ingest import Chunk  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent / "extraction_cases"


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _sentences(text: str) -> list[str]:
    out, cur = [], ""
    for ch in text:
        cur += ch
        if ch in ".!?":
            out.append(cur.strip())
            cur = ""
    if cur.strip():
        out.append(cur.strip())
    return out


def baseline_runner(case: dict):
    """Deterministic offline baseline: quote the sentence containing each expected phrase."""
    def _runner(system, user, tool):
        facts = []
        for exp in case["expected_facts"]:
            phrase = exp["quote_contains"]
            for sent in _sentences(case["snippet"]):
                if _norm(phrase) in _norm(sent):
                    quote = " ".join(sent.split()[:25])
                    facts.append({
                        "evidence_kind": exp["evidence_kind"],
                        "claim": f"baseline match for {exp['evidence_kind']} evidence",
                        "source_quote": quote, "doc_id": case["doc_id"], "page": 1,
                        "confidence": 0.75,
                    })
                    break
        return facts
    return _runner


def score_case(case: dict, live: bool) -> dict:
    chunk = Chunk(doc_id=case["doc_id"], page=1, text=case["snippet"])
    runner = None if live else baseline_runner(case)
    facts = extract_facts(case["control_id"], [chunk], runner=runner)

    expected = list(case["expected_facts"])
    used = set()
    tp = 0
    for e in expected:
        for i, f in enumerate(facts):
            if i in used:
                continue
            if f.evidence_kind == e["evidence_kind"] and _norm(e["quote_contains"]) in _norm(f.source_quote):
                used.add(i)
                tp += 1
                break

    n_extracted = len(facts)
    n_expected = len(expected)
    precision = 1.0 if n_extracted == 0 and n_expected == 0 else (tp / n_extracted if n_extracted else 0.0)
    recall = 1.0 if n_expected == 0 else tp / n_expected
    snippet_norm = _norm(case["snippet"])
    prov_ok = sum(1 for f in facts if f.doc_id == case["doc_id"] and _norm(f.source_quote) in snippet_norm)
    provenance = 1.0 if n_extracted == 0 else prov_ok / n_extracted
    return {"case_id": case["case_id"], "control_id": case["control_id"],
            "expected": n_expected, "extracted": n_extracted, "tp": tp,
            "precision": precision, "recall": recall, "provenance": provenance}


def main() -> int:
    ap = argparse.ArgumentParser(description="Atlas extraction eval")
    ap.add_argument("--live", action="store_true", help="call the real model (needs ANTHROPIC_API_KEY)")
    args = ap.parse_args()

    cases = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CASES_DIR.glob("*.json"))]
    if not cases:
        print("no cases found in", CASES_DIR)
        return 1

    rows = [score_case(c, args.live) for c in cases]

    mode = "LIVE (model)" if args.live else "offline baseline"
    print(f"\nAtlas extraction eval — {mode} — {len(rows)} case(s)\n")
    print(f"{'case_id':<32}{'control':<12}{'exp':>4}{'ext':>4}{'tp':>4}{'prec':>7}{'rec':>7}{'prov':>7}")
    print("-" * 89)
    for r in rows:
        print(f"{r['case_id']:<32}{r['control_id']:<12}{r['expected']:>4}{r['extracted']:>4}"
              f"{r['tp']:>4}{r['precision']:>7.2f}{r['recall']:>7.2f}{r['provenance']:>7.2f}")

    # Aggregate per control.
    print("-" * 89)
    by_control: dict[str, list[dict]] = {}
    for r in rows:
        by_control.setdefault(r["control_id"], []).append(r)
    for cid, rs in sorted(by_control.items()):
        p = sum(x["precision"] for x in rs) / len(rs)
        rec = sum(x["recall"] for x in rs) / len(rs)
        prov = sum(x["provenance"] for x in rs) / len(rs)
        print(f"{'MEAN ' + cid:<32}{'':<12}{'':>4}{'':>4}{'':>4}{p:>7.2f}{rec:>7.2f}{prov:>7.2f}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
