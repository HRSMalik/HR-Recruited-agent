# Guardrails — Non-Destructive, Sandboxed, Cost-Aware

Binding on **every** flow. A flow that cannot honor these must downgrade scope and say so, not proceed.

## 1. Non-destructive on live systems
- **Default to read-only.** Read-only flows declare `disallowedTools: Edit, Write` and never issue mutating HTTP (POST/PUT/PATCH/DELETE) or DB writes against a live/production target.
- Any write/mutation test runs **only against a seeded sandbox** (separate DB name or local instance), never production data.
- **Verify the target before acting:** assert the host/DB is NON-PROD. If you see a production host/connection string, STOP and report `status:error`.

## 2. Sandbox & test data
- Mutating flows seed an **isolated DB** (e.g. `<db>-qa` on a local/staging instance), run, then **drop/restore** it. Confirm teardown in the report.
- Use **golden datasets** with known expected outputs for evaluation; never copy real PII into test data — mask/synthesize.
- Record the fixture/seed id in every finding so repros are deterministic.

## 3. External side-effects
- Do NOT trigger real-world side effects in tests: outbound calls/emails/SMS, third-party charges, calendar/event creation, social posts. Mock them or target sandbox credentials.
- Flows that would cause a side effect mark it **NOT RUN** with a note on how it would be tested in a sandbox.

## 4. Secrets
- Inject via env / secret manager — never in prompts, fixtures, or committed artifacts.
- Scope MCP servers / credentials per-flow so they don't leak into the orchestrator context.
- Never write tokens, keys, or connection strings into `report.json` or logs (redact).

## 5. Determinism, rate limits, cost
- Cap agentic loops with `maxTurns`; prefer cheap models (Haiku) for shallow flows (smoke, sanity).
- Respect SUT and LLM rate limits; back off on 429. **Pre-emptive pause:** for rate-limited endpoints (e.g. login at 10/min), keep a call counter and pause *before* hitting the limit (when within ~2 calls), not just react to a 429 — this avoids false 429 failures polluting auth-heavy runs.
- Idempotent where possible; keep rollback one step away.
- Multi-agent fan-out costs ~15× chat tokens — the orchestrator only fans out when the mandate's value justifies it.

## 6. Enforcement
- A `PreToolUse` hook inspects Bash/HTTP commands and blocks destructive patterns (`INSERT|UPDATE|DELETE|DROP|TRUNCATE`, mutating HTTP verbs to prod hosts) with a non-zero exit.
- Least-privilege `tools` allowlist per flow.
- The orchestrator refuses to run a mutating flow whose target is not confirmed sandbox.

## 7. Test-double mail/SMS sink — verify, don't skip
A bare side-effect ban (§3) turns deliverability and template checks into structural `NOT RUN` amputations: nothing was actually sent, so nothing could be verified. Close that gap with a **sink** instead of a skip.
- Point the SUT's outbound email/SMS at a **test-double sink** — Mailpit/Mailhog (SMTP capture), or a provider in sandbox/test mode (e.g. a seeded Mailtrap/Twilio test sender). The sink **captures** the message and exposes it for assertion; it **never relays** to a real inbox or handset.
- With a sink in place, **VERIFY** rather than skip: that the message was emitted at all (deliverability path is wired), and that template correctness holds — subject, body, merge-field substitution, links, headers — against the grounded oracle. Treat "no message reached the sink" as a real, gradeable failure, not `NOT RUN`.
- **Strictly non-prod.** Assert the SMTP host / provider key resolves to the sink before sending; if it resolves to a real relay, STOP and report `status:error` (same posture as §1's prod-host check). Never seed real PII into the rendered message — mask/synthesize recipients (§2).
- Record the sink id + captured-message id in every finding so the render is a deterministic repro (§2).
- See `workflows/20-interface-data/email-deliverability-qa.md` for the concrete sink wiring, oracle, and template assertions.

## 8. Real-integration smoke — guard against false-green
An all-mock posture (§3) keeps tests hermetic but blinds them to **provider drift**: a mocked third party always agrees with last week's contract, so a breaking change ships green. Counter it with a thin, periodic smoke — separate from the mocked flows, never replacing them.
- Run a **sandbox-credentialed smoke** against the *real* third parties the system depends on (Vapi, the LLM provider, calendar, mail) on a schedule, not on every flow. It exercises the live contract shallowly — auth handshakes, request/response shape, a trivial round-trip — enough to catch a shipped breaking change before the mocks hide it.
- **Strictly non-prod, read-only-first.** Use sandbox/test credentials and sandbox endpoints only; never prod keys, never prod tenants. Prefer read/echo calls; any unavoidable write targets a seeded sandbox and tears down (§2). Confirm each credential resolves NON-PROD before the call, or `status:error` (§1).
- Keep it cheap and bounded — cheap models, low `maxTurns`, back off on 429 (§5). A smoke is a contract canary, not a load test.
- A smoke **failure is a provider-drift signal**, not a SUT defect: report it as such (which provider, which field/behavior changed) so the mocked fixtures can be re-grounded against the new contract.

### Watch (do not gate)
- **EMERGING — sink/provider parity drift:** a test-double sink or sandbox tenant can lag the real provider's rendering/validation (e.g. spam-scoring, link rewriting, or carrier SMS segmentation a sink doesn't model). Note any divergence as an observation; do not fail a flow on sink-vs-prod parity until the §8 smoke confirms a genuine real-provider change.
