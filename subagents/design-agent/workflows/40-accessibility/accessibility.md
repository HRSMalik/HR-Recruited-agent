# accessibility

**Group:** 40-accessibility
**Runs as:** subagent: ../.claude/agents/a11y-auditor.md
**Mode:** audit (read-only)   ·   **Default model:** sonnet

## Purpose
Own WCAG 2.2 AA conformance across the POUR principles (Perceivable, Operable, Understandable, Robust) — assert each target screen against the exact success criteria with deterministic tools plus a manual keyboard pass.

## Inputs & preconditions
- From `project-design-config.md`: dev-server URL/port + login creds, breakpoints, token source (for contrast checks), components dir.
- Target screen(s)/component(s); the relevant WCAG 2.2 SC per check below.
- Preconditions: dev server reachable; able to drive the live screen headlessly and tab through it.

## Oracle (source of truth)
WCAG 2.2 AA success criteria, cited by number. Tools: axe-core / `@axe-core/playwright` and the WebAIM contrast checker. axe catches ~57% of WCAG issues — necessary, not sufficient; always pair it with a manual/keyboard pass.
- **hard (each finding cites its exact SC + the tool):**
  - **1.4.3 / 1.4.11 Contrast** — text ≥ 4.5:1, large (≥18px / 14px bold) ≥ 3:1, non-text/UI ≥ 3:1 (WebAIM).
  - **1.4.1 Use of Colour** — colour never the sole signal; status paired with label/icon.
  - **2.1.1 Keyboard** — every control keyboard-operable, no trap (manual tab pass).
  - **2.4.3 Focus Order** — focus follows a meaningful sequence.
  - **2.4.7 Focus Visible** + **2.4.11 Focus Not Obscured (Minimum)** — focus indicator visible and not hidden by sticky chrome.
  - **2.5.8 Target Size (Minimum)** — interactive targets ≥ 24×24px (44px is AAA).
  - **1.3.1 / 4.1.2 Info & Relationships / Name-Role-Value** — native HTML first, landmarks present, every control has name/role/state (axe).
  - **1.1.1 Non-text Content** — meaningful images have alt; decorative ones are empty-alt.
  - **3.3.1 / 3.3.3 Error Identification / Error Suggestion** — errors identified in text + a correction suggested.
  - **2.3.3 Animation from Interactions** — non-essential motion respects reduced-motion.
  - **2.5.7 Dragging Movements** — every drag has a single-pointer alternative.
  - **WCAG 2.2 cognitive adds** — **3.3.8 Accessible Authentication** (no cognitive-function test; paste-friendly), **3.3.7 Redundant Entry** (don't re-ask known info), **3.2.6 Consistent Help** (help in a consistent location).
  - **2.4.3 / 4.1.2 SPA focus management** — on client-side route change, move focus to the new view's heading (`tabindex="-1"`, focus it, then announce the view via a live region); after a dialog or menu closes, **return** focus to the element that opened it. SPAs swap the DOM without a document load, so focus silently strands on a detached node unless moved (manual route + open/close pass; source: design.va.gov focus-management).
  - **1.4.1 / 1.4.3 / 1.4.11 System preference adaptation** — honour `forced-colors` (Windows High Contrast Mode replaces author colours and **breaks CSS-var branding + glassmorphism** — backgrounds, borders and shadows vanish; assert controls still have a visible boundary), `prefers-contrast` (offer a higher-contrast variant when requested), and `prefers-reduced-transparency` (drop glass/blur for an opaque surface). Test under `forced-colors: active` — emulate it, don't trust the default theme (manual emulation pass).
  - **2.5.3 Label in Name / Accessible-name computation** — the accessible name must contain the visible label text (so speech-input users can target a control by what they see). Debug name mismatches by walking the AccName computation order: `aria-labelledby` → `aria-label` → native label (`<label>` / `alt` / `<legend>` / `title`) → contents → `title` attribute — an `aria-label` silently **overrides** the visible text and is the usual culprit for a 2.5.3 break (axe `label-content-name-mismatch` + manual AccName trace).

**Watch (do not gate):**
- **APCA / WCAG 3 perceptual contrast** — the APCA model (slated for WCAG 3) weights contrast by perceived lightness, font weight and size rather than the 2.x ratio, and can disagree with 4.5:1 in both directions. Track it for awareness, but **the WCAG 2.2 ratios above remain the oracle** — never raise or waive a contrast finding on an APCA score.

## Standards & techniques
Native HTML before ARIA; landmark regions; label every field; visible focus ring ≥ 3:1; reduced-motion media query; keyboard-first interaction model; error text + suggestion adjacent to the field. On route change move focus to the new view heading and announce it; return focus to the trigger on dialog/menu close. Keep the visible label inside the accessible name; adapt to `forced-colors` / `prefers-contrast` / `prefers-reduced-transparency` so branding and glass surfaces degrade gracefully.

## Step sequence
- **audit:** Plan the SC checklist → drive the live screen at each breakpoint → run axe-core, then the manual pass axe can't cover (keyboard/focus/target-size/contrast, SPA route-change + dialog/menu close focus, AccName/label-in-name trace, and a `forced-colors: active` emulation with `prefers-contrast` / `prefers-reduced-transparency`) → assert each result against its SC → emit findings, each citing the exact SC + the tool that caught it (read-only, no edits).

## Assertions & exit gate
- 0 axe-core violations AND 0 contrast failures (light and dark) AND the screen is fully keyboard-operable with visible, unobscured focus.
- Every interactive target ≥ 24×24px; colour never sole signal; errors identified + suggested.
- Route changes move focus to the new view heading and announce it; closing a dialog/menu returns focus to its trigger; controls stay usable under `forced-colors: active`; every visible label is contained in its accessible name.
- **Gate:** 0 axe violations + 0 contrast failures + keyboard-operable. Any open hard finding blocks.

## Output
Write `artifacts/accessibility/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: accessibility`, `oracle: hard`, `wcag_ref` = the exact SC, `evidence` = axe rule id / contrast ratio + screenshot@viewport). Task-blocking failures default to major+. Audit emits findings only — no writes.

## Guardrails
Per `shared/guardrails.md`: read-only — report what axe-core / WebAIM / the keyboard pass say, never "it looks accessible." Cite the SC; don't generalize. One read-only auditor; no edits.
