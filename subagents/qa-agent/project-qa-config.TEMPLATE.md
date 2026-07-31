# Project QA Config — TEMPLATE

> **Generic structure only — fill per project (or let the orchestrator fill it).** When the qa-agent
> is dropped into a project, the `qa-orchestrator` **auto-creates** the real `project-qa-config.md` (no
> `.TEMPLATE` suffix) by scanning that project's codebase. This file is just the **section structure +
> what each section holds** — do NOT hardcode one project's URLs/creds/stack here. The generic QA
> craft + contracts live in `shared/`.

## System under test (SUT)
- The deployable surfaces: frontend (URL/port + start command), backend/API (URL/port + start command), database (connection string + name + key collections/tables), any queues/external services. Health endpoint(s) + the expected healthy response. Environments (local/dev/stage) and which are safe to mutate.

## Test credentials & auth
- Screenshot/API login (user + password), the auth flow (e.g. login → MFA → token), and any MFA/dev shortcuts. RBAC roles + scoping. Note any FE↔BE naming mismatches that contract/role tests must account for.

## Stack & test tooling
- Frontend + backend frameworks, state layer, and what's wired vs mock. Browser automation tool (e.g. puppeteer-core / Playwright) + how to run it. Ticketing integration. Unit-test convention (pytest / data-driven harness / etc.).
- **Test-scripts dir** — where e2e/smoke driver scripts are persisted and re-run from (default: a root **`tests/`** dir; never inside `frontend/`/`backend/`, which sync to deployment). The smoke/e2e flows write their runnable script here (the script analog of `test-cases.md` — see `shared/report-format.md`). Record the dir, the runner command, and the screenshot login creds.

## Business rule → mechanism map (load this BEFORE writing any tenancy/RBAC/state-machine fixture)

> **Why this section exists:** a project's business-rules doc (e.g. `project-understanding.md` §
> Key Business Rules) describes the *effect* of a rule ("staff can only act on their own tenant's
> records"). It is frequently silent on the *mechanism* — which field is checked, what sets that
> field, and non-obvious dependencies (a marker stamped by WHO performed an action, not by the
> target's role name). An agent that builds a fixture from the rule's prose alone can construct
> actors that are subtly the wrong shape, and discovers this only by a live request failing —
> burning a real drive + a real write against the SUT to learn something a `grep` would have
> caught. **This section is where that grep already happened, once, at bootstrap** — for every
> rule risk-worthy enough to earn adversarial depth (tenancy, RBAC, ownership, approval chains,
> state machines). Every flow reads it FIRST, before recon, before writing any fixture.

**Bootstrap/refresh procedure (the orchestrator does this, not each flow):**
1. Read the project's business-rules doc (`project-understanding.md` § Key Business Rules, or
   equivalent) and its journey/workflow sections. For each rule that gates authorization, tenancy,
   ownership, or a multi-step state machine, locate the **exact function/field/route** that
   enforces it in source (grep the guard, not the doc).
2. Record it as a row: **Rule (plain language) → Mechanism (file:function/field) → Gotcha (the
   non-obvious part a paraphrase would miss, if any).**
3. **Refresh, don't regenerate wholesale, on every run.** Diff the business-rules doc's own
   "last updated"/section dates against this map's own stamp; re-derive only the rows whose
   source rule changed. A map that silently goes stale is worse than none — it reads as
   authoritative when it is not.
4. If the project has no business-rules doc, or a rule has no locatable single mechanism (spread
   across multiple checks, or genuinely just a convention), say so in the row rather than
   omitting it — an explicit "no single mechanism, see call sites X/Y/Z" is more useful than a gap.

**Table (fill per project):**

| Rule (plain language) | Mechanism (file:function/field) | Gotcha |
| --- | --- | --- |
| _e.g. "staff can only act on their own tenant's records"_ | _e.g. a `tenant_id`/`org_id` field read by a shared scoping check_ | _e.g. the field is set from WHO created the record's actor (the tenant's own admin vs a platform-level admin), not from the actor's role name alone — two actors with the identical role can carry different tenant ids depending on who created them_ |

## Test data & oracles
- **Grounded oracles** (spec/contract/schema/SLOs/requirements docs) — never the SUT's own echoed output. How to seed test data (which endpoints/fixtures). Known drift/quirks to watch (status casing, env-var name mismatches, dev-only logging).

## CI gates & budgets
- The PR gate (which flows, time budget). NFR/performance targets. a11y target. The hard oracles (e.g. zero console errors on UI flows). Verification conventions specific to the app.
- **Run budget (`shared/run-budget.md`).** Per-tier ceilings for this project: fan-out cap (max concurrent flows), per-flow turn cap, and wall-clock target for smoke / PR-gate / full-sweep / deep-audit. Note any project cost sensitivity (e.g. a metered third-party in the path) that should tighten the defaults, and confirm the one-heavy-run-at-a-time rule.
- **Reliability (`shared/reliability.md`).** Where prior-run artifacts live for **run-over-run diffing** (the `artifacts/` / reports history path). Which auth identities can **re-auth** (login/oauth2) vs are static (api_key/bearer/cookie, stop-clean on repeated 401/403). Any known-flaky endpoints to retry-before-fail.

## Scope (in / out)
- Which flows are in scope vs deferred (e.g. AI/LLM flows if the agent layer is parked; mock-only domains not yet backend-wired). Per-PR vs nightly split.

## Locked rules
- Non-destructive on shared/live targets; mutating flows only against a confirmed sandbox. Grounded oracles only. Agent sets severity; proposes priority, leaves the final P-level to a human.
