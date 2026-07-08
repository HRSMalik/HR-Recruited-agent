# regression-suite-maintenance

**Category:** 00-lifecycle
**Runs as:** subagent: ../.claude/agents/regression-tester.md
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Keep the regression suite healthy: prune obsolete/redundant cases, detect and quarantine flaky tests, retire cases for removed features, and recommend additions for newly-shipped surface. Answers: "Is the regression suite trustworthy, lean, and aligned to current behavior?"

## Inputs & preconditions
- Required artifacts: the regression suite + its execution history (pass/fail per case over N recent runs), code/feature change log, coverage map (from `traceability-coverage`), case→requirement links.
- Target: the test repository + CI run history store (read-only).
- Preconditions: ≥ a configurable window of historical runs exists (flaky detection needs repeated runs); case ids are stable.

## Oracle (source of truth)
**Flakiness** is defined empirically — a test that yields **different verdicts on the same commit/inputs** across reruns (non-deterministic), per the Google/Microsoft flaky-test definition and Martin Fowler's "Eradicating Non-Determinism". **Obsolescence** is defined by the requirement/feature inventory (a case for a removed feature is dead). **Redundancy** is defined by coverage overlap (two cases covering the same partition add no signal). The suite's own green status is NOT the oracle.

## Step sequence (Plan → Act → Verify)
1. **Plan** — pull per-case verdict history; compute a flip rate / flakiness score per case; map each case to a live requirement; identify coverage overlaps and newly-shipped features lacking cases.
2. **Act** — classify one case at a time: **quarantine** flaky (flip rate above threshold → tag, isolate from the gating run, file for fix), **retire** obsolete (feature removed → mark deprecated, keep in labeled-comment history), **prune** redundant (overlapping coverage, keep the stronger), **recommend** additions for uncovered new surface. Skip-and-continue per case.
3. **Verify** — assert no flaky test still gates CI, no retired case references a removed feature, pruning did not drop unique coverage (cross-check `traceability-coverage`), and each new-surface gap has a proposed case.

## Assertions & exit gate
- Every test exceeding the flakiness threshold is quarantined out of the gating suite and ticketed.
- No obsolete case remains in the active suite; no unique-coverage case pruned.
- Each new/changed feature surface without coverage has a recommended addition.
- **Gate:** `suite_healthy` — passes when 0 flaky tests left gating AND 0 coverage lost to pruning (a flaky test gating the pipeline is **major** — it erodes trust and masks real regressions).

## Output
Write `artifacts/regression-suite-maintenance/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"suite_healthy"}`. Findings (`QA-REG-NNN`) record action (quarantine/retire/prune/add), the flakiness score or overlap evidence in `evidence`, and the oracle (history window / feature inventory). Recommended additions feed back into `test-case-design`.

## Guardrails
Read-only analysis — `disallowedTools: Edit, Write` on the test repo; emits recommendations + a quarantine list, a human applies removals. Never delete a case outright — mark deprecated in labeled-comment history. Quarantining must not silently drop coverage (cross-check traceability). Cap `maxTurns`.
