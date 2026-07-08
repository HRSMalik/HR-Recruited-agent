# modern-patterns

**Group:** 80-patterns
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** build (writer + verify loop) · audit (pattern-fit scan)   ·   **Default model:** sonnet

## Purpose
The pattern playbook: pick the right interaction pattern for the job, map it to the project's component library, and reach for the advanced version only when it earns its keep — never a command palette on a three-link app.

## Inputs & preconditions
- From `project-design-config.md`: component library, token source + names, theme (light/dark/both), breakpoints, aesthetic direction, locked rules.
- Target: the screen/flow + the job it does (navigate, re-present, wait, multi-step entry, first-run).
- Preconditions: components dir grepped first — map the pattern onto existing components before inventing.

## Oracle (source of truth)
The established pattern's spec + the "does it earn its keep" test — complexity must be justified by the job, not added for novelty.
- **hard:** keyboard operability (focus order, ⌘K toggle, Esc to close), contrast incl. any glass surface (text ≥ 4.5:1 needs a solid barrier), axe 0 violations, zero console errors.
- **soft:** the pattern fits the job (below); restraint and calm; the advanced variant is justified.

## Standards & techniques
- **Command palette (⌘K):** global toggle, fuzzy search, full keyboard-nav — only when the surface has enough actions/destinations to warrant it.
- **Segmented vs tabs vs toggle:** tabs = navigate to different content; segmented control = re-present the *same* content (e.g. view switch); toggle = a binary on/off.
- **Loading affordance by duration:** skeleton for a full-page load < 10s; spinner for 2–10s; determinate progress bar for > 10s.
- **Bento grid:** tile size = importance; ~10–15 tiles max before it turns to noise.
- **Multi-step wizard + autosave:** 1–3 fields per step, visible progress, free Back with no data loss, inline validation, required* / optional marked.
- **Onboarding:** contextual / just-in-time over forced tours; instructive empty states (icon + next action) over a coach-mark gauntlet.
- **Calm / low-stimulus 2026 aesthetic:** restrained colour, purposeful spacing, accessibility as infrastructure, dark-mode; glassmorphism only with a solid barrier so text holds ≥ 4.5:1.

## Step sequence
- **audit:** identify the job → check the chosen pattern fits (tabs vs segmented vs toggle; correct loading affordance; palette justified) → flag mismatches + over-engineering → emit findings (read-only).
- **build:** Explore (read-only; pick the pattern for the job, map to existing components, confirm the advanced variant earns its keep) → Judge (fit + restraint + keyboard-operability rubric, order-swapped) → Implement (one writer; build the pattern from existing components/tokens, full keyboard support) → Verify (Playwright screenshots every state + ⌘K/keyboard paths @ breakpoints; contrast incl. glass, axe, zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- The pattern matches the job (no tabs where segmented belongs; loading affordance matches the duration band).
- The advanced variant is justified, not novelty; the pattern is built from existing components/tokens.
- Keyboard-operable (⌘K toggle, focus order, Esc); glass text ≥ 4.5:1 over a solid barrier.
- **Gate:** hard oracles green (keyboard, contrast, axe, console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/modern-patterns/report.json` per `shared/report-format.md` — the chosen pattern + the job it serves, the component mapping, plus the verification block (screenshots incl. keyboard states + viewports + hard-oracle results + rubric score); mismatches/over-engineering as findings per `finding-schema.md`.

## Guardrails
Per `shared/guardrails.md`: reuse the component library before inventing a pattern; don't reach for the advanced version unless the job justifies it. Preserve logic byte-for-byte (markup/style only). Read-only audit makes no edits; one writer for build. Trust the screenshot over the diff.
