# token-pipeline

**Group:** 10-tokens-systems
**Runs as:** subagent: ../.claude/agents/design-system-keeper.md
**Mode:** build (writer + verify loop) · audit (token-lint scan)   ·   **Default model:** sonnet

## Purpose
Own the build that turns the one DTCG token source into per-platform artifacts, and define the token-LINT that `guardrails.md` references ("the token linter") but never specifies — so the source is provably valid before it is ever transformed or committed.

## Inputs & preconditions
- From `project-design-config.md`: token source file(s) (e.g. `design-tokens/*.tokens.json`), real token names (grep before use), colour rule, theme (light/dark/both), components dir (for the no-raw-hex consumer check).
- Target: the DTCG source + the generated platform outputs (CSS vars, iOS, Android, JS) + the consumers that import them.
- Preconditions: token source readable and DTCG-shaped (`$value`/`$type` per token, `{alias}` references); Style Dictionary v4 available; the run stage is known — `editor` | `pre-commit` | `CI`.

## Oracle (source of truth)
W3C DTCG format spec + Style Dictionary v4 DTCG-native build (https://styledictionary.com/info/dtcg/) — `$value`/`$type`/`$description` and curly-brace alias references are the contract; the build is the transform, the lint is the gate.
- **hard (token-lint):** schema-valid DTCG (every token has `$value` + `$type`; types are DTCG-legal); zero broken aliases (every `{ref}` resolves to a real token — none dangling); every `color`-typed token has a dark-mode pairing (light/dark counterpart exists per `project-design-config.md` theme); `$description` present on every token; zero orphaned tokens (every defined token is referenced by another token or a consumer — grep proves it); zero raw hex/px in components where a token exists (grep the components dir).
- **hard (build):** Style Dictionary v4 emits all four platforms — CSS variables (`css/variables`), iOS (`ios-swift/class.swift`), Android (`android/resources`), JS (`javascript/es6`) — with **zero** dropped/unresolved tokens, and each output round-trips the same resolved value the source declares.
- **soft:** lint-message clarity, ramp/role completeness, naming consistency across platforms.

## Standards & techniques
- **DTCG-native source:** `{ "$value": "#2563eb", "$type": "color", "$description": "…" }`; alias as `{ "$value": "{color.brand.500}" }`. `$type` may sit on a group and inherit to members — the lint resolves the inherited type, never assumes one.
- **One source → four formats:** a single `tokens.config.json` with `source` + a `platforms` block; each platform names a `transformGroup` (`css`/`scss`, `ios-swift`, `android`, `js`) and a `format` (`css/variables`, `ios-swift/class.swift`, `android/resources`, `javascript/es6`). Generated files are build artifacts, never hand-edited.
- **Token-lint, the six rules** (the previously-unspecified linter): schema-valid · no broken aliases · dark-mode pairing on every colour · `$description` required · no orphaned tokens · no raw hex in components. Each rule emits a finding; any hard miss blocks.
- **Run stages:** `editor` = lint-on-save (fast, source-only, no full build); `pre-commit` = lint + build, block the commit on any hard miss; `CI` = lint + build + diff the committed outputs against a fresh build (stale generated files fail).

**Watch (do not gate):** EMERGING — the DTCG 2025.10 draft is **not** fully supported in Style Dictionary v4 (in progress for v5), and the DTCG→legacy converter does not refactor type values (e.g. `size` → `dimension`). Note any 2025.10-only constructs and any unconverted types; do not lint against them or gate on them yet.

## Step sequence
- **audit:** Run the six token-lint rules over the source (grep consumers for raw hex/orphans, resolve every `{alias}`, check each colour's dark pairing) → emit findings (read-only, no edits, no build).
- **build:** Explore (read-only; map the source tree, the four target platforms, and the run stage; confirm one source of truth) → Judge (lint pre-check + naming rubric, order-swapped) → Implement (one writer; edit `tokens.config.json` + the DTCG source + run Style Dictionary to (re)generate the four outputs — never hand-edit generated files) → Verify (re-run all six lint rules to green; Style Dictionary build emits four platforms with zero unresolved tokens; diff generated outputs are fresh; screenshots every state @ breakpoints; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every token: `$value` + (resolved) `$type` + `$description` present; type is DTCG-legal.
- Every `{alias}` resolves; zero broken/dangling references.
- Every `color` token has its light/dark counterpart; zero orphaned tokens.
- Zero raw hex/px in components where a token exists (grep proves it).
- Style Dictionary v4 emits CSS/iOS/Android/JS with zero dropped tokens; committed outputs match a fresh build (CI stage).
- **Gate:** all six token-lint rules green AND build emits four platforms cleanly AND (build mode) rubric mean ≥ 0.8.

## Output
Write `artifacts/token-pipeline/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: token`, `oracle: hard` for any lint miss — invalid schema, broken alias, missing dark pairing, missing `$description`, orphaned token, raw hex in a component — or a dropped/stale platform output), plus the verification block (per-platform build result + the six lint-rule results + screenshots) for build mode.

## Guardrails
Per `shared/guardrails.md`: this is the linter that section 5 ("the token linter") names — report what it says, not what the agent believes. Never guess a token name — grep the source (a wrong token silently falls back and reads as an orphan). Never hand-edit generated platform files — regenerate from the DTCG source. Reuse existing primitives before adding tokens. Preserve logic byte-for-byte. Read-only audit makes no edits; one writer for build; screenshot-verify.
