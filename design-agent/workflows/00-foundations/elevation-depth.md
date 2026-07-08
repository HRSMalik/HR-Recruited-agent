# elevation-depth

**Group:** 00-foundations
**Runs as:** subagent: ../.claude/agents/visual-designer.md
**Mode:** build (writer + verify loop) · audit (elevation-token scan)   ·   **Default model:** sonnet

## Purpose
Own depth: a small, consistent elevation scale (shadow + tonal surface) where each layer maps to exactly one elevation token, with hairline borders and subtle — never heavy — separation.

## Inputs & preconditions
- From `project-design-config.md`: token source + real elevation/shadow/surface-token names (grep before use), theme (light/dark/both), colour rule, locked aesthetic rules.
- Target: the cards/surfaces/overlays under review and their stacking order.
- Preconditions: token source readable; existing elevation/shadow tokens read before acting.

## Oracle (source of truth)
Material 3 elevation model (shadow + tonal-surface) + the airy-over-boxy craft bar (Refactoring UI).
- **soft:** each visual layer maps to exactly one elevation token from the scale; shadows stay subtle; borders are hairline; radii are used consistently; surfaces read light and airy, never heavy or boxy.
- **hard (carried from the system):** elevation/shadow/surface values resolve to real tokens — no hardcoded shadow/colour where a token exists; any text on a tonal surface still clears contrast (1.4.3) in both themes.

## Standards & techniques
- **Elevation scale:** a short ladder (e.g. flat → raised → overlay → modal) — each step a named token combining a shadow and a tonal surface tint; light-mode leans on shadow, dark-mode on tonal surface.
- **One token per layer:** a card is one elevation; a popover one above it; a modal at the top — never mix two shadow values for the same conceptual layer.
- **Hairline borders + subtle shadows:** prefer a 1px border token and a soft low-spread shadow over a heavy drop shadow; consistent radii across surfaces.

## Step sequence
- **audit:** map each surface to its elevation token → flag any hardcoded shadow, heavy/inconsistent shadow, or two values for one layer → check border weight + radius consistency → emit findings (read-only).
- **build:** Explore (≥2 elevation ladders, read-only) → Judge (one-token-per-layer + subtlety rubric, order-swapped) → Implement (one writer; assign each layer a single elevation token, swap heavy shadows for hairline+soft) → Verify (Playwright screenshots every state @ breakpoints, light+dark; assert token conformance + contrast on tonal surfaces; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every layer maps to one elevation token; shadows subtle; borders hairline; radii consistent.
- No hardcoded shadow/surface where a token exists; tonal-surface text clears contrast both themes.
- **Gate:** hard oracles green (token conformance + contrast) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/elevation-depth/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: visual` for depth/subtlety mapping, `type: token` for hardcoded shadow/surface), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: use elevation/shadow tokens — grep the source, never guess a token; reuse the existing ladder before adding a step. Preserve logic byte-for-byte. Read-only audit makes no edits; one writer for build.
