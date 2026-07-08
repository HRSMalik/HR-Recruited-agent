# traceability-coverage

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Build the requirement→test→result traceability matrix and surface gaps: untested requirements and orphan tests. Answers: "Is every requirement covered by at least one test, and does every test trace back to a requirement?"

## Inputs & preconditions
- Required artifacts: the requirement set (IDs from `requirements-review`), the test-case suite with requirement tags (from `test-case-design`), execution results (from `test-execution`), and any defect→requirement links.
- Target: the requirement store + test repo + result artifacts (read-only).
- Preconditions: requirements carry stable IDs and test cases carry requirement-ID tags (untagged cases are themselves a finding).

## Oracle (source of truth)
A **bidirectional Requirements Traceability Matrix (RTM)** per ISO/IEC/IEEE 29148 / 29119: every requirement must trace **forward** to ≥1 test case (and its result), and every test must trace **backward** to ≥1 requirement. Coverage = covered requirements ÷ total requirements. The matrix — not the suite's size — defines whether coverage is adequate; a green suite that skips a requirement is still a gap.

## Step sequence (Plan → Act → Verify)
1. **Plan** — load all requirement IDs and all test cases with their requirement tags; define the two directions to check (forward: req→test; backward: test→req).
2. **Act** — build the matrix one requirement at a time: link its covering test(s) and their latest verdicts; in parallel detect **orphan tests** (no requirement tag) and **untested requirements** (no linked case). Compute coverage % and pass-state per requirement. Skip-and-continue on a malformed link.
3. **Verify** — assert the matrix is bidirectionally complete: 0 requirements with no test, 0 tests with no requirement; flag requirements whose only tests are failing/blocked as "covered-but-failing".

## Assertions & exit gate
- Every requirement traces forward to ≥1 test case (no untested requirement).
- Every test traces backward to ≥1 requirement (no orphan test).
- Coverage % computed; requirements with only failing/blocked tests flagged.
- **Gate:** `full_bidirectional_coverage` — passes when 0 untested requirements AND 0 orphan tests (an untested requirement is **major** — a real coverage hole; an orphan test is **minor** — wasted/ambiguous effort).

## Output
Write `artifacts/traceability-coverage/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"full_bidirectional_coverage"}` + `notes`/artifact carrying the RTM. Findings (`QA-TRACE-NNN`) name the uncovered requirement ID or orphan test in `evidence`, citing the RTM/29148 in `oracle`. Coverage % feeds `test-reporting-metrics` and `release-readiness`.

## Combinatorial-coverage measurement (NIST ACTS-style gap analysis)
Requirement traceability answers *"is each requirement touched by a test?"* — it does **not** answer *"are the parameter interactions inside those tests exercised?"* A suite can hit 100% requirement coverage yet never combine two input parameters that, together, trigger a defect. This section adds a second, orthogonal coverage axis: **t-way combinatorial coverage measurement** of the *existing* suite, reported alongside the RTM — a measurement pass, not a test-generation pass.

### Oracle (source of truth)
NIST's **Automated Combinatorial Testing for Software (ACTS)** body of work (`csrc.nist.gov/projects/automated-combinatorial-testing-for-software`) and its **interaction rule**: most failures are triggered by interactions among a small number of parameters (typically 1–6, the great majority by 1–2). **Combinatorial Coverage Measurement (CCM)** quantifies, for a given suite, the fraction of all t-way value combinations actually exercised. Coverage here = exercised t-way combinations ÷ total possible t-way combinations, per t (t=2 pairwise as the default floor, t=3 where input criticality warrants). The model — the enumerated parameters and their value sets — not the suite's row count, defines whether interaction coverage is adequate.

### Step sequence (Plan → Act → Verify)
1. **Plan** — derive the input model from the existing suite *as written*: enumerate each test parameter and its observed value set (read-only, no new cases). Pick the target strength(s): t=2 floor, t=3 for inputs the requirement set flags as critical.
2. **Act** — for each t, enumerate all possible t-way value combinations from the model, then mark each as **exercised** (appears together in ≥1 existing test) or **missing** (gap). Compute coverage % per t. Cross-reference each missing combination back to the requirement(s) whose parameters it spans, so a gap is reported as both an interaction gap and a traceability context. Skip-and-continue on an unparseable parameter.
3. **Verify** — assert the measurement is grounded only in suite rows that actually exist; confirm every reported "exercised" combination cites the test(s) covering it and every "missing" combination cites the parameters involved. No combination is inferred as covered from a test merely *looking* related.

### Assertions & exit gate (combinatorial)
- t=2 (pairwise) coverage % computed for the existing suite; t=3 computed where critical inputs are flagged.
- Every **missing** combination names its parameters + value pair and the requirement(s) it spans in `evidence`.
- Every **exercised** combination cites the covering test(s).
- **Gate:** `combinatorial_coverage_measured` — passes when the CCM report is produced and grounded (t=2 floor measured for every multi-parameter requirement); this gate asserts the *measurement exists and is sound*, **not** that coverage is 100%. A low pairwise % is a reported finding for human triage, not an automatic block — combinatorial adequacy is a human judgement call, same as acceptable RTM gaps.

### Output (combinatorial)
Extend `artifacts/traceability-coverage/report.json`: add a `combinatorial` block carrying per-t coverage %, the exercised/missing combination lists, and the input model used. Findings (`QA-CCM-NNN`) name the missing combination's parameters/values and the spanning requirement ID in `evidence`, citing NIST ACTS / the interaction rule in `oracle`. Pairwise coverage % feeds `test-reporting-metrics` and `release-readiness` next to requirement coverage %.

> **Watch (do not gate):** NIST's CCM tooling (and ACTS itself) extends toward **input-space coverage for autonomous / AI-ML systems** where structural coverage does not apply — Combination Frequency Differencing and Combinatorial Coverage Difference Measurement. EMERGING — note only; do not add as a gate until the suite under test actually includes such components.

## Guardrails
Read-only — `disallowedTools: Edit, Write` outside artifacts. The matrix reflects recorded links only — don't infer coverage from a test "looking related"; require an explicit requirement tag. The combinatorial pass is equally non-destructive: it **measures** the existing suite's interaction coverage, it never generates, mutates, or runs tests — the input model is derived from suite rows as written, and every exercised/missing combination is grounded in real rows. Cap `maxTurns`. Recommendations only; a human confirms acceptable coverage gaps — both untested-requirement gaps and low t-way coverage.
