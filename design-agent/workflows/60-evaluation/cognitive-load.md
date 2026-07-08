# cognitive-load

**Group:** 60-evaluation
**Runs as:** subagent: ../.claude/agents/design-reviewer.md
**Mode:** audit (read-only)   ·   **Default model:** sonnet

## Purpose
Scan the live screen for mental effort the UI imposes — recall demands, unchunked choices, clutter, info carried across screens — and flag where load can be cut so the user thinks less to act.

## Inputs & preconditions
- From `project-design-config.md`: dev-server URL/port + creds, breakpoints, component library, token source (to name fixes).
- Target screen(s)/flow; the rule set (NN/g cognitive-load guidance + Laws of UX — Miller, Hick).
- Preconditions: dev server reachable and logged in; reviewer read-only; multi-step flows walkable to check cross-screen recall.

## Oracle (source of truth)
NN/g cognitive-load guidance + Laws of UX (Miller's Law, Hick's Law).
- **hard:** none authored here — observational; any deterministic gate it spots (contrast, target size) is surfaced for the owning build flow.
- **soft:** each load issue scored on Nielsen severity 0–4 by frequency × impact × persistence.

## Standards & techniques
- **Recognition over recall:** options/data shown, not memorised; the UI surfaces what the user needs rather than asking them to remember it.
- **Consistency:** repeated patterns lower load — same control does the same thing everywhere.
- **Reduce clutter:** strip non-essential elements competing for attention (aesthetic & minimalist).
- **Miller 7±2 chunking:** group long lists/forms into chunks of ~5–9; **Hick's Law:** fewer/segmented choices speed decisions — progressively disclose, don't dump.
- **Don't carry info across screens:** never make the user remember a value from a prior step — persist or re-show it.

## Step sequence
- **audit:** Walk the live flow at each project viewport → flag recall demands, unchunked choices, clutter, and cross-screen memory burdens against the oracle → score each 0–4 → emit a prioritized finding list (read-only, no edits).
- **build:** not applicable — audit-only; fixes are routed to the owning build flows (layout/interaction/content).

## Assertions & exit gate
- Each finding names the violated principle (recognition/consistency/clutter/chunking/Hick/cross-screen) with a screenshot + viewport.
- Findings grouped by type then severity, returned critical → cosmetic.
- **Gate:** audit-only — passes when the flow has been walked at every viewport and load findings emitted.

## Output
Write `artifacts/cognitive-load/report.json` per `shared/report-format.md` (`mode: audit`) — findings per `finding-schema.md` (`type: heuristic`, `heuristic: NN/g cognitive load / Laws of UX`, `wcag_ref: null`), prioritized list, plus screenshots + viewports in the verification block. Never edits the app.

## Guardrails
Per `shared/guardrails.md`: read-only — tool-scoped to `Read, Grep, Glob, Bash`, makes no edits. Report what the live flow shows, not what the agent believes; trust the screenshot. Fixes stated in design-system terms (token / spacing / component) and routed to a build flow.
