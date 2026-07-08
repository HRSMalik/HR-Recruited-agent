# mutation-testing

**Category:** 50-automation-platform
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Gate test-suite *adequacy* with a mutation score on changed code — the #1 counter to coverage-theatre. Line/branch coverage only proves a line *ran*; surviving mutants prove an assertion was weak or absent. Answers one question — "do the tests actually fail when the code is wrong?"

## Inputs & preconditions
- Required artifacts: the **mutation-score threshold** (`thresholds.break`, e.g. 60–80% on changed code), the changed-file set (diff vs base branch), the runner's mutator config (`mutate` globs), prior incremental cache if present.
- Target: the **repo + green test suite** in a NON-PROD/CI sandbox checkout (`stryker run`, `mvn pitest`, or `mutmut run`). No live SUT, no network mutation.
- Preconditions to assert before acting: tests are **green at baseline** (mutation testing is meaningless on a red suite → `status:error`); the runner & config resolve; the changed-file set is non-empty (else skip with a note, do not pass vacuously); checkout is NON-PROD.

## Oracle (source of truth)
The declared **mutation-score threshold on changed code** (`thresholds.break`), per https://stryker-mutator.io/docs/. Mutation score = killed / (killed + survived) over detected mutants — timeout and runtime-error count as killed; *no-coverage* mutants count against the score (they expose untested lines). NEVER the suite's own pass/fail or its coverage % as the adequacy oracle.

## Step sequence (Plan → Act → Verify)
1. **Plan** — confirm baseline green; scope mutation to the **changed surface only** (`--incremental` + diff-scoped `mutate` globs / PIT `--since`, mutmut on changed paths) so the gate is fast and PR-relevant; enumerate the mutators (conditional, arithmetic, boolean, return-value, string) the runner will inject.
2. **Act** — run the mutation engine in the sandbox checkout, one changed module at a time; skip-and-continue past a module whose mutants error out (record it). Collect per-mutant state: killed / survived / timeout / no-coverage / runtime-error.
3. **Verify** — compute the changed-code mutation score against the threshold; for each **survived** or **no-coverage** mutant, capture the file:line, the applied mutation, and the (absent) killing test as the actionable weak-assertion evidence. Classify each per `shared/finding-schema.md` (`real_bug` weak assertion vs `test_assertion_issue` vs equivalent-mutant false positive).

## Assertions & exit gate
- Baseline suite was green before mutation (asserted, recorded).
- Changed-code mutation score ≥ `thresholds.break`; no-coverage mutants on changed lines counted against the score (not silently excluded).
- Every survived mutant is carried as a finding with file:line + mutation + missing assertion; equivalent mutants are marked and excused, not hidden.
- **Gate:** `mutation_score_meets_threshold` — changed-code score ≥ threshold AND baseline was green. Below threshold → `fail`; surviving mutants on changed code block the merge via ci-quality-gates.

## Output
Write `artifacts/mutation-testing/report.json` per `shared/report-format.md`:
`{ flow:"mutation-testing", status, summary{total,passed,failed,skipped}, findings[], gate{name:"mutation_score_meets_threshold",passed} }`.
`summary.total` = detected mutants, `failed` = survived + no-coverage on changed code. Each finding follows `shared/finding-schema.md`: a survived mutant on changed code is **major** (a real test-adequacy gap, default P2; evidence = file:line + mutation diff + the killing test that should exist); an equivalent-mutant false positive is **trivial**/`test_assertion_issue`, kept out of the severity tally. Per `shared/report-format.md` this report feeds **ci-quality-gates**, which consumes the gate result and JUnit render to block the merge.

## Watch (do not gate)
LLM-generated mutation-killing tests and auto-equivalent-mutant detection are emerging — note candidates, do not let them set the gate yet.

## Guardrails
Per `shared/guardrails.md`: runs only against a **sandbox/CI checkout with a seeded green suite**, never a live SUT or prod data; non-destructive (mutants are in-memory/throwaway, the working tree is restored — confirm teardown); secrets via env, redacted from the report; deterministic — red baseline or missing config is `status:error`, never an assumed pass; cap turns and prefer `--incremental` to stay inside the PR runtime budget.
