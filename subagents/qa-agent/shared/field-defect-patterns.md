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
- **smoke:** on the key screens you already walk, spot-run the ⚡ *fast* patterns (P1, P4, P6, P7, **P13**, P20) — one extra input or one glance each, catching high-visibility breakage. **P13 (false success) is the single most-repeated real-QA catch — run it on every mutation.**
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
- **First seen:** REZ-324 (form), REZ-328 (review page). *Regressions:* REZ-410, REZ-446 (word broken mid-word), REZ-417 / REZ-449 (a critical control — action buttons, search × — clipped/unreachable, not just cosmetic).

### P2 · Numeric-field validation (negative / invalid)
- **Probe:** in every numeric field enter a negative number, `0` where invalid, a non-numeric string, a decimal where an integer is expected, and an absurdly large value; submit.
- **Expected:** invalid values are rejected with an inline validation message *before* save; valid ranges enforced.
- **Defect signal:** an invalid/negative value is accepted and saved with no validation.
- **Applies to:** every numeric field (amounts, counts, years, ages).
- **First seen:** REZ-329. *Regressions:* REZ-393, REZ-438 (invalid model number), REZ-447 (cheque no. / amount), REZ-464 (change-password FE validation missing).

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
- **First seen:** REZ-327. *Regression:* REZ-415.

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
- **First seen:** REZ-321 (Claim ID shown instead of Claim Number after delete). *Regressions:* REZ-399 (notification), REZ-408 (Settings), REZ-436, REZ-457 (payment-approve). *(sibling: wrong ACTOR recorded in an audit trail — REZ-468 Closure Audit — same "identity mapped wrong" family.)*

### P8 · Error-message quality, format & placement
- **Probe:** trigger validation and API errors (empty required field, bad format, server 4xx). Read the message.
- **Expected:** human-readable, correctly formatted, placed **inline next to the offending field**, actionable, not duplicated.
- **Defect signal:** a raw framework error surfaced to the user (e.g. a bare `422` "String should have at least 1 character"), a technical/blame-y message, a mis-placed/badly-formatted banner, or the same error shown twice.
- **Applies to:** all validation + error surfaces.
- **First seen:** REZ-326. *Regression:* REZ-441 (wrong message for deactivated-account login).

### P9 · Happy-path create must actually persist
- **Probe:** complete each create/add flow with fully valid data and submit. Then re-fetch / reload and confirm the record exists.
- **Expected:** creation succeeds and persists; no spurious validation error blocks a valid submission.
- **Defect signal:** an unexpected validation error blocks creation, or the record doesn't persist after a "success". Don't stop at "the form renders" — *submit valid data and verify it saved*.
- **Applies to:** every create/add flow.
- **First seen:** REZ-322.

---

> **Batch 2 (appended 2026-07-19).** P13–P23 distilled from the real QA tester's REZ-392→REZ-453 filings (all filed by the same tester). Numbered in discovery order; P10–P12 remain the adjacent-heuristics block below. P13 is the highest-frequency catch in the whole corpus (5 tickets).

### P13 · False success — toast fires but the mutation didn't happen ⚡
- **Probe:** after any state-changing action that shows a success message (move-to-pending, advance-stage, enable a setting, dismiss/close an item), **re-fetch / reload** and confirm the change actually persisted server-side — and that a toggled control/flag is actually *enforced*, not just visually on.
- **Expected:** a success message means the state truly changed and survives a reload; a dismissed item stays gone; an enabled security control is enforced on the next attempt.
- **Defect signal:** success toast shown but status unchanged on reload, a dismissed item reappears, a stage doesn't advance, or an enabled control (e.g. 2FA) isn't actually enforced. **The success copy is never the oracle — the persisted state is.**
- **Applies to:** every action that toasts success (status change, stage transition, enable/disable, dismiss, save).
- **First seen:** REZ-402, REZ-330 (status → Pending), REZ-443 (Intake→Release stage), REZ-412 (2FA enabled but not required), REZ-450 (dismissed document reappears).

### P14 · Status/stage indicator disagrees with the real state
- **Probe:** for every record with a lifecycle (claim status, workflow stage, active/inactive), compare the displayed label/stage against the record's actual backend state — especially right after a transition and on deep-link/landing.
- **Expected:** the label always reflects the record's true current state; a detail view opens on the record's *current* stage.
- **Defect signal:** a Closed claim shows "Open", an inactive carrier shows the wrong status message, the stage name is wrong, or details always land on stage 1 regardless of progress.
- **Applies to:** every status pill, stage stepper, and lifecycle label.
- **First seen:** REZ-401 (Closed shows Open), REZ-431 (inactive-carrier message), REZ-448 (wrong stage name), REZ-444 (always opens on Intake). *Regression:* REZ-462 (a newly-created user shows "Inactive" instead of "Invited").

### P15 · Invalid action offered in a state where it can't apply
- **Probe:** for each item with a lifecycle state (expired invite, inactive carrier, closed claim, withdrawn form), open its action menu / row controls and read which actions are offered.
- **Expected:** only actions valid for the current state are shown/enabled; state-inappropriate actions are hidden or disabled.
- **Defect signal:** an action offered that cannot apply — "Cancel Invite" on an already-expired invite, "Reactivate Staff" on an inactive carrier.
- **Applies to:** every row/entity action menu whose options depend on state.
- **First seen:** REZ-406 (Cancel Invite on expired), REZ-430 (Reactivate on inactive carrier). *Regression:* REZ-473 (Reactivate button shown on a PENDING-status record).

### P16 · Conditional / dependent-field validation
- **Probe:** change the controlling field (payment method, claimant age, doc type) and re-check which dependent fields are required/validated. Then enter a *valid* value in a field that showed an error and confirm the error clears.
- **Expected:** required-ness and validation track the controlling field's current value; a valid entry clears its error immediately.
- **Defect signal:** a field required for the wrong mode (ABA/routing demanded when method = Cheque), or a "required"/format error that persists after a valid value is entered.
- **Applies to:** every field whose validity depends on another field, and every field that validates on blur/change.
- **First seen:** REZ-451 (ABA required on Cheque), REZ-442 (CDL stays "required" after a valid value).

### P17 · Raw / unmapped data leaks to the UI
- **Probe:** open detail panels, settings, audit/activity logs, and any newly-wired list; look for machine-shaped output.
- **Expected:** every value is mapped to a human-readable field/label; no raw JSON, object dumps, or empty-because-unmapped sections.
- **Defect signal:** raw JSON / `{key:value}` blobs rendered to the user, or a section that stays empty because the API shape was never mapped to the FE.
- **Applies to:** every detail / settings / log / read-only rendering surface.
- **First seen:** REZ-409 (raw JSON in Settings → Details), REZ-407 (audit logs not mapped to the FE).

### P18 · Multi-step re-entry lands on the right step + restores prior data
- **Probe:** partially complete or fully submit a multi-step form/wizard, leave, then re-open it (edit, resume-after-request-changes, deep-link, refresh). Note which step it lands on and whether prior answers are prefilled.
- **Expected:** re-entry opens the correct step for the record's state and restores every previously-entered value.
- **Defect signal:** it lands on step 1 / Setup-Password / Intake regardless of progress, or shows blank fields where saved answers exist.
- **Applies to:** every wizard / multi-step form with save-and-resume, edit, or request-changes re-entry.
- **First seen:** REZ-419 (redirected to Setup Password again), REZ-420 (no prefill on re-open), REZ-444 (opens on Intake, not the current stage).
- **Complements P5:** P5 = cancel must CLEAR; P18 = re-entry must RESTORE. Test both directions.

### P19 · Count / tab disagrees with its own contents
- **Probe:** read every status count, badge, and filter tab, then compare against the actual rows shown under it — *before* any refresh (this is not the stale-refresh case).
- **Expected:** a count equals the number of rows it summarizes; a filter tab shows only items that match it.
- **Defect signal:** status counts don't match the applied filter, or a tab shows records that don't belong (Withdrawn forms under the Pending tab).
- **Applies to:** every count/badge paired with a filtered list or tab.
- **First seen:** REZ-428 (counts ≠ applied filter), REZ-422 (Withdrawn forms in Pending tab).
- **Distinct from P6:** P6 is stale-until-refresh; P19 is wrong even when freshly loaded.

### P20 · Dead affordance — a visible control does nothing ⚡
- **Probe:** click every icon and button that looks interactive — clock/time pickers, refresh, edit, row-action icons — across *every* module (breakage is often global, not per-screen).
- **Expected:** every visible interactive control performs its action, or is visibly disabled with a reason.
- **Defect signal:** an icon/button that looks clickable is a no-op — no handler, a missing FE method, or a silently-failing action (the clock icon dead in every module; Edit calls a missing method).
- **Applies to:** every icon-button and action control.
- **First seen:** REZ-394 + REZ-404 (clock/time icon dead across modules), REZ-395 (Edit → missing frontend method). *Regression:* BL-BUG-22 (REZ-449 search clear-× visually present + `cursor:pointer` but **unclickable** — computed `pointer-events:none`, so a real click passes through; JS-click works — always check a control is hit-testable, not just present).

### P21 · Error-state layout stability
- **Probe:** trigger inline validation errors on a form and watch the layout as messages appear and disappear; also check required-asterisk styling/alignment across fields.
- **Expected:** error text is reserved-space (or otherwise non-shifting); surrounding fields and buttons don't jump; decorations like required asterisks are consistent.
- **Defect signal:** fields shift/reflow when an error renders (causing mis-clicks / layout shift), or inconsistent asterisk styling and alignment.
- **Applies to:** every validated form.
- **First seen:** REZ-396 (fields shift when errors show, all modules), REZ-397 (inconsistent required-asterisk styling).

### P22 · Input silently coerced / clamped
- **Probe:** type boundary and over-range values into numeric / percent / bounded fields (e.g. 150 into a 0–100 field) and watch what the field holds after blur.
- **Expected:** an out-of-range value is rejected with a message — never silently rewritten.
- **Defect signal:** the field auto-changes the user's value (snaps to 100) with no notice, hiding what they actually entered.
- **Applies to:** numeric / percent / bounded input fields.
- **First seen:** REZ-416 (Safety & Compliance fields snap to 100).

### P23 · Null / empty renders as a stray artifact
- **Probe:** view records with optional fields left empty (no adjuster, no middle name, empty list) in lists, table cells, and any joined / comma-separated display.
- **Expected:** empty values render cleanly — blank, an em dash, or "None" — with no orphaned punctuation.
- **Defect signal:** a stray comma / separator / label emitted from a null inside a joined string (a lone "," shown when no adjuster is assigned).
- **Applies to:** every joined/concatenated or optional-value display.
- **First seen:** REZ-429 (comma shown when no adjuster assigned). *Regression:* REZ-459 (comma shown instead of a dash when no actions are available).

### P24 · Validation blocks with no visible feedback
- **Probe:** submit a form/step with an invalid or incomplete field (empty required, out-of-range, cross-field conflict) — *especially inside nested/array field groups* (repeatable rows, "add another" blocks, multi-step wizards). Watch for BOTH: does advance get blocked, AND does an inline error actually render (text + `aria-invalid`)?
- **Expected:** a blocked submit always shows WHY — an inline error on the offending field (and/or a summary). The user is never stuck with a form that silently refuses to proceed.
- **Defect signal:** the form/step silently refuses to advance (or a mutation no-ops) with **no error text and no `aria-invalid`** — the error is set in state but never renders, typically because the display resolves the error path wrong (e.g. a **field-array error looked up with a flat key** — `errors[`${prefix}.field`]` — instead of the nested `errors.arr[i].field`). Discriminate against a working sibling: a single-level section shows its error while the nested-array section shows none → confirms the path bug.
- **Applies to:** every validated form; highest-risk on field-arrays / repeatable rows / multi-step wizards where error paths are nested. Distinct from **P8** (error shows but is poorly worded/placed) and **P13** (a mutation lies about succeeding) — here the block is *correct* but *invisible*.
- **First seen:** BL-BUG-23 (third-party vehicle validation errors + the BL-BUG-07 VIN/plate cross-check inline error never render — `VehicleBlock` reads flat `errors?.[prefix]` vs RHF's nested `errors.thirdPartyVehicles[i]`; user blocked on intake with zero feedback).

> **Batch 3 (appended 2026-07-20).** P25–P28 distilled from the real QA tester's REZ-454→REZ-475 filings. Standout: P26 (role-based action/visibility parity) is the highest-frequency new class — 4 tickets in one batch.

### P25 · Control misalignment within a toolbar / filter / modal row
- **Probe:** glance at every button/icon that sits in a ROW with siblings — filter bars, table toolbars, modal action rows, "sent invite" / copy-link modals. Check vertical + horizontal alignment against its row-mates.
- **Expected:** controls align to a shared baseline / grid; a button is centered in its row, not offset high/low or crowding a neighbor.
- **Defect signal:** a Clear/Copy/action button is misaligned with the filters or fields beside it (off-baseline, cramped, overflowing its row).
- **Applies to:** filter bars, table toolbars, modal footers, any horizontal control cluster. (Sibling of **P4** — that's *duplicate/ambiguous* chrome icons; this is *misplaced* ones.)
- **First seen:** REZ-461 (Clear button misaligned with the staff-page filters), REZ-465 (Copy button misaligned on the sent-invite modal).

### P26 · Role-based action / visibility parity
- **Probe:** for each user role (super_admin, admin, manager, adjuster), walk the same screens and compare which **actions** (buttons, menu items) and **data** (assigned adjuster, dashboards, queues) are available. Especially: an admin acting on **users/records they created**, a manager's dashboard vs an admin's, and any "Login As" / lower-tier view.
- **Expected:** equivalent roles get the actions + visibility their permissions grant — no action is silently missing for a role that should have it, and no data a role should see is hidden (and vice-versa: nothing a role should NOT have leaks in).
- **Defect signal:** an action/field present for one role is wrongly absent for another equivalent role — e.g. an admin can't take actions on their own created users, "Create Claim" missing on the manager dashboard, admin-created users lack the buttons super_admin sees, the assigned adjuster isn't visible to the manager.
- **Applies to:** every role-gated action menu, dashboard, and record-detail — the whole RBAC surface (complements the charter's BOLA/BFLA server checks with the *client-visibility* half).
- **First seen:** REZ-471 (admin can't act on own-created users), REZ-472 (Create-Claim missing on manager dashboard), REZ-474 (admin-created users lack super_admin's action buttons), REZ-475 (assigned adjuster not visible to the manager).

### P27 · Open overlay must close / reposition on scroll + outside interaction
- **Probe:** open a dropdown / select / menu / tooltip / date-picker, then **scroll the page** (and click outside, resize, open another). Watch the overlay.
- **Expected:** the overlay closes (or stays anchored to its trigger) on scroll; clicking outside dismisses it; it never floats detached over unrelated content.
- **Defect signal:** the dropdown stays open and stranded while the page scrolls, or detaches from its trigger.
- **Applies to:** every popover-style control (custom dropdowns, menus, tooltips, pickers).
- **First seen:** REZ-466 (dropdown remains open while scrolling the page).

### P28 · Cross-step data must reach the Review/downstream view + survive reload
- **Probe:** in a multi-step flow, enter (and later EDIT) values in an early step, then view the **Review / summary** screen and every **downstream** screen that should show them (approval, audit, detail); then **reload** the page and re-check. Use the persistence oracle (re-GET), not just the on-screen echo.
- **Expected:** every entered/edited value appears on the Review and downstream screens, reflects edits, and survives a reload (persisted server-side).
- **Defect signal:** data entered in one step is missing on Review/approval, an edit isn't reflected downstream, or values disappear after a page reload.
- **Applies to:** every multi-step create/intake/payment flow with a Review or a separate approval/detail screen. Complements **P13** (mutation persistence) + **P18** (re-entry restore) — this is the *forward* flow to Review/downstream.
- **First seen:** REZ-454 (Payee/Banking disappear from Review after reload), REZ-455 (updated SSN not reflected on Review), REZ-456 (Payee/Banking not shown during Payment Approval).

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
