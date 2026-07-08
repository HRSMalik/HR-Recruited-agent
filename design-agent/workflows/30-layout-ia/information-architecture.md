# information-architecture

**Group:** 30-layout-ia
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** audit (structure + label scan) · build (re-group + re-label + verify)   ·   **Default model:** sonnet

## Purpose
Structure and label content so the navigation, groupings, and terms match the user's mental model — the question "where would a user look for this, and would they recognise the label when they got there?"

## Inputs & preconditions
- From `project-design-config.md`: the screen set + nav (e.g. applicant-facing apply flow vs recruiter pipeline/candidate views), component library, locked terminology, breakpoints.
- Target: the nav tree, section groupings, and labels of the screen(s) under review; the relevant standard (NN/g IA + Nielsen #2 match between system and the real world).
- Preconditions: dev server reachable; existing labels/terms read before renaming anything.

## Oracle (source of truth)
NN/g information architecture + the project's locked terminology (`project-design-config.md`). Card sorting *generates* an IA (how users group/name things); tree testing *evaluates* one (finds the structure/label problems).
- **hard:** every nav destination resolves (no dead/orphan links); no duplicate labels pointing at different destinations; terms match the locked glossary, no synonym drift.
- **soft:** tree-test task success is high; top-level categories match user expectations; labels are recognisable, not clever.

## Standards & techniques
- **Card sorting (generate):** open/closed sort to derive groupings + names from how users cluster items — use when the IA is new or contested.
- **Tree testing (evaluate):** give a task, navigate the label-only tree, measure success / directness / first-click — isolates structure vs label problems without visual confound.
- **Match the real world:** plain recruiting terms users say (e.g. "Applications", "Candidates", "Open Roles") over internal jargon; one term per concept across the app.
- **Shallow + broad over deep:** group to ~5–9 top-level items; avoid burying a task more than ~3 clicks deep.

## Step sequence
- **audit:** map the live nav tree + every label → run tree-test tasks against label-only paths (assert success/directness) → flag mismatched/duplicate/jargon labels and mis-grouped items → emit findings (read-only, no edits).
- **build:** Explore (≥2 IA structures from a card-sort rationale, read-only) → Judge (tree-test success + label-recognisability rubric, order-swapped) → Implement (one writer; re-group/re-label markup + nav config only, reuse nav components, honour the glossary) → Verify (re-run tree-test tasks; screenshots @ breakpoints; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every destination resolves; no orphan or duplicate-label links; terms match the locked glossary.
- Top-level categories ≤ ~9; no task buried > ~3 clicks; tree-test task success high.
- **Gate:** hard oracles green (links resolve, no label collisions, glossary conformance) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/information-architecture/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: heuristic`, `heuristic: "Nielsen #2 Match between system and the real world"`; `oracle: hard` for dead/duplicate links + glossary drift, `soft` for low tree-test success), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: relabel/re-group markup + nav config only — never touch routing logic or handlers. Reuse existing nav components; honour the locked glossary, don't coin new terms. Read-only audit makes no edits; one writer for build.
