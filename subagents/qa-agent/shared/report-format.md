# Report Format

Two layers: a **structured JSON** every flow writes (source of truth), and a **JUnit XML** render for CI gating (de-facto standard, parsed natively by GitHub Actions / GitLab / Jenkins / Azure DevOps).

## Per-flow report — `artifacts/<flow>/report.json`

```json
{
  "flow": "api-contract",
  "status": "pass|fail|error",
  "started_at": "ISO-8601",
  "ended_at": "ISO-8601",
  "sut": "<base URL / host>",
  "build": "<commit / version>",
  "summary": { "total": 42, "passed": 39, "failed": 3, "skipped": 0 },
  "findings": [ /* finding objects — see finding-schema.md */ ],
  "gate": { "name": "no_schema_violations", "passed": false },
  "notes": ["assumptions made, anything not run and why"]
}
```

## Orchestrator roll-up — `artifacts/summary.json`

```json
{
  "run_id": "<id>",
  "sut": "...", "build": "...",
  "flows": [ { "flow": "...", "status": "...", "gate_passed": true } ],
  "findings_by_severity": { "blocker":0,"critical":1,"major":2,"minor":3,"trivial":0 },
  "gate": { "passed": false, "reason": "1 critical finding (QA-SEC-001)" }
}
```

## Human-readable test cases — `test-cases.md` (BAKED-IN, required)
Every run also emits a Markdown test-case document for human review/UAT — JSON/JUnit stay the machine source of truth; keep TC IDs consistent across all three. `test-case-design` writes its own; the orchestrator merges all flows into the run-level `test-cases.md`.

**Write it as a structured tracker document** (the shape this project already uses for its tracker docs — match whatever bug-sheet / backlog format the repo has). Its structure: a title + project + Last-Updated header → `---` → a `## Summary` count table → `---` → sections grouped by feature/area, each with a case table → `---` → a `## Conventions` block explaining the columns/status values. NOT a single bare table. Before writing, glance at an existing repo tracker doc and mirror its header/summary/section/conventions rhythm.

```markdown
# <Project> — Test Cases

**Project:** <name>
**SUT / build:** <url> · <commit>   ·   **Last Updated:** YYYY-MM-DD

---

## Summary

| Total | Pass | Fail | Blocked | Not-run |
| --- | --- | --- | --- | --- |
| 42 | 38 | 3 | 1 | 0 |

---

## Auth / Login

| ID | Requirement | Technique/Flow | Preconditions | Steps | Test data | Expected | Actual | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-001 | US-01-01 AC2 | EP/BVA | app up, no session | 1. POST /auth/login | valid creds | 200 + JWT | 200 + JWT | Pass |
| TC-002 | US-01-01 AC3 | negative | — | wrong password | bad creds | 401 generic | 401 generic | Pass |

## Claims / Intake
| … |

---

## Conventions
- **Status:** Pass / Fail / Blocked / Not-run
- **ID:** `TC-NNN`, stable across runs; same IDs in `report.json`
- **Expected** is requirement-derived (never the SUT's own output); **Actual** is `—` until executed
- Group cases by feature/area; one row per case
```

## Re-runnable smoke/e2e scripts — `tests/` (BAKED-IN, when a flow drives a browser/UI)
When a flow runs a **scripted browser/UI smoke or e2e pass** (drive the app, walk routes, assert zero console/page/API errors), **persist the runnable driver script** into the project's test-scripts dir — declared in `project-qa-config.md` (default: a root **`tests/`** dir), named per feature/flow (e.g. `tests/smoke_<feature>.mjs`). This is the **script analog of `test-cases.md`**: `report.json`/JUnit stay the machine source of truth and `test-cases.md` is the human tracker, but the script is the *reproducible* artifact anyone can re-run and diff.

- Write it with the project's browser-automation runner (see `project-qa-config.md` — e.g. puppeteer-core / Playwright, headless, the SUT base URL + screenshot login creds).
- Read-only flows persist it via Bash (`cat > tests/…`), the same way they write `report.json` (Edit/Write may be disallowed) — the script reads from the SUT but **writes no SUT state**, so it stays inside the read-only guardrail.
- Keep it in the test-scripts dir, **never** in `frontend/`/`backend/` (those sync to the deployment repo — scripts must not ship). Keep its route/case coverage aligned with `report.json` + `test-cases.md`.

## JUnit XML (CI gate)
Render each finding as a `<testcase>`; a failed assertion becomes a `<failure>`:

```xml
<testsuites name="qa-agent" tests="42" failures="3" time="...">
  <testsuite name="api-contract" tests="42" failures="3">
    <testcase name="QA-API-001 GET /candidates returns 200+schema" classname="api-contract">
      <failure message="schema violation: missing field 'total'">…evidence…</failure>
    </testcase>
    <testcase name="QA-API-002 …" classname="api-contract"/>
  </testsuite>
</testsuites>
```

## Conventions
- `status: error` ≠ `fail`: `error` means the flow itself could not run (env down, missing spec) — distinguish from real defects.
- A flow with 0 findings still writes a report with `status:pass` and an empty `findings[]`.
- For human review, optionally also emit Allure-compatible output; JUnit XML stays the gating artifact.
- The orchestrator's gate fails on: any failed flow gate, OR any open blocker/critical finding (see severity rubric).
