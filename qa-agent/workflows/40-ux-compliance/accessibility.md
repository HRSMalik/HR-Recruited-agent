# accessibility

**Category:** 40-ux-compliance
**Runs as:** subagent: ../.claude/agents/accessibility-tester.md
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Audit the rendered UI for **WCAG 2.2 Level A/AA** conformance, organized under **POUR** (Perceivable, Operable, Understandable, Robust). Answers: "Can every user — keyboard-only, low-vision, screen-reader — perceive and operate this interface?"

## Inputs & preconditions
- Required artifacts: page/route inventory (URLs or component list), the conformance target (WCAG 2.2 AA), any design system token map for contrast.
- Target: base URL of a rendered NON-PROD build, auth/test account if pages are gated, viewport(s) to test.
- Preconditions: assert each target route loads to interactive state (no fatal JS error) before scanning; a route that 500s is `status:error`, not a finding.

## Oracle (source of truth)
The **WCAG 2.2 success criteria** — every finding cites the criterion id and level. Key ones: **1.1.1** Non-text Content (alt text), **1.3.1** Info & Relationships (semantic markup/labels), **1.4.3** Contrast (Minimum) ≥4.5:1 text / 3:1 large, **1.4.11** Non-text Contrast ≥3:1 (UI components/graphics), **2.1.1** Keyboard, **2.4.7** Focus Visible, **2.5.8** Target Size (Minimum) ≥24×24 CSS px, **3.3.2** Labels or Instructions, **4.1.2** Name/Role/Value (ARIA). NEVER the browser's lack of an error as proof of conformance.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate routes × states (default, focused, error, modal-open); bucket checks by POUR; scope to changed components when a diff is given.
2. **Act** — per route: run **axe-core** and **Lighthouse a11y** for automated criteria; run **WAVE** for structure; then manual passes that tools cannot judge — Tab/Shift-Tab through every interactive element (focus order, no traps, visible focus ring), exercise **NVDA/VoiceOver** for announced name/role/state, sample contrast with a ratio check against design tokens, measure hit targets. Skip-and-continue per element.
3. **Verify** — assert each result against its WCAG criterion: contrast ratios meet 1.4.3/1.4.11 thresholds, every control is keyboard-reachable and operable (2.1.1) with a visible focus indicator (2.4.7), every image has appropriate `alt` or is marked decorative (1.1.1), every input has a programmatic label (1.3.1/3.3.2), targets ≥24×24px (2.5.8). Automated tools find ~30–40%; record which findings are manual.

## Assertions & exit gate
- 0 axe-core violations at impact `serious`/`critical`; all flagged contrast pairs meet 1.4.3/1.4.11.
- Full keyboard operability: no focus traps, logical order, every interactive element reachable + visibly focused.
- Every actionable element exposes correct name/role/value to AT (4.1.2).
- **Gate:** `wcag_22_aa_conformant` — passes when 0 Level A and 0 Level AA violations remain (an A violation is **critical**; an AA violation is **major**; advisory AAA notes are **minor**).

## Output
Write `artifacts/accessibility/report.json` per `shared/report-format.md`:
`{ flow:"accessibility", status, summary{total,passed,failed,skipped}, findings[], gate{name:"wcag_22_aa_conformant",passed} }`.
Each finding (`QA-A11Y-NNN`) puts the criterion id+level in `oracle` (e.g. "WCAG 2.2 SC 1.4.3 (AA)"), the element selector + measured value (e.g. contrast 3.1:1, need 4.5:1) in `evidence`, and a concrete remediation in `suggested_fix`. Note tool vs. manual provenance per finding.

## Guardrails
Per `shared/guardrails.md`: read-only — `disallowedTools: Edit, Write`; no form submissions against live data (use seeded account). Automated tools are necessary-not-sufficient — never claim AA conformance from a clean axe run alone; lower confidence on tool-only criteria. Secrets via env; cap `maxTurns`. Findings are recommendations; a human owns the VPAT/sign-off.
