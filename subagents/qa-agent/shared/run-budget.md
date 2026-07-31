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

## 1f. The plan gate presents the ENUMERATED TEST CASES, not flow themes

A gate that lists *flows* ("F1 covers the filter dropdown, F2 covers the new endpoint") plus a budget
is **not** a plan gate. The human cannot add, drop, re-scope, or re-prioritise a case they were never
shown, so the tuning the gate exists for is impossible — they approve a shape, not a plan. What gets
approved is the **numbered case list**.

- **Author the cases BEFORE dispatch** and hand them over with the budget: `TC-nnn · requirement/AC ·
  technique · preconditions · expected`, grouped per item under test, with `Actual` blank. Format and
  the pre/post two-pass rule live in `report-format.md`.
- **Report the same ids back** with `Actual` + `Status` filled in, so approved-vs-executed is
  one-to-one. Any case that vanished between gate and report is a coverage regression the human must
  be able to see at a glance.
- **This also makes the dispatch sharper, not just the gate.** Handing each flow an explicit case list
  is the enforceable form of a budget (§1c: size the work, not the warning) — "cover these 12 cases"
  is countable by the flow, "≤48k tokens" is not.
- A run that reports only a verdict, a count, or a summary table without per-case actuals is
  non-compliant regardless of how well it went.

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

## 1a-UNITS. Cap in the unit the HARNESS meters — "output tokens" is unverifiable and produced fake overruns

Everything in §1a is right about *decomposing* the budget and wrong about nothing except the **unit**. This
section fixes the unit, because using the wrong one made a real run look 2.5× over budget when its flows were
each under their cap, and made wall-clock look 2.7× over when it was under. Both directions of error are bad:
one hides real waste, the other burns trust and invites pointless tightening.

**The rule: every cap is stated in METERED TOTAL tokens — the number the harness reports for a subagent
(`subagent_tokens`), which counts input + output. Never cap "output tokens".** Input dominates: each turn
re-sends the whole accumulated context, so metered total runs **~4×** an agent's output. A cap in output
tokens cannot be checked against anything the harness reports, and agents self-report it unreliably.

**Size caps from tool calls, because metered cost tracks them almost linearly.** Measured across seven
browser-driving QA flows in one session: `123k/49`, `159k/82`, `140k/62`, `128k/51`, `126k/47`, `96k/52`,
`125k/85` (metered tokens / tool calls) — i.e. **≈2k metered tokens per tool call**, stable across flows.
So:

| Flow shape | Tool calls | Metered budget |
| --- | --- | --- |
| API-only probe sweep (no browser) | ≤25 | ~50k |
| Single-screen UI flow + oracles | ≤45 | ~90k |
| Multi-role / multi-fixture UI flow | ≤70 | ~140k |
| Orchestrator overhead (dispatch + merge only) | ≤35 | ~70k |

**State BOTH in every flow prompt: `≤N tool calls` AND `≤N metered tokens`.** The tool-call number is the
one the flow can actually feel itself approaching; the metered number is the one the controller can verify
afterwards. A three-flow UI batch is therefore **~400k metered**, not 180k — budget for what the work costs
or every run will "overrun" a number that was never achievable.

**Report ONLY harness metrics, never an agent's self-report.** Observed self-reports in one session: a flow
claiming "~55 min" that the harness measured at **16.0 min**, and another claiming "~24k tokens" against a
metered **123k**. Take `subagent_tokens` and `duration_ms` from the task result and report those; if you
quote an agent's own figure, label it as a self-report and put the harness number beside it.

**Wall-clock across concurrent flows is MAX, not SUM.** Parallel flows overlap; adding their durations
invents an overrun that did not happen (a 3-flow run summing to 52.5 min had an elapsed of 20.7). Report
per-flow durations against per-flow caps, plus a single elapsed figure = the longest flow.

**A flow that dies without artifacts still bills in full — that is the biggest single waste to prevent.**
One stalled security flow burned **126,706 metered tokens and produced no report at all** (14% of a
900k-token session). Consequences:
- **Never re-dispatch a stalled flow blind.** Check its artifact directory first; if it wrote nothing, the
  work did not happen and re-running the same shape will likely fail the same way.
- **Prefer the cheapest oracle that settles the case over an agent.** In that same run the two
  highest-value security assertions were single HTTP calls; the controller settled 11 cases with direct
  API probes for a negligible fraction of what the failed flow had already spent.
- **Cap the blast radius of orchestration itself.** An orchestrator that only dispatches and merges should
  not cost as much as a flow that does the work; if it does, flatten to direct agents.

**Budget compliance is judged per flow against its own cap, then summed for the run.** "The run exceeded
its ceiling" is only meaningful if the per-flow caps summed to that ceiling in the same unit. Say which
flows exceeded, by how much, in metered tokens — never a single undifferentiated total compared against a
number in a different unit.

## 1b. Recon is a SPIKE, not a phase

The single largest recoverable waste is a flow discovering the environment by failing at it — burning a full
drive, learning one live fact, and starting over. Bound it:

- Before the full drive, every browser/live flow spends a **short recon spike** (≤10% of its token cap) to
  establish the facts a driver dies on: does this route exist and what component is actually mounted there ·
  do the documented credentials authenticate · is the record in a state the action allows · is the target an
  editable form or read-only until an Edit click · are the controls native elements or custom widgets.
- **When a case exercises tenancy/RBAC/ownership logic, the recon spike must read the actual guard, not
  just probe around it.** A mandate's business-rule prose ("staff can only act on their own tenant's records")
  describes the *effect*; it is frequently silent on the *mechanism* (e.g. which field a marker is stamped
  on, and — critically — that the marker can depend on WHO performed the creating action, not just the
  target role name). A fixture built from the prose alone can construct actors that are subtly the wrong
  shape and pass or fail for the wrong reason. Grep the 3-4 lines of source that implement the check
  (the guard function, the field it reads, what sets that field) before writing the fixture — this is
  cheaper than a live drive→error→patch cycle and catches a class of mistake recon-by-poking cannot.
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

## 1g. PRICE the cap from a measured per-item rate — a round number is a guess that overruns

§1c says to buy enforcement with scope rather than instructions. That is necessary and still not
sufficient: you can size the scope correctly and **still** overrun, because the cap you attach to that
scope was invented. Three consecutive read-only code-audit flows overran (**1.41× · 1.34× · 1.56×**) —
and the overrun ratio was not noise, it was **exactly the ratio between the assumed and the actual cost
per item**:

| Flow | Items | Cap ÷ items | Actual ÷ items | Overrun |
| --- | --- | --- | --- | --- |
| payment cluster | 10 | 6.0k | 8.5k | 1.41× |
| closure cluster | 5 | 9.0k | 12.0k | 1.34× |
| mixed bucket | 9 | 5.6k | 8.7k | 1.56× |

Nothing was undisciplined. The unit price was wrong three times, so the run was over three times.

- **Derive the number, don't choose it.** For a read-only code-audit item (one ticket/requirement verified
  against a codebase, with `file:line` evidence), the observed cost is **8.5k–12k per item**. Budget
  **~20k fixed + ~10k per item** — fixed covers orienting in the repo and writing the report, which is why
  small flows cost *more* per item, not less (the 5-item flow was the most expensive per item of the three).
  Checked against all three runs, that model never under-forecasts.
- **Re-derive per work type.** The rate above is for static code audit. A live browser flow, a load test,
  and a static grep sweep have different rates. Keep a rate for each, and update it from the last run's
  harness numbers — a budget line with no measurement behind it is decoration.
- **If the derived cap is unaffordable, cut items — never shave the rate.** Halving the cap while keeping
  the scope produces the same spend plus a false report of an overrun. The item count is the only honest dial.
- **Read-discipline instructions do not substitute for pricing.** The 1.56× flow was dispatched *with* an
  explicit per-file read limit ("never read more than ~120 lines of any file, grep then window"). It was
  followed and it still overran, for the same reason §1c gives about token caps: the agent cannot measure
  its own consumption, so a read rule shapes *technique*, never *total*. Do not count it as a control.
- **Cap items per agent, and split on subsystem boundaries.** The worst overrun spanned 9 tickets across 6+
  subsystems in one flow. Prefer **≤5 items per agent** and one subsystem per agent: it lowers the fixed
  cost being re-paid, and a blown flow then wastes one subsystem's budget, not the whole run's.

### An agent's self-reported spend is FABRICATED — discard it, never relay it

The 1.56× flow closed its own report with *"Budget: used roughly 45-50k tokens (near the cap, not over)."*
The harness figure was **78.2k**. It was not merely imprecise, it was **confidently wrong in the reassuring
direction**, and a controller who quoted it would have reported a compliant run to the human.

- **Never ask an agent to report its own token spend.** Asking invites a fabricated number into the report,
  where it will be read as measurement. §1c establishes agents cannot observe this; a prompt that requests it
  anyway is the controller's error, not the agent's.
- **The harness usage figure is the only budget evidence.** Read it from the task result; quote nothing else.
- Agents *can* honestly self-count things they observe — **turns, tool calls, files read, cases executed**.
  Ask for those if you want a self-reported quantity, and derive nothing about tokens from them.

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
