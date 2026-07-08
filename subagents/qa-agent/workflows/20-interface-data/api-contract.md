# api-contract

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/api-contract-tester.md
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Validate that a deployed REST/GraphQL/gRPC API conforms to its published contract — status codes, response schemas, required fields, CRUD consistency, and error shapes — judged against the spec, not the service's own output.

## Inputs & preconditions
- Required artifacts: the contract spec — OpenAPI/Swagger (`openapi.yaml`), GraphQL SDL, or `.proto` files.
- Target: base URL + auth (API key / bearer via env), environment name.
- Preconditions: spec parses and resolves `$ref`s; base URL is reachable (`GET /health` or equivalent 2xx); auth token present in env.

## Oracle (source of truth)
The OpenAPI/GraphQL/proto **spec** — paths, declared `responses` status codes, `components.schemas`, `required` arrays, and error response definitions. NEVER the SUT's own returned payload.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate every operation in the spec. For each, derive cases across the categories: happy path (valid request, real data → declared 2xx + populated body), valid-but-empty (valid request, no matching data → declared 2xx + empty/"not found" shape), negative/validation (missing/invalid field, wrong types, out-of-range → declared 4xx/422), boundary (min/max ±1 of every constrained field), injection/abuse (oversized, type-confusion, NoSQL/SQL-style, encoding), auth (no/invalid token → 401/403), not-found (bad id → 404 or empty), and method/path (wrong verb → 405, unknown path → 404). **Honor the mandate's per-endpoint case count** when one is given (e.g. "20 per endpoint"): generate exactly that many per operation per the per-unit case-budget rule in `00-lifecycle/test-case-design.md` — coverage first, then fill to the count with non-redundant boundary/injection/combinatorial cases; never go under contract coverage to hit the number. With no count given, derive the minimal contract-complete set. Scope to changed paths when a diff is provided.
2. **Act** — send one request at a time with the flow's HTTP client. Read-only: GET freely; for CRUD-consistency probe a `POST→GET→PUT→GET→DELETE→GET` sequence ONLY on a seeded-sandbox target (skip on live, note it). Skip-and-continue on a single case's transport failure.
3. **Verify** — assert response status is in the spec's declared set for that operation; validate the body against the resolved JSON-schema (json-schema validator); confirm every `required` field is present and typed correctly; confirm error bodies match the declared error schema.

## Assertions & exit gate
- HTTP status ∈ spec's declared responses for the operation.
- Response body passes JSON-schema validation; no missing `required` fields; no type mismatches; no undeclared/extra fields where `additionalProperties:false`.
- CRUD round-trip: created resource is retrievable and reflects the write (sandbox only).
- Error paths return the declared error contract (status + schema), not a 200-with-error-body.
- **Gate:** `no_schema_violations` — 0 schema violations across happy and error paths.

## Output
Write `artifacts/api-contract/report.json` per `shared/report-format.md`:
`{ flow, status, summary{total,passed,failed,skipped}, findings[], gate{name:"no_schema_violations",passed} }`.
Each finding follows `shared/finding-schema.md`; `oracle` names the spec path + schema (e.g. `openapi.yaml#/paths/~1candidates/get/responses/200`). Evidence = exact request + raw response + validator error.

## HTTP-contract cases (beyond schema shape)
Beyond status + body schema, assert the wire-level HTTP semantics the spec declares. Each case is judged against the spec/RFC, NEVER the SUT's own behavior. Read-only cases run freely on live; any case needing a write (Idempotency-Key replay, pagination-under-insert) runs ONLY on a confirmed NON-PROD seeded sandbox, else marked NOT RUN.

### Error bodies — RFC 9457 problem+json
Source of truth: `datatracker.ietf.org/doc/html/rfc9457`. When the spec declares `application/problem+json` for an error response, assert the wire shape, not just "an error came back":
- **Media type** — `Content-Type: application/problem+json` (the canonical JSON format; `application/problem+xml` is the XML alternative). A plain `application/json` body where the spec declared problem+json is a finding.
- **Members** — validate the standard members and their meaning:
  - `type` — a URI-reference string identifying the problem type; absent ⇒ defaults to `"about:blank"`. When `type` is `about:blank`, `title` SHOULD equal the HTTP status phrase for the code (e.g. `404` → `"Not Found"`).
  - `title` — short human-readable summary of the problem *type*; SHOULD be stable across occurrences of the same `type` (modulo localization). Compare two responses of the same `type`: differing `title` strings (beyond locale) is a finding.
  - `status` — a JSON number equal to the actual HTTP status code of the response. `status` member ≠ response status line is a finding.
  - `detail` — human-readable explanation specific to *this occurrence*; assert it is present and occurrence-specific where the spec requires it, not a copy of `title`.
  - `instance` — URI-reference string identifying the specific occurrence (when declared).
- Extension members (e.g. `balance`, `accounts` in the RFC's out-of-credit example) are permitted alongside the standard members — do NOT flag them as undeclared.

### Idempotency-Key semantics
When the spec declares an `Idempotency-Key` request header for an unsafe operation (sandbox only — this is a write):
- **Replay** — issue the same request twice with the same key and identical body: the second response MUST return the original result (same resource, same id), not create a duplicate.
- **Key reuse with a different body** — same key, changed payload ⇒ assert the declared conflict response (`409 Conflict` is the common contract); never a silent second create.
- **Key TTL** — confirm the spec's stated retention window: within TTL the key replays the stored result; after TTL the key may be treated as new. Probe replay only within the declared window — do not assert behavior past TTL on live.

### Pagination
For paginated list operations, assert traversal semantics against the spec:
- **Cursor opacity** — when the spec declares an opaque cursor, treat it as opaque: pass it back verbatim, never parse, decode, or construct one. A cursor whose value leaks/assumes internal structure (offset, raw id) where the spec says opaque is a finding.
- **`has_more`** — follow the chain until `has_more` is `false` (or the cursor/`next` field is absent); assert the terminal page declares end-of-data and does NOT return a non-null cursor.
- **Stability under concurrent insert** — on a seeded sandbox, insert a row mid-traversal and continue paging: assert no item is skipped and no item is duplicated across pages per the spec's stability guarantee. On live this is NOT RUN (read-only; cannot seed) — note it.

### Rate-limit headers
When the spec declares rate limiting, assert the throttle contract, not just "got a 429":
- **`429 Too Many Requests`** returned once the limit is exceeded, with a body matching the declared error schema (problem+json if so declared).
- **`Retry-After`** present on the `429` and parseable as either delta-seconds or an HTTP-date; assert it is a sane positive value.
- **`X-RateLimit-*`** — where declared, validate `X-RateLimit-Limit`, `X-RateLimit-Remaining` (non-negative, decrements across calls), and `X-RateLimit-Reset` (timestamp/seconds in the future). Honor `Retry-After` and back off — do not hammer the limit to "confirm" it; one threshold-crossing probe is enough.

**Watch (do not gate):** EMERGING — `RateLimit` / `RateLimit-Policy` structured fields (the IETF draft superseding ad-hoc `X-RateLimit-*`). Note presence/shape if seen; do NOT gate on it — `X-RateLimit-*` remains the asserted contract until the spec declares the structured-field form.

## Guardrails
Per `shared/guardrails.md`: read-only on live (`disallowedTools: Edit, Write`; GET-only); CRUD mutation cases run ONLY against a confirmed NON-PROD seeded sandbox, else marked NOT RUN. Secrets via env, redacted from the report. Back off on 429; cap turns. Idempotency-Key replay and pagination-under-insert cases are sandbox-only writes — NOT RUN on live.
