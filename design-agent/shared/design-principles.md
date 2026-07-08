# Design Principles — Senior Operating Manual

The mindset and ready-to-run checklist that tie the workflows together. The `quality-rubric.md` is *what's scored*; this is *how a senior designer operates*. Project specifics (brand, tokens, components, dev-server, locked rules) live in `project-design-config.md`.

## How a senior designer operates (habits)

- **Think in principles & patterns, not one-off cases.** Before editing, ask whether the fix should be a reusable pattern (a component, a token, a layout primitive) so every sibling screen benefits. Solve it once, leave it reusable. Less obsessed with the single screen, more with the system.
- **Ask "why" and design the whole journey.** Solve the user's actual problem, not just the surface. Design **every state end-to-end**, not just the happy path: default, hover, focus, active, disabled, loading/skeleton, empty, error, success — and the edge cases (long names, zero rows, huge numbers, missing data, permission-locked). A screen isn't done until its off-states are designed.
- **Progressive disclosure.** Surface the one signal that answers "is this okay?" first; reveal detail on demand. Lead with the primary metric/action; tuck secondary controls behind hover/expand/a second tier. Clarity over clutter — show complexity only when the user is ready.
- **Layer-cake hierarchy.** For every component decide primary / secondary / tertiary and rank with size, weight, and colour: a clear headline → supporting subhead → quiet body/caption. Contrast carries the eye — a confident CTA on a calm muted ground. If a screen "feels off" but looks clean, hierarchy is usually the culprit.
- **Typography discipline.** One or two families, a small modular scale, generous line-height for body and tight for labels; tabular numerals in data. Never a flat wall of same-size text.
- **Depth with restraint.** Elevation + hairline borders to express relationships between surfaces — subtle, consistent, never ornamental. Depth must aid comprehension, not showcase skill.
- **Sweat the details.** Optical alignment, consistent icon size/stroke, matched control heights, even gaps, no orphaned/stranded elements. Self-critique each pass and fix the 1px inconsistencies — detail is what separates "good enough" from senior-grade.

## Form & layout instincts (generic)

- **Compress whitespace with discipline — don't blanket-pad or blanket-strip.** Use a 4/8pt scale; related fields close (8–12px), section breaks wider (16–24px). Stripping space everywhere flattens hierarchy and *raises* cognitive load — proximity communicates grouping.
- **Forms single-column** by default; multi-column only for genuinely paired short fields (City/State/ZIP). Minimize fields — every field is friction. Label above input; inline error under the field; validate on blur.
- **Constrain form width (~440–560px) and place it deliberately.** A small card pinned top-left of a wide area reads as "stranded/unfinished." Either centre it as a framed single-decision task, or fill the horizontal space usefully. The classic stranded-card cause: a width cap on an inner div while the page wrapper stays full-width — **cap the actual column**, not an inner div.
- **Keep actions with the fields** — primary action directly under the last field, secondary beside it; not pushed to a far footer separated by empty space.
- **Density without clutter** — a data-dense screen can still feel calm if alignment, grouping, and a consistent spacing rhythm are respected.

## Minimalist & consolidation (avoid filler, consolidate actions)

- **No filler or DUPLICATE content to fill space.** A second card/panel repeating the same fields reads as broken. When a screen has little data, **content-size it** (a centered/capped column, or two content-sized columns) rather than stretching a grid that forces dead voids. Cap the *content* (the field/column) so a card has no internal void — never strand a narrow field inside a much wider card.
- **Consolidate row-level actions into ONE control.** Don't put an inline button on every row. Make rows **status-only** and place a single trigger by the section/card title — a "Manage …" button opening a modal (best for security/confirm operations that need helper copy) or a row-actions dropdown (for quick switches).
- **Compact footers — no stranded footer band.** Put toggles + live validation checks on one inline band with the primary button pulled up beside/under them (e.g. `Show passwords · ✓ rule · ✓ rule …… [Submit]`), instead of a lone button in a tall footer separated by empty space. Validation rules show **live met-state** (a clear ✓ when satisfied, a muted marker when not).
- **Inline actions use a quiet/subtle button family** — soft-tint pills clearly subordinate to the page's solid primary CTA; destructive actions (Disable/Remove) lean danger-tinted. Prefer adding a **generic reusable variant/size to the Button component** over hand-styling one-off buttons.
- **Cohesive palette — keep new surfaces on the established surface system.** Don't introduce an off-palette surface (e.g. a dark band beside light cards) that clashes with the page chrome; harmonize with the existing surface/border tokens. Use AA-safe status-text colours (a darker green/amber that passes contrast on the surface) for value text, not the bright semantic tokens.

## Behavioural scan checklist (run on every review and before/after every build)

Drive the live screen at the project's breakpoints (incl. a narrow one to catch overflow). When auditing, return findings as a prioritised list (per `finding-schema.md`); when building, satisfy them in the output.

**Accessibility (treat as hard oracle unless noted) →** see `40-accessibility/accessibility.md`
- Focus visible (WCAG 2.4.7) on every interactive element — never `outline:none` without a replacement; a global `:focus-visible` ring is the cheap fix (the most-failed criterion — check first).
- Icon-only buttons carry an `aria-label`; decorative SVGs/dots `aria-hidden`.
- Clickable IDs/rows: URL-changing = real `<a>`/`<Link>` (Enter); action = `<button>` (Enter+Space). Never `onClick` a bare `<span>`/`<tr>`.
- Colour never the only signal (1.4.1) — pair with text/icon. Disabled controls stay legible (explicit muted colour, not vanishing opacity). Inputs have labels; required shows `*`.

**Data tables →** see `30-layout-ia/data-table-design.md`
- Watch column crowding/overlap at mid widths; condense/merge low-priority columns, `overflow-x:auto`, lock the first column, add a scroll-shadow affordance.
- Large sets → pagination ("X–Y of N"), not virtual scroll, for admin/report data. Filtered empty states show active filters + Clear. Avoid redundant double colour-coding of the same signal.

**Colour & tokens →** see `00-foundations/color-system.md`, `10-tokens-systems/`
- Prefer a structured 50–900 ramp over one-off inline tints; map ad-hoc tints onto tokens. Shadows/radii via tokens, not per-component. Test light AND dark.

**Whitespace / density →** see `00-foundations/spacing-grid.md`
- 4/8px scale; "internal ≤ external" (an element's outer spacing ≥ its inner). Group related fields tight, separate groups with more space. Rhythmic, consistent — not blanket whitespace.

**Craft & polish (the senior bar) →** `quality-rubric.md`
- Clear primary/secondary/tertiary hierarchy; the eye lands right first. All states designed (hover/focus/active/disabled/loading/empty/error/success) — empty states get an icon + a next action. Motion present, purposeful, 120–300ms ease-out, `prefers-reduced-motion` respected. Detail pass: optical alignment, matched control heights, even gaps, hairline borders + restrained depth. If it looks "default/bootstrappy", it fails.

**Responsive →** see `30-layout-ia/responsive-density.md`
- Flag fixed widths that clip at narrow breakpoints; confirm a screen is desktop-only before "fixing" mobile.

## How you work

1. Read the target screen + the relevant components/tokens (from `project-design-config.md`) before editing.
2. Trivial fix → the smallest change that fixes the feel (container width, gaps, padding, grouping, component choice). Non-trivial / "feels off" with multiple valid directions → run explore → judge → implement → verify (`70-process/design-exploration.md`).
3. Keep behaviour identical unless asked — change layout/spacing/composition, not logic.
4. Always build and drive the live screen and screenshot to verify — don't trust the diff alone.
5. Report what changed in spacing-system/token terms (e.g. "capped the column at 460px, centred it in a grid frame, field gap 16→12, actions moved under the last field"), and flag any deliberate inconsistency with sibling screens so it's a conscious choice, not an accident.
