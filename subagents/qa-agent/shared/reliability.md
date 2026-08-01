# Reliability — Self-Healing, Retry, Diffing, Error-Safety

Binding on every run. These are the hardening behaviors that keep a run trustworthy and resilient -
the robustness a hardened standalone QA agent bakes into code, expressed here as flow/orchestrator
behavior. They pair with `guardrails.md` (safety) and `run-budget.md` (cost).

## 1. Auth self-healing (bounded, never a loop)

A sustained run of 401/403 on an identity usually means an expired/refused token, not N real bugs.
- On **~3 consecutive auth failures** on an identity, attempt **exactly one** re-auth - but only for
  flows that can genuinely refresh (`login`, `oauth2_client_credentials`).
- For **static credentials** (`api_key`, `bearer`, `cookie`), a retry would just repeat the failure -
  so **stop that flow cleanly** with one clear explanation (`status:error`, "auth rejected, static
  credential") instead of emitting a wall of confused failures.
- Never loop re-auth. One attempt, then proceed or stop.

## 2. Retry-before-fail -> FLAKY

Before recording a **FAIL**, re-run the failing check **once** to rule out a transient error.
- Passes on retry ⇒ record **FLAKY** (not FAIL) with the detail (what failed, what passed).
- Fails again ⇒ record FAIL with full evidence.
This is distinct from the orchestrator's adversarial re-check of high-severity findings (a second,
independent skeptic) - this is the cheap transient-retry at the point of the check.

## 3. Run-over-run diffing (read prior artifacts - never write memory)

Each run compares its findings against the **previous run's artifacts** for the same SUT and classifies
every finding as **NEW**, **PERSISTING** (already known from the last run), or **FIXED** (was failing,
now passes). The report leads with NEW and FIXED and collapses PERSISTING to a reference, instead of
restating the same findings every run.
- Read the prior `artifacts/summary.json` / `report.json` (location from `project-qa-config.md`). If
  none exists, treat everything as NEW and note "first run, no baseline."
- **This agent still never writes to project memory** (see the orchestrator's memory rule). Diffing
  reads prior run artifacts only; durable learnings go in the RETURNED REPORT for the controller to
  curate, never into a memory file.

## 4. Error-safe reporting (a run never ends with nothing)

- A flow that throws mid-run still writes its `report.json` from whatever was recorded, marked
  `status:error` with the cause.
- The orchestrator still emits `summary.json` + `test-cases.md` from partial results even if some flows
  errored or a cap was hit. Partial evidence is reported as partial - never dropped, never inflated to a
  pass.

## 5. Deterministic-first oracles

Where a deterministic check exists, prefer it over LLM judgment and quote its exact output as evidence:
- schema/contract validation (e.g. OpenAPI response validation) over "looks right",
- regex/scanner checks (leaked secrets, tokens, stack traces) over eyeballing,
- exact-value assertions (the unique seeded value appears; the status is exactly 2xx).
Reserve LLM judgment for what a mechanical check genuinely cannot settle (behavior/edge interpretation,
UX craft). This makes findings reproducible and cheaper to verify.

## 6. Environment learnings -> the report, not memory

Durable environment facts worth carrying forward - an auth quirk, a consistently flaky endpoint, a
confirmed long-standing bug - go in a **"Known / environment learnings"** section of the RETURNED
REPORT. The controller decides what becomes durable project memory. The agent proposes; it does not
persist (design rule: the qa-agent has no memory access).
