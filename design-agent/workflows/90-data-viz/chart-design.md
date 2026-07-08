# chart-design

**Group:** 90-data-viz
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** audit (chart-craft scan) · build (re-encode + verify)   ·   **Default model:** sonnet

## Purpose
Own how data becomes a chart (e.g. recruiter funnel, time-to-hire trend, source-of-hire breakdown): pick the chart type that encodes the analytical intent most accurately, make the rendered chart accessible to non-sighted and colourblind users, and refuse encodings that distort the data.

## Inputs & preconditions
- From `project-design-config.md`: the charting component/library (grep the source — never assume Recharts/D3), token source + the categorical/sequential/diverging colour ramps, dev-server URL/port + login creds, breakpoints.
- Target: the chart(s) under review at every configured viewport; the analytical intent each answers (comparison / trend-over-time / part-to-whole / distribution / correlation / geospatial); standard = Datawrapper chart-types guide (https://www.datawrapper.de/blog/chart-types-guide).
- Preconditions: dev server reachable; existing chart component + token ramps read before re-encoding — reuse the ramp, don't invent hues.

## Oracle (source of truth)
Cleveland–McGill encoding-accuracy ranking + the Datawrapper chart-types guide, plus WCAG for the rendered SVG.
- **hard:**
  - **Data integrity** — bar/column value axis starts at zero; no truncated or dual y-axes that distort comparison; choropleth values normalized (per-capita / rate, never raw counts on varying populations); aggregation honest (no cherry-picked bins/time-windows).
  - **Accessibility** — chart SVG carries `role="img"` (or `graphics-document`) + an accessible name (`<title>`/`aria-label`) and a `<desc>`/`aria-describedby` summary; a data-table fallback exists; series are NOT distinguished by colour alone (1.4.1) — pair with direct labels, patterns, or shape; mark-vs-mark and mark-vs-background non-text contrast ≥ 3:1 (WCAG 1.4.11).
- **soft:** chart type is the encoding-accuracy-ranked best fit for the intent; ramp type matches data type (categorical vs sequential vs diverging); legend/labelling and density read cleanly at every breakpoint.

## Standards & techniques
- **Intent → type (ranked by Cleveland–McGill accuracy: position > length > angle/slope > area > colour-saturation):** comparison → bar/column (position+length) over pie (angle); trend → line (position+slope); part-to-whole → stacked bar or, sparingly, pie/donut only at ≤5 slices; distribution → histogram/box; correlation → scatter; geospatial → normalized choropleth or symbol map. Prefer the highest-accuracy encoding the intent allows; demote pie/area/bubble where a bar/line answers the same question.
- **Colourblind-safe ramps:** categorical = qualitative palette safe for deuteranopia/protanopia (never red-vs-green to mean opposite states); sequential = single-hue light→dark for ordered magnitude; diverging = two-hue through a neutral midpoint for above/below-a-reference data — never a rainbow ramp for ordered data.
- **Never colour-only:** direct-label lines/segments, or add shape/pattern, so the series survives greyscale.
- **Accessible structure:** SVG `role`/name/desc + a real `<table>` fallback (or visually-hidden equivalent); units in the accessible name; no information conveyed only by hover.
- **Watch (do not gate):** the **WAI-ARIA Graphics module** (`graphics-document` / `graphics-object` / `graphics-symbol`) and per-datapoint focusable/described chart navigation are EMERGING — screen-reader support is uneven across the configured targets. Offer it as a richer layer to feature-detect on top of the `role="img"` + data-table baseline; flag its absence as advisory only, never a hard oracle, and never a reason to drop the table fallback.

## Step sequence
- **audit:** drive each live chart @ breakpoints → classify the intent → check type vs the encoding-accuracy ranking, ramp-type fit, no colour-only encoding; assert SVG role/name/desc + data-table fallback + 1.4.11 contrast (axe-core / WebAIM); assert data integrity (zero-baseline, no truncated/dual axes, normalized choropleth, honest aggregation) → emit findings (read-only, no edits).
- **build:** Explore (≥2 chart-type/encoding specs for the same intent, read-only) → Judge (encoding-accuracy + accessibility + integrity rubric, order-swapped) → Implement (one writer; re-encode the chart markup/style only — swap type, apply the token ramp, add SVG role/name/desc + table fallback + direct labels, force zero baseline) → Verify (Playwright screenshots default/empty/loading @ breakpoints + a greyscale pass to prove no colour-only encoding; axe-core + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Type is the encoding-accuracy-ranked fit for the intent; ramp type matches data type; no series distinguished by colour alone (survives greyscale).
- SVG has role + accessible name + desc; data-table fallback present; mark contrast ≥ 3:1; bars zero-baselined, no truncated/dual axes, choropleths normalized.
- **Gate:** hard oracles green (integrity + accessibility/contrast + role/name/table) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/chart-design/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: visual`/`accessibility`; `oracle: hard` for truncated/non-zero axis, un-normalized choropleth, missing role/name/table, colour-only series, 1.4.11 fail — cite `1.4.1`/`1.4.11`; `viewport` named; `evidence` = screenshot@viewport + greyscale pass / axe rule id / measured ratio), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: never touch the data query/aggregation or chart-event logic — re-encode markup/style only; if honest encoding needs a data change (e.g. raw→per-capita), stop and flag it, don't silently re-bin. Reuse the project's chart component + token ramps — never hardcode a hue. Read-only audit makes no edits; one writer. Trust the screenshot (and the greyscale pass) over the diff.
