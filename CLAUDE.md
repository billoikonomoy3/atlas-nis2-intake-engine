# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes, plus Atlas-specific rules.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## Atlas — project rules

Atlas is a **deterministic NIS2 readiness engine** (Python 3.11+, FastAPI, Pydantic) with a
**cited, model-assisted extraction slice**. The architecture rests on a few invariants —
treat them as hard constraints, not preferences.

### Commands
```bash
pip install -e ".[dev]"          # core + test deps (offline)
pytest -q                        # full suite; runs fully offline, no API key needed
pytest -q -m "not freshness"     # the gated set CI runs (deselects the staleness canary)
uvicorn atlas.api.main:app --reload   # serve API + frontend at http://localhost:8000
python eval/run_eval.py          # offline extraction eval; --live needs ANTHROPIC_API_KEY
```
Default to verifying changes with `pytest -q`. The whole suite is offline by design.

### Invariants — do not break these
- **No model in the judgment path.** A model is used in exactly one place — locating and
  quoting evidence in `atlas/extraction/`. A model **never** assigns a maturity level or a
  verdict. Keep `validate → classify → proportionality → baseline → score → Finding` pure.
- **Determinism is literal.** Same inputs → byte-identical content and `content_sha256`
  (everything except `generated_at`). Don't introduce nondeterminism (clock, ordering,
  iteration over unordered sets) into the engine. `tests/test_determinism.py` pins this.
- **Don't change the API contract.** The frontend (`frontend/index.html`) calls the API and
  embeds no engine logic. Keep request/response schemas in `atlas/engine/models.py` stable;
  the engine lives in exactly one place (`atlas/engine`) — never duplicate it.
- **Law vs. heuristic stays tagged.** Every field carries `statutory: true` or
  `statutory: false, heuristic: true, tunable: true`. Preserve that split; don't present a
  heuristic as statutory.
- **Provenance is enforced.** Facts without a verifiable `source_quote` in their cited chunk
  are dropped/refused (422). Don't relax this — a fabricated quote must never reach a Finding
  or a snapshot.
- **Veto rules are data, not code.** Add or change disqualifying findings by editing
  `ruleset/nis2_v1.yaml › vetoes`, evaluated by pure code in `atlas/engine/veto.py`.
- **Extraction fails closed.** Without `ANTHROPIC_API_KEY`, extraction endpoints return 503 —
  they never fabricate. The deterministic core, API, frontend classification, and all tests
  still work without a key.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to
overcomplication, and clarifying questions come before implementation rather than after mistakes.
