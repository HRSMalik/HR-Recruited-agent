# confirmation-retest

**Category:** 10-functional
**Runs as:** inline flow
**Default model:** haiku   ·   **Mode:** read-only (or seeded-sandbox if the repro mutates state)

## Purpose
Re-execute the **exact failed steps** of a previously logged defect on the fixed build (ISTQB *confirmation testing / re-testing*): prove the fix resolved the original failure. Answers — "is defect `<DEFECT-ID>` actually fixed?"

## Inputs & preconditions
- Required artifacts: the defect record — its `steps_to_reproduce`, `expected`, `actual`, environment, and the original `oracle` (the finding object from a prior run).
- Target: base URL + auth via env; the **fixed** build/commit that claims to resolve the defect (record it).
- Preconditions: the defect id is resolvable; the original repro is deterministic (has a seed/fixture id if it used a sandbox); reproduce the same environment/account/locale the defect was filed under.

## Oracle (source of truth)
The defect's original **`expected`** value plus the requirement/spec section it was filed against — the same oracle the defect used. NOT the SUT's new output, and NOT the developer's claim that it is fixed.

## Step sequence (Plan → Act → Verify)
1. **Plan** — load the defect; reconstruct its exact `steps_to_reproduce` verbatim, including the same inputs, account/role, and fixture/seed id. Do not "improve" the steps — fidelity to the original is the point.
2. **Act** — replay those exact steps on the fixed build, one step at a time, against the same (seeded, if applicable) environment.
3. **Verify** — assert the observed result now equals the defect's `expected`. If it still equals the old `actual`, the fix failed.

## Assertions & exit gate
- Replaying the steps now produces the defect's documented `expected` outcome.
- The original `actual` (failure symptom) no longer reproduces.
- The fix introduced no new error on the repro path (no new `5xx`/exception in the same flow).
- **Gate:** `defect_resolved` — pass only if the original failure no longer reproduces and `expected` is observed; otherwise `fail` (reopen the defect).

## Output
Write `artifacts/confirmation-retest/report.json` per `shared/report-format.md`:
`{ flow:"confirmation-retest", status, summary{...}, findings[], gate{name:"defect_resolved",passed} }`.
On failure, emit a finding per `shared/finding-schema.md` that **links the original defect id** (in `title`/`evidence`), keeps the original severity, and shows the side-by-side `expected` vs still-observed `actual`. On pass, note the defect id as verified-closed.

## Guardrails
Per `shared/guardrails.md`: read-only on live; replay against a seeded sandbox if the original repro mutated state (same seed id, torn down after); secrets via env; no real side-effects; `maxTurns: 10`. This flow verifies one defect — broader impact of the fix is `regression`'s responsibility, not this one's.
