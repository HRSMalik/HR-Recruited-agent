# Reliability — Self-Healing, Retry, Diffing, Error-Safety

Binding on every run. Design verification drives a live browser (flaky by nature), so these keep a run
trustworthy and resilient. Pairs with `guardrails.md` (safety) and `run-budget.md` (cost).

## 1. Retry-before-fail -> FLAKY (browser/screenshot oracles)
Before recording a hard-oracle **FAIL** that could be a render/timing blip (a screenshot mismatch, a
transient console error, a slow-mount overflow), re-run the check **once**.
- Passes on retry ⇒ record **FLAKY** with detail, not FAIL.
- Fails again ⇒ FAIL with the screenshot + the exact oracle output (axe rule, contrast ratio, overflow
  box) as evidence.
Deterministic oracles (contrast ratio, axe rule id, token linter) rarely flake - a repeat FAIL there is
real; a screenshot-diff or console FAIL is the one that warrants the retry.

## 2. App-login self-healing (bounded)
For authed screens, on **~3 consecutive auth/redirect-to-login failures** during a screenshot run,
attempt **exactly one** re-login from the config creds. If it still fails, **stop that flow clean**
(`status:error`, "auth rejected") instead of screenshotting a wall of login pages. Never loop re-login.

## 3. Run-over-run diffing (read prior artifacts - never write memory)
Compare this run's findings against the **previous run's artifacts** for the same app and classify each
as **NEW**, **PERSISTING** (already known), or **FIXED** (was failing, now green). The report leads with
NEW and FIXED and collapses PERSISTING. No baseline ⇒ everything NEW, note "first run." Diffing reads
prior `artifacts/` only; durable learnings go in the RETURNED REPORT for the controller to curate - the
design-agent never writes project memory.

## 4. Error-safe reporting (a run never ends with nothing)
A verify pass that throws mid-run still emits `summary.json` with whatever screenshots/oracle results
were captured, marked partial. Partial is reported as partial - never dropped, never inflated to a pass.

## 5. Deterministic-first oracles
Gate on the **deterministic hard oracles** first - contrast checker, axe-core, zero console errors, no
viewport overflow, token conformance, logic-unchanged diff - and quote their exact output. The rubric
(craft) score is **soft/advisory only**, applied after hard oracles are green; never let taste flip a
deterministic failure, and never gate on taste alone. (Position bias is already handled: `design-judge`
scores twice and swaps order.)

## 6. Environment learnings -> the report, not memory
Durable facts (a consistently flaky screen, a known-benign console message to allowlist, an auth quirk)
go in a **"Known / environment learnings"** section of the RETURNED REPORT. The controller curates
memory; the agent proposes, never persists.
