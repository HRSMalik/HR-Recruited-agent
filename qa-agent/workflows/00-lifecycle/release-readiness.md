# release-readiness

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Decide go/no-go: verify the plan's exit criteria are met, no open blocker/critical defects remain, and produce a sign-off recommendation with closure notes. Answers: "Is this build releasable, and if not, exactly what blocks it?"

## Inputs & preconditions
- Required artifacts: the test plan's exit/suspension criteria (from `test-strategy-plan`), all per-flow `report.json` + `summary.json`, the open-defect list (from `defect-triage`), coverage report (from `traceability-coverage`), metrics (from `test-reporting-metrics`).
- Target: the `artifacts/` aggregate (read-only) for the candidate build/version.
- Preconditions: the planned flows have run and written reports; exit criteria are quantified (the plan gate passed).

## Oracle (source of truth)
The **test plan's documented exit criteria** (IEEE 829 / ISO 29119-3 exit-criteria clause — e.g. "≥95% planned cases executed, ≥90% pass, 0 open blocker/critical, ≤N open major, coverage ≥ target") plus `shared/severity-priority-rubric.md` gate rule (any open blocker/critical → no-go). The decision is checked against the agreed criteria, **not** against gut feel or schedule pressure.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate every exit criterion from the plan as a checkable assertion; list the data source for each.
2. **Act** — evaluate each criterion against the aggregated reports one at a time: execution %, pass %, open blocker/critical/major counts, coverage vs target, any suspended flows. Skip-and-continue, recording met/unmet per criterion.
3. **Verify** — assert each criterion's met/unmet status from cited numbers; derive an overall **go / no-go / conditional-go** recommendation; draft closure notes (what shipped, known issues + their tickets, deferred items).

## Assertions & exit gate
- Every plan exit criterion evaluated with a cited source number (met/unmet, no unevaluated criterion).
- 0 open blocker or critical defects for a "go".
- Coverage and pass-rate meet or exceed the plan's targets; suspended flows resolved.
- **Gate:** `release_criteria_met` — passes (recommend **go**) only when all exit criteria met AND 0 open blocker/critical; any open blocker/critical → **no-go** (that defect's id is the gate reason). Outstanding majors → **conditional-go** with a documented waiver request.

## Output
Write `artifacts/release-readiness/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"release_criteria_met", passed}` + `notes` carrying the sign-off recommendation and closure notes. Unmet-criterion findings (`QA-REL-NNN`) cite the criterion in `oracle` and the blocking defect ids in `evidence`. This gate feeds the orchestrator's final pass/fail.

## Guardrails
Read-only — `disallowedTools: Edit, Write` outside artifacts. The agent **recommends**; a human owns the final release sign-off. Never relax a documented exit criterion to force a "go" — surface the unmet criterion + the waiver path instead. Redact secrets/PII. Cap `maxTurns`.
