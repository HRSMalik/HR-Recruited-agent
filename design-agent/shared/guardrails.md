# Guardrails — Preserve Logic · Reuse · One Writer · Verify

Binding on every design flow. A flow that can't honor these downgrades scope and says so.

## 1. Preserve app logic byte-for-byte
The designer changes **layout / style / markup only** — never event handlers, state, data flow, store calls, validation logic, API calls, audit/navigation. Enforce in the writer's prompt AND a diff check: logic files/lines unchanged. If a visual fix appears to require a logic change, stop and flag it — don't change behaviour to make a layout work.

## 2. Reuse before invention
- Check the existing **component library** first (`project-design-config.md` lists it) before writing any new JSX. If a component exists, use it.
- Use **existing tokens** — never hardcode a colour/spacing/radius/shadow where a token exists. Grep the token source for the real name; never guess a token (a wrong/non-existent token silently falls back).
- Extract a repeated pattern into a component/token immediately (two identical structures is already too many). New tokens go in the token source, new components in `components/` — document both.

## 3. One writer (no parallel-write conflicts)
- Proposer/auditor/judge agents are **read-only** — tool-scoped to `Read, Grep, Glob, Bash` (no `Edit`/`Write`/`Write`-MCP).
- Exactly **one** implementer (`visual-designer`, then `interaction-designer`) writes, **sequenced not parallel**. The orchestrator never runs two writers concurrently on the same surface.

## 4. Verify by running it (the gate)
- Drive the **live app** headlessly (Playwright); screenshot **every state** (default/hover/focus/active/disabled/loading/empty/error/success) at the project's breakpoints.
- Hard oracles are **blocking**: contrast, axe-core, **zero console errors**, no viewport overflow, token conformance, logic-unchanged. Soft (rubric) scores only after hard oracles are green.
- The evaluator screenshots and grades **what it sees** — not the writer's prose. Trust the screenshot over the diff. Delete temp Playwright scripts after.
- Bound the loop (≤ ~15 iterations) so it terminates.

## 5. External oracle over self-judgment
Report what axe-core / Playwright / the token linter / the contrast checker say — not what the agent believes. A generator never grades its own work; a separate skeptical evaluator does.

## 6. Project-config abstraction (reusability)
All project specifics — brand/palette, token source + names, component library, dev-server URL/port + login creds, breakpoints, locked rules, design-template folder — live in `project-design-config.md`. Flows read config, never hardcode a project's values. This is what lets the same agent run on any project.
