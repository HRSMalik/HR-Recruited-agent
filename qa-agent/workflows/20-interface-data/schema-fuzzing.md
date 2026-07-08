# schema-fuzzing

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/schema-fuzzing-tester.md
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Auto-derive thousands of valid + malformed requests from the OpenAPI/GraphQL spec (Schemathesis / Dredd) and assert that EVERY response conforms to the declared schema and status set — surfacing unhandled 500s and contract violations no example-based suite would hit. Collapses property-based API testing + security fuzzing + CI conformance into one gate; complements the example-based `api-contract.md`.

## Inputs & preconditions
- Required artifacts: the machine-readable spec — OpenAPI/Swagger (`openapi.yaml` / `openapi.json`) or GraphQL SDL — with resolvable `$ref`s.
- Target: base URL + auth (API key / bearer via env), environment name, a fixed RNG seed for reproducible case generation.
- Preconditions: spec parses and Schemathesis loads it without errors; base URL reachable (`GET /health` 2xx); auth token present in env; target asserted NON-PROD before any non-GET probe.

## Oracle (source of truth)
The OpenAPI/GraphQL **spec** — per-operation `responses` status set, `components.schemas`, `required` arrays, `additionalProperties`, parameter/body `schema` constraints, and declared error responses. Correctness is "the response matches what the spec declares for this operation", NEVER the service's own returned payload. See https://schemathesis.io.

## Step sequence (Plan → Act → Verify)
1. **Plan** — point Schemathesis at the spec; let it enumerate every operation and generate cases by property-based strategies (boundary ints, oversized strings, wrong types, missing required, extra fields, null bytes, unicode, negative/overflow numbers) plus the spec's own examples. Fix the seed; scope to changed operations when a spec diff is provided. Default checks: `not_a_server_error`, `status_code_conformance`, `response_schema_conformance`, `content_type_conformance`.
2. **Act** — run the generated cases via Schemathesis's runner one operation at a time. GET/HEAD/OPTIONS freely on any target; mutating verbs (POST/PUT/PATCH/DELETE) execute ONLY against a confirmed NON-PROD seeded sandbox, else mark those operations NOT RUN. Use `--hypothesis-max-examples` and a per-op deadline to cap cost; back off on 429; skip-and-continue on a single case's transport error.
3. **Verify** — for every response assert: status ∈ the operation's declared set; body validates against the resolved JSON-schema (no missing `required`, no type mismatch, no undeclared field where `additionalProperties:false`); `Content-Type` matches the declared media type; and NO unhandled `5xx`. Schemathesis auto-reports the minimal failing example (shrunk) for each violation.

## Assertions & exit gate
- `not_a_server_error` — no operation returns an undeclared `500`/`5xx` on any generated input (unhandled crash → at least **major**; data-corruption/auth-bypass surface → **critical**).
- `status_code_conformance` — every status returned is in the spec's declared set for that operation.
- `response_schema_conformance` — every body validates against its declared schema; `content_type_conformance` holds.
- **Gate:** `spec_conformance_clean` — 0 server-errors AND 0 status/schema/content-type violations across all generated cases (read-only ops always; mutating ops on sandbox or explicitly NOT RUN).

## Output
Write `artifacts/schema-fuzzing/report.json` per `shared/report-format.md`:
`{ flow, status, summary{total,passed,failed,skipped}, findings[], gate{name:"spec_conformance_clean",passed} }`.
Each finding follows `shared/finding-schema.md`; `id` = `QA-FUZZ-<NNN>`; `oracle` names the spec location + check (e.g. `openapi.yaml#/paths/~1candidates/post/responses` + `response_schema_conformance`). Evidence = the shrunk minimal failing request (method, path, headers redacted, body) + raw response + validator/check error + the RNG seed for deterministic replay. Classify each failure (`real_bug` / `known_expected` / `test_assertion_issue`) before carding.

## Guardrails
Per `shared/guardrails.md`: read-only on live (`disallowedTools: Edit, Write`; GET/HEAD/OPTIONS only); fuzzing of mutating verbs runs ONLY against a confirmed NON-PROD seeded sandbox (record fixture/seed id), else NOT RUN with a note. Secrets via env, redacted from every finding and from the saved cassette. Bound generation with `--hypothesis-max-examples` + per-op deadline; respect SUT rate limits and back off on 429; cap turns.

## Watch (do not gate)
- GraphQL fuzzing via Schemathesis is newer than its OpenAPI path — treat GraphQL coverage as informational until verified against this SUT; do not fail the gate on GraphQL-only findings yet.
