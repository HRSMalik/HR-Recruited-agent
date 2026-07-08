# figma-design-to-code

**Group:** 70-process
**Runs as:** subagent: ../.claude/agents/visual-designer.md (the orchestrator pulls the frame; one writer generates)
**Mode:** build (writer + verify loop)   ·   **Default model:** opus

## Purpose
Turn a referenced Figma frame into framework code that REUSES the project's canonical components via Code Connect — "connect first, generate second" — instead of re-deriving raw markup from the design's visual tree.

## Inputs & preconditions
- From `project-design-config.md`: token source + real token names, component library + components dir, framework + dev-server/port + screenshot creds, breakpoints, locked rules.
- Target: a Figma frame/node (URL or node-id) and the screen/component it implements.
- Preconditions: Figma Dev-Mode MCP server reachable and authenticated (`whoami`); token source + components dir read first; the frame's components are Code-Connected in the project's library (else flag and stop — don't free-hand markup for a connected component).

## Oracle (source of truth)
The Figma frame's design data (via the Dev-Mode MCP server) + Code Connect mappings + the project token map — never a hand-eyeballed copy of the pixels.
- **hard:** every Figma component with a Code Connect mapping is emitted via its mapped import (`<CodeConnectSnippet>` import statements honored), not re-derived markup; every Figma variable resolves to a real project token (grep the token source — no raw hex/spacing where a token exists); generated screen renders with zero console errors; contrast + axe pass at the screenshot viewport; no viewport overflow; logic files unchanged.
- **soft:** craft rubric on the rendered output — fidelity to the frame, hierarchy, spacing rhythm, state coverage.

## Standards & techniques
- **Two-pass read (token budget):** Pass 1 — `get_metadata` for the cheap structural map (node ids, names, hierarchy) and pick the exact node. Pass 2 — `get_design_context` for the targeted subtree + `get_variable_defs` for the variable→value bindings; `get_screenshot` only as a visual reference. Never pull `get_design_context` over a whole large frame in one shot — scope to the node from pass 1 so you stay within budget.
- **Connect first, generate second** (per source): resolve mappings with `get_code_connect_map`/`get_code_connect_suggestions` BEFORE writing JSX. A mapped component is emitted through its Code Connect import + design-property values (variant/boolean/text); only genuinely unmapped, layout-only nodes are authored as fresh markup — and a repeated unmapped pattern is extracted into `components/`.
- **Variable → token mapping:** map each Figma variable from `get_variable_defs` to its project token; record the design-value → token pairs in the report's token map. If a variable has no token equivalent, flag it (do not invent a token name).
- Honor the **"Add instructions for MCP"** guidance attached to connected components (prop patterns, a11y, team conventions) — they are authoritative over the writer's defaults.

## Step sequence
- **build:** Explore (read-only; two-pass read the frame, resolve Code Connect mappings, build the variable→token map, sketch the component tree — no edits) → Judge (design-judge confirms connect-coverage + token mapping + fidelity, order-swapped) → Implement (one writer generates the framework code: mapped components via Code Connect imports, unmapped layout via tokens, reusing the component library) → Verify (Playwright screenshots every state @ breakpoints; contrast + axe + zero console errors; logic-unchanged diff; evaluator re-scores from screenshots vs the Figma reference) → loop ≤15 or pass.

## Assertions & exit gate
- Two-pass read used (metadata → scoped design-context/variable-defs); no whole-frame single-shot pull.
- Every connected Figma component emitted via its mapped import — zero re-derived markup for a mapped node.
- Every Figma variable resolves to a real token (grep-verified); token map recorded.
- All states render; zero console errors; contrast ≥ thresholds; axe 0 violations; no overflow; logic diff clean.
- **Gate:** hard oracles green AND rubric mean ≥ 0.8.

## Output
Write `artifacts/figma-design-to-code/report.json` per `shared/report-format.md` — the node id + frame ref, the Code Connect coverage (mapped vs authored nodes), the variable→token map, plus the verification block (per-state screenshots + viewports + hard-oracle results + rubric score). Findings per `finding-schema.md` for any unmapped-but-should-be-connected node or unmapped variable.

## Guardrails
Per `shared/guardrails.md`: reuse canonical components/tokens before inventing — Code Connect is the reuse mechanism here; one writer, sequenced; the evaluator grades the rendered screenshots vs the frame, not prose; preserve app logic byte-for-byte; trust the screenshot over the diff; delete temp Playwright scripts.

> **Watch (do not gate):** code-to-design **write-back** — `use_figma` / `generate_figma_design` (and `create_new_file`/`add_code_connect_map`) — is EMERGING and **client-gated**. Read-from-Figma is the standard path; never auto-write back into a Figma file. Treat any write-back only as a separately-approved, human-initiated step — it never becomes a hard oracle and never runs unattended in this flow.
