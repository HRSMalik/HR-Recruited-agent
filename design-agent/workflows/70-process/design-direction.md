# design-direction

**Group:** 70-process
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (one writer produces the set; design-judge gates it)
**Mode:** build (deliverable + verify)   ·   **Default model:** opus

## Purpose
When proposing a design DIRECTION (not a one-screen tweak), deliver a full, self-contained multi-screen set so the direction can be judged as a whole — a genuinely different layout / IA / interaction model, never a recolour.

## Inputs & preconditions
- From `project-design-config.md`: brand/palette, aesthetic direction, theme, token source + names, component library, **design drop folder `designs/<slug>/`** (where the set lands), kept/approved references to match.
- Target: a new direction for the product (or a major surface family), not a single screen.
- Preconditions: token source + kept references read first; design drop folder `designs/<slug>/` path resolved from config.

## Oracle (source of truth)
"New direction" = genuinely different layout / IA / interaction model — plus the hard oracles on every rendered screen.
- **hard:** each screen is standalone HTML that renders with zero console errors, passes contrast + axe at the screenshot viewport, and uses real tokens (no raw hex where a token exists).
- **soft:** the senior craft rubric across the whole set — coherence, hierarchy, restraint, polish — scored on the screenshots.

## Standards & techniques
- **The set (in the design drop folder `designs/<slug>/`, one folder per direction):** primary screen · component / design-system sheet (buttons, inputs, pills, cards, KPI tiles, tabs, modal, empty, toast) · a detail screen · a dashboard · a login.
- Each screen is **standalone HTML + a 1440×900 screenshot**, production-grade — not a wireframe.
- A direction must differ in **layout / IA / interaction model**, not palette; if it's a recolour, it doesn't qualify as a new direction — say so and stop.
- Update the **folder README + token map** so the set is self-documenting (design value → token).

## Step sequence
- **build:** Explore (read-only; confirm the direction is structurally new vs kept references, sketch the IA + screen list) → Judge (design-judge scores coherence + distinctness + craft, order-swapped) → Implement (one writer authors every standalone HTML screen, the design-system sheet, README + token map, in the design drop folder `designs/<slug>/`) → Verify (Playwright screenshots each screen @ 1440×900 + the project breakpoints; contrast + axe + zero console errors per screen; evaluator re-scores from the screenshots) → loop ≤15 or pass.

## Assertions & exit gate
- All five deliverables present in their own design drop folder `designs/<slug>/`; each standalone HTML renders cleanly, and the set is compiled into a single PDF "book" (`designs/<slug>/<slug>.pdf`) on completion — **no per-screen PNGs** (verify-grading screenshots stay ephemeral).
- The direction is structurally distinct from the kept references (layout/IA/interaction), not a recolour.
- Folder README + token map updated and accurate.
- **Gate:** hard oracles green on every screen AND rubric mean ≥ 0.8 across the set.

## Output
Write `artifacts/design-direction/report.json` per `shared/report-format.md` — the screen list + folder path, the distinctness rationale, the token map, plus the verification block (per-screen screenshots + viewports + hard-oracle results + rubric score).

## Guardrails
Per `shared/guardrails.md`: reuse the token set before inventing; one writer authors the whole set, sequenced; the evaluator grades the rendered screenshots, not the prose. Don't touch app logic — this is a standalone deliverable. Trust the screenshot over the diff.
