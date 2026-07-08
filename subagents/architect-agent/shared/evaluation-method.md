# Evaluation Method — ATAM · Utility Tree · CBAM · Lightweight Menu

How the `architecture-evaluator` (and the `60-evaluation/` flows) judge an architecture or choose between options. Grounded in the SEI's **ATAM** (Architecture Tradeoff Analysis Method), the **utility tree**, **CBAM** (Cost-Benefit Analysis Method), and the SEI **lightweight-evaluation** family. The evaluator scores against *drivers and structural facts*, never the writer's prose.

> **Authority split (ISO/IEC/IEEE).** Architecture *description* structure is governed by **42010:2022**; architecture *evaluation* process is governed by **42030:2019** (and the broader 42020 process framework). This file is the fleet's evaluation method (the 42030 lane); `architecture-description-arc42.md` owns the 42010 description lane. Keep the two distinct.

## Step 0 — scope by architecture quantum (do this BEFORE the utility tree)

A single utility tree across a multi-service system is misleading: each independently-deployable unit has its *own* operational characteristics. Following Richards & Ford, an **architecture quantum** is an independently deployable artifact with high functional cohesion and **synchronous connascence** — i.e. the parts that must scale/fail/deploy together.

1. Identify the quanta (cut at synchronous-connascence boundaries — anything that must respond synchronously to serve a request is in the same quantum).
2. Build **one utility (sub-)tree per quantum** where characteristics genuinely differ (the public API quantum may need `p99 ≤ 200ms`; the nightly-batch quantum does not). Shared, system-wide attributes (security posture, compliance) stay at the root.
3. Score each quantum against *its own* tree. A "the system is scalable" claim that ignores the per-quantum split fails the grounding rule.

## The utility tree (how drivers become an oracle)

The utility tree turns vague "-ilities" into a prioritized, measurable oracle. Build it (per quantum) before evaluating anything:

1. **Root:** "Utility" (the overall goodness of the system/quantum).
2. **Quality attributes** (ISO/IEC 25010): performance efficiency, reliability/availability, security, maintainability/evolvability, scalability, usability, cost, compliance, **sustainability**…
3. **Attribute refinements** under each (e.g. Performance → latency, throughput; Reliability → availability, recoverability).
4. **Leaves = quality-attribute scenarios**, each **6-part** and ending in a **response measure** (the canonical SEI form — see `00-drivers/quality-attribute-scenarios.md`):
   - *source · stimulus · artifact · environment · response · response-measure*
   - e.g. "A user (source) submits checkout (stimulus) to the order API (artifact) at peak Black-Friday load (environment); the system completes the order (response) at **p99 ≤ 200ms with error-rate ≤ 0.1%** (response-measure)."
5. **Prioritize each leaf on two axes** — **(business value, technical risk)**, each H/M/L. The `(H,H)` scenarios are where the architecture lives or dies — evaluate those hardest. `(L,L)` scenarios are noise.

A scenario with no response measure is not a leaf yet — push for the number. The utility tree *is* the hard-oracle target set.

## How much evaluation? — the risk-driven gate + lightweight menu

ATAM is heavyweight (originally a multi-day, multi-stakeholder workshop). Running full ATAM on a low-risk CRUD change kills adoption; running one ADR on a bet-the-company platform is negligent. **Calibrate evaluation effort to risk** (Fairbanks, *Just Enough Software Architecture*):

1. Read the **risk register** (`constraints-assumptions-risks.md` → `shared/risk-register.md`): the highest likelihood×impact items + the one-way-door decisions.
2. Pick the method from the menu by *phase × time × stakeholder availability*:

| Risk / situation | Method | Roughly |
|---|---|---|
| One bounded, reversible decision | **single ADR** with its tradeoff | minutes |
| A screen/subsystem, design-time, low stakeholder availability | **Lightweight Architecture Evaluation** / Mini-ATAM (internal team, a few `(H,*)` scenarios) | hours |
| An intermediate EXPLORE design needs an early reviewability check | **ARID** (active review of an incomplete design) | hours |
| A pattern/style choice | **PBAR** (pattern-based) against `80-patterns` | hours |
| Evaluating *implemented* code/architecture (not a design) | **TARA** / a metric + fitness-function scan of the real system | hours–day |
| A bet-the-system / one-way-door / multi-stakeholder decision | **full ATAM** + CBAM | days |

**Soft oracle:** flag any run that applies *full* ATAM to a sub-6-hour, low-risk window (over-process) — or a *single ADR* to a one-way-door, high-risk decision (under-process). The risk-driven gate is the entry condition to the heavyweight path.

## ATAM evaluation (scoring a design against the tree)

For each high-priority scenario, walk the architecture (the relevant quantum) and produce:

- **Architectural approaches** — the patterns/decisions the design uses to meet this scenario (e.g. "read-replica + connection-pool" for a latency scenario; "saga + outbox" for a consistency scenario).
- **Analysis** — does the approach actually meet the response measure? Justify by a **capacity model**, a **named pattern's guarantee**, or a **fitness function** — never by assertion. If the measure isn't met, that's a `critical`/`major` finding.
- **Sensitivity points** — a decision where a single property strongly determines whether a scenario is met (e.g. "p99 is *sensitive* to the cache hit-rate: below 90% the budget blows"). Sensitivity points are where to focus risk control.
- **Tradeoff points** — a decision that is a sensitivity point for **two or more attributes that pull in opposite directions** (e.g. "synchronous replication is a tradeoff point: it *improves* consistency/RPO but *worsens* write latency"). Tradeoff points are the heart of the report — name them explicitly.
- **Tradeoff-mining sweep** — after the per-scenario pass, do one explicit pass over *all* sensitivity points looking for cross-attribute tradeoff *pairs* the scenario-by-scenario walk missed (a decision good for one scenario, silently bad for another). A tradeoff the design makes but no ADR records is a finding.
- **Risks** — a decision (or a missing decision) that threatens a scenario; goes to the risk register with likelihood×impact and a disposition (accept/mitigate/monitor).
- **Non-risks** — decisions confirmed safe given the drivers (record them too; they justify *not* spending more effort there).
- **Risk themes** — cluster the risks into systemic themes (e.g. "no coherent failure-handling strategy across services") and tie each theme back to the business driver it threatens.

## Choosing between options (proposals)

When `architecture-explorer` returns N divergent directions:
1. **Style-normalize first.** Strip incidental formatting (markdown polish, length, verbosity, vocabulary sophistication) from the option specs before judging — *style/formatting bias is now the dominant judge bias* (0.10–0.76 in studies), far larger than position bias. Judge substance, not presentation.
2. Score **each option against every high-priority scenario** in the utility tree (does it meet the response measure? at what tradeoff?) — **one scoring call per scenario/criterion** (see *Evaluator discipline* below), never one holistic verdict that lets a strong attribute inflate a weak one.
3. Build a **decision matrix** — scenarios (weighted by priority) × options → a per-option profile. Show *where each option wins and loses*, not a single blended score that hides the tradeoff.
4. Pick a winner and **explicitly graft** the superior ideas from the runners-up where they don't break conceptual integrity. Record *why* the winner won and what each loser was better at — that's the durable rationale.

## Evaluator discipline & debiasing (binding on `architecture-evaluator`)

The evaluator is an LLM judge; it must be run against the known failure modes (2024–2026 LLM-as-judge findings):

- **Per-criterion scoring (anti cross-contamination).** Score each quality-attribute scenario in its *own* call → `{criterion, score, evidence, rationale}`. A single holistic call lets strength on one attribute inflate an unrelated one. See `60-evaluation/per-criterion-evaluation.md`.
- **Evidence anchoring / rubric-locking (RULERS-style).** Every soft score cites a **typed evidence pointer** — a quote from the design doc, a diagram node, an ADR id, a capacity-model line — never a free-floating impression. The rubric criteria are a *locked* checklist with score anchors (see `shared/evaluation-evidence-protocol.md`); the evaluator does not re-interpret the bar per run.
- **Style normalization** (above) is the *primary* debias — apply it always.
- **Position/order bias** — now small (≤~0.04) in frontier judges; still **swap order and judge twice for small/open-weight judges** or when the two options are close. Not the headline rule anymore.
- **Self-preference / cross-family.** The `solution-architect` (writer) and the evaluator must not be the *same* model grading its own generation — self-preference inflates a writer's own options ~10–25%. Prefer the evaluator on a **different model family/provider**; where that's impossible, **strip identifying style markers** from the candidate before judging and emit a soft warning that writer and judge share a family.
- **Evaluator self-check.** Before emitting, confirm *all* rubric dimensions + every `(H,*)` scenario were covered (no silent omission). Stop criterion: all dimensions scored OR the bounded iteration cap is hit.
- **External-signal gate on the revise loop (anti reward-hacking).** The EVALUATE→revise loop must **not close more than twice** on the evaluator's word alone — intrinsic self-correction degrades and the generator↔evaluator pair can reward-hack (Huang et al., ICLR 2024). A loop may only re-close after an **external signal**: a passing executable hard oracle (a fitness function / conftest / depcruise / diagram-compile) or a human decision. See `fallacies-and-tradeoffs.md` → reflection-loop reward hacking.
- **Judge panels — cap and diversify, don't multiply.** If a panel is ever used, cap at **3** judges from **≥2 distinct model families** (9 correlated judges ≈ 2.2 effective votes). Multi-agent *debate* and large panels are immature — do not adopt as a gate; a single disciplined evaluator is the default.

## CBAM (when cost must be weighed against benefit)

When two options both meet the drivers but cost differs, quantify:
- **Benefit** of each architectural strategy = Σ (scenario utility gained × scenario priority weight).
- **Cost** = build + run (infra + operational + opportunity) over the relevant horizon.
- **ROI = benefit / cost**; rank strategies by ROI and pick under the budget constraint. Use this to justify *not* gold-plating — the multi-region option may have higher utility but a sub-1 ROI against the actual availability driver. (CBAM is the ROI-gate for the *heavyweight* path; the risk-driven gate above decides whether you even get here.)

## Output of an evaluation
A scorecard: the per-quantum utility tree (prioritized scenarios), a per-scenario approach+analysis (met/unmet + the model that proves it) **with its evidence pointer**, the **sensitivity points**, the **tradeoff points** (incl. the mining-sweep finds), the **risk register** (with themes), the **non-risks**, and — for option selection — the decision matrix + the winner with grafted ideas. Findings/risks follow `finding-schema.md`; hard-oracle failures (`oracle:"hard"`) block, craft gaps (`oracle:"soft"`) are advisory. The evaluator **never edits** the architecture it grades, and never closes the revise loop on its own word past the external-signal gate.
