# interaction-states

**Group:** 20-interaction
**Runs as:** subagent: ../.claude/agents/interaction-designer.md
**Mode:** build (writer + verify loop) · audit (state-coverage scan)   ·   **Default model:** sonnet

## Purpose
Own the full state set for every interactive element — design and verify default/hover/focus/active/disabled plus the functional states (loading, empty, error, success) — so no control is ever left in an undefined or unstyled state.

## Inputs & preconditions
- From `project-design-config.md`: component library (reuse before inventing), token source + names, dev-server URL/port + creds, breakpoints, theme (light/dark/both), locked rules.
- Target: every interactive element on the screen — buttons, inputs, selects, links, rows, tabs, toggles, and any async surface (lists, tables, submit flows).
- Preconditions: dev server reachable; existing component states read before adding any.

## Oracle (source of truth)
Material 3 interaction states + the rule that a control with an undefined state is a defect.
- **hard (verify):** every interactive element has all applicable states, each screenshot to prove it; **focus is mandatory** for keyboard/AT and is visually distinct from hover (focus ≠ hover — never share one style); disabled is non-interactive and reads ≥ 3:1; loading shows a skeleton/spinner not a frozen control; error/success surfaces are present where the action can fail.
- **soft:** state transitions feel coherent; empty states are inviting, not dead ends.

## Standards & techniques
- **Baseline 5 (every interactive element):** default · hover (pointer only) · **focus-visible** (distinct ring, ≥ 3:1, keyboard-reachable) · active/pressed · disabled (muted, `aria-disabled`, no pointer events).
- **Functional states (where the element does async work):** loading = **skeleton** for full surfaces / spinner for inline; empty = **icon + one-line explanation + a next-action control**, never a bare sentence; error = inline message + retry/recovery; success = confirmation tied to the actual outcome.
- focus and hover are separate styles; touch targets keep hover optional but focus + active required.
- Pull every state colour/elevation/radius from a token — no ad-hoc per-state hex.

## Step sequence
- **audit:** enumerate every interactive element → drive the live screen, tab + hover + activate + disable each → trigger loading/empty/error/success paths → screenshot each state → flag any missing/undefined state or focus==hover collision → emit findings (read-only).
- **build:** Explore (≥2 state-spec sets from existing component tokens, read-only) → Judge (coverage + focus≠hover + token-conformance rubric, order-swapped) → Implement (one writer; add states to existing components via tokens, mark up `:focus-visible`/`aria-disabled`/skeletons) → Verify (Playwright screenshots **every state** @ breakpoints — default/hover/focus/active/disabled/loading/empty/error/success; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every interactive element has all 5 baseline states; focus is present and visually ≠ hover.
- Async elements have loading (skeleton), error, and success; empty states carry an icon + next action.
- Every state colour/elevation resolves to a token; disabled control reads ≥ 3:1 and takes no pointer events.
- **Gate:** hard oracles green (full coverage + focus≠hover + axe + console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/interaction-states/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: interaction`, `oracle: hard` for a missing state or focus==hover, `heuristic` Nielsen #1 Visibility of system status), plus the verification block (a screenshot per state per element @ breakpoints + hard-oracle results + rubric score).

## Guardrails
Per `shared/guardrails.md`: reuse component states before inventing; never guess a token name — grep the source. Preserve logic byte-for-byte (markup/style only). Read-only audit makes no edits; one writer for build; trust the screenshot over the diff.
