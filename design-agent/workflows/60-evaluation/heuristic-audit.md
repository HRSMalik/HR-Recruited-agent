# heuristic-audit

**Group:** 60-evaluation
**Runs as:** subagent: ../.claude/agents/design-reviewer.md
**Mode:** audit (read-only)   ·   **Default model:** sonnet

## Purpose
The behavioural UI scan: drive the live screen and inspect it against Nielsen's 10 usability heuristics, flagging hierarchy, spacing, contrast, consistency, state, and copy issues. Never edits.

## Inputs & preconditions
- From `project-design-config.md`: dev-server URL/port + login creds, breakpoints to screenshot, token source (to name fixes), component library.
- Target screen(s); Nielsen's 10 heuristics + `shared/deceptive-pattern-checklist.md` (EDPB taxonomy) as the rule set.
- Preconditions: dev server reachable and logged in; reviewer is tool-scoped read-only (`Read, Grep, Glob, Bash` — no Edit/Write).

## Oracle (source of truth)
Nielsen's 10 usability heuristics + the live rendered screen at the project's viewports.
- **hard:** none authored here — the scan is observational; any deterministic gate (contrast, axe, overflow) is surfaced as a finding for the relevant build flow, not fixed here.
- **soft:** each heuristic violation scored on Nielsen severity 0–4 (frequency × impact × persistence).

## Standards & techniques
- **Nielsen's 10:** visibility of system status, match to the real world, user control/freedom, consistency & standards, error prevention, recognition over recall, flexibility/efficiency, aesthetic & minimalist design, help users with errors, help & documentation.
- **Drive the live screen** at every breakpoint; flag hierarchy, spacing, contrast, consistency, state coverage, and copy issues against the heuristics.
- **Nielsen severity 0–4:** `0` none · `1` cosmetic · `2` minor · `3` major · `4` catastrophe — mapped to the finding-schema severity (cosmetic/minor/major/critical).
- **Deceptive-pattern axis:** run `shared/deceptive-pattern-checklist.md` (EDPB 6 + 4 classic types) on consent/signup/checkout/cancel paths — a GDPR/DSA legal-risk axis, a confirmed pattern defaults to **major+**, the fix is the listed fair-pattern alternative.
- Every finding **cites the heuristic number** (Nielsen #N or EDPB D-0N) and carries a screenshot + viewport as evidence.

## Step sequence
- **audit:** Plan checks per heuristic → log in and drive the live screen at each project viewport → screenshot every relevant state → assert against the 10 heuristics → score each violation 0–4 → emit a prioritized finding list (read-only, no edits).
- **build:** not applicable — this flow is audit-only; fixes are routed to the owning build flows (visual/interaction/content/token).

## Assertions & exit gate
- Every finding cites a Nielsen heuristic number, a Nielsen 0–4 severity, and a screenshot + viewport.
- Findings grouped by type then severity, returned critical → cosmetic.
- **Gate:** audit-only — no build gate; the flow passes when every reachable screen at every viewport has been scanned and findings emitted.

## Output
Write `artifacts/heuristic-audit/report.json` per `shared/report-format.md` (`mode: audit`) — findings per `finding-schema.md` (`type: heuristic`, `heuristic: Nielsen #N`, `wcag_ref: null`), prioritized list, plus screenshots + viewports in the verification block. Never edits the app.

## Guardrails
Per `shared/guardrails.md`: read-only — the reviewer is tool-scoped to `Read, Grep, Glob, Bash`, makes no edits. Report what the live screen shows, not what the agent believes; trust the screenshot. Fixes are stated in design-system terms (token / spacing / component) and routed to a build flow.
