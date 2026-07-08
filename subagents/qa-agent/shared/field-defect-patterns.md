# Field-tested defect patterns (real-QA-tester heuristics)

> **What this is.** A *growing* catalog of concrete, field-proven defect patterns distilled from bugs
> a real human QA tester actually filed. The category workflows (`negative-boundary`, `usability`,
> `exploratory`, `smoke`, `regression`) say *what kinds* of testing to do; this file says the
> *specific things a senior manual tester always tries* because they keep catching real bugs.
>
> **Who applies it.** Any flow that touches a UI or a form — `smoke` (the quick ⚡ high-value subset),
> `exploratory` (the full catalog as heuristics), `negative-boundary` (inputs), `usability` (chrome +
> copy + status), and `regression` (re-run every pattern with a `First seen` ticket so it can't
> regress). Each pattern is an executable check: **Probe → Expected → Defect signal**.
>
> **How to grow it.** When a QA-filed bug reveals a pattern not yet here, **append it** (same shape,
> with a `First seen` ticket). This is the QA agent's long-term memory of "what breaks in this kind of
> app." Never delete a pattern; if one stops applying, note why inline.

## How to use in a run
- **smoke:** on the key screens you already walk, spot-run the ⚡ *fast* patterns (P1, P4, P6, P7) — one extra input or one glance each, catching high-visibility breakage.
- **exploratory / usability / negative-boundary:** work the **full** list against the change surface; each finding cites the pattern number + the oracle it breaks.
- **regression:** every pattern with a `First seen` ticket is a permanent regression check on that surface.
- A pattern hit is a finding per `shared/finding-schema.md`; severity per `shared/severity-priority-rubric.md`. The oracle is the stated expectation below (a real requirement / UX expectation), never the SUT's own output.

---

## Patterns

### P1 · Long-text / overflow stress ⚡
- **Probe:** enter very long values (100+ chars, and a long no-space token) into *every* text field — names, titles, descriptions, notes, addresses. Save, then view the record in **all** its surfaces: the form, list/table cells, cards, and the read-only **review/detail** page.
- **Expected:** text wraps or truncates (ellipsis/tooltip) inside its container; layout holds.
- **Defect signal:** text overflows its container, pushes/breaks layout, misaligns columns, or clips.
- **Applies to:** every text input + every screen that renders user text.
- **First seen:** REZ-324 (form), REZ-328 (review page).

### P2 · Numeric-field validation (negative / invalid)
- **Probe:** in every numeric field enter a negative number, `0` where invalid, a non-numeric string, a decimal where an integer is expected, and an absurdly large value; submit.
- **Expected:** invalid values are rejected with an inline validation message *before* save; valid ranges enforced.
- **Defect signal:** an invalid/negative value is accepted and saved with no validation.
- **Applies to:** every numeric field (amounts, counts, years, ages).
- **First seen:** REZ-329.

### P3 · Notification behind a modal (stacking / top layer)
- **Probe:** open a modal/dialog, then trigger a success / warning / error notification *while the modal is still open* (submit inside it, or fire an action that toasts).
- **Expected:** the notification renders **above** the modal and is fully visible.
- **Defect signal:** the toast/message appears **behind** the modal and is hidden or clipped. (Common cause: a native `<dialog>`/`showModal()` sits in the browser *top layer*, above any `z-index`; the toast container must share the top layer.)
- **Applies to:** any flow that can toast from inside a modal.
- **First seen:** REZ-325.

### P4 · Duplicate / ambiguous icons in chrome ⚡
- **Probe:** glance at every modal, dialog, toast, and banner. Count close (×) controls and status icons.
- **Expected:** exactly one close (×) per dismissible surface; the status icon is visually distinct from the close control.
- **Defect signal:** two ×-like glyphs, or a status glyph indistinguishable from the close button, or otherwise duplicated/cluttered icons.
- **Applies to:** all modal + notification + banner chrome.
- **First seen:** REZ-332.

### P5 · Form state reset on cancel / reopen
- **Probe:** open a create/edit form, type into several fields, click **Cancel**; reopen the *same* form. Also open "create new" right after editing an existing record.
- **Expected:** the reopened form is blank / at defaults (create) or shows the correct record's values (edit) — never leftover data from the cancelled attempt.
- **Defect signal:** previously-entered (cancelled) data persists into the next open.
- **Applies to:** every create/edit modal + multi-step wizard.
- **First seen:** REZ-327.

### P6 · Live update after a mutation (no manual refresh) ⚡
- **Probe:** perform a state-changing action — toggle active/inactive, add, delete, assign, approve — and watch every derived UI element that should reflect it (counts, badges, totals, list rows, status pills) **without refreshing the page**.
- **Expected:** derived UI updates immediately (optimistic or via refetch).
- **Defect signal:** the count/list/badge is stale until a manual page refresh.
- **Applies to:** any summary/count/list fed by a mutation.
- **First seen:** REZ-323.

### P7 · Human-facing identifier vs internal ID ⚡
- **Probe:** after create / delete / status-change actions, read every user-facing reference — confirmation messages, toasts, timelines, activity/audit logs, table cells, breadcrumbs.
- **Expected:** the user sees the human-facing identifier (e.g. a formatted number like `CCA-2026-000123`), never the internal UUID/DB `_id`.
- **Defect signal:** an internal ID leaks into user-facing text (wrong field mapping).
- **Applies to:** every place a record is named to the user.
- **First seen:** REZ-321 (Claim ID shown instead of Claim Number after delete).

### P8 · Error-message quality, format & placement
- **Probe:** trigger validation and API errors (empty required field, bad format, server 4xx). Read the message.
- **Expected:** human-readable, correctly formatted, placed **inline next to the offending field**, actionable, not duplicated.
- **Defect signal:** a raw framework error surfaced to the user (e.g. a bare `422` "String should have at least 1 character"), a technical/blame-y message, a mis-placed/badly-formatted banner, or the same error shown twice.
- **Applies to:** all validation + error surfaces.
- **First seen:** REZ-326.

### P9 · Happy-path create must actually persist
- **Probe:** complete each create/add flow with fully valid data and submit. Then re-fetch / reload and confirm the record exists.
- **Expected:** creation succeeds and persists; no spurious validation error blocks a valid submission.
- **Defect signal:** an unexpected validation error blocks creation, or the record doesn't persist after a "success". Don't stop at "the form renders" — *submit valid data and verify it saved*.
- **Applies to:** every create/add flow.
- **First seen:** REZ-322.

---

## Adjacent heuristics (same tester mindset — apply on exploratory / negative-boundary runs)

### P10 · Input hygiene: whitespace, unicode, markup
- **Probe:** submit leading/trailing spaces, emoji/unicode, and markup/quote characters (`<b>`, `'`, `"`, `&`) in text fields.
- **Expected:** values are trimmed where appropriate and stored/rendered safely — no layout break, no HTML injection, no broken display.
- **Defect signal:** untrimmed values, broken rendering, or markup interpreted as HTML.
- **Applies to:** every free-text field.

### P11 · Double-submit / rapid re-click
- **Probe:** click Submit/Save (and destructive confirms) twice in quick succession; double-click action buttons.
- **Expected:** the control disables on first submit; exactly one record/action results.
- **Defect signal:** duplicate records, duplicate API calls, or a double-fired action.
- **Applies to:** every submit + destructive confirm.

### P12 · Interrupt & resume mid-flow
- **Probe:** in a multi-step form/wizard, use browser Back and Refresh partway through; reopen the flow.
- **Expected:** state is coherent — preserved intentionally or cleanly reset; no crash, no half-saved record, no stuck spinner.
- **Defect signal:** lost/corrupt state, a crash, or an orphaned partial record.
- **Applies to:** every multi-step flow.
