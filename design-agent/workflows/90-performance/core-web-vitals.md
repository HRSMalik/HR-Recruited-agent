# core-web-vitals

**Group:** 90-performance
**Runs as:** subagent: ../.claude/agents/design-reviewer.md (audit) · ../.claude/agents/design-judge.md (build verify) — extend, don't replace; one writer applies
**Mode:** audit (field-budget scan) · build (perf-fix + verify loop)   ·   **Default model:** sonnet

## Purpose
Own the design-side performance budget: make the screen feel instant by hitting the three Core Web Vitals at p75 — responsiveness (INP), loading (LCP), and visual stability (CLS) — and fix them with layout/markup techniques only, never by changing app logic.

## Inputs & preconditions
- From `project-design-config.md`: dev-server URL/port + login creds, breakpoints to measure, token source (spacing/size + font tokens), component library, theme, locked rules.
- Target screen(s); the oracle = Google Core Web Vitals thresholds (INP/LCP/CLS) measured against the rendered page.
- Preconditions: dev server reachable; existing media-sizing and font tokens read before reserving space or touching font loading.

## Oracle (source of truth)
Core Web Vitals "good" thresholds at **p75**, per https://web.dev/articles/inp and the CWV set — measured via Lighthouse and a Playwright trace, not asserted by prose.
- **hard (verify, all three at p75):** **INP ≤ 200ms** · **LCP ≤ 2.5s** · **CLS ≤ 0.1**. Any one over budget → reject, loop back to the writer. Re-run after each fix; a regression on any of the three blocks the gate.
- **soft:** the largest element really is the intended hero (not a stray banner); skeletons match final layout so nothing jumps; interactions feel responsive, not just barely-passing.

## Standards & techniques (design-side levers, cite the principle)
- **LCP — prioritise the hero:** `<link rel="preload">` the LCP image + `fetchpriority="high"`; `loading="eager"` on it (never lazy-load the LCP element); responsive `srcset`/`sizes` so no oversized download. Demote below-the-fold media with `loading="lazy"`.
- **INP — yield to the main thread:** keep interaction handlers short; break long tasks and `await scheduler.yield()` / `setTimeout(0)` so input + paint aren't blocked; render the visual acknowledgement (pressed/loading state) **before** heavy work; avoid synchronous layout reads inside handlers.
- **CLS — reserve space before content arrives:** set explicit `width`/`height` (or `aspect-ratio`) on every image/embed/ad slot; reserve skeleton boxes at final dimensions; `font-display: swap` **paired with `size-adjust`/metric overrides** so the fallback matches the webfont's box and the swap doesn't reflow; never inject content above existing content.
- **Avoid layout thrash:** batch DOM reads then writes (read-then-write, never interleaved in a loop); use `transform`/`opacity` for motion, not `top`/`left`/`width`; prefer `content-visibility` for offscreen sections.

## Step sequence
- **audit:** load the target at the project's breakpoints → run Lighthouse + a Playwright interaction trace → read measured INP/LCP/CLS at p75 → identify the LCP element, the longest interaction, and every unsized media / late-loaded font causing shift → emit findings (read-only, no edits), each with the measured number vs its budget.
- **build:** Explore (≥2 fix strategies from the levers above, read-only) → Judge (budget-met + hero-correct + skeleton-match rubric, order-swapped) → Implement (one writer; preload/priority hints, handler yielding, reserved dimensions, font metric-overrides — markup/style/loading attrs only, reuse components/tokens) → Verify (Playwright @ breakpoints: re-measure all three vitals at p75 + Lighthouse; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Measured **INP ≤ 200ms**, **LCP ≤ 2.5s**, **CLS ≤ 0.1** at p75 on every configured breakpoint.
- LCP element is preloaded + `fetchpriority="high"` and not lazy-loaded; every image/embed has explicit dimensions or `aspect-ratio`; webfonts use `swap` + `size-adjust`; no layout-thrash read/write interleave in touched handlers.
- Sizes/spacing resolve to tokens (never raw px where a token exists); logic files unchanged (diff check).
- **Gate:** hard oracles green (all three vitals within budget + axe + console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/core-web-vitals/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: responsive` for layout-shift/sizing, `type: interaction` for INP, `oracle: hard` for any vital over budget; record the measured ms/score and `viewport` on every finding), plus the verification block (Lighthouse + per-breakpoint INP/LCP/CLS at p75, hard-oracle results, rubric score).

> **Watch (do not gate):** emerging field signals — long-animation-frame (LoAF) attribution for INP hotspots, and `Interaction to Next Paint` sub-part breakdown (input delay / processing / presentation). Track for prioritising fixes; do **not** treat as a hard oracle until standardised.

## Guardrails
Per `shared/guardrails.md`: change loading attrs / dimensions / handler scheduling — never event logic, data flow, or API calls (preserve behaviour byte-for-byte). Reuse size/spacing/font tokens before inventing; grep the token source, never guess a name. Read-only audit makes no edits; one writer for build; trust the measured trace over the diff; delete temp Playwright/Lighthouse scripts after.
