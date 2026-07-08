# design-exploration

**Group:** 70-process
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (fans out design-explorer ×N, then design-judge)
**Mode:** build (explore → judge → implement → verify)   ·   **Default model:** opus

## Purpose
The diverge → judge → converge loop for a non-trivial layout decision where several valid directions exist — generate distinct grounded proposals, score them against weighted criteria, implement only the winner.

## Inputs & preconditions
- From `project-design-config.md`: token source + names, component library, dev-server URL/port + creds, breakpoints, locked rules, aesthetic direction.
- Target: one screen/region with a stated complaint (e.g. "this detail header feels off / cramped / unfocused").
- Preconditions: dev server reachable; existing components + tokens read before any proposal; the complaint is concrete enough to score against.

## Oracle (source of truth)
The weighted judging criteria + the hard oracles — not "looks nicer".
- **hard:** each proposal cites only real components/tokens (grep-confirmed); the implemented winner passes contrast / axe / zero console errors / no overflow / token conformance / logic-unchanged.
- **soft:** the weighted rubric below, scored by a separate evaluator on the live screenshot.

## Standards & techniques
- **Diverge:** 2–4 DISTINCT proposals, each with a clear lens (centered single-card / two-column with a useful secondary / full-width header band) — not three recolours of one layout.
- Each proposal is a concrete **spec, no edits:** layout shape, 4/8pt spacing values, pseudo-JSX with real component names, rationale, risks.
- **Weighted criteria:** fixes the stated complaint at the target viewport (×3); appropriate for the tool not marketing fluff (×2); single clear focus (×2); fits conventions/tokens (×2); graceful at the narrow breakpoint (×1); low logic-change risk (×1).
- **Judge:** score every proposal, then **swap order and judge twice** to kill position bias; graft good ideas from the runners-up into the winner.

## Step sequence
- **build:** Explore (design-explorer ×N, read-only — N divergent specs, no edits) → Judge (design-judge scores vs the weighted criteria + hard oracles, order-swapped twice) → Implement (one writer applies the winning spec; layout/style/markup only, reuse components/tokens) → Verify (Playwright screenshots every state @ breakpoints; contrast + axe + zero console errors; evaluator re-scores from the screenshot) → loop ≤15 or pass.

## Assertions & exit gate
- ≥2 genuinely distinct proposals, each grounded in real components/tokens (not generic).
- Judge ran twice with order swapped; the same winner survives both passes (or position bias is explicitly resolved).
- Winner verified by screenshot at every breakpoint; hard oracles green.
- **Gate:** hard oracles green AND rubric mean ≥ 0.8.

## Output
Write `artifacts/design-exploration/report.json` per `shared/report-format.md` — the N proposal specs, the two scoring passes, the chosen winner + grafted ideas, plus the verification block (screenshots + viewports + hard-oracle results + rubric score).

## Guardrails
Per `shared/guardrails.md`: proposers and judge are read-only (no edits); exactly one writer implements the winner. Grounded oracles — judge the live screenshot, never the prose. Trust the screenshot over the diff. Maps 1:1 to the design-orchestrator explore → judge → implement → verify loop.
