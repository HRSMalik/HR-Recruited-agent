# Workflow Template

Every flow in `workflows/` follows this shape. Keep flows single-responsibility, Plan → Act → Verify, with a **grounded oracle** and a **deterministic exit gate**.

```markdown
# <flow-name>

**Category:** <00-lifecycle | 10-functional | 20-interface-data | 30-non-functional | 40-ux-compliance | 50-automation-platform>
**Runs as:** <inline flow | subagent: ../.claude/agents/<name>.md>
**Default model:** <haiku | sonnet | opus>   ·   **Mode:** <read-only | seeded-sandbox | mutating-sandbox>

## Purpose
One or two lines: the QA responsibility this flow owns and the question it answers.

## Inputs & preconditions
- Required artifacts: <spec / baseline / SLOs / requirements / charter>.
- Target: base URL / host / connection string, auth, environment.
- Preconditions to assert before acting (env reachable, NON-PROD host, seeded data present).

## Oracle (source of truth)
Where "correct" is defined — OpenAPI spec / golden baseline / SLO thresholds / requirement IDs / WCAG criteria. NEVER the SUT's own output.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate cases (happy / edge / error / negative); scope to the change surface when given.
2. **Act** — execute one case at a time via the flow's tools; skip-and-continue on a single item's failure.
3. **Verify** — assert each result against the oracle; capture evidence for every failure.

## Assertions & exit gate
- Concrete, checkable assertions (status codes, schema, thresholds, transitions…).
- **Gate:** the single pass/fail condition (e.g. "0 schema violations", "p95 ≤ SLO", "no high/critical findings").

## Output
Write `artifacts/<flow>/report.json` per `shared/report-format.md`:
`{ flow, status, summary{total,passed,failed,skipped}, findings[], gate{name,passed} }`.
Each finding follows `shared/finding-schema.md`.

## Guardrails
Per `shared/guardrails.md`: non-destructive on live systems; seeded/golden DB only for mutations; secrets via env; respect rate limits; cap turns.
```

**Authoring rules**
- One responsibility per flow — if it does two things, split it.
- The oracle is external. If you can only check against the SUT's own response, say so explicitly and lower confidence.
- Make failure output actionable enough for a developer to fix without re-running.
