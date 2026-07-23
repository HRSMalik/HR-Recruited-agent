# Run Budget — Cost & Termination Discipline

Binding on every run. Design runs fan out explorers/auditors and drive a real browser for screenshot
verification - both burn tokens and wall-clock. This makes cost a **first-class, bounded, reported**
dimension. Pairs with `guardrails.md` (safety) and `reliability.md`.

## 1. Every run has an explicit budget (set at intake)

At intake the orchestrator fixes a budget from the effort tier and states it in the plan:

| Tier | Fan-out (explore/audit) | Per-agent turn cap | Verify loop | Wall-clock target |
| --- | --- | --- | --- | --- |
| one-screen tweak | none (writer only) | 12 | ~3 | ~5 min |
| "feels off" screen | 2-4 explorers + judge | 20 | ≤ ~15 | ~15-25 min |
| whole-app audit / redesign / token-migration | auditors + explorers, pipelined writer | 25 | ≤ ~15 per screen | ~30-45 min |

- **Verify loop is capped** (~15 iterations, already the loop bound): stop when hard oracles are green
  AND rubric mean ≥ 0.8 - never keep re-screenshotting past that.
- **Per-agent turn cap** bounds each dispatched flow. **Wall-clock target** bounds the whole run; past
  it, stop dispatching new flows and report coverage.

## 2. Single heavy run at a time
Do not launch a second whole-app audit/redesign while one is in flight. Shallow single-screen work may
run alone; heavy fan-outs are serialized.

## 3. Model routing (cheap by default)
Read-only auditors (`design-reviewer`, `a11y-auditor`, `design-system-keeper`) and shallow scans →
Haiku. The writer (`visual-designer`/`interaction-designer`) and `design-judge` → the capable tier.
Never run a whole audit on the top tier by default.

## 4. Stop on ENOUGH, not on the cap
The iteration cap is a backstop. Stop the verify loop the moment hard oracles pass and the rubric clears
- do not iterate a passing screen for polish. Driver/screenshot de-flaking is overhead to minimize, not
a finding (`reliability.md`).

## 5. Budget accounting IS reported
`artifacts/summary.json` records budget usage so cost is visible and gated:

```json
"budget": {
  "tier": "feels-off-screen",
  "agents_dispatched": 5,
  "verify_iterations": 4,
  "wall_clock_min": 18,
  "caps": { "per_agent_turns": 20, "verify_loop": 15, "wall_clock_target_min": 25 },
  "cap_hit": false,
  "coverage": "complete | partial (which screens/breakpoints were cut and why)"
}
```

A run that hit a cap reports **partial coverage**, never inflates a truncated run to complete. Fan out
only up to the tier ceiling and only when the mandate's value justifies it.

## Budget: tunable at the plan gate + actual spend reported (standing directive 2026-07-23)

**The budget is a first-class, TUNABLE deliverable at the PLAN GATE.** Present it as its own explicit block — token ceiling · fan-out · per-agent turn cap · wall-clock target — so the human can adjust the caps BEFORE anything runs. Also state a **token ceiling** for the run (derive from the effort tier if none is given). A budget embedded silently in the dispatch and never surfaced for tuning does NOT satisfy this — cost must be visible and adjustable up front.

**Actual spend is reported in the HUMAN summary too, not just `summary.json` — unasked.** State actual vs cap for BOTH tokens AND wall-clock; flag any overrun plainly even when the other dimension stayed under cap (a run can be under the token cap yet over the wall-clock target — say so). Report the wall-clock MEASURED, never the planned ETA. This lets the human tune the caps for the next run.
