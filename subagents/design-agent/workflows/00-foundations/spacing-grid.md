# spacing-grid

**Group:** 00-foundations
**Runs as:** subagent: ../.claude/agents/visual-designer.md
**Mode:** build (writer + verify loop) · audit (spacing-scale scan)   ·   **Default model:** sonnet

## Purpose
Own the spacing rhythm: every margin and padding is a token on a 4/8pt scale, internal spacing is tighter than external, and a consistent grid with gutters carries the layout.

## Inputs & preconditions
- From `project-design-config.md`: token source + real spacing-token names (grep before use), style-object source, breakpoints, locked legibility/density rules.
- Target: the screen(s)/component(s) whose spacing is under review.
- Preconditions: dev server reachable; existing spacing tokens read before acting.

## Oracle (source of truth)
The 4/8pt spacing scale + the internal ≤ external grouping principle (Refactoring UI / proximity, Gestalt).
- **hard:** every margin/padding/gap resolves to a spacing-scale token (a multiple of the base step) — grep the source; no off-scale raw px where a token exists.
- **soft:** grouping reads — space within a group is tighter than space between groups; columns/gutters align to a consistent grid.

## Standards & techniques
- **4/8pt scale:** all spacing is a token multiple (4, 8, 12, 16, 24, 32 …) — no arbitrary 7px/13px values.
- **Internal ≤ external:** padding inside an element and gaps within a group are smaller than the margins separating groups, so proximity signals relatedness.
- **Grid & gutters:** lay content on a consistent column grid with even gutters; cap and centre wide content blocks rather than letting them sprawl.
- Honour the locked density scale — compact, not inflated.

## Step sequence
- **audit:** measure every margin/padding/gap and map it to a token → flag off-scale values → check internal-vs-external rhythm and gutter consistency → emit findings (read-only).
- **build:** Explore (≥2 spacing rhythms, read-only) → Judge (on-scale + grouping rubric, order-swapped) → Implement (one writer; snap every value to a spacing token, tighten internal / loosen external, align to the grid) → Verify (Playwright screenshots every state @ breakpoints; assert no off-scale values + no viewport overflow; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every margin/padding/gap is a token multiple of the base step; zero off-scale raw values.
- Internal spacing tighter than external; gutters/columns consistent; no horizontal overflow at any breakpoint.
- **Gate:** hard oracles green (on-scale tokens + no overflow) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/spacing-grid/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: token` for off-scale spacing, `type: visual`/`responsive` for grouping/grid/overflow), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: use spacing tokens — grep the source, never guess a token. Preserve logic byte-for-byte (style/markup only). Read-only audit makes no edits; one writer for build; trust the screenshot over the diff.
