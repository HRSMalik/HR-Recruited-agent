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
up front) and say so. **A token ceiling that is not decomposed per §1a is not a cap — it is a wish.**

**The budget is a first-class, TUNABLE deliverable at the PLAN GATE.** The plan the orchestrator halts on
(see `qa-orchestrator.md` step 3) MUST present the budget as its own explicit block — token ceiling ·
fan-out · per-flow turn cap · wall-clock target — so the human can **adjust the caps before anything runs**.
A budget silently embedded in the dispatch (never surfaced for tuning) does not satisfy this: cost must be
visible and adjustable *up front*, not discovered after the spend. (Standing user directive 2026-07-23: the
gate must always show the flows-to-test + actions + budget so the human can tune; failing to surface it is a
process failure, even when the run stays under cap.)

## 1a. The token ceiling MUST be DECOMPOSED at dispatch (or it is unenforceable)

A run-level token ceiling alone does not bind anything. It is a number in a plan, not a control. Once
flows are dispatched they spend against their own limits and no later instruction can claw budget back —
the orchestrator cannot retroactively shrink a flow that is already running. So the ceiling MUST be split
into named, enforced sub-budgets **at the moment of dispatch**:

| Sub-budget | Share of the token ceiling | Rule |
| --- | --- | --- |
| **Orchestrator overhead** (recon + plan + dispatch + synthesis) | **≤ 20%**, hard | Recon and planning are overhead, not deliverables. Blow this and the run is already failing, whatever the flows do. |
| **Per-flow execution** | remaining ~80% ÷ number of flows | Each flow is dispatched with an **explicit token cap in its prompt**, not just a turn cap. |
| **Controller slack** | keep ≥ 10% unallocated | Reserved for the re-verify pass and for finishing owed work that came back BLOCKED. |

- **Every flow prompt states its own token cap in numbers.** "You have ≤70k tokens" is enforceable; "≤35 turns"
  is not — turns are a bad proxy for spend (a flow can burn 240k inside 35 turns of tool-heavy work, and
  routinely does when it is driving a browser).
- **Both caps bind, whichever is hit first — and hitting one is a STOP, not a note.** A flow that reaches
  its token OR turn cap terminates immediately and reports partial coverage, naming every unrun case.
  Reporting an overrun after the fact is NOT compliance: `~60 turns vs a ≤35 cap` means the cap did nothing.
- **Never let a run-level ceiling be "adjusted mid-flight."** If the human tightens the budget after dispatch,
  the honest answer is that in-flight flows cannot be re-capped — say so, and apply the new cap to what has
  not yet been dispatched.
- **A cheap flow gets a cheap cap.** Mechanical assertion sweeps (pixel deltas, string presence, status codes)
  are the cheapest work in the fleet and must be capped accordingly — if a flow of trivial oracles is
  outspending a flow doing adversarial reasoning, the caps are wrong.

## 1b. Recon is a SPIKE, not a phase

The single largest recoverable waste is a flow discovering the environment by failing at it — burning a full
drive, learning one live fact, and starting over. Bound it:

- Before the full drive, every browser/live flow spends a **short recon spike** (≤10% of its token cap) to
  establish the facts a driver dies on: does this route exist and what component is actually mounted there ·
  do the documented credentials authenticate · is the record in a state the action allows · is the target an
  editable form or read-only until an Edit click · are the controls native elements or custom widgets.
- **Write those facts into the artifact directory immediately**, before the full drive. A later flow (or a
  re-run) must never rediscover them.
- **Cap de-flaking explicitly: two invalidated attempts, then STOP** and report the flow BLOCKED with the
  environment fact that defeated it. A third full re-drive is never authorized inside a flow's own budget —
  it is a new, separately-budgeted run. Driver de-flaking is overhead to bound, never a finding, and never
  an open-ended licence to retry.
- Environment facts that invalidated a run are **reported as first-class output** (they are the most reusable
  thing a failed attempt produces), and belong in the handoff doc if they contradict it.

## 1c. A cap an agent cannot MEASURE is a cap it cannot honor

batch-39 decomposed its ceiling exactly as §1a requires — and every single flow still overran
(f1 1.10× · f2 1.01× · f3 1.82× · f4 1.69× · run 1.38×). The decomposition was not the failure;
the **enforcement model** was. An agent cannot observe its own token usage, so "you have ≤75k" is
advice, not a limit. F4 said so in its own report: *"full turn/token spend not self-measurable
precisely from inside the run."*

So stop buying enforcement with instructions and buy it with **scope**:

- **Size the work, not the warning.** A flow's real cap is how many cases, viewports, and seeded
  identities it is told to cover. Cutting 22 cases to 12 halves the spend; writing "≤75k" does not.
- **State the cap anyway** (it is the honest budget line and it shapes triage), but treat it as a
  *forecast the controller verifies afterwards*, never as a control the flow can self-apply.
- **The controller is the enforcement point.** Watch artifacts as they land, and stop a flow at
  "enough" (`TaskStop`) rather than trusting it to stop itself. Nobody inside the run can.
- **Turn caps are the only limit an agent CAN self-count** — so where a hard stop matters, express it
  in turns, tool calls, or cases, all of which the agent can actually observe.
- **Expect the overrun and leave room**: budget flows to ~70% of the ceiling so a 1.3–1.8× flow
  overrun still lands inside the run's total.

## 1d. The orchestrator's own overhead is the #1 observed overrun

Three consecutive runs blew their ceiling on **orchestrator overhead, not flow work**: batch-38 spent
**215.8k (48% of a 450k ceiling)** before a case ran; batch-39 spent **237.5k against a 104k cap
(2.28×)**, with **zero cases run** at the moment of first overrun.

- **Never re-gate a plan the controller has already gated.** When the dispatch prompt states the plan
  was approved by the user — or hands over the flow list, the case split, and the caps as numbers —
  that prompt **IS** the approved plan: **dispatch immediately.** Re-reading context and re-authoring
  a case matrix in order to ask "approve?" produces **no executable work**; in batch-39 that second
  gate consumed the entire overhead cap by itself. Gate only when the plan is genuinely undetermined,
  and then in ≤1 turn on a plan already written — never by re-deriving it.
- **A gate that produces no executable work still counts against overhead.** There is no free
  planning turn.
- **Overhead is measured from the harness's reported usage, NEVER the agent's self-estimate.** In
  batch-39 the orchestrator self-reported "~34k spent" against an actual **108,503** — a **3×**
  under-estimate (see §1c: it cannot see its own cost).
- **When a flow dies or needs re-running, the controller re-dispatches it directly** rather than
  paying orchestrator overhead a second time for the same plan.

## 1e. Silence is not progress, and a stopped parent is not a finished run

An orchestrator that returns claiming "N flows running in parallel" has **stopped**. Before believing
either outcome, poll the artifacts for **growth**, and arm the watch so it reports a **stall** as
loudly as it reports progress.

- **Absence of a driver process is NOT evidence of death** — agent turns are server-side, and a driver
  process exists only while a script is actually executing.
- **A 0-byte artifact is NOT evidence of a phantom dispatch** — batch-38's flows were real and merely
  slow, and calling them phantom was wrong.
- **Only artifact growth over time distinguishes alive from dead.** In batch-39 the flows outlived
  their stopped parent and kept writing for ~8 minutes after it returned.
- Verify artifacts before concluding **either** success or failure.

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
  "caps": { "tokens": 300000, "orchestrator_overhead": 60000,
            "per_flow_tokens": 60000, "per_flow_turns": 25, "wall_clock_target_min": 15 },
  "actual": { "tokens_total": 284000, "orchestrator_overhead": 51000,
              "per_flow_tokens": { "f1": 58000, "f2": 71000, "f3": 49000, "f4": 55000 } },
  "cap_hit": false,
  "overruns": [],
  "coverage": "complete | partial (which flows were cut and why)"
}
```

**Per-flow actuals are itemized, not just the total.** A run that reports only its total hides which flow
overspent and makes the next run's caps guesswork. Any flow over its own cap is listed in `overruns` with
the factor (`"f4: 244k vs 70k cap (3.5x) — 161 tool-uses on 17 mechanical assertions"`), and the
orchestrator's own overhead is always reported as its own line — never folded into the flow totals, because
overhead invisible inside a total is exactly how a run spends half its budget before testing anything.

A run that hit a cap reports **partial coverage** with what was cut - it does not present a truncated run
as complete. Escalate fan-out/depth beyond the tier only when the mandate's value clearly warrants it,
and note the escalation.

**Actual spend is reported in the HUMAN summary too, not just `summary.json` — unasked.** The concise
human report at the end of every run MUST carry an explicit budget line stating **actual vs cap for BOTH
tokens AND wall-clock** (e.g. `budget: 152k / 300k tokens · 60 min / ~40 min target — wall-clock OVER`).
Any overrun is flagged plainly even when the other dimension stayed under cap (a run can be under the token
cap yet over the wall-clock target — say so; do not quietly report the flattering number). Report the
wall-clock **measured**, never the planned estimate. This lets the human tune the caps for the next run.
