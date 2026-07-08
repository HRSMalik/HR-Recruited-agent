# radius-iconography

**Group:** 00-foundations
**Runs as:** subagent: ../.claude/agents/visual-designer.md
**Mode:** build (writer + verify loop) · audit (radius + icon consistency scan)   ·   **Default model:** sonnet

## Purpose
Own corner radii and icons: a radius scale that nests concentrically, and an icon set drawn on one grid with a uniform stroke and consistent optical sizing.

## Inputs & preconditions
- From `project-design-config.md`: token source + real radius-token names (grep before use), component library + icon set location, theme, colour rule.
- Target: the components with corners + the icons on the screen(s) under review.
- Preconditions: token source + icon set readable; existing radius tokens and icons read before adding any.

## Oracle (source of truth)
The radius scale + concentric-nesting rule (Refactoring UI) + a consistent icon grid/stroke (Material/Refactoring UI icon guidance).
- **soft:** radii come from the scale and nest concentrically (outer radius = inner radius + padding, so corners stay parallel); icons share one grid, one stroke width, and one optical size — the set reads as one family.
- **hard (carried from the system):** radius values resolve to real tokens (no hardcoded radius where a token exists); icon-button hit targets meet the target-size minimum (WCAG 2.5.8, ≥ 24×24 CSS px).

## Standards & techniques
- **Radius scale:** a small ramp (e.g. sm/md/lg/full) as tokens; pick by element size, not arbitrarily.
- **Concentric nesting:** a child's radius nests inside its parent's — outer = inner + the gap between them — so nested cards/buttons keep parallel corners.
- **Icon grid:** draw on a 24×24 grid (or a multiple of 8); keep a uniform **1.5–2px stroke** across the set.
- **Optical balance:** size icons by visual weight, not raw bounding box; align to text baselines/centres; one consistent size per context.

## Step sequence
- **audit:** map each corner to a radius token + check concentric nesting → measure icon grid/stroke/size across the set and flag outliers → check icon-button target size → emit findings (read-only).
- **build:** Explore (≥2 radius+icon treatments, read-only) → Judge (concentric-nesting + icon-family-consistency rubric, order-swapped) → Implement (one writer; snap radii to tokens, normalise icon grid/stroke/size, fix nesting) → Verify (Playwright screenshots every state @ breakpoints; assert token conformance + target size; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every radius is a scale token; nested elements nest concentrically.
- Icons share grid, stroke (1.5–2px) and optical size; icon-button targets ≥ 24×24.
- **Gate:** hard oracles green (radius-token conformance + target size) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/radius-iconography/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: visual` for nesting/icon-family, `type: token` for hardcoded radius, `type: accessibility` + `wcag_ref: 2.5.8` for target size), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: use radius tokens + the existing icon set — grep the source, never guess a token or reinvent an icon. Preserve logic byte-for-byte. Read-only audit makes no edits; one writer for build.
