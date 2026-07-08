# Design Agent — Multiflow UI/UX Design System

A full-scale, agentic UI/UX design system: an **orchestrator** decomposes a design mandate into discrete, single-responsibility **workflows** (one per design responsibility), runs the **explore → judge → implement → verify** loop where *only one agent writes files* and a *separate skeptical evaluator* screenshots the live app, and gates on **hard oracles** (contrast, token conformance, console errors, viewport overflow) before **soft oracles** (taste, hierarchy, craft).

Grounded in NN/g, W3C WCAG 2.2 (POUR), Material Design 3, the W3C Design Tokens (DTCG) spec, Refactoring UI, Laws of UX, and Anthropic's orchestrator-worker + generator-evaluator harness design. The craft bar and locked patterns are distilled from a battle-tested production design agent.

> **Reusable by design.** Everything project-specific (brand, tokens, component library, dev-server, breakpoints, locked rules) lives in `project-design-config.md` — fill it per project and the same agent works anywhere. See the Rezolv24 instance for a worked example.

---

## Core thesis

Design has **two kinds of oracle**, and the architecture treats them differently:

- **Hard oracles** (deterministic, blocking gate): WCAG contrast ratios, axe-core violations, design-token/convention conformance (no hardcoded hex), **zero console errors**, no viewport overflow at any breakpoint. A failure here rejects the work and loops back.
- **Soft oracles** (rubric-judged, advisory): hierarchy, typographic rhythm, spacing discipline, restraint, polish — scored by a **separate skeptical evaluator** against an explicit rubric (generators praise their own mediocre work; never self-grade).

And one structural rule above all: **only one agent writes files.** Proposers and auditors are read-only; exactly one implementer edits, sequenced not parallel — parallel writers on a shared frontend conflict.

---

## The loop (per design task)

```
EXPLORE   → N read-only proposer agents produce DIVERGENT directions (specs only, no writes)
JUDGE     → 1 skeptical evaluator scores each vs the rubric + hard oracles; order swapped to kill position bias
IMPLEMENT → 1 writer applies the winning direction — layout/style/markup ONLY, logic byte-for-byte preserved
VERIFY    → Playwright drives the live app, screenshots EVERY state @ multiple viewports,
            axe-core + zero-console-errors gate; evaluator re-scores from screenshots → loop (≤N) or pass
```

A "new direction" = a genuinely different layout / information-architecture / interaction model — not the same screen recoloured.

---

## Architecture

```
                ┌──────────────────────────────────────┐
   mandate ────▶│  DESIGN ORCHESTRATOR                 │
                │  scope (1 / 2-4 / 10+), fan-out vs    │
                │  pipeline, dispatch, synthesize, gate │
                └───────────────┬──────────────────────┘
     ┌──────────────────┬───────┴────────┬─────────────────────┐
     ▼ (fan-out, R/O)    ▼                ▼ (pipeline, 1 writer) ▼ (gate)
 design-explorer ×N  design-reviewer  visual-designer  ───▶ design-judge
 (divergent dirs)    a11y-auditor      interaction-designer    (skeptical
                     ds-keeper         (the ONE writer)          evaluator)
     │                    │                   ▲                    │
     └──── judge picks 1 ─┘                   │   loop ≤15×         │
                                              └────────────────────┘
                              VERIFY: Playwright headless,
                              screenshots @ N viewports, axe-core,
                              zero console errors
```

---

## Workflow catalog (44)

Each lives in `workflows/<group>/<flow>.md` following `shared/workflow-template.md`.

### 00 · Visual foundations
1. `typography` — type scale + hierarchy (incl. tabular numerals for data)
2. `color-system` — accessible 50–900 ramps + semantic roles (light/dark)
3. `color-balance` — 60-30-10 proportion + accent discipline
4. `spacing-grid` — 4/8pt scale, internal ≤ external, grid/gutters
5. `elevation-depth` — shadow + tonal-surface elevation scale
6. `radius-iconography` — radii scale + icon grid/stroke/optical consistency

### 10 · Tokens & systems
7. `design-tokens` — three-tier primitive→semantic→component (DTCG JSON)
8. `component-library` — variants × full state matrix + docs; reuse-before-invent
9. `theming-branding` — token-swap themes preserving proportions
10. `design-system-governance` — SemVer, deprecation, managed migration
- `token-pipeline` — DTCG → Style Dictionary build + token-lint (schema/alias/dark-pairing/description) **(new)**

### 20 · Interaction
11. `interaction-states` — default/hover/focus/active/disabled/loading/empty/error/success
12. `motion-microinteractions` — 120–300ms timing/easing tokens + reduced-motion
13. `feedback-surfaces` — toast vs inline vs banner vs dialog + copy
14. `optimistic-ui` — instant update + rollback/reconcile
15. `progressive-disclosure` — accordions/show-more/drill-down (≤2 levels)

### 30 · Layout & IA
16. `information-architecture` — card-sort generate / tree-test evaluate
17. `responsive-density` — breakpoints + comfortable/compact modes
18. `form-design` — single-column, minimal fields, top labels, inline validation
19. `data-table-design` — alignment, sticky, pagination vs virtual scroll, bulk/inline/expansion
20. `dashboard-design` — bento KPI tiles, trend context, drill-down
- `user-flow-design` — multi-step task/user flows between screens (state carry, resume, drop-off) **(new)**

### 40 · Accessibility
21. `accessibility` — WCAG 2.2 AA (POUR): contrast, color-not-sole, keyboard/focus, target size, ARIA/semantics, alt/labels, motion/drag, auth/redundant-entry/help, error a11y; + SPA focus mgmt, forced-colors/prefers-contrast
- `aria-widget-patterns` — APG keyboard+role contract per composite widget (dialog/combobox/menu/tabs/grid) **(new)**

### 50 · Content design
22. `microcopy` — verb-first labels, the 3 C's
23. `error-empty-copy` — specific/human/actionable errors, empty + notification copy
24. `tone-voice` — voice/tone matrix, terminology + glossary governance
25. `content-hierarchy` — front-load, plain language, scannability

### 60 · Evaluation
26. `heuristic-audit` — Nielsen's 10 + behavioural UI scan → prioritized findings (0–4 severity)
27. `usability-testing` — qual (5-user rounds) vs quant, moderated/unmoderated
28. `cognitive-load` — recognition-over-recall, chunking, clutter reduction

### 70 · Process & craft
29. `design-exploration` — diverge → judge → converge (the loop)
30. `design-direction` — multi-screen set + design-system sheet deliverable
31. `design-qa-verify` — Playwright screenshot verification + visual regression
32. `handoff-spec` — Dev Mode redlines, token map, ready-vs-WIP
- `figma-design-to-code` — Figma Dev-Mode MCP + Code Connect (connect first, generate second) **(new)**
- `discovery-intake` — JTBD / problem-framing front door before exploration **(new)**
- `success-metrics` — HEART + analytics-instrumentation handoff (a production scoreboard) **(new)**

### 80 · Modern pattern playbook
33. `modern-patterns` — command palette, segmented controls, skeleton loading, bento, multi-step autosave wizard, onboarding, calm/dark/glass aesthetic

### 90 · Performance · Data-viz · i18n · Channels (new)

- `core-web-vitals` (90-performance) — INP/LCP/CLS as design budgets (hard oracle)
- `chart-design` (90-data-viz) — chart-type selection + chart accessibility + data integrity
- `i18n-foundations` (90-i18n) — dir/RTL, CSS logical properties, Intl formatting, translation-readiness
- `transactional-email-design` (90-channels) — email-client physics: table layout, inlined CSS, dark-mode email
- `notification-strategy` (90-channels) — in-app/push/email taxonomy, frequency, preference center

---

## Specialized subagents (`agents/`)

The definitions live in `agents/` (canonical, inside this system) and are symlinked into `.claude/agents/` only so the agent registry discovers them.


`design-orchestrator` (lead) · `design-explorer` (read-only proposer ×N) · `visual-designer` (the one writer) · `interaction-designer` (writer, sequenced) · `a11y-auditor` (read-only, axe-core) · `design-system-keeper` (read-only token/convention conformance) · `design-judge` (skeptical evaluator) · `design-reviewer` (heuristic/behavioural audit).

## Running it
**Default to the lightweight tier.** Most design work is small — dispatch the **`visual-designer` directly** (one agent, one round-trip, the calling assistant reviews). The full `design-orchestrator` is **slow** (fans out sub-agents that drive a real browser + run axe/contrast — minutes to tens of minutes) and is reserved for genuine multi-direction work. Don't reach for the orchestrator on routine polish; the calling assistant coordinates multi-item work item-by-item and pulls the orchestrator in only when a real explore→judge is needed.
- **Single screen tweak / small task (DEFAULT):** the `visual-designer` does it directly — no overhead, fast.
- **"Feels off" / multiple valid directions:** the orchestrator runs explore→judge→implement→verify.
- **Whole-app audit / redesign / token migration (MAX-required only):** orchestrator fans out auditors + proposers, pipelines the single writer, gates on hard oracles + rubric.

## Contracts (read first)
- `shared/workflow-template.md` — the shape every flow follows
- `shared/finding-schema.md` — the design finding/recommendation object
- `shared/quality-rubric.md` — the senior craft bar + hard vs soft oracles + scoring
- `shared/design-principles.md` — senior operating habits + the behavioural-scan checklist + how-you-work
- `shared/report-format.md` — per-flow `report.json` + roll-up
- `shared/guardrails.md` — preserve-logic / reuse-before-invent / one-writer / screenshot-verify
- `project-design-config.md` — the per-project abstraction layer (brand, tokens, components, dev-server, locked rules)
- `shared/responsible-ai-ethics.md` — HAX/PAIR + AI-disclosure + bias/fairness lens (esp. recruitment surfaces)
- `shared/deceptive-pattern-checklist.md` — EDPB dark-pattern taxonomy + fair-pattern alternatives (legal-risk)

## Non-goals (out of scope — stated, not accidental)

This is a **web/React UI-design + frontend-implementation** agent. It deliberately does NOT cover:
- **Native mobile** (iOS HIG / Android Material specifics — safe-areas, back-stack, platform nav), **spatial/AR/VR/visionOS**, **TV/10-foot/watch/wearable**.
- **Live moderated research execution** (recruiting + running participant sessions), **running A/B tests / live analytics dashboards** — it produces the *artifacts* (JTBD, personas, HEART + instrumentation specs) but a human/product runs the live work.
- **Service design / blueprinting** as a formal practice (the user-facing slice is covered by `user-flow-design`).
- **Brand/illustration/3D/logo production** and **sound/haptic/voice-UI** (except the screen-reader announcement experience, owned by accessibility/feedback flows).
- It changes **layout/style/markup, never application logic** (see `guardrails.md`).
