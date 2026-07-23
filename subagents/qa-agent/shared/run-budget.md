# Run Budget — Cost & Termination Discipline

Binding on every run. Every run burns real tokens AND hits a live, often billed, SUT. A confused
agent must never loop forever, and a run must never silently overspend. This contract makes cost a
**first-class, bounded, reported** dimension - the same discipline a hardened standalone QA agent
enforces in code, expressed here as orchestrator behavior.

## 1. Every run has an explicit budget (set at intake)

At intake the orchestrator fixes a budget from the effort tier (from the mandate + `project-qa-config.md`),
and states it in the plan. Three hard ceilings, plus model routing:

| Effort tier | Max flows (fan-out) | Per-flow turn cap | Wall-clock target |
| --- | --- | --- | --- |
| smoke / sanity | 1-2 | 15 turns | ~5 min |
| PR gate | 3-5 | 25 turns | ~10-15 min |
| full release sweep | 8-12 | 40 turns | ~30-45 min |
| deep audit (one area) | sub-decompose, 6-10 workers | 40 turns | scoped, stated up front |

- **Per-flow turn cap** is the analog of a coded iteration cap: every dispatched flow is given an explicit
  `maxTurns` from its tier. A flow that hits its cap **stops and reports partial coverage** - it never
  silently keeps looping.
- **Wall-clock target** bounds the whole run. Past it, the orchestrator stops dispatching NEW flows,
  lets in-flight ones finish, and reports what was and was not covered.
- **Fan-out ceiling** caps concurrent Agent dispatches. Multi-agent fan-out costs ~15x chat tokens, so
  fan out only up to the tier ceiling and only when the mandate's value justifies it.

No tier stated ⇒ default to the smallest that fits the mandate (smoke), and say so.

Alongside the three ceilings, state a **token ceiling** for the run (the hard cap on total spend). No token
figure given ⇒ derive one from the tier (smoke ~75k · PR gate ~200k · full sweep ~400k · deep audit stated
up front) and say so.

**The budget is a first-class, TUNABLE deliverable at the PLAN GATE.** The plan the orchestrator halts on
(see `qa-orchestrator.md` step 3) MUST present the budget as its own explicit block — token ceiling ·
fan-out · per-flow turn cap · wall-clock target — so the human can **adjust the caps before anything runs**.
A budget silently embedded in the dispatch (never surfaced for tuning) does not satisfy this: cost must be
visible and adjustable *up front*, not discovered after the spend. (Standing user directive 2026-07-23: the
gate must always show the flows-to-test + actions + budget so the human can tune; failing to surface it is a
process failure, even when the run stays under cap.)

## 2. Single heavy run at a time

Do not launch a second full-sweep / deep-audit while one is in flight (the analog of a single-trigger
lock). Shallow checks (smoke) may run alone; heavy fan-outs are serialized. If asked to start a heavy
run while one is active, say so and queue it rather than doubling spend.

## 3. Model routing (cheap by default)

- Route **shallow flows** (smoke, sanity, discovery, recon, link/integrity) to the **cheapest capable
  model** (Haiku).
- Reserve the **capable tier** (Opus/Sonnet) for judgment-heavy flows (exploratory, security reasoning,
  triage/synthesis, adversarial verification).
- Never run a whole sweep on the top tier by default.

## 4. Stop on ENOUGH, not on the cap

The turn cap is a backstop, not a target. Halt a flow the moment it has enough evidence to report -
do not ride the loop to `maxTurns` for its own sake. Re-executing to reproduce a result already produced
is pure waste (see the orchestrator's plan-vs-run split). Driver de-flaking is overhead to minimize,
never a finding.

## 5. Pre-emptive rate-limit pausing

For rate-limited endpoints (e.g. login at 10/min), keep a call counter and pause **before** hitting the
limit (within ~2 calls), not just react to a 429 (see `guardrails.md` §5). Back off on 429.

## 6. Budget accounting IS reported (cost is visible + gated)

`artifacts/summary.json` records the run's budget usage so cost is never a black box:

```json
"budget": {
  "tier": "pr-gate",
  "flows_dispatched": 4,
  "wall_clock_min": 11,
  "caps": { "per_flow_turns": 25, "wall_clock_target_min": 15 },
  "cap_hit": false,
  "coverage": "complete | partial (which flows were cut and why)"
}
```

A run that hit a cap reports **partial coverage** with what was cut - it does not present a truncated run
as complete. Escalate fan-out/depth beyond the tier only when the mandate's value clearly warrants it,
and note the escalation.

**Actual spend is reported in the HUMAN summary too, not just `summary.json` — unasked.** The concise
human report at the end of every run MUST carry an explicit budget line stating **actual vs cap for BOTH
tokens AND wall-clock** (e.g. `budget: 152k / 300k tokens · 60 min / ~40 min target — wall-clock OVER`).
Any overrun is flagged plainly even when the other dimension stayed under cap (a run can be under the token
cap yet over the wall-clock target — say so; do not quietly report the flattering number). Report the
wall-clock **measured**, never the planned estimate. This lets the human tune the caps for the next run.
