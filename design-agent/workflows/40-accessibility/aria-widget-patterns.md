# aria-widget-patterns

**Group:** 40-accessibility
**Runs as:** subagent: ../.claude/agents/a11y-auditor.md
**Mode:** audit (read-only) · build (writer + verify loop)   ·   **Default model:** sonnet

## Purpose
Own the per-pattern WAI-ARIA Authoring Practices Guide (APG) contract for every composite widget — assert each custom widget exposes its APG role/state and answers its full keyboard model, so a custom control behaves exactly like the native one a screen-reader/keyboard user expects.

## Inputs & preconditions
- From `project-design-config.md`: dev-server URL/port + login creds, breakpoints, components dir, **declared headless primitive lib** (React Aria / Radix / Base UI — read before judging any hand-rolled widget), token source.
- Target: every composite widget on the screen — dialog, disclosure, combobox, listbox, menu/menubar, tabs, grid/treegrid, accordion.
- Preconditions: dev server reachable; able to drive the live screen headlessly and keyboard-walk it; the declared headless lib confirmed in `project-design-config.md` before assessing any hand-rolled control.

## Oracle (source of truth)
The WAI-ARIA Authoring Practices Guide patterns — https://www.w3.org/WAI/ARIA/apg/patterns/ — each pattern's `role` + required `aria-*` states + its keyboard-interaction table, verified by a manual keyboard-walk (axe checks ARIA *validity*, not the *keyboard contract* — necessary, not sufficient).
- **hard (each finding cites its APG pattern + the exact key/state that failed):**
  - **Role/state contract** — the widget exposes the pattern's role and required `aria-*` (e.g. `combobox` → `aria-expanded`/`aria-controls`/`aria-activedescendant`; disclosure trigger → `aria-expanded`; tab → `role=tab`+`aria-selected`+`aria-controls`; treegrid cell → `aria-expanded` on expandable rows).
  - **Keyboard model** — every key in the pattern's interaction table works on a keyboard-walk: arrows move within the widget, `Home`/`End` jump, `Enter`/`Space` activate, `Esc` dismisses, `Tab` enters/leaves the composite as one stop (see per-pattern table below).
  - **Focus management** — exactly one of **roving `tabindex`** *or* **`aria-activedescendant`** drives the active descendant (never both, never neither); the composite is a single Tab stop.
  - **Modal dialog** — `role=dialog` + `aria-modal="true"`, background made `inert`, focus trapped inside and **restored to the invoking element on close**, `Esc` closes.
  - **Prefer a headless primitive** — a widget that maps to an APG pattern is built on the project's declared headless lib (React Aria / Radix / Base UI), not hand-rolled keyboard/focus/`aria-*` wiring (re-implementing the contract by hand when the declared lib ships it = a fail; cross-ref `10-tokens-systems/component-library.md`).
- **soft:** disclosure/accordion expand-collapse reads instantly clear; menu vs listbox chosen correctly for the job (commands vs selection); `aria-activedescendant` vs roving choice fits the widget (large virtualized lists favour activedescendant); chevron/affordance matches `aria-expanded` state.

## Standards & techniques (per APG pattern)
- **Dialog (modal):** `Esc` closes; `Tab`/`Shift+Tab` cycle *within*; focus trapped + restored; `aria-modal`+`inert` siblings.
- **Disclosure:** `Enter`/`Space` toggles; trigger carries `aria-expanded`; controlled region `id` referenced by `aria-controls`.
- **Combobox:** `Down`/`Up` open + move through options, `Enter` selects, `Esc` closes (then clears), `aria-expanded`/`aria-activedescendant`/`aria-controls`; popup `role` (`listbox`/`grid`/`tree`/`dialog`).
- **Listbox:** `Up`/`Down` move, `Home`/`End` ends, `Shift`/`Ctrl` for multi-select, `aria-selected` on options, `aria-multiselectable` when relevant.
- **Menu / menubar:** `Up`/`Down` within a menu, `Left`/`Right` across a menubar / into submenus, `Enter`/`Space` activate, `Esc` closes + returns focus to trigger; `role=menu`/`menubar`/`menuitem`.
- **Tabs:** `Left`/`Right` (or `Up`/`Down` vertical) move between tabs, `Home`/`End` jump; `role=tablist`/`tab`/`tabpanel`, `aria-selected`, `aria-controls`; automatic vs manual activation declared.
- **Grid / treegrid:** arrow keys move by cell, `Home`/`End`+`Ctrl` to row/grid ends, `PageUp`/`PageDown`; treegrid rows expand/collapse with `Right`/`Left` + `aria-expanded`, `aria-level`/`aria-posinset`/`aria-setsize`.
- **Accordion:** each header is a disclosure button with `aria-expanded`+`aria-controls`; optional `Up`/`Down`/`Home`/`End` to move between headers.
- **Focus model choice:** **roving `tabindex`** (only the active item is `tabindex=0`, rest `-1`; DOM focus moves) for small static sets; **`aria-activedescendant`** (container holds focus, `aria-activedescendant` points at the active option `id`) for large/virtualized lists and comboboxes.
- **Prefer a headless primitive** over hand-rolling any of the above — the lib owns roving/activedescendant, focus trap+restore, and the `aria-*` wiring; you own markup + tokens.

## Step sequence
- **audit:** enumerate every composite widget → map each to its APG pattern → keyboard-walk it (Tab in/out, arrows, `Home`/`End`, `Enter`/`Space`, `Esc`) asserting each key in the pattern's interaction table → inspect role + `aria-*` state in the accessibility tree → confirm exactly one focus model (roving XOR activedescendant) and, for dialogs, `inert`/`aria-modal`/trap+restore → flag any hand-rolled widget that should sit on the declared headless lib → emit findings, each citing the APG pattern + the failing key/state (read-only, no edits).
- **build:** Explore (read-only; resolve the APG pattern + declared headless primitive from `project-design-config.md`, sketch role/state + keyboard table) → Judge (role/state + keyboard-model + focus-model + headless-primitive rubric, order-swapped) → Implement (one writer; build on the declared headless primitive, wire role/`aria-*` + the focus model, markup/tokens only) → Verify (Playwright keyboard-walks every key in the pattern table @ breakpoints, reads role/state from the a11y tree, asserts dialog focus trap+restore; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

**Watch (do not gate):** native platform primitives moving APG behaviour into the browser — `<dialog>` (with `inert`/focus-restore), the `popover`/`popovertarget` attribute + Invoker `command`, and customizable `<select>`/`<selectlist>` — are EMERGING. Where baseline they can satisfy a pattern without a headless dep, but cross-browser focus/`aria` behaviour isn't settled — record as an advisory option to feature-detect, never a hard oracle and never a reason to skip the declared headless primitive today.

## Assertions & exit gate
- Every composite widget matches its APG role + required `aria-*` state, verified in the accessibility tree.
- Every key in the pattern's interaction table works on a keyboard-walk; the composite is a single Tab stop.
- Exactly one focus model (roving `tabindex` XOR `aria-activedescendant`); modal dialogs set `aria-modal`+`inert`, trap focus, and restore it to the trigger on close, `Esc` dismisses.
- Each APG-pattern widget is built on the project's declared headless primitive — no hand-rolled keyboard/focus/`aria-*` wiring.
- **Gate:** every widget's APG role + keyboard contract verified (keyboard-walk) + 0 axe violations + 0 console errors AND (build) rubric mean ≥ 0.8. Any open hard finding blocks.

## Output
Write `artifacts/aria-widget-patterns/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: accessibility`, `oracle: hard` for a missing role/state, a broken key in the pattern's interaction table, a dual/absent focus model, or a hand-rolled widget bypassing the declared headless primitive; `wcag_ref` 4.1.2 Name·Role·Value / 2.1.1 Keyboard as relevant; `evidence` = the failing key + a11y-tree role/state + screenshot@viewport), plus the verification block (keyboard-walk results per pattern + hard-oracle results + rubric score) for build mode. Task-blocking failures default to major+.

## Guardrails
Per `shared/guardrails.md`: report what the keyboard-walk + the accessibility tree say — never "the widget seems accessible"; cite the APG pattern + the exact key/state. For any APG-pattern widget, build on the declared headless primitive (React Aria / Radix / Base UI) — never hand-roll the keyboard/focus/`aria-*` layer. Preserve logic byte-for-byte (markup/tokens only). Read-only audit makes no edits; one writer for build; trust the keyboard-walk over the diff.
