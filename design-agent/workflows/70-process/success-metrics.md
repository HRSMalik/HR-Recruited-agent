# success-metrics

**Group:** 70-process
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (deliverable author)
**Mode:** deliverable (read-only — defines + instruments the scoreboard, no logic edits)   ·   **Default model:** sonnet

## Purpose
Pair with `handoff-spec` so "proven done" means a production scoreboard, not just a passing screenshot. Define the HEART signals for the surface, the north-star + funnel/conversion metric the design decision moves, and the analytics-instrumentation spec (events + naming) so the outcome is measurable after ship.

## Inputs & preconditions
- From `project-design-config.md`: the target surface + locked rules, component library + token source (events bind to real component states, not invented ones), the analytics sink/SDK if named.
- Target: the approved screen(s)/flow from `handoff-spec` and the single design decision under measurement.
- Preconditions: the design is approved (build-ready) and its states are enumerated; no metric is defined for a region still marked WIP.

## Oracle (source of truth)
Google/NN/g **HEART + Goals-Signals-Metrics** — each category maps Goal (what to improve) → Signal (observable behaviour) → Metric (quantifiable measure), per the cited source. The instrumentation is the deterministic part; the metric *targets* are craft.
- **hard:** every HEART row present for the surface with a Goal→Signal→Metric chain (no orphan signal, no metric without a signal); exactly one north-star named + one funnel/conversion metric tied to the decision; every metric has a firing event whose name follows the convention and whose trigger is a real, enumerated component state.
- **soft:** the metrics are the *right* ones — the funnel metric genuinely moves with this decision; targets are defensible, not vanity numbers.

## Standards & techniques
- **HEART per surface** (definitions per source): Happiness — attitudes/satisfaction (signal: positive survey feedback; metric: NPS / star rating). Engagement — depth of interaction (signal: more time/actions per session; metric: avg session length / actions per visit). Adoption — new users converting to active (signal: first-time feature activation; metric: registration / feature-adoption rate). Retention — keeping users over time (signal: returning at regular intervals; metric: churn / renewal rate). Task success — completing intended actions (signal: successful workflow completion; metric: completion rate / time-to-completion + error rate). Drop a row only with a written reason (the surface genuinely has no signal there).
- **North-star + funnel:** name ONE north-star the surface serves and ONE funnel/conversion metric the design decision is expected to move (the step-to-step rate the redesign targets) — state the expected direction.
- **Instrumentation spec:** per metric, the event(s) to fire, the trigger state (bind to the handoff-spec's enumerated states), required properties, and the naming convention — `object_action` snake_case (e.g. `application_submitted`, `screening_started`), one convention applied everywhere, documented once.

## Step sequence
- **deliverable:** Read the approved surface + its enumerated states from `handoff-spec` → write the HEART table (Goal→Signal→Metric per category, drop-with-reason allowed) → name the north-star + the funnel/conversion metric the decision moves and its expected direction → map each metric to firing event(s), trigger state, properties, and a convention-conformant name → assert the chains + naming → assemble the spec (read-only; defines and documents, fires no events, edits no logic).

## Assertions & exit gate
- Every present HEART category has a complete Goal→Signal→Metric chain; any dropped row carries a written reason.
- Exactly one north-star and one funnel/conversion metric named, each tied to the design decision with an expected direction.
- Every metric resolves to ≥1 event; every event name follows the single convention and triggers on a real enumerated component state (no metric without an event, no event without a state).
- **Gate:** hard oracles green (chains complete, north-star + funnel present, events named + state-bound to the convention).

## Output
Write `artifacts/success-metrics/report.json` per `shared/report-format.md` — the HEART table, the north-star + funnel/conversion metric (with expected direction), and the event/naming instrumentation map; any orphan signal, unmeasurable metric, or off-convention event name emitted as a `hard` finding per `finding-schema.md`.

> **Watch (do not gate):** *auto-instrumentation / autocapture* (SDKs that record every DOM interaction and let metrics be defined retroactively) is EMERGING — it promises measurement without hand-placed events. Treat it as advisory only; this flow still ships an explicit, named event map, and autocapture never replaces the convention-conformant spec or becomes a hard oracle.

## Out of scope
Running A/B tests, live dashboards, or post-ship analysis — this flow defines the scoreboard and its instrumentation; it does not operate it.

## Guardrails
Per `shared/guardrails.md`: read-only deliverable — defines metrics + events, never fires them and never edits logic. Bind every event to a real enumerated state from `handoff-spec` (never invent a state); reference existing components/tokens by name. Report what the source/convention says — never define a metric for a WIP region or grade the scoreboard against taste alone.
