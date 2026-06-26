# Atlas — NIS2 readiness engine

![CI](https://github.com/billoikonomoy3/atlas-nis2-intake-engine/actions/workflows/ci.yml/badge.svg)

A deterministic **Stage-3 → compliance-baseline** engine for NIS2 (Directive (EU)
2022/2555), with a **cited, model-assisted document-extraction slice** for one control
end-to-end (`RM-21D-01`, supply-chain security, Art 21(2)(d)).

> From user facts alone: **applicability & classification → proportionality → the
> minimum maturity bar per control → jurisdiction & clocks**; then, for the slice,
> **PDF in → cited facts → deterministic level → gap vs the bar → a cited finding.**

Everything that decides the law is pure, offline, reproducible code. A model is used in
**one place only** — locating and quoting evidence inside documents. A model never
assigns a maturity level or a verdict.

---

## The two boundaries that define this system

### 1. The law determines vs. our heuristic suggests

Every output separates what the **law determines** from what **our heuristic suggests**,
and the split is encoded in the schema itself (`statutory: true` vs
`statutory: false, heuristic: true, tunable: true` on every field).

| THE LAW DETERMINES (statutory) | OUR HEURISTIC SUGGESTS (no statutory force, tunable) |
|---|---|
| in scope? essential / important? | proportionality score (0–100) |
| size band (2003/361/EC) | proportionality tier (Foundational … Critical) |
| Article 6 consolidation | required maturity rung per control |
| Article 4(2) two-year rule | 0–4 maturity ladder & achieved level |
| Article 3 / 2(2) overrides | gap vs the bar |
| supervisor routing, Art 23 clocks | — |

NIS2 Art 21(1) is **outcomes-based** ("appropriate and proportionate"); the heuristic
**informs, never replaces** that judgment. A maturity rung is **not** a statutory safe
harbour. Every artefact is stamped **DRAFT — REQUIRES REVIEW**.

### 2. The LLM-only-in-extraction guarantee

```
                         ┌───────────────────────── judgment path: NO MODEL ───────────────────────────┐
  user facts ─▶ validate ─▶ classify ─▶ proportionality ─▶ baseline (bar) ─▶ score_control ─▶ Finding
  (INSUFFICIENT_INPUT on bad numerics)                                            ▲
                                                                                  │ ExtractedFact[]
  documents ─▶ ingest (offline) ─▶ extract  ── MODEL (locate + quote only) ──────┘
                                   (provenance enforced; facts w/o source_quote discarded)
```

The deterministic core and the **entire test suite run fully offline**; CI is given no
API key, which is the proof. The extraction endpoints **fail closed (503)** without a
key — they never fabricate facts.

**Provenance is enforced at every ingress, not just during extraction.** A fact's
quote must actually appear in its cited chunk and the cited `(doc_id, page)` must
exist, or the fact is dropped. This check runs inside `/extract` *and* again at the
public `/score` and `/snapshot` boundary: caller-supplied facts must carry their source
`chunks` for re-verification, and facts without verifiable provenance are **refused
(422)** — a fabricated quote can never become cited evidence in a finding or a hashed
snapshot. The safe end-to-end path is `/assess/control` (extract → score in one step).

---

## Architecture (text diagram)

```
atlas/
  ruleset/nis2_v1.yaml          versioned single source of truth (thresholds, weights,
                                16-criteria registry); sha256 stamped into every snapshot
  atlas/
    engine/
      ruleset.py                load YAML, compute sha256, expose version
      models.py                 Pydantic schemas (one schema for API + tests; law/heuristic tags)
      validate.py               bad numerics -> INSUFFICIENT_INPUT (never a silent verdict)
      classify.py               Art 6 consolidation, size band, two-year rule, overrides  [STATUTORY]
      proportionality.py        additive weighted score -> tier                            [HEURISTIC]
      baseline.py               required rung per control from tier                        [HEURISTIC]
      scoring.py                facts -> maturity level -> cited Finding (NO model)         [HEURISTIC]
      veto.py                   disqualifying findings: cited content that defeats a control [HEURISTIC]
      snapshot.py               content_sha256 over everything except generated_at
    extraction/
      ingest.py                 PDF/DOCX/TXT -> page-tagged chunks (offline)
      extract.py                MODEL: locate + quote evidence (schema-locked, provenance-checked)
    jurisdiction.py             NL · Cbw overlay: supervisor routing, three duties, clocks
    api/main.py                 FastAPI: /classify /extract /score /assess/control /snapshot /version
    service.py                  validate -> classify -> proportionality -> bar -> score (offline)
  tests/                        32-case oracle + validation + proportionality + baseline + scoring + determinism + api + extraction
  eval/                         labelled extraction cases + precision/recall/provenance harness
  frontend/index.html           rewired to the API; the engine is NOT duplicated here
```

**One source of truth for the law.** The deterministic engine exists in exactly one
place (`atlas/engine`). The frontend calls the API; it embeds no engine.

### Disqualifying ("veto") findings — presence ≠ conformance

The maturity rung credits whether a control is **documented**. That alone can produce a
false negative: a policy can be *full* of supply-chain clauses (high `design_done`) while
several of those clauses are themselves the defect. A **veto** closes that gap — when a
control's own cited evidence contains a clause whose **content defeats** the outcome, the
achieved rung is capped at **L1**, the gap recomputed, and the status set to **`vetoed`**
(never `meets`), with the offending clause surfaced on the Finding (`vetoes[]`) so a reader
sees *why* it failed.

Veto rules are **data** (`ruleset/nis2_v1.yaml › vetoes`), evaluated by **pure
deterministic code** (`atlas/engine/veto.py`) over the already-cited facts — **no model**
in the path. The seed rule encodes the supply-chain archetype: a supplier
incident-notification window longer than the entity's own **Art 23** cascade (early warning
≤24h, notification ≤72h) leaves it unable to meet its statutory reporting duty. A control
with **zero** active vetoes scores exactly as before. Like the rungs themselves, a veto is a
tunable heuristic, **not** a safe harbour. Adding a veto is a YAML edit, not a code change.

---

## Run it

```bash
pip install -e ".[dev]"        # core + test deps (offline)
pytest -q                       # 32-case oracle + validation + proportionality + baseline + scoring + determinism + api + extraction

uvicorn atlas.api.main:app --reload   # serve the API + frontend at http://localhost:8000
python eval/run_eval.py               # offline extraction eval (baseline)
python eval/run_eval.py --live        # real model (needs ANTHROPIC_API_KEY)
```

The extraction slice (`/extract`, `/assess/control`) needs `ANTHROPIC_API_KEY`. Without
it the core, the API's deterministic endpoints, the frontend's classification, and all
tests still work — only cited extraction is unavailable, and it fails closed.

### Re-derive a snapshot from its JSON (reproducibility is literal)

Every snapshot embeds `engine_version`, `ruleset_version`, `ruleset_sha256`,
`generated_at`, and a `content_sha256` taken over **everything except `generated_at`**.
To verify a snapshot is genuine:

1. load `snapshot.inputs`;
2. re-run the engine (`POST /snapshot`, or `atlas.service.run_snapshot`) with the same
   `generated_at`;
3. assert the recomputed `content_sha256` equals the snapshot's.

Same inputs → byte-identical content and hash. (`tests/test_determinism.py` pins this.)

---

## Copyright

**ISO/IEC 27001:2022 control text is never reproduced.** Each criterion lists ISO
**clause numbers only** (e.g. `5.19`, `8.16`) as a licensed crosswalk pointer carrying no
protected expression — resolve them against your own licensed copy. Public criteria are
keyed to paraphrased **NIS2** prose (EU law) and **NIST CSF 2.0** identifiers (US
Government, public domain).

---

## Open TODOs (for a human — deliberately not invented)

The heuristic weights and one baseline policy are **judgment calls with no statutory
force**. They must be justified by a person, not by this tool:

- [ ] **Proportionality weight rationale.** For each weight in
  `ruleset/nis2_v1.yaml › heuristic_weights` (size 25/14/6, class 25/12, annex 15/8,
  cross-border 15/9, supply 5/3, special-entity 5, footprint ladders, and the
  essential→60 / systemic→80 floors), document *why that number*. They are tunable and
  currently carry **no documented justification** — `TODO: REVIEW`.
- [ ] **Foundational / L1 for in-scope `important` entities.** The monotonic
  tier→rung map (`Foundational→L1 … Critical→L4`) means an in-scope *important* entity at
  the Foundational tier gets a required rung of **L1**. This is **surfaced, not silently
  corrected** (`tests/test_baseline.py::test_important_can_sit_at_foundational_l1_policy_artifact`).
  Decide whether that floor is the intended policy or should be raised — `TODO: REVIEW`.
- [ ] **Maturity L4 from documents.** The facts-only scorer tops out at **L3**: the basic
  extracted-fact schema carries no "monitoring/metrics on a cadence" signal, so "Managed
  / measured" cannot be proven from policy documents alone. Extend the schema if L4 must
  be reachable from evidence — `TODO: REVIEW`.
- [ ] **Sector & supervisor coverage.** Annex sector lists are top-level groupings to
  verify against the official Annex text; supervisor routing asserts a name only where
  the source names one (RDI / IGJ / DNB+AFM) and is otherwise `TBD` → human review.

---

## Scope of this run

Depth on **one control end-to-end** (`RM-21D-01`) before breadth. No DORA / CSRD /
multi-regulation work, and no extra controls were added. The Netherlands overlay is
precise as of **25 June 2026** (Cbw, dossier 36.764): **adopted by the Tweede Kamer on
15 April 2026**, **awaiting the Eerste Kamer plenary vote**, with **targeted commencement
1 July 2026** — until then the **Wbni** still governs. The dated status is a single
structured field (`atlas/jurisdiction.py › IN_FORCE_STATUS`) from which every report line
is derived; a **non-gating freshness canary** (`tests/test_jurisdiction_freshness.py`,
`-m freshness`) is set to fail on/after **1 July 2026** as a re-verification alarm without
flipping the CI badge.
