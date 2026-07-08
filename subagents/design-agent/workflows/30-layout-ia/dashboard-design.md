# dashboard-design

**Group:** 30-layout-ia
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** audit (dashboard-craft scan) · build (re-layout + verify)   ·   **Default model:** sonnet

## Purpose
Lay out the recruiter dashboard (pipeline/throughput KPIs) so the headline reads at a glance and detail is one drill away — a bento grid where tile size tracks importance, every KPI carries a trend, and it stays enterprise (no gauges, no health rings, no gamified copy).

## Inputs & preconditions
- From `project-design-config.md`: component library (KPI tile / `Card` / `Badge` / sparkline), token source, theme, the locked "stay enterprise" rule, breakpoints.
- Target: the dashboard screen at every configured viewport; the standard (bento + KPI/dashboard guidance).
- Preconditions: dev server reachable; existing tile/card/chart components read before re-laying-out — reuse, don't reinvent tiles.

## Oracle (source of truth)
Bento-grid + KPI dashboard guidance + the project's locked enterprise rule.
- **hard:** ≤ 5–7 primary KPIs per view; every KPI tile shows a temporal comparison (sparkline or delta), not a bare number; no gauges / health-rings / gamified copy (a dot or thin categorical bar to encode status is fine; a percentage "health" ring is not); 12-col grid, 16px gutters.
- **soft:** tile size genuinely tracks importance; progressive disclosure reads well (headline first, drill for detail); the grid is balanced, not lopsided.

## Standards & techniques
- **Bento grid:** 12-col, 16px gutters; tile size = importance — the lead metric gets the biggest tile, supporting metrics smaller.
- **5–7 primary KPIs per view:** above that, split into views or push to a drill — don't crowd the headline.
- **Every KPI gets a temporal comparison:** sparkline trend or a delta vs prior period — a number without context isn't a KPI.
- **Progressive disclosure:** headline figure first; detail (breakdown, table, time-series) revealed on drill, not stacked on the overview.
- **Stay enterprise:** precise KPI tiles + figures; status encoded with a dot or a thin categorical bar + label — never a gauge, health-ring, or gamified "score".

## Step sequence
- **audit:** drive the live dashboard @ breakpoints → count primary KPIs, check each carries a trend/delta, flag gauges/health-rings/gamified copy, check grid (12-col/16px) + tile-size-to-importance + drill availability → emit findings (read-only, no edits).
- **build:** Explore (≥2 bento arrangements ranking tiles by importance, read-only) → Judge (KPI-trend + enterprise-restraint + grid rubric, order-swapped) → Implement (one writer; re-layout tiles/grid markup/style only, reuse KPI/`Card`/sparkline components and tokens) → Verify (Playwright screenshots default/loading/empty @ breakpoints; assert ≤7 KPIs + each has a trend + no gauges; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- ≤ 5–7 primary KPIs; every KPI shows a sparkline/delta; no gauge/health-ring/gamified element.
- 12-col grid, 16px gutters; tile size tracks importance; detail behind a drill, not crowded onto the overview.
- **Gate:** hard oracles green (KPI count, trend present, no banned gimmicks, grid spec) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/dashboard-design/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: visual`/`heuristic`, `oracle: hard` for >7 KPIs / trendless KPI / gauge-or-health-ring / off-grid; `viewport` named), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: never touch metric computation or data-fetch logic — re-layout tiles/grid markup/style only. Reuse the KPI tile / `Card` / sparkline components and tokens; honour the locked enterprise rule, never add a gauge or health-ring. Read-only audit makes no edits; one writer. Trust the screenshot over the diff.
