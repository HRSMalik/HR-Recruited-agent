# negative-boundary

**Category:** 10-functional
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only (or seeded-sandbox for invalid writes)

## Purpose
Negative and boundary-value testing (ISTQB *negative testing* + *boundary value analysis*): drive invalid inputs, edge/boundary values, and error conditions to confirm the system **rejects bad input cleanly** instead of crashing. Answers — "does it fail safely, with the right error, on everything it should refuse?"

## Inputs & preconditions
- Required artifacts: the request schema / OpenAPI (field types, required flags, ranges, enums) — the source for what is *invalid* and where the *boundaries* are.
- Target: base URL + auth via env; build/commit recorded.
- Preconditions: smoke passed; invalid-write cases (POST/PUT with bad bodies) only against a seeded sandbox, never live data.

## Oracle (source of truth)
The **schema / API contract**: which inputs are invalid, which fields are required, the documented valid ranges/enums, and the contract's error semantics (validation → `422`/`400`, missing resource → `404`, wrong method → `405`). NEVER the SUT's own error response as the definition of correct.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate negative + boundary cases from the schema: wrong types (string for int), missing required fields, out-of-range values, BVA at min−1/min/max/max+1, invalid enums, malformed/empty/oversized JSON, wrong `Content-Type`, wrong HTTP method, and empty/oversized strings.
2. **Act** — send one malformed/edge request at a time; skip-and-continue; mutating cases go to the seeded sandbox.
3. **Verify** — assert the *precise* error code and a clean, structured error body — and crucially that no `500` and no stack trace/leak occurs.

## Assertions & exit gate
- Validation failures return `422` (FastAPI/Pydantic) or the contract's `400`, with a structured error body naming the offending field — never a bare `500`.
- Missing resource → `404`; unsupported method → `405`; malformed JSON → `400`/`422`, not `500`.
- BVA: min and max accepted; min−1 and max+1 rejected with the right code (off-by-one detector).
- No internal `500`, stack trace, SQL/exception text, or PII leaks in any error body.
- **Gate:** `clean_error_handling` — pass only if every invalid input yields the correct documented error code with no `500` and no leak; any `500`/wrong-code/leak → `fail`.

## Output
Write `artifacts/negative-boundary/report.json` per `shared/report-format.md`:
`{ flow:"negative-boundary", status, summary{...}, findings[], gate{name:"clean_error_handling",passed} }`.
Findings per `shared/finding-schema.md`; `oracle` = the schema field/range + expected error code; a `500` on bad input is **major** (an information leak in the error body is **critical**); evidence = the exact malformed request + the actual status/body.

## Guardrails
Per `shared/guardrails.md`: read-only on live; invalid-write cases only against a seeded sandbox (`<db>-qa`, seeded → run → torn down, confirm teardown); never send injection payloads at a production target (that surface belongs to `security`, sandboxed); secrets via env; redact any leaked secret in evidence; `maxTurns: 30`.
