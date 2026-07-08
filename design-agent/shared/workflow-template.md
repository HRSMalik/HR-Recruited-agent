# Workflow Template

Every flow in `workflows/` follows this shape. Single responsibility, grounded in a standard/heuristic, with hard + soft oracles and a verify step. Read `project-design-config.md` first — never hardcode a project's tokens/components/dev-server.

```markdown
# <flow-name>

**Group:** <00-foundations | 10-tokens-systems | 20-interaction | 30-layout-ia | 40-accessibility | 50-content | 60-evaluation | 70-process | 80-patterns>
**Runs as:** <inline | subagent: ../.claude/agents/<name>.md>
**Mode:** <audit (read-only) | build (writer + verify loop)>   ·   **Default model:** <haiku | sonnet | opus>

## Purpose
One or two lines: the design responsibility this flow owns and the question it answers.

## Inputs & preconditions
- From `project-design-config.md`: token source + names, component library, dev-server URL/port + creds, breakpoints, locked rules.
- Target screen(s)/component(s); the relevant standard (WCAG SC / Nielsen heuristic / Material/NN-g guidance).
- Preconditions: dev server reachable; existing tokens/components read before acting.

## Oracle (source of truth)
Name the external truth — a WCAG success criterion, a token/convention, a measured threshold (contrast, spacing scale, timing band), a heuristic. Split **hard** (deterministic gate) vs **soft** (rubric/craft). NEVER "it looks fine."

## Standards & techniques
The concrete rules this flow applies (cite the principle): e.g. 4/8pt scale + internal≤external; single-column forms; 60-30-10; type scale; 120–300ms ease-out; tabular numerals; right-align numbers.

## Step sequence
- **audit:** Plan checks → drive the live screen at the project's viewports → assert against the oracle → emit findings (read-only, no edits).
- **build:** Explore (N divergent specs, read-only) → Judge (rubric + hard oracles, order-swapped) → Implement (one writer; layout/style/markup only, reuse components/tokens) → Verify (Playwright screenshots every state @ breakpoints; axe-core + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Concrete checks (token used not hex; contrast ≥ threshold; states all present; spacing on-scale; numbers right-aligned…).
- **Gate:** hard oracles green AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/<flow>/report.json` per `shared/report-format.md` — findings per `finding-schema.md`, plus the verification block (screenshots + viewports + hard-oracle results + rubric score) for build mode.

## Guardrails
Per `shared/guardrails.md`: preserve logic byte-for-byte; reuse components/tokens before inventing; read-only flows make no edits; one writer; screenshot-verify; trust the screenshot over the diff.
```

**Authoring rules**
- One responsibility per flow. Ground every rule in a named standard/heuristic.
- The oracle is external. Hard where you can measure it; soft (rubric) only for genuine taste.
- A "fix" is stated in design-system terms (token / spacing value / component), actionable without re-running.
