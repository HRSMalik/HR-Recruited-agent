# user-flow-design

**Group:** 30-layout-ia
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** audit (flow-trace scan) · build (re-sequence + verify)   ·   **Default model:** sonnet

## Purpose
Design the multi-step task flow *between* screens (distinct from single-screen IA) so the user completes the job with no dead ends, lost state, or orphan steps — the question "can the user get from start to finish, and back, without getting stuck or losing work?"

## Inputs & preconditions
- From `project-design-config.md`: the screen set + nav (applicant-facing apply funnel; recruiter create→review→shortlist→schedule), component library, locked terminology, breakpoints, dev-server URL/creds.
- Target: the cross-screen flow(s) under review — step order, what state carries forward, entry/exit points; the standard (NN/g flow design + Nielsen #3 User control and freedom, #1 Visibility of system status).
- Preconditions: dev server reachable; existing routes/steps walked end-to-end before re-sequencing anything.

## Oracle (source of truth)
NN/g task-flow / funnel design + the project's locked terminology — trace the actual flow, don't assume it.
- **hard:** the flow reaches a terminal success state from each entry point (no dead end / no orphan step with no inbound or outbound path); state carried forward survives a step transition (a value entered on step N is present on step N+1, not silently dropped); browser **Back** returns to the prior step without data loss or duplicate submission; every error path offers an in-context recovery action (retry / edit / go-back), never a terminal dead screen; a partially-done flow is resumable (deep-link / saved-progress lands on the right step, not a reset to step 1).
- **soft:** step count is minimised; progress is visible (step N of M); drop-off-risk steps (heavy input, dead time, re-auth) are softened; empty→populated transitions across screens read continuously, not as a jarring reset.

## Standards & techniques
- **Map the flow as a funnel:** enumerate steps, the inbound/outbound edges of each, entry points (apply CTA, shared job link, recruiter "create role"), and exit points (submitted, saved-draft, abandoned) — one canonical happy path plus its branches.
- **Carry state forward + autosave/resume:** what each step must remember (applicant answers, recruiter shortlist selection); persist on transition so refresh/return resumes mid-flow, not at step 1.
- **Honour back-button + deep-link semantics:** **Back** is a real prior step (no re-POST, no wipe); a deep link lands the user on the correct step with prior state intact, not bounced to the start.
- **Error-recovery, never dead ends:** every failure (validation, upload fail, slot taken at schedule) offers retry/edit/alternative in context; expired/invalid deep-links recover gracefully, not a blank stop.
- **Design empty→populated across screens:** the first-run/empty state of a downstream screen (no applicants yet, no shortlist) flows into the populated state without a hard visual reset.

## Step sequence
- **audit:** walk each flow live from every entry point → trace step order, state carried across transitions, Back-button + deep-link + resume behaviour, and each error path → flag dead ends, orphan steps, dropped state, non-recoverable errors, and high drop-off steps → emit findings (read-only, no edits).
- **build:** Explore (≥2 step-sequence/recovery specs from a funnel map, read-only) → Judge (no-dead-end + state-preserved + recoverable rubric, order-swapped) → Implement (one writer; re-sequence step markup / nav wiring / progress UI only — never the submit/persistence logic, reuse nav + step components) → Verify (Playwright walks every step @ breakpoints; assert state survives transition + Back; assert each error path recovers; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every entry point reaches a terminal success state; no orphan step; no dead-end error screen.
- State carried forward survives step transition + Back; deep-link/resume lands on the correct step with data intact; no duplicate submit on Back.
- Progress is visible (step N of M); step count minimised; drop-off-risk steps softened.
- **Gate:** hard oracles green (no dead end/orphan, state preserved, Back-safe, errors recoverable, resumable) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/user-flow-design/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: heuristic`/`interaction`, `heuristic: "Nielsen #3 User control and freedom"`; `oracle: hard` for dead ends, orphan steps, lost state, non-recoverable errors, Back-button data loss), plus the verification block for build mode.

## Watch (do not gate)
Emerging funnel concerns to note as findings, never as a hard oracle: per-step drop-off instrumentation/analytics on the apply funnel; save-and-resume-later via emailed link; and recruiter flow re-entry after interruption. Flag as advisory, not blocking.

## Guardrails
Per `shared/guardrails.md`: re-sequence step markup / nav wiring / progress UI only — never touch submit handlers, persistence, validation, or scheduling logic. Reuse existing nav + step components; honour the locked glossary. Read-only audit makes no edits; one writer for build.
