# contract-testing

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/contract-tester.md
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Consumer-driven contract testing (Pact): the consumer records its expectations against a mock provider, producing a pact file; the provider replays and verifies it. Catches breaking interface changes before deploy — for both HTTP request/response and async message contracts.

## Inputs & preconditions
- Required artifacts: consumer expectation definitions (the interactions the consumer relies on); provider service or a startable provider instance; Pact Broker URL + token (if used).
- Target: consumer build + provider build/branch under test, with provider states (fixtures) defined.
- Preconditions: Pact tooling present; provider can be started against a seeded sandbox; broker reachable when version compatibility is in scope.

## Oracle (source of truth)
The **pact file** generated from the consumer's recorded expectations (request/response shapes, matchers, message bodies, provider states). For compatibility checks, the **Pact Broker** matrix of verified consumer↔provider version pairs. NEVER the provider's live output alone.

## Step sequence (Plan → Act → Verify)
1. **Plan** — list consumer interactions: each HTTP request→response pair and each async message contract, with the provider state each requires.
2. **Act** — consumer side: run consumer tests against the Pact **mock**, generating/refreshing the pact file (publish to broker with the consumer version + git sha). Provider side: start the provider against the seeded sandbox, set up each provider state, replay every interaction from the pact, verify async contracts by asserting the produced message matches the recorded body/matchers.
3. **Verify** — compare each provider response/message to the pact's expected shape via Pact's matchers; query the broker's `can-i-deploy` for the version pair.

## Assertions & exit gate
- Every recorded interaction verifies: status/headers/body (HTTP) or message body+metadata (async) match the pact's matchers.
- No required field removed, renamed, or retyped versus the pact (breaking change detection).
- Each interaction's provider state was satisfiable.
- `can-i-deploy` returns compatible for the consumer↔provider versions.
- **Gate:** `pact_verified` — all interactions verified AND `can-i-deploy` is true.

## Output
Write `artifacts/contract-testing/report.json` per `shared/report-format.md`:
`{ flow, status, summary{...}, findings[], gate{name:"pact_verified",passed} }`.
Each finding follows `shared/finding-schema.md`; `oracle` = pact file + interaction description (e.g. `pacts/web-candidates.json#"a request for candidate 7"`). Evidence = the diff between expected matcher and actual provider output, plus the failing provider state.

## Guardrails
Per `shared/guardrails.md`: provider verification runs against a seeded NON-PROD sandbox only — confirm host before starting. Broker token via env, redacted. Do not publish pacts from an unverified/dirty build. Cap turns; back off on broker 429.
