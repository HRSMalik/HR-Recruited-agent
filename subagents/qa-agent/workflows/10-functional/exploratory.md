# exploratory

**Category:** 10-functional
**Runs as:** subagent: ../.claude/agents/exploratory-tester.md
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Charter/session-based autonomous bug hunting (ISTQB *exploratory testing*; Bach's session-based test management): simultaneously learn the app, design tests, and execute them within a time-boxed charter — finding anomalies no scripted case anticipated. Answers — "what's broken that nobody wrote a test for?"

## Inputs & preconditions
- Required artifacts: a **charter** — a one-line mission scoping the session (e.g. "explore the application-submission flow for input-handling and state anomalies"). No detailed scripts.
- Target: base URL / API (or app URL) + auth via env; build/commit recorded.
- Preconditions: smoke passed (the surface is explorable); a **time-box / turn budget** is set; read-only against a non-prod build (mutations only against a seeded sandbox if the charter requires them).

## Oracle (source of truth)
Heuristic and consistency oracles, not a single spec: HICCUPPS-style consistency (with History, the Image/brand, Comparable products, Claims/docs, User expectations, the Product itself, Purpose, Statutes). Because there is no scripted oracle, each finding **states the heuristic it violates and lowers confidence accordingly** (per the template: if you can only check against the SUT's own behavior, say so).

## Step sequence (Plan → Act → Verify)
1. **Plan** — read the charter; pick an exploration path and a few heuristics to apply (boundary, sequence/state, CRUD round-trip, "follow the data"). Keep a running session log of what you try.
2. **Act** — navigate the app/API freely within the charter and time-box; vary inputs and order; chase anything surprising (odd status, inconsistent state, ugly error, slow path). Skip-and-continue; log every observation, not just failures.
3. **Verify** — for each anomaly, name the oracle/heuristic it breaks, reproduce it deterministically (minimize the steps), and capture evidence; discard ones you cannot reproduce.

## Assertions & exit gate
- Reproducible anomalies are logged as findings with minimized repro steps + the heuristic violated.
- The session log records coverage (areas touched) and any areas left unexplored (for the next session).
- **Gate:** `session_completed_in_timebox` — pass = the charter was explored within the time-box and findings logged. Exploratory does **not** block the release gate on its own; its findings feed triage and may *seed* new scripted cases. High-severity reproducible findings still escalate to the orchestrator's critic.

## Output
Write `artifacts/exploratory/report.json` per `shared/report-format.md`, plus the session log in `notes`:
`{ flow:"exploratory", status, summary{...}, findings[], gate{name:"session_completed_in_timebox",passed} }`.
Findings per `shared/finding-schema.md`; `oracle` = the named heuristic; confidence is explicit because the oracle is heuristic; evidence = minimized repro + response/console output.

## Guardrails
Per `shared/guardrails.md`: read-only on live; any mutating exploration only against a seeded sandbox (recorded seed, torn down); no real outbound side-effects (emails/SMS/charges); secrets via env; strict time-box via `maxTurns: 25` and back off on `429`. Run as an isolated subagent so the free-roaming context does not leak into the orchestrator.
