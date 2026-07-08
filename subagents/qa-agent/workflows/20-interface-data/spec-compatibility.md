# spec-compatibility

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/spec-compatibility-checker.md
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Static spec-vs-spec breaking-change diffing in PR CI — no test code, no running service. Diff the changed interface definitions against the previous published spec version to catch breaking API changes BEFORE deploy: OpenAPI via oasdiff, proto/gRPC wire compatibility via `buf breaking`, plus a Spectral style/lint pass. Distinct from runtime contract testing — this never sends a request, it compares two documents.

## Inputs & preconditions
- Required artifacts: the **changed** spec(s) from the PR branch — OpenAPI (`openapi.yaml`/`.json`), `.proto` files; the **previous published baseline** to diff against (released tag, `main`, or a registry-published version); a compatibility ruleset/policy (oasdiff `--severity` levels, `buf.yaml` breaking rules, `.spectral.yaml`).
- Target: the PR diff only — scope to spec files touched by the change. No base URL, no auth, no live host (static analysis).
- Preconditions to assert before acting: `oasdiff`, `buf`, and `spectral` present; base specs resolve and parse on both sides (old + new); `$ref`s resolve; the baseline ref is fetchable. If the baseline is missing, emit `status:error` (cannot diff against nothing) — do not pass by default.

## Oracle (source of truth)
The **previous published spec version** (the baseline document) plus the **compatibility ruleset** — oasdiff's breaking-change classification (https://www.oasdiff.com), Buf's wire/source breaking rules (`buf.yaml`), and the Spectral ruleset. "Breaking" is defined by these rulesets diffing old→new, NEVER by the new spec alone or by any running service's output.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate the spec files changed in the PR and pair each with its baseline counterpart. For each pair pick the checker: OpenAPI → oasdiff; proto → `buf breaking`; both get a Spectral lint pass. List the breaking categories in scope (removed path/operation, removed/renamed required field, narrowed type, new required request param, removed enum value, removed proto field/changed field number or type).
2. **Act** — run one checker at a time, read-only, machine output: `oasdiff breaking <base> <revision> -f json`; `buf breaking --against '<baseline-git-ref>' -o json`; `spectral lint <spec> -f json`. Skip-and-continue if a single spec pair fails to load — record it as a skipped item with the parse error, do not abort the run.
3. **Verify** — classify each diff entry against the ruleset's severity. Map oasdiff `ERR` (and `buf` breaking violations) to breaking changes; oasdiff `WARN` and Spectral `error/warn` to lint findings. Triage every flagged change (`real_bug` vs `test_assertion_issue` — e.g. an intentional v2 break behind a new path is not a regression) before carding.

## Assertions & exit gate
- OpenAPI: oasdiff reports **0 breaking changes** (no `ERR`) between baseline and revision for in-scope severity.
- Proto/gRPC: `buf breaking` reports **0 violations** — no removed/renumbered/retyped fields, no removed RPCs or messages.
- Lint: Spectral surfaces no `error`-level rule violations on the changed spec (style/consistency).
- Each flagged break is triaged; intentional, versioned changes are reclassified out of the breaking tally with a note.
- **Gate:** `no_breaking_spec_changes` — 0 oasdiff `ERR` AND 0 `buf breaking` violations across all changed specs.

## Output
Write `artifacts/spec-compatibility/report.json` per `shared/report-format.md`:
`{ flow, status, summary{total,passed,failed,skipped}, findings[], gate{name:"no_breaking_spec_changes",passed} }`.
Each finding follows `shared/finding-schema.md`; `oracle` names the baseline ref + ruleset entry (e.g. `baseline@v1.4.0 openapi.yaml#/paths/~1candidates/get — oasdiff:response-required-property-removed`, or `buf:FIELD_NO_DELETE proto/candidate.proto Candidate.id#3`). Evidence = the exact oasdiff/buf/Spectral JSON entry (rule id, location, old→new value). Severity defaults: breaking change to a published, consumed contract → **major** (P2); lint `error` → **minor**; cosmetic style → **trivial**.

## Guardrails
Per `shared/guardrails.md`: fully read-only — `disallowedTools: Edit, Write`; static document diff only, never issues an HTTP call or DB query, so no live/prod target is touched. No mutation, no seeded data needed. Baseline ref fetched read-only; registry/broker tokens via env, redacted from the report. Cap turns; this is a cheap deterministic flow.

**Watch (do not gate):** schema-aware diffing of JSON example payloads and AsyncAPI/event-schema (Avro/protobuf registry) backward-compat checks are emerging surfaces — note any drift observed but do not fail the gate on them yet.
