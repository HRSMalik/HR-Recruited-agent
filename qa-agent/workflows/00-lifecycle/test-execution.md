# test-execution

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Orchestrate execution of the designed test cases — manual-scripted and automated — recording actual vs expected per case. Answers: "Which cases pass, which fail, and what exactly was observed for each?"

## Inputs & preconditions
- Required artifacts: the case suite (from `test-case-design`), seeded fixtures (from `test-data-management`), a ready environment (from `test-environment`), and any automation harness/runner config.
- Target: the verified NON-PROD SUT base URL / host + auth context per case.
- Preconditions to assert before acting: `test-environment` gate passed (env ready + NON-PROD); fixture ids referenced by cases exist; auth/role contexts available.

## Oracle (source of truth)
Each test case's **predefined expected result** (itself derived from the requirement in `test-case-design`). A case passes only when the observed actual matches that expected result — pass/fail is decided against the case's documented oracle, **never** by asking whether the SUT "seems fine". Automated assertions compare to the same recorded expected values.

## Step sequence (Plan → Act → Verify)
1. **Plan** — order cases (smoke/critical-path first, then by risk/priority from `risk-based-prioritization`); partition into automated vs manual-scripted; resolve the fixture + auth context for each.
2. **Act** — execute one case at a time against the sandbox: drive the automated runner or follow the manual script; capture the full actual (response/status/state, logs, screenshot path). **Skip-and-continue** on any single case failure or error — never abort the run; mark blocked cases that depend on a failed precondition.
3. **Verify** — compare each actual to the case's expected result; set per-case status `pass | fail | blocked | skipped`; attach evidence to every non-pass.

## Assertions & exit gate
- Every in-scope case executed or explicitly marked blocked/skipped with a reason.
- Each result has actual-vs-expected recorded; every fail/blocked carries evidence.
- No case silently dropped (executed + blocked + skipped == planned).
- **Gate:** `execution_complete_no_critical_fail` — passes when all planned cases reach a terminal status AND 0 failed cases are critical/blocker (a failing critical-path case is **critical**; a non-critical functional fail is **major**).

## Output
Write `artifacts/test-execution/report.json` per `shared/report-format.md`: status, summary{total,passed,failed,skipped}, findings[], `gate{name:"execution_complete_no_critical_fail"}`. Each failing case becomes a finding (`QA-EXE-NNN`) with deterministic `steps_to_reproduce` (incl. fixture/seed id), `expected` (the case oracle), `actual`, and `evidence`. Per-case results feed `defect-triage` and `test-reporting-metrics`.

## Guardrails
Mutations against the seeded sandbox only; assert NON-PROD first. No real external side-effects (emails/SMS/charges) — target stubs; mark side-effecting cases NOT RUN with how-to-test-in-sandbox note. Skip-and-continue, never crash the run. Redact secrets/PII from evidence. Cap `maxTurns`; back off on 429.
