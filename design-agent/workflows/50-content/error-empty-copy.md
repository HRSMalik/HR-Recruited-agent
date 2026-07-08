# error-empty-copy

**Group:** 50-content
**Runs as:** inline
**Mode:** build (writer + verify loop) · audit (state-copy scan)   ·   **Default model:** sonnet

## Purpose
Own the copy of the unhappy and the void states — error messages, empty states, no-results, confirmation dialogs — so each one tells the user what happened, why, and the one next thing to do.

## Inputs & preconditions
- From `project-design-config.md`: component library (AlertBanner variants, EmptyState, FormModal), token source, dev-server URL/port + creds, breakpoints, locked rules (status never colour-alone).
- Target: every error/empty/no-results/confirmation surface on the screen; the relevant guidance (NN/g error & empty-state guidance); the non-visible copy surfaces this flow owns — `alt` text on every image and the polite/assertive announcement strings on status/error live regions.
- Preconditions: dev server reachable; existing AlertBanner/EmptyState components read; states reachable to screenshot (trigger the error, empty the list).

## Oracle (source of truth)
NN/g error-message + empty-state + confirmation guidance; W3C WAI alt-text decision tree (`w3.org/WAI/tutorials/images/decision-tree/`) for the authored non-visible copy this flow owns.
- **hard:** an error names the specific problem using the user's own data, contains no blame/jargon, offers the fix in ≤2 sentences, sits near its source, is **not colour-alone** (icon/text redundant), and the user's input is preserved; an empty state is never a bare blank; every informative image carries meaningful `alt` and every decorative image carries empty `alt=""`; status/error live regions announce a concise polite (or assertive, when urgent) string — never silent, never the raw colour/icon alone.
- **soft:** human tone; empty state teaches + directs; confirmations gated to consequential/irreversible actions; undo preferred over a confirm dialog; announcement strings stay short enough to finish before the user moves on, and read naturally when localized.

## Standards & techniques
- **Errors:** specific (echo their value), human (no "invalid input", no error codes alone), actionable (state the fix), near the field, colour + icon + text redundant, input never cleared.
- **Empty states:** communicate status + teach what goes here + a direct CTA — never a bare blank (a blank reads as loading). No-results offers next steps (broaden filter, clear search).
- **Notifications/confirmations:** name outcomes on the buttons (`Delete file` / `Keep file`, not `OK` / `Cancel`); confirm only for consequential/irreversible actions; prefer an **undo** toast over an upfront dialog.
- **Authored non-visible copy (alt + announcements):** `alt` text and ARIA live-region announcement strings are content this flow owns and ships — not just the visible characters. Per the W3C WAI alt decision tree (`w3.org/WAI/tutorials/images/decision-tree/`): an **informative** image (status icon that carries meaning, illustrative empty-state art that says something) gets meaningful `alt` describing its information, not its appearance; a **decorative** image (pure ornament, an icon already labelled by adjacent text) gets empty `alt=""` so a screen reader skips it. Announcement strings on status/error live regions are **polite** for non-urgent updates (results loaded, filters applied) and **assertive** for ones that interrupt (a destructive action failed, the form was rejected) — keep each one concise, plain-language, and the same content as the visible message so nothing is colour- or icon-only. Both `alt` and announcement strings are **localizable surfaces**: route them through the same string source as visible copy, never hardcode, and write them to read naturally once translated.

## Step sequence
- **audit:** Enumerate each error/empty/no-results/confirm state → assert specific+human+actionable+near-source+colour-redundant+input-preserved (and bare-blank check) against the oracle → check the authored non-visible copy: informative images carry meaningful `alt`, decorative ones carry `alt=""`, status/error live regions announce a concise polite/assertive string matching the visible message → emit findings (read-only).
- **build:** Explore (≥2 copy sets, read-only) → Judge (rubric: specificity/actionability/tone, order-swapped) → Implement (one writer; copy + AlertBanner/EmptyState wiring only) → Verify (screenshot every state incl. error/empty/no-results @ breakpoints; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every error is specific, blame-free, actionable in ≤2 sentences, near its source, colour-redundant, input preserved.
- No empty state is a bare blank; no-results offers a next step; confirm dialogs only on irreversible actions, buttons name outcomes.
- Every informative image has meaningful `alt`; every decorative image has empty `alt=""`; every status/error live region announces a concise polite/assertive string carrying the same content as the visible message; both `alt` and announcement strings come from the localizable string source, not hardcoded.
- **Watch (do not gate):** AI-generated empty-state illustrations and emerging in-product "assistant" status messages are increasingly authored copy surfaces too — note any present (do their `alt` and announcement strings exist and read naturally when localized?) as an observation, but do not block the gate on them.
- **Gate:** hard oracles green AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/error-empty-copy/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: content`, `heuristic: NN/g error/empty-state`; `oracle: hard` for blame/jargon, colour-alone, lost input, bare blank), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: change copy + component props only — never validation, error-trigger logic, or data flow. Reuse AlertBanner/EmptyState/FormModal before inventing. Status never colour-alone (locked rule). Read-only audit makes no edits; one writer for build.

## Related
- `accessibility.md` — owns the structural/semantic side of `alt` and live regions (the `alt` attribute exists, `aria-live`/`role="status"`/`role="alert"` is wired, focus/announcement order is correct); this flow owns the **wording** that goes inside them.
- `feedback-surfaces.md` — owns when and where a status/error surface fires; this flow owns the announcement string it speaks.
