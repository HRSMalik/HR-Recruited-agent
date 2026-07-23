# Run Budget — Cost & Termination Discipline

Binding on every run. Architecture runs fan out explorers + up to five domain specialists + an
evaluator - the heaviest fan-out of any agent, and "token budget explains most of the outcome variance."
This makes cost a **first-class, bounded, reported** dimension. Pairs with `guardrails.md` and
`reliability.md`.

## 1. Every run has an explicit budget (set at intake)

At intake the orchestrator fixes a budget from the effort tier and states it in the plan:

| Tier | Fan-out | Per-agent turn cap | Verify loop | Wall-clock target |
| --- | --- | --- | --- | --- |
| single bounded decision (one ADR) | none | 15 | ~2 | ~10 min |
| "which way should we build this?" | 2-4 explorers + relevant specialists | 25 | ≤ ~10 | ~30-45 min |
| whole-system / greenfield / migration | explorers + 5+ specialists, pipelined writer | 40 | ≤ ~10 | scoped, stated up front |

- **Verify loop is capped** (~10 iterations, already the loop bound): stop when hard oracles are green
  AND rubric mean ≥ 0.8.
- Don't fan out the full specialist roster on a single-decision mandate (1 / 2-4 / 5+ by complexity).

## 2. Single heavy run at a time
Do not launch a second whole-system design/audit while one is in flight. A single ADR may run alone;
heavy fan-outs are serialized.

## 3. Model routing (strong orchestrator, right-sized workers)
Orchestrator + `solution-architect` writer + `architecture-evaluator` → capable tier (Opus). Read-only
domain analysts → Sonnet; Haiku only for shallow lookups. Match the tier to reasoning depth, not title.

## 4. Task-quality gate before spawning (waste prevention)
A vague subagent task wastes the whole call. Before dispatching any specialist, give a self-contained
brief (mandate + scope, the `QAS-*` drivers, the workflow path, the output contract, what NOT to do). If
you can't write that brief, frame more first - don't spend a call to discover the task.

## 5. Stop on ENOUGH, not on the cap
The iteration cap is a backstop. Stop once hard oracles pass and the rubric clears - do not keep
re-documenting a passing design for polish.

## 6. Budget accounting IS reported
`artifacts/summary.json` records budget usage so cost is visible and gated:

```json
"budget": {
  "tier": "which-way",
  "explorers": 3, "specialists": 3,
  "evaluate_iterations": 2,
  "wall_clock_min": 34,
  "caps": { "per_agent_turns": 25, "verify_loop": 10, "wall_clock_target_min": 45 },
  "cap_hit": false,
  "coverage": "complete | partial (which dimensions/directions were cut and why)"
}
```

A run that hit a cap reports **partial coverage**, never inflates a truncated run to complete.

## Budget: tunable at the plan gate + actual spend reported (standing directive 2026-07-23)

**The budget is a first-class, TUNABLE deliverable at the PLAN GATE.** Present it as its own explicit block — token ceiling · fan-out · per-agent turn cap · wall-clock target — so the human can adjust the caps BEFORE anything runs. Also state a **token ceiling** for the run (derive from the effort tier if none is given). A budget embedded silently in the dispatch and never surfaced for tuning does NOT satisfy this — cost must be visible and adjustable up front.

**Actual spend is reported in the HUMAN summary too, not just `summary.json` — unasked.** State actual vs cap for BOTH tokens AND wall-clock; flag any overrun plainly even when the other dimension stayed under cap (a run can be under the token cap yet over the wall-clock target — say so). Report the wall-clock MEASURED, never the planned ETA. This lets the human tune the caps for the next run.
