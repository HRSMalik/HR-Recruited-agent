# service-virtualization

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/service-virtualizer.md
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Stand in virtual replicas of dependencies that are unavailable, costly, rate-limited, or external (third-party APIs, payment gateways, partner services) using WireMock / Mountebank / Hoverfly, so the SUT's flows run in isolation — including under injected failure and latency.

## Inputs & preconditions
- Required artifacts: stub definitions (request matchers → canned responses) grounded in the dependency's published contract; the SUT's expected behavior spec for each dependency response.
- Target: SUT instance configurable to point at the virtual service base URL; the virtualization tool (WireMock/Mountebank/Hoverfly).
- Preconditions: SUT's dependency endpoints are repointable via env/config to the stub host; stub server starts and serves mappings.

## Oracle (source of truth)
The **dependency's contract** (the stub mappings derived from it) PLUS the **SUT's expected-behavior spec** for each stubbed scenario — what the SUT must do given a 200, a 500, a timeout, or malformed data. NEVER the SUT's own output deciding correctness.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate scenarios per dependency: nominal success, contract-valid edge cases, and fault injection (HTTP 5xx, 429, malformed body, connection reset, slow response > timeout).
2. **Act** — load stub mappings into the virtual service; point the SUT at it; drive the SUT flow that calls the dependency, one scenario at a time. For latency/failure cases, configure the stub's delay/fault, then exercise the flow.
3. **Verify** — assert the SUT's observable behavior matches the expected-behavior spec: success path completes; on 5xx/timeout the SUT retries/backs off/degrades/surfaces the right error (no crash, no data corruption); confirm the stub recorded the expected outbound request shape.

## Assertions & exit gate
- Nominal: SUT completes the flow correctly against the stubbed success response.
- Fault injection: SUT handles 5xx/429/timeout/malformed per spec (retry, circuit-break, graceful degrade, user-facing error) without crashing or corrupting state.
- Outbound request the SUT sent matches the dependency contract (verified via stub request journal).
- **Gate:** `behaves_against_stubs` — every scenario's SUT behavior matches the expected-behavior spec; 0 unhandled failures.

## Output
Write `artifacts/service-virtualization/report.json` per `shared/report-format.md`:
`{ flow, status, summary{...}, findings[], gate{name:"behaves_against_stubs",passed} }`.
Each finding follows `shared/finding-schema.md`; `oracle` = dependency contract section + SUT behavior requirement id. Evidence = stub mapping used, injected fault, SUT logs/response, and the stub request journal entry.

## Guardrails
Per `shared/guardrails.md`: virtual services replace real third-party calls — no real outbound side effects (charges, emails) ever fire. SUT runs against a seeded NON-PROD sandbox. Stub data is synthetic/masked, no real PII. Secrets via env. Cap turns.
