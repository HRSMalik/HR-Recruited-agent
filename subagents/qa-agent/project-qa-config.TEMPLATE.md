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

## Test data & oracles
- **Grounded oracles** (spec/contract/schema/SLOs/requirements docs) — never the SUT's own echoed output. How to seed test data (which endpoints/fixtures). Known drift/quirks to watch (status casing, env-var name mismatches, dev-only logging).

## CI gates & budgets
- The PR gate (which flows, time budget). NFR/performance targets. a11y target. The hard oracles (e.g. zero console errors on UI flows). Verification conventions specific to the app.

## Scope (in / out)
- Which flows are in scope vs deferred (e.g. AI/LLM flows if the agent layer is parked; mock-only domains not yet backend-wired). Per-PR vs nightly split.

## Locked rules
- Non-destructive on shared/live targets; mutating flows only against a confirmed sandbox. Grounded oracles only. Agent sets severity; proposes priority, leaves the final P-level to a human.
