# Quality Rubric — the Senior Craft Bar + Oracles

Two layers: **hard oracles** gate deterministically; **soft oracles** are rubric-scored by a separate skeptical evaluator. Never let taste override a hard-oracle failure.

## Hard oracles (deterministic, BLOCKING)

Any failure → reject, loop back to the writer. Checked first, before any soft scoring.

| Oracle | Check / threshold |
|--------|-------------------|
| **Contrast** | text ≥ 4.5:1, large text (≥18px/14px bold) ≥ 3:1, non-text/UI & adjacent ≥ 3:1 (WCAG 1.4.3 / 1.4.11). Verify light AND dark. |
| **axe-core** | 0 violations (missing alt, unlabeled fields, heading skips, ARIA misuse, dup IDs, missing lang, target-size). axe catches ~57% of WCAG — necessary, not sufficient. |
| **Console errors** | 0 console/page errors per state, asserted via Playwright. |
| **Viewport overflow** | no horizontal scroll / clipped content at any defined breakpoint. |
| **Token conformance** | no hardcoded hex/spacing where a token exists; every colour/border/space resolves to a real token (grep the token source — never guess a token name). |
| **Logic preserved** | logic files unchanged (diff check) — the designer changed layout/style/markup only. |
| **Core Web Vitals** | INP ≤ 200ms, LCP ≤ 2.5s, CLS ≤ 0.1 at p75 (Lighthouse/Playwright). A design that ships a layout-shift or a janky interaction fails like a contrast failure. See `90-performance/core-web-vitals.md`. |
| **Chart integrity** | for any data viz: zero-baselined bars, no truncated/dual axes, normalised choropleths, honest aggregation — a misleading axis blocks the build. See `90-data-viz/chart-design.md`. |
| **Live-region / error a11y** | dynamic status/error announced via a pre-mounted ARIA live region; form errors programmatically associated (`aria-invalid` + `aria-describedby`). See `40-accessibility/`, `20-interaction/feedback-surfaces.md`. |

## Soft oracles (rubric-scored, ADVISORY — only after hard oracles are green)

Score each 0.0–1.0 with a single skeptical evaluator (one prompt → score + pass/fail). Mean ≥ 0.8 to pass. The senior craft bar:

- **Precision & alignment** — optical alignment, consistent edges, nothing 1px off; strict 4/8 spacing rhythm; a clear grid. Crispness from discipline, not decoration.
- **Typographic hierarchy** — deliberate contrast in weight/size/colour so the eye lands right first; tight line-heights for labels, comfortable for body; no flat walls of same-size text; tabular numerics in data.
- **Purposeful depth** — elevation + hairline borders used intentionally and consistently; subtle, never heavy; consistent radii; light, airy cards over boxy ones.
- **Considered colour** — restrained 60-30-10; accent earns attention (10%); calm neutrals carry the surface; status colour always paired with a label/icon.
- **Polished states & micro-interactions** — every interactive element has crisp hover/focus/active/disabled/loading/empty/error; ~120–300ms ease-out transitions; empty states get an icon + a next action, never a bare sentence.
- **Refined details** — consistent icon sizing/stroke, aligned controls, balanced whitespace, no orphaned/stranded elements. If it reads "default/bootstrappy", it fails this bar.

## Finding severity (Nielsen 0–4, for audits)

`0` not a problem · `1` cosmetic · `2` minor · `3` major · `4` catastrophe. Severity = f(frequency, impact, persistence). Map to the finding-schema `severity` (cosmetic/minor/major/critical). Accessibility failures that block a task default to **major+**.

## LLM-as-judge guardrails
- **Position bias** — judging proposals: swap order and judge twice.
- **Length/verbosity bias** — don't reward longer specs; score against criteria only.
- **Self-preference** — a separate evaluator, never the generator grading itself.
- The evaluator **navigates + screenshots the live page itself** before scoring; it grades what it sees, not the writer's prose claims.
