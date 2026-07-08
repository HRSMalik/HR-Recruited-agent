# test-strategy-plan

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Generate a test strategy and a project-/release-level test plan: scope, approach, risk-based coverage, entry/exit criteria, environments, schedule, and deliverables. Answers: "What will we test, how, in what order, and when are we done?"

## Inputs & preconditions
- Required artifacts: reviewed requirements (output of `requirements-review`), architecture/feature inventory, change surface, RAID/risk register (or `risk-based-prioritization` output), available environments + timeline.
- Target: the test scope (epic / release / sprint); no running SUT needed.
- Preconditions: requirement IDs are testable (the requirements-review gate passed) and the in-scope feature list is enumerable.

## Oracle (source of truth)
The **ISO/IEC/IEEE 29119-3** document templates plus **IEEE 829-2008**: the Test Plan must populate the standard clauses — context, scope (in/out), test items, approach/strategy, features to test, pass/fail (entry/exit/suspension/resumption) criteria, deliverables, environment, schedule, risks & contingencies, staffing/responsibilities. Test-level selection follows **ISTQB CTFL v4.0** test types and the **test pyramid** (unit > integration > E2E). NEVER the team's habit — the standard's required sections are the checklist.

## Step sequence (Plan → Act → Verify)
1. **Plan** — map each in-scope feature to applicable test types (functional, API-contract, security, perf, accessibility…) and to a pyramid level; pull risks from the RAID register to weight depth.
2. **Act** — draft each 29119-3 clause one at a time: scope, approach, environment needs, entry/exit criteria (quantified — e.g. "exit when ≥95% planned cases executed, 0 open critical, ≤2 open major"), schedule, and the flow-to-feature coverage map. Skip-and-continue if a clause lacks input, marking it TBD with the missing dependency.
3. **Verify** — assert every required 29119-3/829 clause is present and non-empty, entry/exit criteria are measurable, and every in-scope feature maps to ≥1 planned test type.

## Assertions & exit gate
- All mandatory 29119-3 Test Plan clauses present and populated (no empty required section).
- Entry, exit, suspension, and resumption criteria are quantified and objectively checkable.
- Each in-scope requirement/feature is covered by ≥1 planned test activity (no coverage hole at plan time).
- **Gate:** `plan_complete_and_measurable` — passes when 0 missing required clauses and 0 unquantified exit criteria (a missing required clause is **major**; an unmeasurable exit criterion is **major**).

## Output
Write `artifacts/test-strategy-plan/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"plan_complete_and_measurable"}`. Findings (`QA-PLAN-NNN`) flag missing/empty clauses and unmeasurable criteria; `oracle` cites the 29119-3 clause name; `notes` may carry the assembled plan path. The plan document itself is a deliverable artifact alongside the report.

## Guardrails
Read-only — no SUT mutation, `disallowedTools: Edit, Write` outside the artifacts dir. Do not fabricate schedule/staffing data; mark unknowns TBD with the owner. Secrets via env. Cap `maxTurns`. Plan is a draft for human review and sign-off, not an authority.
