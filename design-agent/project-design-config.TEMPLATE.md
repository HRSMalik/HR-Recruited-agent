# Project Design Config — TEMPLATE

> **Generic structure only — fill per project (or let the orchestrator fill it).** When the
> design-agent is dropped into a project, the `design-orchestrator` **auto-creates** the real
> `project-design-config.md` (no `.TEMPLATE` suffix) by scanning that project's codebase. This file is
> just the **section structure + what each section holds** — do NOT hardcode one project's brand,
> tokens, or components here. The generic, project-agnostic craft lives in `design-principles.md`;
> what's *scored* lives in `quality-rubric.md`. Route design work through the `design-orchestrator`.

## Brand & aesthetic
- Theme (light / dark / both), the primary + accent colour(s) and where each is used, the type stack and density scale, the overall feel/positioning, and any parked alternate brand. Locked brand rules (e.g. status never by colour alone; conventional over gimmicky; legible-not-oversized).

## Tokens
- **Token source file** (the project's CSS / theme file). List the **REAL token names** — grep the source, never guess — for colours, surfaces/backgrounds, text, borders, inputs, radii, shadow.
- Flag commonly-mistyped names (the ones that *look* right but don't exist and silently fall back).
- Flag **AA-fail tokens** (bright semantic colours that fail contrast as text on the surface) and give the darker text-safe values to use instead.
- Style-object source (if the project centralizes inline-style objects). The colour rule for the stack (inline `style` vs utility classes — and whether utility-class CSS-var refs resolve).

## Component library
- Components dir + the reusable inventory grouped (layout/shell · containers · inputs · actions/feedback · data/status · nav/controls · domain controls). Headless primitive lib (if any). Charting lib.

## Standards & budgets
- Accessibility target (WCAG level). Performance budget (Core Web Vitals). Device/viewport matrix (desktop-only? responsive?).

## Internationalization
- Default direction, locales, translation-readiness.

## Dev server & verification
- Frontend/backend start commands + base URLs/ports, screenshot **login credentials**, breakpoints to screenshot, Playwright/automation conventions.

## Locked rules (seed EMPTY — fills as the user iterates)
- Project-specific design rules the user has locked in (e.g. table-alignment conventions, dashboard rules), plus the **bindings** for the generic minimalist rules from `design-principles.md` (which Button variants, which AA-safe hex, which surface tokens this project uses).

## Stack-mapped pattern playbook
- The generic modern patterns (progressive disclosure, skeleton loading, optimistic UI, bento dashboards, empty states, inline-vs-toast, data-table power patterns, wizards, command palette, segmented control) — mapped to THIS project's actual components + state layer so they stay easy to build.

## Design output — drop folder (BAKED-IN bootstrap)
When the design-agent **creates designs first** (a design-direction set, an explored concept set, standalone mockups — visuals authored before/instead of editing the live app), it drops them into a **`designs/` folder at the project root — auto-created if missing** (`mkdir -p designs/<slug>`), one subfolder per effort:
- `designs/<slug>/*.html` — standalone, self-contained screens (real tokens; no raw hex where a token exists)
- `designs/<slug>/<slug>.pdf` — a single compiled PDF "book" of all the mockups, produced on completion (headless Chrome `--print-to-pdf` / puppeteer). **The deliverable is the PDF book, NOT per-screen PNGs.** (Live-app verify/audit screenshots are a separate ephemeral QA concern.)
- `designs/<slug>/README.md` — screen list + token map + one-line rationale per screen

The design analog of the qa-agent's `test-cases.md`. Explore→judge→verify *run reports* go to `artifacts/<flow>/`; the actual designs land in `designs/<slug>/`. Never scatter mockups elsewhere. (`<slug>` = the feature/screen, kebab-case.)

## Crash-protection / logic rules
- When touching logic: guard clauses / optional chaining, preserve existing behaviour exactly. The designer changes layout/spacing/composition, NOT logic.
