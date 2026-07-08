# usability

**Category:** 40-ux-compliance
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Heuristic + task-based evaluation of ease-of-use: can a representative user complete core tasks efficiently, recover from errors, and understand the interface without training? Answers: "Is this usable, or merely functional?"

## Inputs & preconditions
- Required artifacts: the core task list (key user journeys, e.g. "apply to a job", "screen a candidate") with a defined success state per task, target persona(s), any design/style guide for microcopy tone.
- Target: base URL of a rendered NON-PROD build, seeded account + sample data so journeys can be walked end-to-end.
- Preconditions: each task has an unambiguous, observable success criterion (a reached screen / confirmation / persisted state); if a task lacks one, flag it and walk it descriptively.

## Oracle (source of truth)
**Nielsen's 10 usability heuristics** (visibility of system status, match to real world, user control & freedom, consistency & standards, error prevention, recognition over recall, flexibility/efficiency, aesthetic & minimalist design, help users recognize/diagnose/recover from errors, help & documentation) plus **task-success criteria** (completion, error rate, steps-vs-optimal, time-on-task) and **microcopy clarity** (plain language, no unexplained jargon, actionable error messages). NEVER "it works for me" — judge against the heuristic and the defined success state.

## Step sequence (Plan → Act → Verify)
1. **Plan** — list each task with its success state and the optimal step count; map which heuristics each screen touches; identify high-risk moments (destructive actions, irreversible submits, empty/error states).
2. **Act** — walk each task one at a time as the persona: record actual steps vs. optimal, dead-ends, ambiguous labels, missing system-status feedback (no spinner/confirmation), missing undo on destructive actions, jargon-heavy or blame-y error copy. Probe error prevention: submit empty/invalid forms and check for inline guidance before failure. Skip-and-continue if one task is blocked.
3. **Verify** — assert each screen against the heuristics and each task against its success criterion: task completed? within reasonable step overhead? errors preventable and recoverable? status always visible? Capture the friction point with screenshot/step trace as evidence.

## Assertions & exit gate
- Every core task reaches its success state with no dead-end and no more than a small step overhead vs. optimal.
- Destructive/irreversible actions have confirmation or undo (user control & freedom; error prevention).
- Error messages are specific, blameless, and tell the user how to recover; system status is always visible.
- **Gate:** `core_tasks_completable_no_critical_friction` — passes when every core task completes and 0 critical heuristic violations remain (a task that cannot complete is **critical**; a recurring friction point is **major**; cosmetic/microcopy nits are **minor**).

## Output
Write `artifacts/usability/report.json` per `shared/report-format.md`:
`{ flow:"usability", status, summary{total,passed,failed,skipped}, findings[], gate{name:"core_tasks_completable_no_critical_friction",passed} }`.
Each finding (`QA-UX-NNN`) names the violated Nielsen heuristic (or task id) in `oracle`, the step trace + screenshot in `evidence`, and a concrete redesign/copy fix in `suggested_fix`. Severity reflects task impact, not aesthetics.

## Guardrails
Per `shared/guardrails.md`: read-only walkthrough — `disallowedTools: Edit, Write`; never submit against live data (seeded account only); mock outbound side effects (emails, applications). Heuristic findings are subjective — keep them grounded in a named heuristic + reproducible step, and lower confidence where judgment is involved. Secrets via env; cap `maxTurns`. Recommendations only — UX sign-off is a human's.
