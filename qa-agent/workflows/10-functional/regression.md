# regression

**Category:** 10-functional
**Runs as:** subagent: ../.claude/agents/regression-tester.md
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Guard previously-working behavior against a recorded **baseline** (ISTQB *regression testing*): a change must not break what already worked. Answers — "did this build alter any behavior that was correct before?"

## Inputs & preconditions
- Required artifacts: a **baseline** — golden responses / recorded sessions / approved snapshots captured from a known-good build (with the baseline build id).
- Target: current build base URL + auth via env; current build/commit recorded.
- Preconditions: **smoke passed** (no point diffing a dead build); the baseline exists and is versioned; same request set, account, and (seeded) data the baseline was recorded under.

## Oracle (source of truth)
The **baseline**, NOT the current SUT output. Correct = "matches the golden response recorded from the last good build." This is the one flow where the SUT's *current* answer is explicitly distrusted — if the current output differs from baseline, the current output is suspect until proven an intended change.

## Step sequence (Plan → Act → Verify)
1. **Plan** — load the baseline request/response set; scope to the change surface when given (prioritize endpoints near the diff), else replay the full golden set. Tag any diffs the change ticket says are *intended* (those are approved updates, not regressions).
2. **Act** — replay each baseline request against the current build, one at a time, identical inputs/headers/account; skip-and-continue.
3. **Verify** — diff each current response against its baseline (status, body, normalized to ignore volatile fields: timestamps, generated ids, request ids). Any unexpected, un-approved diff is a regression.

## Assertions & exit gate
- Every replayed request's status + normalized body matches its baseline.
- Diffs are limited to fields the change ticket pre-approved; no unapproved behavioral drift.
- No new `4xx`/`5xx` on a request that was `2xx` in the baseline.
- **Gate:** `no_regression_vs_baseline` — pass only if 0 unapproved diffs; any unapproved diff → `fail`.

## Output
Write `artifacts/regression/report.json` per `shared/report-format.md`:
`{ flow:"regression", status, summary{...}, findings[], gate{name:"no_regression_vs_baseline",passed} }`.
Findings per `shared/finding-schema.md`; `oracle` = "baseline `<build-id>`, request `<id>`"; a broken previously-working core path is **major**/**critical**; evidence = the unified diff (baseline vs current) with the normalization applied.

## Pipeline position
Runs **only after smoke passes**. Pairs with `regression-suite-maintenance` (00-lifecycle) which curates and de-flakes the golden set this flow consumes.

## Guardrails
Per `shared/guardrails.md`: read-only; replay against a seeded sandbox if any baseline request mutated state (same seed); secrets via env; back off on `429`; `maxTurns: 40`. Never re-record the baseline from the current build to make a diff disappear — that would lock a regression in as "expected."
