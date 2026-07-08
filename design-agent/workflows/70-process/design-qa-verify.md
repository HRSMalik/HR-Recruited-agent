# design-qa-verify

**Group:** 70-process
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (the verifier the writer/judge call)
**Mode:** build (verification gate — drives the live app, no source edits)   ·   **Default model:** sonnet

## Purpose
The verification gate every build flow calls to pass. Drive the live app, screenshot every state at every breakpoint, and run the hard oracles deterministically — this is what turns "looks done" into "proven done".

## Inputs & preconditions
- From `project-design-config.md`: dev-server start command + base URL/port, login/auth creds for screenshots, breakpoints, Playwright settings, token source.
- Target: the screen(s)/component(s) just built; the states they expose.
- Preconditions: dev server reachable and logged in; the build under test is deployed to the dev server.

## Oracle (source of truth)
The live screenshot + the deterministic checkers — never the writer's prose. The screenshot is the truth; the visual-diff is advisory (see *Visual-regression sub-procedure*).
- **hard (all blocking):** zero console/page errors per state (the primary oracle); contrast ≥ thresholds (light AND dark); axe-core 0 violations; no viewport overflow at any breakpoint; token conformance; logic-unchanged diff.
- **soft:** none here — soft scoring is the evaluator's job; this flow gates on hard oracles only.

## Standards & techniques
- Drive headlessly with **Playwright** (chromium, `--no-sandbox`) using the config dev-server + creds.
- Screenshot **every state**: default / hover / focus / active / disabled / loading / empty / error / success — at each project breakpoint.
- **Assert zero console/page errors** as a hard oracle (listen for `console` + `pageerror` across every state).
- Run **axe-core** per state; record violations as `hard` findings.
- **Masked visual-regression** is a real sub-procedure now, not a one-line afterthought — see *Visual-regression sub-procedure* below. It stays advisory: **trust the screenshot over the diff** when they disagree.
- **Delete temp Playwright scripts** after the run — leave no scaffolding behind.

## Visual-regression sub-procedure
Advisory only — every assertion here is **soft**; visual-regression never gates this flow. Its job is to surface *suspected* changes for a human/writer to look at, not to fail the build. A diff that disagrees with the live screenshot loses — the screenshot is the oracle. Run it like this:

**Baseline management.** Baselines live under `artifacts/design-qa-verify/baselines/<browser>/<viewport>/<state>.png`, committed and reviewed like code. Never auto-accept a new baseline silently — a baseline update is a reviewed diff, not a side effect of a green run. On a legitimate intended change, regenerate only the affected baselines (see change-scoped snapshots) and record *why* in the report. A missing baseline is a **soft** "new snapshot — needs baseline approval" finding, never a hard fail.

**Browser × viewport matrix.** Capture each state across the matrix of `{chromium, firefox, webkit} × {project breakpoints}` (the exact set comes from `project-design-config.md` — don't invent breakpoints). One baseline per cell; a diff is only ever compared against the baseline for its own `<browser>/<viewport>/<state>` cell. Cross-cell comparisons are meaningless and forbidden.

**Change-scoped snapshots (TurboSnap-style).** Don't re-shoot the whole app every run. Scope snapshots to what the build actually touched: diff the changed files, map them to the components/stories that depend on them, and snapshot only those cells. Unchanged surfaces inherit their existing baseline untouched. This keeps the matrix cheap enough to run on every build and keeps the diff signal focused on the work under test.

**FLAKE-CONTROL checklist (run before every capture).** A flaky visual diff is worse than no diff — it trains everyone to ignore the channel. Neutralize every source of nondeterminism *before* the snapshot, not after (the failure modes below follow shakacode's flaky-visual-regression breakdown — *Flaky Visual Regression Testing*, shakacode.com):
- **Freeze animations + transitions** — inject CSS forcing `animation-duration: 0s !important; transition-duration: 0s !important; animation-play-state: paused !important`, and set `prefers-reduced-motion`. A snapshot caught mid-tween is the classic false diff.
- **Pin fonts + container** — wait for `document.fonts.ready`, self-host/embed the exact font files (no live webfont fetch), and pin the container (fixed width/height/device-scale, `devicePixelRatio`) so sub-pixel reflow can't shift glyphs.
- **Freeze the clock + seed the RNG** — pin time with `page.clock.setFixedTime(...)` (or equivalent) so "2 minutes ago" / dates / charts are stable, and seed any RNG to a constant so randomized layout/content is reproducible.
- **Mask remaining dynamic content** — mask timestamps, ids, avatars, ads, and personalized data that can't be frozen; intercept the API responses that feed them where practical.
- **Generate baselines in the SAME environment as comparison** — baselines and diffs MUST be produced in the *identical* Docker/CI image (same OS, same browser build, same fonts, same `devicePixelRatio`). **Mac-baseline-vs-Linux-CI font rendering is the #1 source of false diffs** — antialiasing and hinting differ across OSes, so a Mac-authored baseline will diff against a Linux-CI run on text it never actually changed. Bake the baseline-generation step into the same CI container that runs the comparison; never commit a locally-captured (Mac/Windows) baseline.

> **Watch (do not gate):** *AI/perceptual visual-diff* (LLM-judged or perceptual-hash "looks the same to a human" comparison) is EMERGING — it promises to absorb sub-pixel/antialiasing noise without per-pixel thresholds. Treat any signal it produces as advisory observation only; it never becomes a hard oracle and never gates this flow.

## Step sequence
- **build (gate only):** Launch the dev server + log in → enumerate states → drive + screenshot every state @ every breakpoint → assert zero console errors, run axe-core, check contrast + overflow + token conformance + logic-unchanged diff → (advisory) run the visual-regression sub-procedure — FLAKE-CONTROL, then change-scoped snapshots across the browser × viewport matrix vs same-environment baselines → emit pass/fail per hard oracle (visual-regression results are advisory, never gating) → delete temp scripts. No source edits; on failure, hand findings back to the writer.

## Assertions & exit gate
- A screenshot exists for every state × breakpoint (filename records the viewport).
- Zero console/page errors across all states; axe 0 violations; contrast ≥ thresholds light + dark; no overflow; tokens conform; logic diff clean.
- Temp Playwright scripts removed.
- **Gate:** all hard oracles green — any single failure fails the gate and returns to the writer.

## Output
Write `artifacts/design-qa-verify/report.json` per `shared/report-format.md` — the full `verification` block (screenshots + viewports + per-oracle hard results) and any `hard` findings per `finding-schema.md` (console errors, axe violations, contrast/overflow/token failures).

## Guardrails
Per `shared/guardrails.md`: verify by running it — drive the live app, never assert from the diff alone. Hard oracles are blocking; the gate doesn't reach soft scoring until they're green. This flow makes no source edits (drives + screenshots only). Trust the screenshot over the diff; delete temp scripts.
