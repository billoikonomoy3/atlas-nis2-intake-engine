# Atlas — NIS2 Stage-3 Intake & Compliance-Baseline Engine

Turns a generic directive into a **specific, finite, defensible checklist for *this* client** —
from user-provided facts alone, before a single document is requested:

> applicability & classification → assessment scope → tailored criteria set →
> proportionality → **the minimum compliance bar per control** → jurisdiction & clocks → draft PBC list.

Offline, deterministic, audit-grade. No LLM, no network, no external libraries — the whole
demo is **one self-contained HTML file** that runs from a USB stick in a client room or from the
Railway deployment unchanged.

## Why this exists (and what the v1 toy got wrong)

A naive scope checker uses the practitioner shorthand "≥50 staff **OR** ≥€10m turnover". That
produces **negligent verdicts**. This engine encodes the real Stage-3 logic explicitly:

| Trap | Naive tool | Atlas |
|---|---|---|
| **Size test** | staff OR turnover | Staff is a hard ceiling (≥); the two financials are **one limb read in the entity's favour** — breached only by exceeding **BOTH** turnover AND balance sheet (>). 2003/361/EC. |
| **40 staff / €15m turnover / €5m balance** | wrongly *in scope* | correctly **small / out of scope** (balance only €5m) — the canonical false-positive trap, pinned by a regression test |
| **Group structure** | ignored | **Article 6 recursive aggregation**: +100% of linked (controlled) enterprises, pro-rata of partners (25–50%), consolidated down the whole tree — a subsidiary of a multinational is never a microenterprise |
| **One anomalous year** | flips scope | **Article 4(2) two-year rule**: a band change only takes effect across two consecutive periods |
| **Article 3 carve-outs** | silently deferred | **encoded**: QTSP/DNS/TLD = essential at any size; medium/large e-comms = essential (not merely important); Art 2(2) designation = essential at any size (or held *pending* the act); central-/local-government bodies in scope regardless of size |

## What's new beyond a scope checker — the pre-PBC "map"

The point of getting Stage 3 right is that everything downstream is measured against it. So Atlas
pre-computes, **before any evidence arrives**, everything that makes the post-PBC assessment mechanical:

- **Verdict & sensitivity** — the verdict, plus *what would flip it*: live distance to every size
  threshold and the single binding constraint. Teaches the trap (the financial limb needs **both** figures).
- **Compliance baseline** — the **minimum maturity rung every in-scope control must clear**, derived from
  the proportionality tier; the exact evidence that proves it; `operating-critical` / governance-liability /
  reporting-clock flags; and a **tier-sweep matrix** of the bar across all parameters (Foundational→L1 … Critical→L4).
- **Jurisdiction & clocks** — Netherlands / Cbw governing law by date, the named supervisor for the sector,
  the 24h / 72h / 1-month Art 23 reporting clocks, the three Dutch duties, and the Art 20 personal-liability vector.
- **Prioritised, bar-tagged PBC list**, a traced printable scope memo, and a JSON snapshot export.

## What's in the box

| File | Role |
|---|---|
| `atlas_nis2_intake.html` | **The demoable artifact.** Single self-contained file — stepper UI, live verdict + sensitivity, group-tree builder, derived compliance baseline, jurisdiction pack, traced scope memo, prioritised PBC list, print-to-PDF + JSON export. Embeds a faithful JS port of the engine and runs a **32-case self-test on load** (green badge). |
| `scope.py` | Stage-3 gold layer: recursive Article 6 aggregation, size band, two-year rule, classification + Article 3/2(2) overrides. Pure functions, full audit trail per verdict. |
| `criteria.py` | NIS2 Art 20 / 21(2)(a–j) / 23 → NIST CSF 2.0 criteria set (16 rows), 0–4 maturity, evidence, PBC items; transparent additive proportionality model. |
| `assess.py` | Stage 4–7 maturity engine: the 0–4 ladder, the proportionate **required rung** per tier, gap + likelihood×impact risk, and a deterministic EQCR challenger. Source of the compliance-baseline logic. |
| `jurisdiction.py` | Netherlands (Cbw) overlay: governing law by date, supervisor routing (RDI / IGJ / DNB+AFM, honest TBD elsewhere), the three duties, dual incident reporting, registratieplicht check. |
| `economics.py` | The pyramid economics — what the Stage 4–7 first pass costs in junior hours vs Atlas at ~€0, one hand-re-derivable chain. |
| `test_scope.py` / `test_assess.py` | Test catalogues proving the engines correct (`32 passed`; 6 assess/jurisdiction/economics groups). |
| `server.py` / `Procfile` | Minimal stdlib static server (serves only the artifact); Railway-ready. |

The HTML is a self-contained port; the Python modules are the tested source of truth (the "gold layer").

## Two decisions that make it defensible (interview talking points)

1. **Correctness of the size logic is the whole game.** A wrong applicability verdict is a negligent
   verdict. The boolean logic, group aggregation, two-year rule, and Article 3 overrides are encoded
   explicitly and pinned by 32 tests — *and the verdict ships with its own audit trail*, so every
   conclusion is re-derivable, not asserted.

2. **ISO/IEC 27001 control text is copyrighted by ISO — so it is never reproduced.** The public-facing
   criteria are keyed only to (a) paraphrased **NIS2** prose (EU law) and (b) **NIST CSF 2.0**
   function/subcategory IDs (US Government, public domain). ISO is referenced by **clause number only**
   (e.g. `8.16`) as a *licensed internal crosswalk* — a factual pointer a licensed user can resolve,
   carrying no protected expression.

## Run it

```bash
python test_scope.py     # prove the Stage-3 engine: 32 passed
python test_assess.py    # prove the assessment/jurisdiction/economics layer
python scope.py          # quick CLI demo (trap + subsidiary)
python criteria.py       # criteria coverage + a proportionality example
python server.py         # serve the artifact at http://localhost:8765
```

Then open **`atlas_nis2_intake.html`** in a browser for the full interactive demo, or use the
**Load a worked scenario** menu on the engagement screen.

## Honest limitations (flagged in-tool for human review)

First-pass triage, not legal advice; every output is marked **DRAFT — REQUIRES REVIEW**. The 0–4 ladder
and the tiers are consulting conventions — NIS2 prescribes no numeric maturity scale and a rung is never a
statutory safe harbour. The "central-government ⇒ essential" class is transposition-dependent; deep
partner-of-partner chaining and mixed-sector entities are flagged for manual review; sector lists are
top-level Annex groupings to verify against the official text. The Netherlands overlay is precise as of
24 June 2026 (Cbw, dossier 36.764, not yet in force). The tool defers what it should defer — and says so
on the face of the memo.
