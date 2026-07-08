# progressive-disclosure

**Group:** 20-interaction
**Runs as:** subagent: ../.claude/agents/interaction-designer.md
**Mode:** build (writer + verify loop) · audit (disclosure-depth scan)   ·   **Default model:** sonnet

## Purpose
Own information layering: surface what's needed frequently up front and tuck the rest behind clearly-labelled disclosure controls — so the common task is one glance, and advanced detail is reachable without clutter.

## Inputs & preconditions
- From `project-design-config.md`: component library (accordion, show-more, drill-down, `Card`/`SectionHeader` — reuse before inventing), token source + names, breakpoints, theme, locked rules.
- Target: dense screens — detail panes, settings, long forms, record views — and the task each user comes to do.
- Preconditions: dev server reachable; the frequency of each piece of information understood (what's primary vs occasional).

## Oracle (source of truth)
NN/g progressive disclosure + the rule that nothing essential is buried beyond two levels.
- **hard:** **max ~2 disclosure levels** — nothing essential is reachable only at level 3+; every disclosure control has **clear information scent** (a descriptive label that tells you what's behind it, not "More…"); the disclosed region is keyboard-operable and its expanded/collapsed state is exposed (`aria-expanded`).
- **soft:** common tasks need no extra clicks (the frequently-needed is already visible); the primary/secondary split is sensible; controls read as obviously expandable.

## Standards & techniques
- **Disclose frequently-needed up front:** primary info and the common-path action are visible without interaction; only occasional/advanced detail is hidden.
- **Two levels max:** primary surface → one disclosure → (at most) one more. If something essential needs a 3rd level, the IA is wrong — restructure, don't nest deeper.
- **Information scent on the control:** the trigger names its payload — *"Show salary & benefits"*, *"Edit screening questions"* — never a bare "More" / chevron-only.
- **Pattern by shape:** accordion for peer sections; show-more for a truncated list/text; drill-down for hierarchical detail. Reuse the library's components.
- **State exposed:** `aria-expanded`, focusable trigger, region revealed in DOM order so keyboard + AT follow it.

## Step sequence
- **audit:** map each information element to its frequency and its disclosure depth → check the frequently-needed is visible up front and nothing essential sits beyond level 2 → check every disclosure control has a descriptive label + `aria-expanded` → flag buried essentials, scent-less controls, over-deep nesting → emit findings (read-only).
- **build:** Explore (≥2 disclosure structures from existing components, read-only) → Judge (frequency-up-front + ≤2-levels + information-scent rubric, order-swapped) → Implement (one writer; build accordions/show-more/drill-down from existing components/tokens, label each control, wire `aria-expanded`) → Verify (Playwright screenshots collapsed + expanded states + the keyboard path @ breakpoints; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Frequently-needed info + the common action are visible up front; nothing essential beyond 2 disclosure levels.
- Every disclosure control has a descriptive (scented) label and exposes `aria-expanded`; region is keyboard-operable.
- Built from existing components; all colour/spacing resolves to tokens.
- **Gate:** hard oracles green (≤2 levels + information scent + keyboard/`aria-expanded` + axe + console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/progressive-disclosure/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: heuristic`, `oracle: hard` for a buried essential / scent-less control, `heuristic` Nielsen #8 Aesthetic & minimalist design), plus the verification block (collapsed + expanded + keyboard captures @ breakpoints + hard-oracle results + rubric score).

## Guardrails
Per `shared/guardrails.md`: reuse accordion/show-more/drill-down components before inventing; never guess a token name — grep the source. Preserve logic byte-for-byte (markup/style only). Read-only audit makes no edits; one writer for build; trust the screenshot over the diff.
