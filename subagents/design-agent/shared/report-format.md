# Report Format

A structured JSON every flow writes, plus an orchestrator roll-up. Audits emit findings; build flows emit findings + a verification result.

## Per-flow report — `artifacts/<flow>/report.json`

```json
{
  "flow": "data-table-design",
  "mode": "audit | build",
  "status": "pass | fail | error",
  "screen": "claims/list",
  "started_at": "ISO-8601",
  "ended_at": "ISO-8601",
  "summary": { "findings": 4, "critical": 0, "major": 1, "minor": 2, "cosmetic": 1 },
  "findings": [ /* finding objects — see finding-schema.md */ ],
  "verification": {
    "screenshots": ["screenshots/claims-list-1440.png", "...-900.png"],
    "viewports": ["1440x900", "1280x800", "900x800"],
    "hard_oracles": { "contrast": "pass", "axe": "pass", "console_errors": 0, "overflow": "pass", "tokens": "pass", "logic_unchanged": true },
    "rubric_score": 0.86
  },
  "gate": { "name": "hard_oracles_green_and_rubric>=0.8", "passed": true },
  "notes": ["assumptions, anything deferred and why"]
}
```

- `mode: audit` → read-only, `verification` may be just screenshots + hard-oracle reads, no writes.
- `mode: build` → went through the writer + the verify loop; `rubric_score` from the evaluator.
- `status: error` ≠ `fail`: `error` = the flow couldn't run (dev server down, screen not found).

## Orchestrator roll-up — `artifacts/summary.json`

```json
{
  "run_id": "<id>",
  "mandate": "<what was asked>",
  "flows": [ { "flow": "...", "mode": "...", "status": "...", "gate_passed": true } ],
  "findings_by_severity": { "critical": 0, "major": 1, "minor": 3, "cosmetic": 2 },
  "findings_by_status": { "new": 1, "persisting": 2, "fixed": 1 },
  "hard_oracles": "all green | <which failed>",
  "budget": {
    "tier": "feels-off-screen",
    "agents_dispatched": 5,
    "verify_iterations": 4,
    "wall_clock_min": 18,
    "caps": { "per_agent_turns": 20, "verify_loop": 15, "wall_clock_target_min": 25 },
    "cap_hit": false,
    "coverage": "complete | partial (which screens/breakpoints were cut and why)"
  },
  "gate": { "passed": true, "reason": "all hard oracles green; mean rubric 0.86" }
}
```
- **`budget`** — required on every run (`shared/run-budget.md` §5). A run that hit a cap reports `coverage: partial` with what was cut, never silently presented as complete.
- **`findings_by_status`** — required when prior-run artifacts exist (`shared/reliability.md` §3, run-over-run diffing); omit only on a genuine first run ("no baseline").

## Conventions
- Every screenshot path records its **viewport** in the filename.
- A build flow that didn't pass the verify loop is `status: fail` with the failing hard oracle named.
- The orchestrator gate fails on: any failed flow gate, any open `hard` finding, or any build flow whose `logic_unchanged` is false.
