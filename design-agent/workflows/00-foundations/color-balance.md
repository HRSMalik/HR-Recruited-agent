# color-balance

**Group:** 00-foundations
**Runs as:** subagent: ../.claude/agents/visual-designer.md
**Mode:** build (writer + verify loop) · audit (proportion + status scan)   ·   **Default model:** sonnet

## Purpose
Own colour proportion and accent discipline: a calm 60-30-10 surface where the accent earns the eye, and status is never carried by colour alone.

## Inputs & preconditions
- From `project-design-config.md`: brand/palette, token source + real token names (grep before use), theme, colour rule, locked brand rules (e.g. accent rationed; status never colour-alone).
- Target: the screen(s) under review + every status indicator on them.
- Preconditions: token source readable; role tokens from `color-system` read before acting.

## Oracle (source of truth)
The 60-30-10 proportion heuristic (Refactoring UI / interior-design rule) + WCAG 1.4.1 Use of Colour.
- **hard:** status/meaning is never conveyed by colour alone — every status colour is paired with a label or icon (WCAG 1.4.1); status pairings still clear the contrast threshold.
- **soft:** proportion reads as ~60% neutral surface / ~30% secondary / ~10% accent; the accent stays rationed and earns attention rather than flooding.

## Standards & techniques
- **60% dominant neutral** (surface/background), **30% secondary** (supporting tone/containers), **10% accent** (the one colour that earns attention — CTAs, key emphasis).
- **Accent discipline:** the accent is rationed as chrome; if everything is accented, nothing is.
- **Status never colour-alone:** success/warning/danger/info always pair the hue with a label or icon (a `Badge`/`StatusPill`/`AlertBanner` from the component lib), never a bare coloured dot.

## Step sequence
- **audit:** estimate the neutral/secondary/accent split across the screen → list every status indicator and check each pairs colour with a label/icon → flag accent overuse → emit findings (read-only).
- **build:** Explore (≥2 proportion treatments, read-only) → Judge (60-30-10 + accent-restraint rubric, order-swapped) → Implement (one writer; pull accent back to ~10%, wire status to label+icon components) → Verify (Playwright screenshots every state @ breakpoints; assert status has non-colour cue; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Surface reads ~60/30/10; accent rationed to key actions only.
- Every status indicator carries a label or icon, not colour alone; status contrast clears threshold.
- **Gate:** hard oracles green (status-not-colour-alone, WCAG 1.4.1) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/color-balance/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: accessibility` + `wcag_ref: 1.4.1` for colour-alone status, `type: visual` for proportion/accent), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: reuse status components from the lib before inventing; use accent/neutral role tokens, never hardcode. Preserve logic byte-for-byte. Read-only audit makes no edits; one writer for build.
