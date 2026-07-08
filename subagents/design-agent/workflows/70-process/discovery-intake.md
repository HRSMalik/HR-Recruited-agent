# discovery-intake

**Group:** 70-process
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (one writer authors the brief; design-judge gates it)
**Mode:** build (deliverable + verify)   ·   **Default model:** opus

## Purpose
The FRONT DOOR — runs BEFORE `design-exploration` so the agent frames the problem before it diverges, and stops perfectly building the wrong thing. Per NN/g, discovery is "framing the problem(s) to be solved" so the team is "focusing on the right problems and, consequently, building the right thing."

## Inputs & preconditions
- From `project-design-config.md`: brand/aesthetic, the product/surface family this brief covers, target users / roles, locked rules, and any kept references — read first; never hardcode a project's users, goals, or metric.
- A stated mandate or complaint (the surface or problem someone wants designed).
- Preconditions: the mandate is concrete enough to name a user and an outcome; config read before authoring. An agent cannot run live moderated research (interviews/field studies) — this flow produces an authorable *synthesis* brief from config + mandate + cited evidence, and flags every assumption as such.

## Oracle (source of truth)
The NN/g discovery completion bar — discovery is done when the team has "consensus on a problem to be solved and its desired outcomes" — plus a structural completeness check on the brief.
- **hard:** the brief states all five required artifacts (JTBD, target user/persona, user need + success criteria, constraints, one named success metric); the metric is measurable (a number/direction/timeframe, not "improve UX"); every claim is either grounded in config/cited evidence or explicitly labelled `assumption`.
- **soft:** the senior rubric below — is the problem framed (not the solution), is the user real and specific, is the metric a true outcome.

## Standards & techniques
- **JTBD statement** — "When [situation], I want to [motivation], so I can [expected outcome]"; describe the job, not a feature.
- **Target user / lightweight persona** — one primary user: role, context, goal, top frustration; drawn from config roles, not invented demographics.
- **User need + success criteria** — a need statement ("[user] needs a way to [need] because [insight]") plus what "working" looks like for them.
- **Constraints** — known business-process, technology, and locked-rule limits from config (NN/g: "business processes and technology constraints").
- **One named success metric** — what to measure "to understand whether the solution is working towards the desired outcome": baseline → target → timeframe.
- Frame the problem, not the solution — NN/g warns against "focusing on symptoms rather than causes" and moving "forward on only assumptions."

## Step sequence
- **build:** Explore (read-only; pull users/goals/constraints from config + mandate, gather any cited evidence, draft the five artifacts, tag each line `grounded` or `assumption`) → Judge (design-judge checks the completeness oracle + scores the rubric, order-swapped twice; rejects a solution masquerading as a problem, a vague metric, or unlabelled assumptions) → Implement (one writer authors the synthesis brief — JTBD, persona, need + success criteria, constraints, named metric — into the artifact) → Verify (re-read the written brief: assert all five artifacts present, metric measurable, assumptions labelled; evaluator re-scores from the brief) → loop ≤15 or pass.

## Assertions & exit gate
- All five artifacts present and non-empty; JTBD in situation/motivation/outcome form; exactly one primary user defined.
- The success metric is measurable (baseline + target + timeframe), an outcome not an output.
- Every line is `grounded` (config/cited) or labelled `assumption`; no naked claims.
- **Gate (front-door release):** `design-exploration` MUST NOT start until the JTBD + target user + success metric are stated — hard oracles green AND rubric mean ≥ 0.8.

## Output
Write `artifacts/discovery-intake/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (type `heuristic`, each gap a finding with `evidence` = the missing/weak brief section), the five-artifact brief inline, plus the verification block (artifacts-present + metric-measurable + assumptions-labelled checks + rubric score). `mode: build`.

## Watch (do not gate)
EMERGING, advisory only — never a hard oracle: assumption-mapping / research-question workshops and a competitive review may strengthen the brief, but an agent can't run moderated research, so note them as recommended follow-ups, not blocking checks.

## Guardrails
Per `shared/guardrails.md`: explorer + judge are read-only; exactly one writer authors the brief. This is a standalone synthesis deliverable — touch no app logic. Reuse config's users/tokens/constraints before inventing; grade the written brief, not the prose claims. Label every assumption — never let an unverified guess pass as a grounded finding.
