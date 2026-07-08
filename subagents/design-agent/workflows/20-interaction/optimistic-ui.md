# optimistic-ui

**Group:** 20-interaction
**Runs as:** subagent: ../.claude/agents/interaction-designer.md
**Mode:** build (writer + verify loop) · audit (responsiveness scan)   ·   **Default model:** sonnet

## Purpose
Own perceived responsiveness: reflect an action in the UI immediately, then reconcile to the server — with a clean rollback path on failure — so the interface never feels like it's waiting. This flow touches state, so it specs the behaviour and preserves the logic.

## Inputs & preconditions
- From `project-design-config.md`: component library, token source + names, breakpoints, theme, crash-protection/logic rules, locked rules.
- Target: actions where the result is high-probability and the round-trip is user-visible (toggle, move card to a stage, mark read, save).
- Preconditions: dev server reachable; the backend action is **idempotent** (re-applying the same op is safe) — if not, flag it before applying optimism.

## Oracle (source of truth)
The Doherty Threshold (< 400ms keeps engagement) + the optimistic-update contract: reflect → snapshot → reconcile → roll back on failure.
- **hard:** a rollback **snapshot** is captured before the optimistic change; concurrent ops are **tracked independently** (one failing doesn't corrupt another); on failure the UI **rolls back, shows a clear message, and offers undo/retry**; the backend op is **idempotent**; perceived response < 400ms.
- **soft:** the optimistic state is visually distinguishable as pending where it matters; reconciliation to the server value is seamless, not a flicker.

## Standards & techniques
- **Reflect immediately:** apply the expected result on interaction — don't gate the UI on the network.
- **Snapshot + rollback:** keep the prior value; on error restore it exactly, surface an inline message, and offer undo/retry (per `feedback-surfaces`).
- **Independent op tracking:** key each in-flight op so reconciling/failing one never clobbers another in the same list.
- **Reconcile to server truth:** replace the optimistic value with the server's authoritative response, not the guess.
- **Idempotency:** retries and double-fires must not double-apply — confirm the backend contract.
- **Designer specs, preserves logic:** this flow describes the state behaviour and styles the pending/rolled-back surfaces; it does **not** rewrite the store/API. If correct behaviour needs a logic change, **stop and flag it** for the engineer.

## Step sequence
- **audit:** identify candidate actions → check for an immediate reflect, a snapshot, independent op tracking, a rollback-with-message-and-undo path, and backend idempotency → measure perceived latency vs 400ms → flag missing snapshots, shared-state corruption, silent failures, non-idempotent ops → emit findings (read-only).
- **build:** Explore (≥2 optimistic specs incl. the pending + rollback surfaces, read-only) → Judge (snapshot + independent-tracking + rollback-message-undo + idempotency rubric, order-swapped) → Implement (one writer; style the pending/rolled-back/undo surfaces from existing components/tokens — **logic preserved byte-for-byte**, flag any required logic change) → Verify (Playwright drives success + forced-failure paths, screenshots reflect/pending/rollback/undo @ breakpoints; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- A snapshot is taken before the change; rollback restores it and shows a message + undo/retry on failure.
- Concurrent ops are tracked independently; the backend op is idempotent; perceived response < 400ms.
- Logic files unchanged (diff check); any needed logic change is flagged, not made.
- **Gate:** hard oracles green (snapshot + independent tracking + rollback/undo + idempotency + logic-unchanged + axe + console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/optimistic-ui/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: interaction`, `oracle: hard` for a missing snapshot / silent failure / non-idempotent op / changed logic, `heuristic` Nielsen #1 Visibility of system status), plus the verification block (success + forced-failure captures incl. rollback/undo @ breakpoints + hard-oracle results + rubric score).

## Guardrails
Per `shared/guardrails.md`: **preserve app logic byte-for-byte** — this flow specs state behaviour and styles surfaces only; if a fix needs a logic change, stop and flag it. Reuse components/tokens before inventing; never guess a token name. Read-only audit makes no edits; one writer for build; trust the screenshot over the diff.
