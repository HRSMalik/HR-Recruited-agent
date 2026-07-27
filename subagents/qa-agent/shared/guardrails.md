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
- **Never drive a fixture into a state that makes it UNDELETABLE.** A product that archives records —
  claim `Closed`, invoice `Paid`, case `Locked` — is *correct* to refuse deletion afterwards, so a flow
  that reaches that state has created **permanent residue** in a shared environment. It cannot be torn
  down without a direct DB write, which QA is forbidden from doing, and the next run then reads the
  extra row as unexplained drift.
  - The rule is about the **transition**, not the assertion: a flow may freely *submit* for closure,
    *request* a lock, or *attempt* a terminal action and assert the response. What it must not do is
    **complete** the transition on a fixture it intends to delete.
  - If a terminal state genuinely must be exercised, do it deliberately: **accept the permanent +1**,
    say so in the report, and name the record so the next run's baseline is explained rather than
    surprising.
  - ⚠️ **Never "fix" the archive guard to make teardown easier.** Read-only-after-terminal is a real
    product requirement; loosening it to serve test convenience trades a correctness guarantee for a
    cleanup shortcut. Work around it in the fixture, never in the product.
  - Corollary for teardown order: deletion often requires a record to be *inactive* first. Sequence
    teardown (deactivate → delete) and **assert each step's status code** — a teardown that reports
    success because nobody checked the response is how residue accumulates unnoticed.

## 3. External side-effects
- Do NOT trigger real-world side effects in tests: outbound calls/emails/SMS, third-party charges, calendar/event creation, social posts. Mock them or target sandbox credentials.
- Flows that would cause a side effect mark it **NOT RUN** with a note on how it would be tested in a sandbox.
- **⛔ This applies to endpoints that send mail INCIDENTALLY, in flows that are not about mail.** The observed failure was a *security-regression* flow calling `POST /auth/forgot-password` purely to prove "the route still responds, not 500" — a reasonable-looking regression check that is also a live send. Before calling **any** endpoint that may emit mail/SMS (password reset, invite, resend-invite, share-link, notification triggers), either point it at a §7 sink or treat it as a side-effect gate.
- **A shared relay makes the blast radius bigger than your own run.** Where outbound goes through a shared corporate relay, bounces are commonly rate-limited to a threshold that suspends **all** outbound for everyone (e.g. 5 bounces/hr → 60-minute block). So a **plausible-but-fake recipient is the worst option available**: it is guaranteed to bounce, it disables mail for every other session and environment, and it proves nothing the sink would not have proven. Send only to a **known-real mailbox** you control, or to a **known-nonexistent account** on a route that provably short-circuits before sending; never to an address invented to look real.
- **Do not treat "the env probably has mail disabled" as a safeguard.** That is luck, not a control, and it silently stops being true the moment ops provisions credentials. Assert the outbound config resolves to a sink/disabled state *before* sending (§7), or don't send.

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

## 9. No unreproduced findings — validate before you file
A filed defect that isn't real is as costly as a missed one: it burns a build session's audit, gets logged/triaged, and erodes trust in the whole report. Before ANY finding is filed (not `observation`), the tester MUST:
- **Independently reproduce it deterministically** against the real target — the same environment/account/role/fixture, minimized steps, captured evidence. An anomaly you cannot reproduce is **discarded or downgraded to `observation`**, never filed as a defect (mirrors `workflows/10-functional/exploratory.md`).
- **Confirm the thing it names actually EXISTS and you used the REAL shape.** Check the live contract, not an assumed one: does the endpoint/method exist (live OpenAPI / a real call — a 404/405 means there is no such route), and are the field/key names the ones the real store/schema uses (not guessed camelCase/snake_case)? A "defect" produced by probing a route that doesn't exist, or by sending keys the app never reads, is a **false defect** — the tester's own artifact, not a SUT bug (see `field-defect-patterns.md` → false-defect pattern).
- **⛔ If your harness CONSTRUCTS state the app normally constructs, construct it the way the APP does — or you are testing your own harness.** Forged auth/session/tenant/feature-flag state is the classic case: writing a raw API payload straight into the app's session storage skips the app's own normalisation layer (role-vocabulary mapping, derived tenant fields, schema version), which **silently disables every branch that reads the normalised value**. The harness then observes the feature "not working" and files a product bug that cannot be reproduced through the UI. Before filing anything about a role-gated, tenant-gated, or flag-gated behaviour:
  - **Find the app's own builder** (the login/impersonation path) and use it, or replicate its transform exactly — then say in the finding which you did.
  - **Prefer driving the real UI control** ("Login As", a role switcher) over hand-writing storage; a forged session is a last resort, not the default.
  - **Run the inverse control:** reproduce the failure with the forged state AND show it disappearing with app-built state. If the behaviour tracks *how you built the session* rather than *what the code does*, the finding is a harness artifact — discard it and fix the harness.
  - **A dispatch prompt that hands flows a state-forging recipe is a defect source.** Whoever writes the brief owns any false finding it manufactures; audit the recipe against the app's builder before shipping it to N parallel flows, because they will all inherit the same error and their agreement will look like corroboration.
- **State the validity verdict in the finding**: reproduced (with the exact repro) — or it doesn't get filed.
- **Enforcement:** the orchestrator's critic REJECTS any finding lacking a deterministic repro or naming an endpoint/field it did not confirm exists; such items are dropped or re-labeled `observation`. This is the QA-side of the controller's **audit-first** rule: validate the defect is real before reporting it, exactly as the controller validates a request is real before building.
