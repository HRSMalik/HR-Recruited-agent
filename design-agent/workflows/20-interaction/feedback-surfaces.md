# feedback-surfaces

**Group:** 20-interaction
**Runs as:** subagent: ../.claude/agents/interaction-designer.md
**Mode:** build (writer + verify loop) · audit (surface-fit scan)   ·   **Default model:** sonnet

## Purpose
Own how the system talks back: choose the right feedback surface — toast vs inline vs banner vs dialog — by scope, urgency, and persistence, and write specific copy that names the actual outcome.

## Inputs & preconditions
- From `project-design-config.md`: component library (`AlertBanner`, toast, dialog/`FormModal`, inline field error — reuse before inventing), token source + names, breakpoints, theme, locked rules.
- Target: every point where the system reports a result, warns, or asks for confirmation — form submits, async actions, validation, destructive ops.
- Preconditions: dev server reachable; existing feedback components read before adding any.

## Oracle (source of truth)
The surface-selection rules below + the rule that important feedback must not rely on a missable transient.
- **hard:** an action with **2+ actions or a destructive consequence uses a dialog**, never a toast; a field-level validation result is **inline** (attached to the field), not a toast; a toast carries **≤ 3 lines and ≤ 1 action**; copy is **specific** (states the actual outcome), never a bare "Success"/"Error".
- **hard:** any **transient announcement** (toast / status / async result / error) is exposed to assistive tech via a **live region** — `role="status"` (implicit `aria-live="polite"`) for confirmations, `role="alert"` / `aria-live="assertive"` for errors — and that **region is pre-mounted in the DOM before the text is injected**. Mounting the region and its text together in one render is **not announced**; the region must already exist empty, then receive the text.
- **soft:** the surface matches scope/urgency/persistence; important results favour inline over toast (toasts are missable / accessibility-risky); tone is calm and human.

## Standards & techniques
- **Toast:** transient, low-urgency, non-blocking confirmation — ≤ 3 lines, ≤ 1 action; 2+ actions → escalate to a dialog. Auto-dismiss; never the only record of an important result.
- **Inline:** attached + persistent, tied to a specific field/section — the default for validation and anything the user must act on (toasts get missed by sighted and AT users alike).
- **Banner:** top-of-product, persistent, page- or app-scoped status (degraded service, account state) — stays until resolved.
- **Dialog:** blocking, requires a decision — destructive confirmations and any 2+-action choice.
- **Copy:** name the outcome — *"Candidate moved to Interview stage"*, *"Settlement $9,500 paid via ACH"* — not *"Success"*; errors say what failed + how to recover. Status colour always paired with an icon/label.
- **Native top-layer primitives:** implement the surfaces above with the platform's built-in top layer — no `z-index` wars, no focus-trap library. Use **`<dialog>` + `.showModal()`** for the dialog surface (built-in focus trap, `Esc`-to-dismiss, `::backdrop`, inert background); the **Popover API** (`popover` + `popovertarget`, or `popover="manual"` for toasts) for non-modal toasts/banners that ride the top layer above everything; and **Invoker Commands** (`command` / `commandfor`, e.g. `command="show-modal"` / `command="close"`) to wire the trigger button to the surface declaratively, without a click handler. The live-region rule still applies — a popover/toast surface must sit inside a pre-mounted live region to be announced.
- **Watch (do not gate):** **CSS Anchor Positioning** (`anchor-name` + `position-area` / `position-try`) places a tooltip/popover relative to its trigger with zero JS and auto-reflows off-screen cases. Not yet baseline across all targets — **feature-detect** (`@supports (anchor-name: --x)`) and keep a JS-positioned fallback. Track it; never make placement depend on it as a hard oracle.

## Step sequence
- **audit:** enumerate every feedback point → classify each by scope/urgency/persistence → check the chosen surface matches (no toast for 2+ actions/destructive; inline for validation; banner for product-scoped status) → check copy is specific → flag mismatches + vague copy → emit findings (read-only).
- **build:** Explore (≥2 surface mappings from existing components, read-only) → Judge (surface-fit + copy-specificity + ≤3-line/≤1-action rubric, order-swapped) → Implement (one writer; build each surface from existing components/tokens, write the specific copy) → Verify (Playwright triggers each path, screenshots the surface @ breakpoints; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- 2+-action/destructive results use a dialog; validation is inline; toasts are ≤ 3 lines / ≤ 1 action.
- No bare "Success"/"Error" copy — every message names the actual outcome; status colour paired with icon/label.
- Every transient announcement fires through a **pre-mounted live region** (`role="status"`/`alert` or `aria-live`); the region exists empty before text is injected, never mounted together with its text.
- Every surface built from existing components; all colour/spacing resolves to tokens.
- **Gate:** hard oracles green (correct surface choice + copy specificity + pre-mounted live region + axe + console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/feedback-surfaces/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: heuristic`, `oracle: hard` for a wrong surface or vague copy, `heuristic` Nielsen #1 Visibility of system status / #9 Help users recover from errors), plus the verification block (a screenshot per feedback surface @ breakpoints + hard-oracle results + rubric score).

## Guardrails
Per `shared/guardrails.md`: reuse `AlertBanner`/toast/dialog before inventing; never guess a token name — grep the source. Preserve logic byte-for-byte (markup/style/copy only — not the trigger logic). Read-only audit makes no edits; one writer for build; trust the screenshot over the diff.

## References
- **Live regions** (the pre-mounted hard oracle): Sara Soueidan — *"A guide to designing accessible, WCAG-conformant accessible notifications"* (`sarasoueidan.com`) — establishes that a live region must already exist in the DOM, empty, *before* its text is injected; injecting the region and the announcement together in one render is silently dropped by assistive tech.
- **Native top-layer primitives:** MDN — *Popover API* (`developer.mozilla.org/en-US/docs/Web/API/Popover_API`) for `popover` / `popovertarget` and `popover="manual"`; MDN — `<dialog>` / `HTMLDialogElement.showModal()` for the built-in focus trap, `Esc`-to-dismiss and `::backdrop`; MDN — *Invoker Commands* (`command` / `commandfor`) for wiring triggers declaratively.
- **Watch source (do not gate):** MDN — *CSS Anchor Positioning* (`anchor-name`, `position-area`, `position-try`); feature-detect via `@supports` and keep the JS-positioned fallback. Tracked, never a hard oracle.
