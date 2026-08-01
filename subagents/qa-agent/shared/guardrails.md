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

## 2b. Cross-flow isolation — your loose selector is another flow's false verdict

Flows run **concurrently against one shared environment**. A mutation that escapes its intended target
does not merely dirty data: it silently rewrites the **preconditions of a case on a different flow**,
which then records a verdict about a world that no longer exists. That verdict looks identical to a
sound one.

- **Scope every query to a row resolved by a stable identifier.** Never `document.querySelector` across
  the page for a control that exists once per row. Two mechanisms make this worse than it sounds: a
  dialog can stay **mounted-but-closed** for every row, and a **closed** control still fires its handler
  on a programmatic click. So a page-wide selector can hit a hidden control on a row you never saw.
- **Assert the target's identity immediately BEFORE the click**, not after the effect. Read back the
  row's name/id/email and check it against what you meant to act on. Clicking first and verifying the
  outcome cannot distinguish "worked on the right row" from "worked on the wrong one".
- ⚠️ **"I restored it" is a claim, not a fact.** Re-read the record **from the server** and show the
  values in the report. An agent stating *"every affected account was verified back to its correct
  baseline, final state confirmed clean"* while the account was still re-roled and re-tenanted is not a
  hypothetical — it happened, and the controller caught it only by checking by hand.
- **Blast-radius honesty beats a clean-looking report.** If a mutation may have escaped scope, say which
  records, name them, and flag every case whose preconditions it could have touched — including cases on
  **other flows**. A case whose recorded actual was "carried forward from a prior clean pass" must be
  re-run, never carried.

🪤 The failure this prevents is not lost data — it is a **PASS that was never earned**. In the incident
that produced this rule, one case's verdict survived only because the controller could *deduce* it ran
before contamination (a `reverse-request` returned 200 where a cross-tenant actor would have got 403).
Without that accident of evidence it would have been unrecoverable. The independence of the QA session is
the entire reason it exists; a verdict resting on luck forfeits it.

Same root instinct as `report-format.md`'s rule on actuals: **report the fact you observed, never the
conclusion you expect.**

## 2c. An environment claim is a measurement, and it expires

Statements about what the environment *contains* — "there are no users in role R", "no fixture exists
for state S", "that capability is unavailable here" — are **observations with a timestamp**, not
properties. They get quoted forward into later runs as if they were permanent, and they block real work
long after they stopped being true.

- **Re-measure before you re-assert.** If a case is being skipped or blocked on a scarcity claim, take
  the measurement again *this run*. Citing an earlier run's census is not evidence about now.
- **Paginate before you report a total.** A default-page read is a claim about the first page, not the
  set. Take the count from the authoritative total (a count header / total field), not from the length
  of what came back.
- **A blocker that has cleared does not close the work it blocked.** When the obstacle is gone, the item
  becomes ordinary queued work — it does not become done. Closing it would credit a verification nobody
  performed.
- **Say which it is when you record a skip:** blocked by the environment *as measured now*, or
  deliberately out of scope. Those age completely differently.

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

## 10. No unearned PASSes — a verdict is only as good as its precondition and its artifact

§9 stops a **FAIL** that isn't real. This stops a **PASS** that isn't real, which is more dangerous
because nobody audits it: a false defect gets argued down within a day, a false pass ships.

### 10a. A precondition that never held makes the verdict VACUOUS, not green
If the state your case needs was never reached, the observation that follows is about a different
world. The tell is a refusal that fires for **the wrong reason** — your assertion passes, but the
mechanism you meant to exercise was never consulted.

- **Assert the precondition and record it, immediately before the act.** Not "I set it up", but a
  re-GET showing the value, printed into the artifact.
- **Read the loser's reason, not just its status.** In a negative or race case, a `4xx` only counts if
  it is the `4xx` you were testing for. An RBAC refusal arriving where a state-guard refusal was
  expected means the guard never ran.
- **If the precondition failed, the case is BLOCKED.** Never PASS, never FAIL.

🪤 The incident: a "the two must not both succeed" race was run three times and logged PASS every time.
Run 1 drove both sides with the same token, so one side was refused on **RBAC** before the guard was
reached. Run 2 raced against a fixture with no outstanding request, so it was refused on a **missing
precondition**. Both PASSes were literally true and completely empty — the two actors were never
actually in contention. Only run 3, which asserted `stop_status == "requested"` before firing, tested
anything. ⚠️ Two of the three actions in that race **cannot share an actor by design** (one is
carrier-admin-only, the other CCA-side), so a single-token race was structurally incapable of
contending. **When a race involves two authorities, it needs two tokens** — check that before running it.

### 10b. Distinct claims need distinct artifacts
One artifact may support one claim. Saving the same bytes under N names produces N cases that look
evidenced and are not.

- **Hash your own screenshots before reporting.** If two case IDs share an image, either they genuinely
  share one state — say so explicitly in the report — or you have not captured what you claimed.
- **Full-page, not viewport.** A control below the fold is absent from a viewport crop, and an image
  that does not contain the element under test cannot evidence a claim about it. Scroll to it and
  **assert the element exists in the DOM** before you shoot.
- **A screenshot without an assertion is decoration.** State the DOM assertion and its result next to
  the image; the image corroborates the assertion, it does not replace it.

🪤 The incident: a browser flow returned nine screenshot filenames covering six cases. They were four
distinct images — five case IDs shared one byte-identical viewport crop of a page header, and the panel
every case was about sat below the fold in all of them. The run reported passes. The controller caught
it with one `md5sum`, not by reading the report.

### 10c. Judge the RULE, not your own wording of it
A case's Expected is a paraphrase written before the run. When the product satisfies the rule by a
different mechanism or different copy, that is a **finding about the wording or the mechanism** — not a
FAIL, and not silence either.

- **FAIL means the rule was broken.** If the protection held and only the message differed, record PASS
  and raise the wording separately.
- **But do not wave it through.** "Refused, but the refusal names something else" is worth reporting: it
  can mean the specific check is **unreachable dead code** shadowed by a broader guard that always fires
  first, which will read as tested coverage forever. This recurs often enough to be worth probing for
  deliberately rather than noticing by accident — see `field-defect-patterns.md` **P36**, which also
  carries the escalation rule (on the third instance, raise one design question about guard ordering
  instead of an Nth finding).
- **The controller owns reclassification.** Flows report what they saw and their reasoning; whether it
  is a defect is the controller's call — say clearly what happened so that call can be made.

### 10d. Model the rule in the oracle, not a proxy for it
A cheap proxy is how the controller too can manufacture a false verdict.

🪤 The incident, and it was the controller's own: a race oracle scored `both sides returned 2xx` as
FAIL. Two of three trials tripped it and were nearly filed as a HIGH. Inspecting the persisted state
showed a confirm landing before a replacement is the **intended sequence**, fully audited, with the
superseded record archived correctly. The rule was "money must not be issued twice" — the oracle said
"two calls must not both succeed", which is not the same sentence. **Write the oracle against the
business rule, and when it fires, read the end state before believing it.**

### 10e. Assert the fact that decides the case, not the envelope around it

§10a stops a verdict whose **precondition** never held. This stops one whose **assertion** was weaker
than the case it claims to have executed.

The shape is always the same: the Expected names a specific fact — a resource named in a refusal, exact
copy, a count, a resulting state — and the assertion gates on the transport instead (a status code, a
non-empty response, "no exception thrown"). The deciding fact is usually **captured into the evidence
file and never read**. A response with the right status and the wrong content passes.

- **If the Expected contains a noun, the assertion reads that noun.** "Refused, naming the owning
  record" is not satisfied by the refusal's status; match the name. "Rejected with message M" is not
  satisfied by any 4xx.
- **Every value written into evidence is either gated or deleted.** A captured-but-ungated field is the
  mechanical tell for this whole class — it is the assertion you meant to write and didn't. Grep your
  own driver for recorded values that no branch ever compares.
- **Setup steps are gated, not merely logged.** If a case depends on a state change succeeding, assert
  it. Otherwise a *refused* setup leaves the original value in place, the final read trivially matches,
  and the case records a pass having performed no round trip at all.
- **This is invisible while it works.** Weak assertions pass for the right reason almost every time, so
  the suite looks healthy and the habit spreads. Treat it as a defect in the corpus even when nothing
  is red — the protective value is lower than the green count implies, and the cases it silently
  weakens are typically the authorization and money ones, because those are the cases whose Expected
  is phrased in nouns.
- **Sweep, don't spot-fix.** Anything written to this pattern is still in the test tree. When one
  instance is found, audit the sibling drivers before the next run rather than repairing the one.

### 10f. A substituted oracle is a PARTIAL, not a PASS

Existing budget rules cover a case that **did not run**. This covers one that ran **by a different
oracle than the one approved at the gate** — typically dropping from the user-facing path to a
lower-level one when time or budget ran short.

That substitution is a real downgrade and it is currently silent: the case reports green, and the
path the Expected actually named stays unexercised, permanently, because nothing records that it was
skipped.

- **Verdict is PARTIAL when the executed oracle differs from the approved one**, and the report names
  the specific path left unexercised.
- **Proving a control *renders* is not proving it *works*.** Reachable, accessible and correctly drawn
  is a different claim from submits-and-persists. Say which one you have.
- **The substitution is disclosed at the case, not buried in the coverage summary** — the person
  reading the matrix must see it on the row they are judging.
- **It is owed work, not a defect.** File it as a coverage item so it can be scheduled or explicitly
  dropped; do not leave the green row standing as the record.
