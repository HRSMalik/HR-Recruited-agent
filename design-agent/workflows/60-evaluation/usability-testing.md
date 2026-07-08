# usability-testing

**Group:** 60-evaluation
**Runs as:** subagent: ../.claude/agents/design-reviewer.md
**Mode:** audit / plan (read-only)   ·   **Default model:** sonnet

## Purpose
Own the usability-test plan: match method (qual vs quant, moderated vs unmoderated) to the research goal and author realistic, success-criteria'd tasks against the live screen — it plans and grounds tests, it does not run live participants.

## Inputs & preconditions
- From `project-design-config.md`: dev-server URL/port + creds, breakpoints, the primary user flows/personas, component library.
- Target flow(s) + the research question (discover problems vs. measure a rate); usability-research methodology as the rule set.
- Preconditions: dev server reachable; the target flow walkable to write realistic tasks; reviewer read-only.

## Oracle (source of truth)
Established usability-research methodology (NN/g) — sample-size & method-fit evidence.
- **hard:** each authored task is realistic, has a defined start state + measurable success criterion, and the chosen method actually fits the goal (qual for problems, quant for rates).
- **soft:** task wording is non-leading; coverage spans the critical-path flow; round size is justified.

## Standards & techniques
- **Qual vs quant:** ~5 users surface ~75–85% of problems in many small rounds (qual, find problems); ~40+ users needed for stable metrics (quant, measure rates).
- **Moderated vs unmoderated:** moderated = deep, probing, low N; unmoderated = scale, more participants, shallower signal — pick by goal.
- **Realistic tasks:** scenario-framed, non-leading, with a start state and a binary success criterion; never "click the blue button."
- **Method matched to goal:** the plan states the research question first, then derives method + N + moderation from it.

## Step sequence
- **audit/plan:** State the research question → choose qual/quant + moderated/unmoderated + N with the method-fit rationale → walk the live flow at the project's viewports → author realistic tasks with start states + success criteria → emit the plan as findings/notes (read-only, no edits).
- **build:** not applicable — this flow produces a test plan, not app changes.

## Assertions & exit gate
- Method (qual/quant, moderated/unmoderated) + N are justified against the stated research goal.
- Every task is realistic, non-leading, with a start state and a measurable success criterion.
- **Gate:** audit/plan-only — passes when the plan covers the critical-path flow with method-fit rationale and grounded tasks.

## Output
Write `artifacts/usability-testing/report.json` per `shared/report-format.md` (`mode: audit`) — the plan as findings/notes per `finding-schema.md` (`type: heuristic`, `heuristic: NN/g usability methodology`), plus screenshots of the walked flow + viewports in the verification block. Never edits the app.

## Guardrails
Per `shared/guardrails.md`: read-only — plans and grounds tests, makes no edits and runs no live participants. Tasks are grounded in the actual rendered flow (screenshot-verified), not imagined. Method follows the goal, never the reverse.
