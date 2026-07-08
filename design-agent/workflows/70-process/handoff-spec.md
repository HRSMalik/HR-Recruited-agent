# handoff-spec

**Group:** 70-process
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (deliverable author)
**Mode:** audit (read-only deliverable — measures + documents, no source edits)   ·   **Default model:** sonnet

## Purpose
Produce a build-ready spec from an approved design so a developer can build it without asking a single spacing or token question — redlines, the token map, component states, and an explicit ready-vs-WIP line.

## Inputs & preconditions
- From `project-design-config.md`: token source + names, component library, breakpoints, dev-server URL/port (to screenshot the approved design), aesthetic/locked rules.
- Target: the approved screen(s)/component(s) to hand off.
- Preconditions: the design exists and is screenshot-able; token source read so every value maps to a real token name.

## Oracle (source of truth)
The approved design's measured values + the project's real tokens — every measurement traces to a token, never a guessed pixel.
- **hard:** every colour/space/radius/size in the spec resolves to a real token name (grep-confirmed); every redline measurement is on the 4/8pt scale; every component state is enumerated.
- **soft:** clarity and completeness — a dev could build from it cold with no follow-up questions.

## Standards & techniques
- **Redlines / measurements:** annotate spacing (4/8pt scale, internal ≤ external), sizes, and alignment on screenshots at each breakpoint.
- **Token map:** design value → code token (`#2563eb` → `color-action-primary`; `16px` → `space-inset-md`) — never a raw value in the handoff.
- **Component states:** enumerate default / hover / focus / active / disabled / loading / empty / error / success for every interactive element.
- **Ready vs WIP:** mark each region `READY` (spec complete, build it) or `WIP` (still in design — don't build yet) so nothing half-specified reaches a dev.

## Step sequence
- **audit:** Screenshot the approved design at each breakpoint → measure spacing/sizes/alignment and annotate redlines → map every value to a real token (grep the source) → enumerate states per component → mark each region READY/WIP → assemble the spec (read-only, no source edits).

## Assertions & exit gate
- Every measurement is on the spacing scale and annotated on a breakpoint screenshot.
- Every colour/space/radius/size maps to a real token (no raw values, no guessed token names).
- Every interactive component lists all its states; every region marked READY or WIP.
- **Gate:** hard oracles green (all values tokenized, scale-conformant, states + ready/WIP complete).

## Output
Write `artifacts/handoff-spec/report.json` per `shared/report-format.md` — the redline screenshots (viewport in filename), the token map, the per-component state list, and the READY/WIP marking; any gaps emitted as `hard` findings per `finding-schema.md`.

## Guardrails
Per `shared/guardrails.md`: read-only deliverable — no source edits. Never guess a token name (grep the source; a wrong token silently falls back). Reference existing components by name. Anything not fully specified is marked WIP, never shipped as READY.
