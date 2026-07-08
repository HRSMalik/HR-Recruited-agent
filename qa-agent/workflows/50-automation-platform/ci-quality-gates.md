# ci-quality-gates

**Category:** 50-automation-platform
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Enforce CI/CD quality gates: decide which QA flows gate which pipeline stage, block merge/deploy on failure, detect and quarantine flaky tests, and keep gate runtimes inside their budget. Answers one question — "is this pipeline stage allowed to proceed?"

## Inputs & preconditions
- Required artifacts: the **gate policy** (stage → required flows → thresholds), coverage thresholds, the **mutation-score threshold** (per `mutation-testing.md`), the **schema-fuzz conformance** result (per `schema-fuzzing.md`), the **spec-compat breaking-change** verdict (per `spec-compatibility.md`), the SLA per stage, the prior run's flaky-test quarantine list, the CI retry budget (`max_retries` per test).
- Target: CI context — the per-flow `artifacts/<flow>/report.json` files, the pipeline stage (`commit | pr | build | release`), commit/build id.
- Preconditions: stage identified; gate policy parses; the flows mapped to this stage have produced reports (else `status:error`, do not infer a pass).

## Oracle (source of truth)
The **gate policy + thresholds** (required flows per stage, coverage minimums, mutation-score minimum, runtime budgets, smoke-before-deploy rule) and each flow's own gate result — `mutation-testing` (`mutation_score_meets_threshold`), `schema-fuzzing` (schema-fuzz conformance), and `spec-compatibility` (no breaking change) are first-class gate inputs alongside the existing flows. NEVER infer a pass from a missing/empty report.

**COVERAGE-IS-GAMEABLE (Goodhart):** line coverage measures only that a line *ran*, not that an assertion would catch a defect — the moment a coverage % becomes a *target*, it is gamed (assertion-free tests, padded paths) and stops measuring anything. Per [journal.optivem.com — coverage-vs-mutation](https://journal.optivem.com/p/coverage-vs-mutation), treat line coverage as a *floor / leading indicator only*, and use the **mutation score** (from `mutation-testing.md`) as the adequacy oracle — it is gamed far harder because a surviving mutant proves a real assertion gap.

## Step sequence (Plan → Act → Verify)
1. **Plan** — map stage to its required flows and budget: `commit/PR` → smoke + fast regression + api-contract + security + **mutation-testing** (changed-code score) + **schema-fuzzing** (conformance) + **spec-compatibility** (breaking-change), ≤ 5–10 min via parallelization/sharding; `build` → full regression + contract; `release` → performance + smoke-before-deploy. Enumerate the gates that must pass.
2. **Act** — collect each required flow's `report.json`, including `mutation-testing`, `schema-fuzzing`, and `spec-compatibility`; tag any test failing intermittently across reruns against the flaky list, quarantine it (exclude from gating, file a tracking finding), and confirm coverage, mutation score, and stage runtime were measured. Apply the **bounded-retry policy** (below) to flaky-suspect tests — retry only inside CI, only up to `max_retries`, and log every retried test as flaky. Skip-and-continue past a single missing report (record it).
3. **Verify** — assert every required flow's gate passed, coverage ≥ threshold AND mutation score ≥ threshold (coverage alone is *not* sufficient — see COVERAGE-IS-GAMEABLE), schema-fuzz conformance held, no spec-compat breaking change, no non-quarantined failure, runtime ≤ budget, and smoke passed before any deploy step.

## Assertions & exit gate
- Every flow required for this stage reports `status:pass` with its gate `passed:true`.
- Coverage (line/branch as policy dictates) ≥ the declared threshold **and** is treated only as a floor — adequacy is decided by mutation score, never by coverage alone (COVERAGE-IS-GAMEABLE); smoke is green before any deploy stage runs.
- Mutation score ≥ threshold (`mutation_score_meets_threshold` from `mutation-testing.md`); schema-fuzz conformance passed (`schema-fuzzing.md`); no breaking change (`spec-compatibility.md`).
- No open blocker/critical finding; flaky tests are quarantined (not silently passing), each with a tracking finding; every CI-retried test is logged flaky, never silently passed.
- Stage runtime ≤ budget (sharding/parallelization applied to PR-stage flows).
- **Gate:** `stage_gate_satisfied` — all required gates pass AND coverage ≥ threshold AND mutation score ≥ threshold AND schema-fuzz conformance held AND no spec-compat breaking change AND no blocking finding. Any miss → `fail` and the pipeline blocks merge/deploy.

## Output
Write `artifacts/ci-quality-gates/report.json` per `shared/report-format.md`:
`{ flow:"ci-quality-gates", status, summary{total,passed,failed,skipped}, findings[], gate{name:"stage_gate_satisfied",passed} }`.
Also emit **JUnit XML** (per `shared/report-format.md`) so the CI runner parses it natively to block the merge/deploy. Each finding follows `shared/finding-schema.md`; a flaky quarantine is **minor**, a bounded-retry'd test carries a **minor** flaky finding (with retry count), a failed required gate — including a sub-threshold mutation score, a schema-fuzz non-conformance, or a spec-compat breaking change — is **blocker** (pipeline cannot proceed), evidence = the offending `report.json` excerpt + coverage/mutation-score/runtime numbers.

## Bounded-retry policy (flaky tests)
Retries exist only to absorb genuine infra/timing flakiness — never to wash out a real failure into a pass:
- **CI-only** — retries run exclusively inside the CI sandbox; the gate verdict is computed on CI results, never on a developer's local rerun.
- **Capped** — at most `max_retries` (policy-set, e.g. 2) per test; once exhausted, the test's last result stands and a still-failing test fails the gate.
- **Always logged as flaky** — any test that needed a retry to pass is recorded with its retry count and quarantined per the flaky list with a tracking finding. A retried test is **never silently passed** — a green-after-retry result is a flaky signal, not a clean pass.
- **Deterministic** — a missing/ambiguous retry record is treated as `error`, not as an implicit pass.

## Watch (do not gate)
Predictive flaky-test scoring and auto-tuned per-test retry budgets (ML over historical rerun data) are emerging — surface candidates as notes, but keep `max_retries` policy-set and never let a model relax the gate yet.

## Pipeline position
Runs **last per stage**, after the stage's flows complete — it is the deterministic gate that consumes their reports and returns the single proceed/block verdict for commit, PR, build, or release.

## Guardrails
Per `shared/guardrails.md`: read-only (consumes reports — including `mutation-testing`, `schema-fuzzing`, `spec-compatibility` — `disallowedTools: Edit, Write`); never mutates the SUT; bounded retries are a CI-runner concern, this gate only *reads* their logged outcomes; secrets via env, redacted from JUnit/report; deterministic — a missing report, a coverage-only "pass" with no mutation score, or an ambiguous retry record is `error`, never an assumed pass; cap turns.
