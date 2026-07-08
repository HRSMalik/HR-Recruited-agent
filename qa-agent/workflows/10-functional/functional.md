# functional

**Category:** 10-functional
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only (or seeded-sandbox when a flow mutates state)

## Purpose
Specification-based black-box testing (ISTQB *functional testing*): verify features do what the requirements/acceptance-criteria say, exercising **positive flows** against the spec. Answers — "does each feature meet its documented requirement?"

## Inputs & preconditions
- Required artifacts: requirements / user stories with acceptance criteria, or an OpenAPI/Swagger spec, plus requirement IDs for traceability.
- Target: base URL + auth via env; build/commit recorded.
- Preconditions: smoke passed; requirement IDs resolvable; mutating cases (POST/PUT) only against a confirmed seeded sandbox DB, never live data.

## Oracle (source of truth)
The **requirements / acceptance criteria** (requirement IDs, AC bullets, or the OpenAPI schema for response shape). Each assertion traces to a named requirement. NEVER the SUT's own response.

## Step sequence (Plan → Act → Verify)
1. **Plan** — derive black-box positive cases per requirement using equivalence partitioning (one valid representative per class) and decision-table coverage for branching rules. Map each case → requirement ID.
2. **Act** — execute one case at a time against the documented happy path (valid inputs, expected preconditions); skip-and-continue; for state-changing features run against the seeded sandbox and assert the resulting state.
3. **Verify** — assert response status, body schema, and business outcome against the spec; capture the request/response for every mismatch with its requirement ID.

## Assertions & exit gate
- Each feature returns the documented success status (`200`/`201`) and a body matching the spec schema for valid input.
- Business rules hold (e.g. REQ-CAND-04: submitting a complete application sets `status="received"` and returns the application id).
- Every requirement ID in scope has ≥ 1 passing positive case (coverage check).
- **Gate:** `all_requirements_pass` — pass only if every in-scope requirement's positive case passes; any failed AC → `fail`.

## Output
Write `artifacts/functional/report.json` per `shared/report-format.md`:
`{ flow:"functional", status, summary{...}, findings[], gate{name:"all_requirements_pass",passed} }`.
Findings per `shared/finding-schema.md`; `oracle` = the requirement/AC id; a primary feature returning wrong output on valid input is **major** (or **critical** if it breaks a core capability with no workaround), evidence = request/response vs the spec.

## Guardrails
Per `shared/guardrails.md`: read-only on live targets; mutating cases only against a seeded sandbox (`<db>-qa`), seeded → run → torn down (confirm teardown in report); record fixture/seed id in each finding; secrets via env; no real outbound side-effects (emails/SMS mocked); `maxTurns: 30`.
