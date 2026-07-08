# typography

**Group:** 00-foundations
**Runs as:** subagent: ../.claude/agents/visual-designer.md
**Mode:** build (writer + verify loop) · audit (hierarchy + contrast scan)   ·   **Default model:** sonnet

## Purpose
Own the type system: a restrained scale and a deliberate hierarchy so the eye lands on the right element first and data columns read cleanly with tabular numerals.

## Inputs & preconditions
- From `project-design-config.md`: token source + real token names (grep before use), style-object source, colour rule, theme (light/dark/both), breakpoints, locked legibility rule.
- Target: the screen(s)/component(s) carrying the text and any data columns.
- Preconditions: dev server reachable; existing type tokens/style objects read before acting.

## Oracle (source of truth)
WCAG 1.4.3 Contrast (Minimum) + WCAG 1.4.4 Resize Text + NN/g visual hierarchy + Refactoring UI type guidance.
- **hard:** every text/background pairing ≥ 4.5:1 (≥ 3:1 for ≥18px / ≥14px-bold), verified light AND dark via the contrast checker; data-column numbers use `font-variant-numeric: tabular-nums` and are right-aligned.
- **hard:** if `clamp()` fluid type is used, text still scales to 200% under browser zoom (WCAG 1.4.4) — the `min`/`max` bounds are in `rem` (never `px`) and the preferred value carries a `rem` term, not pure `vw`; verified by zooming to 200% and confirming reflow without clipping or loss of content.
- **soft:** the hierarchy reads when the screen is squinted at — header → subhead → body is unmistakable; no flat wall of same-size text.

## Standards & techniques
- **1–2 typefaces** only; one family carries the UI.
- **~3 effective sizes:** header ~32, subhead 18–22, body 14–16 — resist a fourth.
- Establish hierarchy with **weight + colour, not size alone** (e.g. muted token for secondary, bold for emphasis).
- **Tabular numerals** + **right-aligned numbers** in every data column so digits align vertically; tight line-height for labels, comfortable for body.
- Stay on the locked compact scale — legible, not inflated to "accessibility" sizes.

### Fluid type & space (clamp + modular scale)
Derive sizes from a **modular scale** (base × ratio — e.g. body × 1.2 minor-third, × 1.25 major-third) rather than hand-picking each value, then make each step fluid with `clamp(min, preferred, max)` (Utopia method). The browser interpolates between a small-screen scale and a large-screen scale across two viewport widths — no per-breakpoint redeclarations, no magic numbers.
- **Bounds in `rem`, never `px`.** `min` and `max` are the small-screen and large-screen value of the step; `px` bounds do not respond to the user's font preference and break WCAG 1.4.4.
- **Preferred value carries a `rem` term, not pure `vw`** (e.g. `clamp(1rem, 0.85rem + 0.9vw, 1.375rem)`). Browsers do not scale `vw` under zoom — the `rem` term is what keeps text growing toward 200%; pure `vw` fails resize.
- **Keep `max ≤ 2.5 × min`** per step. Within that ratio the step still reaches 200% under zoom on all modern browsers; beyond it, fluid display sizes can clip the zoom range.
- **Reserve fluidity for large display steps** (header/hero) where the min→max gap is meaningful — body text stays on the locked compact scale; do not make 14–16px body fluid.
- **Space scale shares the base.** Derive T-shirt space tokens (S/M/L/XL) from Step 0 of the type scale with the same multipliers and the same `clamp()` interpolation, so gaps stay in tune with type at every width.
- The hard 1.4.4 oracle below gates the `rem`-bounds + `rem`-term + 200%-reflow rules; the modular-scale ratio itself is a soft choice (squint test), not a gate.

### Font loading (swap-CLS elimination)
Self-hosted, preloaded, metric-matched fonts so the primary family paints fast and does not shift layout when it swaps in.
- **`font-display: swap`** in every `@font-face` so text is visible immediately in the fallback rather than invisible during fetch (no FOIT).
- **Self-host + subset** the primary font (Latin subset, only the weights actually used — typically regular + one bold) and **`<link rel="preload" as="font" type="font/woff2" crossorigin>`** it so the critical weight is in flight before first paint.
- **Metric overrides on the fallback `@font-face`** — `size-adjust`, `ascent-override`, `descent-override`, `line-gap-override` tuned so the fallback occupies the same box as the web font; this is what removes swap-CLS (the fallback→web-font reflow), letting you keep `swap` without the layout jump.
- **Watch (do not gate):** the `@font-face` `size-adjust` descriptor and tooling like Fontaine / `next/font` that auto-generate metric overrides are still settling across browsers — note the metric-override block as EMERGING, prefer hand-tuned overrides for the primary family, and do not gate a build on auto-generated metrics matching exactly.

## Step sequence
- **audit:** map every text node to its size/weight/colour token → run the contrast checker on each pairing (light + dark) → check data columns for tabular-nums + right-align → if `clamp()` is used, check bounds are in `rem`, the preferred value carries a `rem` term, and `max ≤ 2.5 × min`, then zoom to 200% and confirm reflow → check `@font-face` for `font-display: swap`, a preloaded subset primary font, and metric-override descriptors on the fallback → emit findings (read-only, no edits).
- **build:** Explore (≥2 hierarchy specs, read-only) → Judge (squint test + contrast rubric, order-swapped) → Implement (one writer; apply size/weight/colour tokens, set tabular-nums + right-align on number columns; if fluid, generate the `clamp()` steps from the modular scale and the space tokens from Step 0; wire `font-display: swap` + preload + metric overrides) → Verify (Playwright screenshots every state @ breakpoints; contrast check light+dark; zoom to 200% and confirm no clipping/loss; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- ≤ 2 typefaces; ≤ ~3 effective sizes; secondary text differentiated by weight/colour token, not size alone.
- Every text/bg pairing ≥ threshold in both themes; number columns tabular + right-aligned.
- If fluid: `clamp()` bounds in `rem`, preferred value carries a `rem` term, `max ≤ 2.5 × min` per step, and text reaches 200% under zoom without clipping or loss of content.
- Primary font self-hosted + subset + preloaded with `font-display: swap`; fallback `@font-face` carries metric-override descriptors so the swap causes no measurable layout shift.
- **Gate:** hard oracles green (contrast + tabular numerals + 1.4.4 200% reflow when fluid) AND (build) rubric mean ≥ 0.8. The metric-override block is EMERGING — verified as a "Watch", never a gate.

## Output
Write `artifacts/typography/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: accessibility` + `wcag_ref: 1.4.3` for contrast, `wcag_ref: 1.4.4` for fluid-type 200% resize, `type: visual` for hierarchy/numerals, `type: performance` for font-loading swap-CLS), plus the verification block for build mode. Tag the metric-override finding `status: watch` so it never reads as a gate.

## Guardrails
Per `shared/guardrails.md`: use existing type tokens — grep the source, never guess a token. Preserve logic byte-for-byte (style/markup only). Read-only audit makes no edits; one writer for build; trust the screenshot over the diff.
