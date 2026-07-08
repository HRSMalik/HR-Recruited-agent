# motion-microinteractions

**Group:** 20-interaction
**Runs as:** subagent: ../.claude/agents/interaction-designer.md
**Mode:** build (writer + verify loop) · audit (motion-conformance scan)   ·   **Default model:** sonnet

## Purpose
Own motion: tune every animation to the right duration and easing so it clarifies, guides, or confirms — and ensure each one degrades gracefully under reduced-motion. Motion that doesn't do a job is removed.

## Inputs & preconditions
- From `project-design-config.md`: token source + names (motion/duration/easing tokens), component library, breakpoints, theme, locked rules.
- Target: every transition/animation on the screen — state changes, entrances/exits, expand/collapse, toasts, loaders, page transitions.
- Preconditions: dev server reachable; existing motion tokens read before any new timing is invented.

## Oracle (source of truth)
Material motion timing bands + the WCAG 2.3.3 reduced-motion requirement.
- **hard:** **EVERY animation has a `prefers-reduced-motion: reduce` fallback** (motion replaced by an instant/opacity-only change, asserted in that media state); durations come from **motion tokens**, never ad-hoc inline ms.
- **soft:** the motion clarifies / guides / confirms — or it's removed; easing matches the direction (entrance vs exit); nothing draws attention to itself.

## Standards & techniques
- **Duration bands:** micro-interactions 100–200ms (hover, press, toggle); transitions 200–300ms (**Material standard 200ms**); page-level up to ~400ms. < 100ms is unnoticed (skip it); > 400ms reads sluggish.
- **Easing:** **ease-out for entrances** (decelerate in), **ease-in for exits** (accelerate out), ease-in-out for moves between two on-screen positions; **never the `linear` keyword** for UI (it reads mechanical — reserve for spinners only). **The "never linear" rule bans the `linear` KEYWORD, not the `linear()` FUNCTION** — a generated spring/bounce curve compiles to a many-stop `linear(...)` and is a legitimate easing; never flag `linear()` as a linear-easing violation.
- **Spring/bounce easing via `linear()`:** express spring and bounce as a `linear()` easing function (a sampled curve, e.g. `linear(0, 0.5 25%, 1.1, 1)`) rather than emulating it with JS frame loops. Token it like any other easing (`motion.easing.spring`); the audit must treat `linear()` as token-backed easing, not ad-hoc.
- Motion serves one of three jobs — clarify a change, guide the eye, confirm an action; anything else is decoration and gets cut.
- All durations/easings as **tokens** (`motion.duration.fast` / `motion.easing.standard`), reused across the system — no per-element magic numbers.

## Modern transition techniques
- **View Transitions API:** for same-document state/route changes wrap the DOM mutation in `document.startViewTransition(() => updateDOM())`; the browser snapshots before/after and cross-fades the root. Promote specific elements to **shared-element morphs** by giving them a matching `view-transition-name` on both states so the browser tweens position/size between them. For multi-page navigations use the **cross-document** form (`@view-transition { navigation: auto; }` in CSS) so the morph spans a full page load. Style the generated pseudo-elements (`::view-transition-old/new(name)`) with **motion tokens** — same duration bands and direction-matched easing as everything else; gate the whole effect behind `prefers-reduced-motion: reduce` (no snapshot, instant swap).
- **FLIP as the fallback:** where View Transitions is unsupported, fall back to **FLIP** (First-Last-Invert-Play) — measure first/last rects, apply the inverted transform, then play it out — to reproduce the shared-element morph. Feature-detect (`if (document.startViewTransition) … else FLIP`); never let an unsupported browser drop to an instant jump when a FLIP path exists.
- **Animating top-layer + `display:none` entry/exit:** elements that enter from `display:none`, or live in the **top layer** (`dialog`, `popover`), can't transition on the first frame without help. Set the entry start state in a **`@starting-style`** block, and add **`transition-behavior: allow-discrete`** so discrete properties (`display`, `overlay`) animate as part of the same transition instead of snapping — this is what lets a popover/dialog both fade in and fade out. Direction-match the easing (ease-out in, ease-in out) and token the durations as usual; under `reduce`, collapse to an opacity-only or instant change.
- **Animating to `height: auto` (the accordion problem):** to expand/collapse to intrinsic size set **`interpolate-size: allow-keywords`** (on `:root` or an ancestor) so a transition can interpolate to/from `height: auto` (and other size keywords) instead of needing a hardcoded pixel target or a `max-height` hack. Keep it inside the 200–300ms transition band with direction-matched easing, token-backed, with a `reduce` fallback.

### Watch (do not gate)
- **Scroll-driven animations** (`animation-timeline: scroll()` / `view()`) — progress-linked motion tied to a scroll or view-progress timeline. Treat as **progressive enhancement only**: layer it on top of a design that already reads correctly with no scroll animation, feature-detect support, and respect `prefers-reduced-motion`. Do **not** make it a hard oracle and do not fail an audit for its absence — note it as an opportunity, never a gate. Source: developer.chrome.com View Transitions (2025).

## Step sequence
- **audit:** enumerate every animated transition (including View-Transition pseudo-elements, `@starting-style`/`allow-discrete` entry-exit, and `interpolate-size` expands) → measure duration + easing against the bands → confirm a token backs each one → toggle `prefers-reduced-motion: reduce` and check every animation has a fallback → flag the `linear` **keyword** (but **never** the `linear()` function — a generated spring), off-band durations, ad-hoc ms, and any motion with no fallback or no job → emit findings (read-only).
- **build:** Explore (≥2 motion specs from existing tokens, read-only) → Judge (timing-band + easing-direction + reduced-motion + purpose rubric, order-swapped) → Implement (one writer; wire transitions to motion tokens, add the reduced-motion media query) → Verify (Playwright screenshots/records key transitions @ breakpoints in **both** default and reduced-motion emulation; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every animation has a reduced-motion fallback; under `reduce` no non-essential motion plays.
- Micro-interactions 100–200ms, transitions 200–300ms; no linear easing on UI; no off-band or ad-hoc durations.
- Every duration/easing resolves to a motion token; every retained animation does a clarify/guide/confirm job.
- **Gate:** hard oracles green (reduced-motion fallback on all + token-backed timing + axe + console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/motion-microinteractions/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: interaction`, `oracle: hard` for a missing reduced-motion fallback or ad-hoc ms, `wcag_ref` 2.3.3 Animation from Interactions where relevant), plus the verification block (transition captures in default + reduced-motion @ breakpoints + hard-oracle results + rubric score).

## Guardrails
Per `shared/guardrails.md`: reuse motion tokens before inventing a timing; never guess a token name — grep the source. Preserve logic byte-for-byte (style/markup only). Read-only audit makes no edits; one writer for build; trust the screenshot over the diff.
