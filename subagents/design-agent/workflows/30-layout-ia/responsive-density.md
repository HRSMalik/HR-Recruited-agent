# responsive-density

**Group:** 30-layout-ia
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** audit (overflow + reflow scan) · build (reflow + density + verify)   ·   **Default model:** sonnet

## Purpose
Adapt layout, hierarchy, and information density across viewport sizes and density modes so nothing cramps, stretches, or overflows — the question "does this hold together from the narrowest to the widest project breakpoint, comfortable and compact?"

## Inputs & preconditions
- From `project-design-config.md`: breakpoints to screenshot, token source (spacing scale), component library, theme, locked density/scale rules.
- Target: the screen(s) under review at every configured viewport; the standard (content-first breakpoints + density theory).
- Preconditions: dev server reachable; confirm desktop-only before "fixing" mobile — don't invent a mobile layout the project doesn't ship.

## Oracle (source of truth)
Content-first responsive breakpoints (set the break where the *layout* actually breaks, not at device widths) + density theory (comfortable vs compact, −4dp/step). Modern responsive primitives — container queries, relational/quantity selectors, mobile viewport units, and safe-area/thumb-zone ergonomics — extend the same content-first principle from the viewport down to the component.
- **hard (verify):** no cramped / stretched / overflow / clipped content at any configured project breakpoint *or container size* — Playwright drives each viewport and asserts no horizontal scroll and no clipping. Mobile viewport must use dynamic units (`dvh`/`svh`) where the browser chrome collapses — assert no content trapped under collapsing chrome and no element clipped by a notch/home-indicator safe area.
- **soft:** hierarchy survives reflow (the right thing stays primary); spacing stays on the token scale in both density modes; container-query components adapt to their container, not the viewport; primary actions land in the mobile thumb zone.

## Standards & techniques
- **Content-first breakpoints:** add a break where the content stops working; common bands 320–480 / 481–768 / 769–1024 / 1025–1280 / 1281+ are a starting grid, not a mandate.
- **Density modes:** comfortable (default) vs compact; step spacing down ~4dp per level (e.g. inset 16→12→8) — change spacing tokens, never font legibility.
- **Reflow, don't shrink:** multi-column → stacked, side-nav → drawer, table → condensed/cards — preserve hierarchy through the reflow.
- **Verify the actual project widths:** if the project is desktop-only, test only its widths; don't manufacture a 320px layout it never renders.

### Container queries — component adapts to its container, not the viewport
A component placed in a sidebar, a main column, and a card grid sees three different widths at the same viewport — viewport breakpoints can't address that. Container queries let the component respond to the box it lives in. Baseline since Chrome/Edge 105, Firefox 110, Safari 16 (web.dev, *Container Queries Reach Baseline*) — safe in production with no per-browser fallback.
- **Establish a container:** set `container-type: inline-size` (or `size`) on the parent; name it with `container-name` (or shorthand `container:`) so nested containers stay unambiguous.
- **Query it:** `@container (min-width: 400px) { … }` switches the *component's* layout from its container's inline size, independent of the viewport.
- **Container query units:** `cqi`/`cqb` (inline/block), `cqw`/`cqh` (width/height), `cqmin`/`cqmax` — size type/padding relative to the container, not `vw`/`vh`. Use these for component-internal fluid sizing.
- **When to reach for a CQ vs a breakpoint:** a reusable component that ships in multiple slot widths → container query; a page-level layout shell → viewport breakpoint. Don't convert a one-placement page region to a CQ for its own sake.

### Relational & quantity queries — `:has()`
`:has()` lets a parent style itself from what it contains, removing layout-state classes that JS used to toggle.
- **Relational:** `.card:has(img)` adds media padding only when an image is present; `.field:has(:invalid)` flags the wrapper without a JS error class.
- **Quantity queries:** combine `:has()` with `:nth-child`/`:nth-last-child` patterns (e.g. `:has(> :nth-child(6))`) to switch a grid to a denser layout once the item count crosses a threshold — density driven by content count, not just width.
- Treat `:has()` reflow the same as any other: hierarchy must survive the state change.

### Mobile ergonomics — dynamic viewport units, safe areas, thumb zone
On mobile the viewport is not a fixed rectangle and not edge-to-edge usable.
- **Dynamic viewport units:** use `dvh`/`svh`/`lvh` (and `dvw`/`svw`/`lvw`) instead of `vh` for full-height regions. `svh` = smallest (chrome expanded), `lvh` = largest (chrome collapsed), `dvh` = dynamic (tracks the chrome live). `100vh` overflows under collapsing browser chrome and traps content below the fold — prefer `dvh` for app-shell height, `svh` for "must always be visible without scrolling."
- **Safe-area insets:** pad against the notch, rounded corners, and home indicator with `env(safe-area-inset-top|right|bottom|left)` — `padding-bottom: env(safe-area-inset-bottom)` on a sticky action bar so it clears the home indicator. Requires `viewport-fit=cover` in the viewport meta.
- **Thumb-zone reachability:** on phone widths, primary/destructive actions and the main nav belong in the lower reachable band, not pinned top-corner where a one-handed thumb can't reach. Keep tap targets ≥ the project's minimum touch size and clear of safe-area edges.

> **Watch (do not gate):** scroll-driven animations (`animation-timeline: scroll()/view()`), `@container style()` queries, and anchor positioning (`anchor()` / `position-area`) are EMERGING — uneven engine support. Note them in findings where relevant, but never assert them as a hard oracle until they reach Baseline.

## Step sequence
- **audit:** drive every configured viewport (both density modes if shipped) → for any container-query component, resize its container across its slot widths (sidebar / main / grid) independent of the viewport → assert no overflow/clip/cramp/stretch at every viewport *and* container size → check mobile full-height regions use `dvh`/`svh` (not `100vh`) and sticky action bars clear `env(safe-area-inset-bottom)` → confirm primary actions sit in the thumb zone at phone widths → flag breaks where hierarchy collapses or spacing leaves the scale → emit findings (read-only, no edits).
- **build:** Explore (≥2 reflow strategies per break, read-only) → Judge (overflow-free + hierarchy-preserved rubric, order-swapped) → Implement (one writer; responsive layout/markup + spacing-token density only, reuse components) → Verify (Playwright screenshots every state @ every breakpoint × density; assert zero overflow; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- No horizontal scroll, clipping, cramping, or stretching at any configured breakpoint × density, *or at any container-query slot width*.
- Hierarchy preserved through each reflow (viewport, container, and `:has()` state changes); spacing resolves to scale tokens, never raw px.
- Mobile full-height regions use `dvh`/`svh` — no content trapped under collapsing browser chrome; no element clipped by a safe-area edge; sticky action bars pad against `env(safe-area-inset-bottom)`; primary actions reachable in the thumb zone.
- **Gate:** hard oracles green (no overflow at any breakpoint *or container size*, no safe-area clipping / `100vh` trap on mobile, token-conformant spacing) AND (build) rubric mean ≥ 0.8. EMERGING primitives (scroll-driven animation, `style()` queries, anchor positioning) are Watch-only and never gate.

## Output
Write `artifacts/responsive-density/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: responsive`, `oracle: hard` for any overflow/clip at a breakpoint, container slot width, or safe-area edge; `viewport` named on every finding, plus the container slot width for container-query findings), plus the verification block listing each breakpoint × density screenshotted and each container slot width exercised. EMERGING primitives surface as `oracle: soft` Watch notes only.

## Guardrails
Per `shared/guardrails.md`: confirm the shipped breakpoint set before acting — never invent a mobile layout the project doesn't render. Layout/markup + spacing tokens only; preserve logic byte-for-byte. Read-only audit makes no edits; one writer. Trust the screenshot over the diff.
