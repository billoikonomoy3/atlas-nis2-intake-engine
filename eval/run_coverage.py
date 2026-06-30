"""Supply-chain coverage demo — render the Art 21(2)(d) coverage map for one document.

  python eval/run_coverage.py                 # offline: deterministic stub locates verbatim
                                              # quotes in the PDF; coverage is pure code
  python eval/run_coverage.py --live          # use the real model (needs ANTHROPIC_API_KEY)
  python eval/run_coverage.py --doc PATH --html OUT.html

The deterministic core has no API key here, so (like eval/run_eval.py) the offline mode
injects a baseline runner: it does NOT invent anything — it only emits a fact when its
seed phrase is a verbatim substring of the ingested document, so every quote clears the
same anti-fabrication firewall the live model's quotes do. The model (or the stub) ONLY
locates + quotes + tags an evidence_item_id; every present/ambiguous/absent status and
the per-control coverage state are computed deterministically in atlas/engine/coverage.py.
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from atlas.engine import ruleset as R  # noqa: E402
from atlas.extraction.extract import extract_evidence_facts  # noqa: E402
from atlas.extraction.ingest import Chunk, ingest_file  # noqa: E402
from atlas.service import run_area_coverage  # noqa: E402

DEFAULT_DOC = ROOT / "eval" / "sample_docs" / "supplier_security_policy_PowerGridHellas_TESTDOC.pdf"
DEFAULT_HTML = ROOT / "eval" / "out" / "coverage_21D.html"

# Deterministic locating seeds: (evidence_item_id, evidence_kind, verbatim_phrase, confidence).
# Each phrase is a real substring of the PowerGrid policy; the stub emits a fact only when
# the phrase is actually found in an ingested chunk (else the item stays absent — no
# fabrication). Confidence >= present_confidence (0.60) -> present; below -> ambiguous.
SEEDS: dict[str, list[tuple[str, str, str, float]]] = {
    "RM-21D-01": [
        ("21D-01-a", "operating", "The supplier register is maintained in the GRC platform", 0.93),
        ("21D-01-b", "design", "Suppliers are classified into three criticality tiers", 0.90),
        ("21D-01-c", "operating", "records the criticality tier and assessment status for 214 active suppliers", 0.45),
    ],
    "RM-21D-02": [
        ("21D-02-a", "design", "The assessment methodology, scoring rubric and tier definitions are maintained", 0.88),
        ("21D-02-b", "design", "documented security assessment before onboarding", 0.90),
        ("21D-02-c", "operating", "Critical suppliers are reassessed each assessment cycle", 0.86),
        # 21D-02-d (supplier's own posture: certifications / SOC 2) — not evidenced -> absent.
    ],
    "RM-21D-03": [
        ("21D-03-a", "design", "must include the mandatory Security Schedule", 0.92),
        ("21D-03-b", "design", "notify PowerGrid of any security breach affecting PowerGrid data within 24 hours", 0.93),
        ("21D-03-c", "design", "The right-to-audit clause permits PowerGrid", 0.90),
        ("21D-03-d", "design", "sub-processor disclosure", 0.45),
    ],
    "RM-21D-04": [
        # 21D-04-a (acquisition security criteria) and 21D-04-b (provenance) — not evidenced -> absent.
        ("21D-04-c", "design", "sub-processor disclosure", 0.45),
    ],
    "RM-21D-05": [
        ("21D-05-a", "operating", "Supplier security performance shall be reviewed at least annually", 0.88),
        ("21D-05-b", "design", "shall be reviewed at least annually", 0.84),
        # 21D-05-c (change management of supplier services) — not evidenced -> absent.
    ],
    "RM-21D-06": [
        # 21D-06-a/b/c (supplier-incident handling, exit procedure, access revocation) -> absent.
        ("21D-06-d", "design", "return or destruction of data on exit", 0.88),
    ],
}

_STATUS_GLYPH = {"present": "●", "ambiguous": "◐", "absent": "○"}


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def stub_runner(control_id: str, chunks: list[Chunk]):
    """Offline locating stub for one control: emit a fact per seed phrase found verbatim."""
    norm_chunks = [(c.doc_id, c.page, _norm(c.text)) for c in chunks]

    def _runner(system, user, tool):
        facts = []
        for item_id, kind, phrase, conf in SEEDS.get(control_id, []):
            for doc_id, page, ntext in norm_chunks:
                if _norm(phrase) in ntext:
                    facts.append({
                        "evidence_item_id": item_id, "evidence_kind": kind,
                        "claim": f"located in the policy ({item_id})",
                        "source_quote": phrase, "doc_id": doc_id, "page": page,
                        "confidence": conf,
                    })
                    break
        return facts
    return _runner


def build_coverage(doc: Path, live: bool):
    chunks = ingest_file(doc, doc_id=doc.name)
    if not chunks:
        raise SystemExit(f"no readable text in {doc}")
    facts = []
    for control in R.supply_chain_controls():
        cid = control["id"]
        runner = None if live else stub_runner(cid, chunks)
        facts.extend(extract_evidence_facts(cid, chunks, runner=runner))
    return run_area_coverage(facts), facts


def render_text(cov) -> str:
    out = []
    out.append(f"\nCoverage map — {cov.area_id} · {cov.article} · {cov.title}")
    out.append(f"registry sha256: {cov.registry_sha256[:16]}…   present_confidence: {R.present_confidence()}")
    out.append("=" * 78)
    for c in cov.controls:
        head = (f"{_STATUS_GLYPH[c.coverage_state]} {c.control_id}  {c.title}"
                f"   [{c.coverage_state.upper()}]  {c.present_count}/{c.total_items} present")
        out.append("\n" + head)
        out.append("-" * 78)
        for it in c.items:
            star = " *decisive" if it.decisive else ""
            q = it.evidence[0].source_quote if it.evidence else "—"
            pg = f"p{it.evidence[0].page}" if it.evidence else "  "
            out.append(f"  {_STATUS_GLYPH[it.status]} {it.evidence_item_id:<9} {it.status:<9}"
                       f"{star:<10} {pg:<4} “{q[:58]}”")
        if c.veto_capped:
            out.append(f"  ⚠ VETO: {', '.join(v.veto_id for v in c.vetoes)}")
    out.append("\n" + "=" * 78)
    out.append(f"items   — present {cov.item_summary['present']}  ambiguous {cov.item_summary['ambiguous']}  "
               f"absent {cov.item_summary['absent']}")
    out.append(f"controls— present {cov.control_summary['present']}  ambiguous {cov.control_summary['ambiguous']}  "
               f"absent {cov.control_summary['absent']}")
    return "\n".join(out)


_COL = {"present": "#1a7f4b", "ambiguous": "#b7791f", "absent": "#9aa3ad"}
_BG = {"present": "#e9f6ef", "ambiguous": "#fdf4e3", "absent": "#f1f3f5"}


def render_html(cov) -> str:
    def esc(s):
        return html.escape(str(s))

    controls_html = []
    for c in cov.controls:
        items_html = []
        for it in c.items:
            q = esc(it.evidence[0].source_quote) if it.evidence else "<i>no evidence located</i>"
            cite = f"{esc(it.evidence[0].doc_id)} · p{it.evidence[0].page}" if it.evidence else ""
            dec = '<span class="dec">decisive</span>' if it.decisive else ""
            items_html.append(
                f'<tr class="s-{it.status}"><td class="dot">{_STATUS_GLYPH[it.status]}</td>'
                f'<td class="iid">{esc(it.evidence_item_id)} {dec}</td>'
                f'<td class="idesc">{esc(it.item)}</td>'
                f'<td class="st">{it.status}</td>'
                f'<td class="q">“{q}”<span class="cite">{cite}</span></td></tr>')
        veto = (f'<div class="veto">⚠ Disqualified — {esc(", ".join(v.veto_id for v in c.vetoes))}</div>'
                if c.veto_capped else "")
        controls_html.append(f"""
        <section class="ctrl">
          <div class="ch">
            <span class="badge s-{c.coverage_state}">{_STATUS_GLYPH[c.coverage_state]} {c.coverage_state}</span>
            <span class="cid">{esc(c.control_id)}</span><span class="ctitle">{esc(c.title)}</span>
            <span class="ratio">{c.present_count}/{c.total_items} present</span>
          </div>
          {veto}
          <table><tbody>{''.join(items_html)}</tbody></table>
        </section>""")

    s = cov.item_summary
    cs = cov.control_summary
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Coverage map — {esc(cov.area_id)}</title>
<style>
  body{{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#1b2733;background:#fff;margin:0;padding:28px;}}
  h1{{font-size:19px;margin:0 0 2px}} .sub{{color:#5b6b7b;font-size:12.5px;margin-bottom:18px}}
  .summary{{display:flex;gap:10px;margin:0 0 22px;flex-wrap:wrap}}
  .pill{{padding:6px 12px;border-radius:8px;font-weight:600;font-size:12.5px}}
  .ctrl{{border:1px solid #e6e9ee;border-radius:11px;margin:0 0 14px;overflow:hidden}}
  .ch{{display:flex;align-items:center;gap:10px;padding:11px 14px;background:#fafbfc;border-bottom:1px solid #eef1f4}}
  .cid{{font-weight:700;font-variant-numeric:tabular-nums}} .ctitle{{color:#33414f}}
  .ratio{{margin-left:auto;color:#6b7785;font-size:12.5px;font-variant-numeric:tabular-nums}}
  .badge{{padding:3px 9px;border-radius:20px;font-size:11.5px;font-weight:700;text-transform:capitalize}}
  table{{width:100%;border-collapse:collapse}} td{{padding:8px 10px;border-bottom:1px solid #f1f3f5;vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  .dot{{width:18px;text-align:center;font-size:15px}} .iid{{white-space:nowrap;font-weight:600;font-size:12.5px}}
  .idesc{{color:#3a4753;font-size:12.5px}} .st{{font-size:12px;text-transform:capitalize;white-space:nowrap}}
  .q{{color:#475563;font-size:12.5px}} .cite{{display:block;color:#94a0ac;font-size:11px;margin-top:2px}}
  .dec{{background:#1b2733;color:#fff;border-radius:4px;font-size:9.5px;padding:1px 5px;margin-left:4px;vertical-align:middle;text-transform:uppercase;letter-spacing:.04em}}
  .veto{{background:#fbeaea;color:#9b1c1c;padding:8px 14px;font-size:12.5px;font-weight:600}}
  .s-present td.dot,.s-present.st{{color:{_COL['present']}}} .s-ambiguous td.dot{{color:{_COL['ambiguous']}}} .s-absent td.dot{{color:{_COL['absent']}}}
  .badge.s-present{{background:{_BG['present']};color:{_COL['present']}}}
  .badge.s-ambiguous{{background:{_BG['ambiguous']};color:{_COL['ambiguous']}}}
  .badge.s-absent{{background:{_BG['absent']};color:{_COL['absent']}}}
  .pill.present{{background:{_BG['present']};color:{_COL['present']}}}
  .pill.ambiguous{{background:{_BG['ambiguous']};color:{_COL['ambiguous']}}}
  .pill.absent{{background:{_BG['absent']};color:{_COL['absent']}}}
  .foot{{color:#94a0ac;font-size:11.5px;margin-top:18px;border-top:1px solid #eef1f4;padding-top:10px}}
</style></head><body>
  <h1>Supply-chain coverage map — {esc(cov.area_id)} · {esc(cov.title)}</h1>
  <div class="sub">{esc(cov.article)} · registry sha256 {esc(cov.registry_sha256[:16])}… · present-confidence {R.present_confidence()} · model located + quoted; every status computed deterministically</div>
  <div class="summary">
    <span class="pill present">items present {s['present']}</span>
    <span class="pill ambiguous">items ambiguous {s['ambiguous']}</span>
    <span class="pill absent">items absent {s['absent']}</span>
    <span class="pill present">controls present {cs['present']}</span>
    <span class="pill ambiguous">controls partial {cs['ambiguous']}</span>
    <span class="pill absent">controls absent {cs['absent']}</span>
  </div>
  {''.join(controls_html)}
  <div class="foot">{esc(cov.note)}</div>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Atlas Art 21(2)(d) supply-chain coverage demo")
    ap.add_argument("--doc", default=str(DEFAULT_DOC), help="document to assess (.pdf/.docx/.txt)")
    ap.add_argument("--html", default=str(DEFAULT_HTML), help="where to write the HTML coverage map")
    ap.add_argument("--live", action="store_true", help="use the real model (needs ANTHROPIC_API_KEY)")
    args = ap.parse_args()

    try:  # the coverage glyphs are UTF-8; make a cp1252 console (Windows) print them
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    doc = Path(args.doc)
    if not doc.exists():
        raise SystemExit(f"document not found: {doc}")

    cov, facts = build_coverage(doc, args.live)
    print(render_text(cov))

    out = Path(args.html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(cov), encoding="utf-8")
    print(f"\nHTML coverage map -> {out}")
    print(f"facts located: {len(facts)}  (mode: {'LIVE model' if args.live else 'offline stub'})")

    # Self-check the demo actually spans all three buckets at the item level.
    s = cov.item_summary
    missing = [k for k in ("present", "ambiguous", "absent") if s[k] == 0]
    if missing:
        print(f"\nWARNING: no evidence item landed in: {', '.join(missing)}")
        return 1
    print("OK — at least one evidence item in each of present / ambiguous / absent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
