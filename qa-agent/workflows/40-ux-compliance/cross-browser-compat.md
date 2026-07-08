# cross-browser-compat

**Category:** 40-ux-compliance
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Verify the UI renders and behaves consistently across the supported browser/OS/device matrix and responsive breakpoints. Answers: "Does every supported user — on Chrome, Firefox, Safari, Edge, desktop or mobile — see and operate the same working interface?"

## Inputs & preconditions
- Required artifacts: the **support matrix** (browsers × versions × OS × devices), the responsive breakpoint spec, the route/journey list, and the **reference render** (the designated baseline browser+viewport the UI is signed off against).
- Target: base URL of a NON-PROD build reachable from a grid (BrowserStack / Sauce Labs / local Playwright with Chromium+Firefox+WebKit).
- Preconditions: assert the SUT loads on the baseline (reference) target first; if the baseline itself is broken, that's `status:error`, not a cross-browser delta.

## Oracle (source of truth)
The **reference render/behavior** — the baseline browser+viewport the design is signed off on — plus the documented support matrix and breakpoint spec. A finding is a *deviation from the reference* (visual regression, functional break, or layout collapse) on a supported target. NEVER treat one browser's output as automatically correct without the baseline; if no baseline exists, flag that gap first.

## Step sequence (Plan → Act → Verify)
1. **Plan** — build the test grid: each in-scope route × {Chrome, Firefox, Safari/WebKit, Edge} × {desktop, tablet, mobile} × each breakpoint boundary; scope to changed views when a diff is given. Identify risk features (CSS grid/flex edge cases, `:has()`, date inputs, video/codecs, sticky/position, Safari-specific quirks).
2. **Act** — drive each grid cell via **Playwright/BrowserStack**: load the route, capture a screenshot at each breakpoint, and run the core interaction (the page's primary action). Compare each cell's render against the reference via pixel/DOM diff; replay the key journey to catch behavioral (not just visual) breaks. Skip-and-continue per cell; record the exact browser+OS+viewport.
3. **Verify** — assert: render matches the reference within tolerance (no overlap, clipping, invisible text, broken layout at a breakpoint), and the core interaction succeeds identically on every supported target. A console error or failed action on one browser but not the baseline is a finding. Evidence = side-by-side screenshots + diff + console log.

## Assertions & exit gate
- Every supported browser/OS/device renders each route within visual tolerance of the reference (no layout collapse/clipping/overlap).
- The core interaction completes on every supported target with no browser-specific JS error.
- Responsive layout holds at every breakpoint boundary (no horizontal scroll, no overlap, content reflows correctly).
- **Gate:** `consistent_across_support_matrix` — passes when 0 functional breaks and 0 layout-collapse deltas on supported targets (functional break on a supported browser is **critical**; visual regression/layout collapse is **major**; minor cosmetic pixel diff is **minor**).

## Output
Write `artifacts/cross-browser-compat/report.json` per `shared/report-format.md`:
`{ flow:"cross-browser-compat", status, summary{total,passed,failed,skipped}, findings[], gate{name:"consistent_across_support_matrix",passed} }`.
Each finding (`QA-XBROWSER-NNN`) records the exact browser+version+OS+viewport in `environment.extra`, names the reference target in `oracle`, attaches the side-by-side diff + console log in `evidence`, and suggests the fix (polyfill / prefix / fallback / breakpoint correction) in `suggested_fix`.

## Guardrails
Per `shared/guardrails.md`: read-only — `disallowedTools: Edit, Write`; never submit against live data (seeded account); mock outbound side effects. Respect grid concurrency/rate limits and back off on throttling; the matrix can be costly — scope to the change surface and a representative subset when a full grid isn't justified, and note what was skipped. Secrets (grid keys) via env, redacted from reports. Cap `maxTurns`. Recommendations only.
