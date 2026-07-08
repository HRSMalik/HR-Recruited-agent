# smoke

**Category:** 10-functional
**Runs as:** subagent: ../.claude/agents/smoke-tester.md
**Default model:** haiku   ·   **Mode:** read-only

## Purpose
Broad, shallow build-verification (ISTQB *smoke testing*): confirm the SUT is up and every core path is alive before any deeper flow runs. Answers one question — "is this build worth testing further?"

## Inputs & preconditions
- Required artifacts: list of critical paths (health endpoint, key business endpoints, critical user journey). Falls back to `GET /health` + the OpenAPI's primary GET routes if no list is given.
- Target: base URL + auth (read token / API key via env), environment id.
- Preconditions: target host reachable (DNS + TCP); environment is the intended one; declares `disallowedTools: Edit, Write` and issues no mutating verbs.

## Oracle (source of truth)
The pre-declared critical-path list and their expected liveness signals (health contract says `200` + `{"status":"ok"}`; key endpoints documented to return `2xx`). NOT the SUT's own output for *what* is correct — only *that* it responds.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate critical paths only: liveness/health, auth issuance, 3–6 key endpoints, one critical journey reachable (e.g. login → list candidates → open job). No edge or error cases — that is smoke's whole point: wide and shallow. **For a project with a frontend, also list the key UI routes to drive in a real browser** (e.g. login → dashboard → the 3–6 primary screens).
2. **Act** — one shallow GET per path; `curl -s -o /dev/null -w "%{http_code} %{time_total}"`. Skip-and-continue; never retry-storm. Cap at `maxTurns: 12`. **UI smoke (frontend projects):** drive the app **headless** with the project's browser-automation runner (see `project-qa-config.md` — base URL, screenshot login creds, browser binary), visit each key route, and capture **console errors, page errors, and failed `/api/*` requests** per route.
3. **Verify** — assert each path is alive against the oracle; on the first dead critical path, mark the build blocked but finish probing the rest for a complete picture. For the UI smoke, a route with any console/page error or failed API request is a finding (the oracle = **zero** errors per route).

## Assertions & exit gate
- Health endpoint returns `200` and the documented liveness body.
- App boots: no path returns `5xx`, connection-refused, or timeout (> 5s).
- Auth path mints a token; the critical journey's entry endpoint returns `2xx`.
- **(UI smoke)** every key route renders with **zero** console/page errors and no failed `/api/*` request (hard oracle).
- **Gate:** `all_critical_paths_up` — pass only if every critical path is alive. Any dead path → `fail` (and the orchestrator stops the pipeline before regression).

## Output
Write `artifacts/smoke/report.json` per `shared/report-format.md`:
`{ flow:"smoke", status, summary{total,passed,failed,skipped}, findings[], gate{name:"all_critical_paths_up",passed} }`.
Each finding follows `shared/finding-schema.md`; a dead core path is **blocker** severity (testing cannot proceed), evidence = the exact `curl` line + status/latency.

**If a UI smoke ran, persist the runnable driver script** into the project's test-scripts dir (`tests/` per `project-qa-config.md`, e.g. `tests/smoke_<feature>.mjs`) — the reproducible script analog of `test-cases.md` (see `shared/report-format.md` → "Re-runnable smoke/e2e scripts"). Write it via Bash (Write is disallowed for this read-only flow); **never** under `frontend/`/`backend/`.

## Pipeline position
Runs **first**, before regression and all deeper flows. A failed smoke gate short-circuits the sweep — no point regression-testing a build that will not boot.

## Guardrails
Per `shared/guardrails.md`: read-only on the live target; GET-only, no writes/side-effects; secrets via env (never logged/redacted in report); back off on `429`; `maxTurns: 12`. If the host looks like production, still safe (read-only) — proceed but note the environment.
