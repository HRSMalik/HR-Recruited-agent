# form-design

**Group:** 30-layout-ia
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** audit (form-heuristic scan) · build (re-layout + verify)   ·   **Default model:** sonnet

## Purpose
Lay out forms (e.g. the candidate apply flow, recruiter create-role / edit-candidate forms) for fast, error-resilient completion — single-column, minimal fields, visible labels, validation that helps rather than punishes.

## Inputs & preconditions
- From `project-design-config.md`: component library (`Input`, `TextArea`, `Select`, `Button`, `AlertBanner`, …), token source, style-object source, breakpoints.
- Target: the form(s) under review; the standard (NN/g forms guidance).
- Preconditions: dev server reachable; existing form components/styles read before re-laying-out — reuse, don't reinvent inputs.

## Oracle (source of truth)
NN/g forms guidance + measured outcomes.
- **hard:** single-column flow; every field has a visible top-aligned `<label>` (never placeholder-as-label); on a validation error the user's input is preserved (not wiped); the form column is actually capped (~440–560px) — not a capped inner div stranded inside a full-width wrapper; **errors are programmatically associated** — each invalid field carries `aria-invalid` and its inline error is linked via `aria-describedby`/`aria-errormessage`, grouped inputs are wrapped in `<fieldset>`/`<legend>`, an error-summary renders at the top of the form on submit, and focus moves to the first invalid field; **name/address/phone fields are locale-aware** — no single forced first/last split assuming Western name order, no US-shaped state/zip lockstep, and phone accepts an international format (not a hardcoded US mask).
- **soft:** field count is minimised (drop anything not required now); inline validation reads well; the layout feels deliberate, not stranded or sprawling.

**Watch (do not gate):** native customizable `<select>` (`appearance: base-select` + `::picker`) paired with `field-sizing: content` is emerging — where used, it must progressively enhance over a working JS combobox / native `<select>`, never replace it. Note it; never gate on it.

## Standards & techniques
- **Single column by default:** one-try success ~78% single-column vs ~42% multi-column — only split when fields are truly parallel (e.g. city/state/zip).
- **Top-aligned visible labels:** label above the field; never use the placeholder as the label (it vanishes on focus and fails screen readers).
- **Inline validation after blur, near the field:** validate when the user leaves the field, message beside/under it; preserve their input on error.
- **Constrain + place the column deliberately:** cap the *actual* column ~440–560px and either centre it as a framed task **or** fill the horizontal space — a capped inner div in a full-width wrapper reads as a stranded card.
- **Primary action under the last field:** the submit button sits directly below the final field, in the column's reading flow.
- **Programmatic error association (a11y, not just visual):** set `aria-invalid="true"` on each errored field and link its inline message with `aria-describedby`/`aria-errormessage`; wrap genuinely grouped inputs (a name pair, an address block, a radio set) in `<fieldset>` with a `<legend>`; on a failed submit render an error-summary at the top of the form linking to each invalid field, then move focus to the first invalid field. Red borders alone are not an oracle pass — the association has to be in the DOM (per w3.org WAI ARIA21).
- **Locale-aware name/address/phone:** do not hardcode Western name order or a US address shape. Prefer a single full-name field (or a swappable given/family order) over a forced first/last split; treat state/province and postal code as locale-driven rather than a US state-dropdown + 5-digit-zip lockstep; accept an international phone format instead of a fixed US mask. Cross-link `i18n-foundations` for locale rules, ordering, and field-shape source of truth.

## Step sequence
- **audit:** drive the live form → check column count, label presence/position, placeholder-as-label, error-state input preservation, column cap + placement, submit position, **error association** (`aria-invalid` + `aria-describedby`/`aria-errormessage`, `<fieldset>`/`<legend>` on groups, error-summary on submit, focus-to-first-invalid), and **locale-aware name/address/phone shape** → emit findings (read-only, no edits).
- **build:** Explore (≥2 single-column layouts + placement, read-only) → Judge (single-column + visible-label + error-association + non-stranded rubric, order-swapped) → Implement (one writer; re-layout markup/style + a11y wiring only, reuse `Input`/`Select`/`Button`, cap the real column) → Verify (Playwright screenshots default/focus/error/success @ breakpoints; assert input preserved on error; submit-with-errors → assert error-summary present, first invalid field focused, and each error reachable via `aria-describedby`/`aria-errormessage`; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Single column; every field has a visible top label; no placeholder-as-label; input preserved on error.
- The real column is capped ~440–560px and deliberately placed; submit sits under the last field.
- Errors are programmatically associated: every invalid field has `aria-invalid` + a linked inline message (`aria-describedby`/`aria-errormessage`); grouped inputs sit in `<fieldset>`/`<legend>`; submit renders an error-summary and moves focus to the first invalid field.
- Name/address/phone are locale-aware: no forced Western first/last split, no US-shaped state+zip lockstep, phone accepts an international format.
- **Gate:** hard oracles green (labels, single-column, input-preserved, capped column, error-association, locale-aware fields) AND (build) rubric mean ≥ 0.8. The native customizable-`<select>` Watch item never gates.

## Output
Write `artifacts/form-design/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: heuristic`/`accessibility`, `heuristic: "Nielsen #5 Error prevention"`; `oracle: hard` for placeholder-as-label / wiped input / stranded column / unassociated error / locale-naive name+address+phone), plus the verification block for build mode. Any native customizable-`<select>` usage is logged as a `Watch` note (`oracle: soft`, do not gate), cross-linking `i18n-foundations` for the locale-aware field rules.

## Guardrails
Per `shared/guardrails.md`: never touch validation logic, handlers, or submission — re-layout markup/style only. Reuse the form components before inventing inputs; cap the actual column, not a stranded inner div. Read-only audit makes no edits; one writer for build.
