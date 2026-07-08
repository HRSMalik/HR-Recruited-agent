# specialized

**Category:** 50-automation-platform
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only (sub-modes may use seeded-sandbox)

## Purpose
Umbrella for specialized testing dispatched **on demand** when the mandate names it. One flow, several sub-modes — each with its own grounded oracle — covering domains the core flows do not: mobile, microservices, AI/ML, chaos, and canary/production shift-right. Answers — "does this build hold up under the specialized condition the mandate asked for?"

## Inputs & preconditions
- Required artifacts: the **sub-mode selector** plus that mode's oracle (device matrix / consumer contracts / golden eval set + drift baseline / steady-state hypothesis / SLO + rollback policy).
- Target: per sub-mode — device farm, service mesh, model endpoint + golden data, the chaos target, or the canary cohort.
- Preconditions: exactly one sub-mode selected; its oracle present; target confirmed NON-PROD for any fault-injection/mutation (canary runs on a guarded production slice with auto-rollback armed).

## Oracle (source of truth)
Per sub-mode, an **external** truth — never the SUT's own output:
- **mobile** — device/OS support matrix + UX spec (run via Appium across the fragmentation set).
- **microservices** — provider/consumer **contracts** (Pact); service virtualization stands in for unavailable deps.
- **AI/ML** — labelled **golden eval set** + drift baseline + fairness/robustness thresholds (eval, drift, bias, adversarial + model fault-injection).
- **chaos** — the **steady-state hypothesis** measured by observability (the SLO dashboard *is* the oracle), with minimized blast radius.
- **canary** — production SLOs + the auto-rollback policy during progressive rollout.

## AI/ML sub-mode — check set (C1–C5)

The AI/ML sub-mode expands into named checks, each bound to an **external** oracle (never the model's own output). C1–C3 are the established facets already implied by the AI/ML oracle above; C4–C5 extend coverage to the oracle problem and serving performance.

- **C1 — eval** — predictions on the labelled **golden eval set** meet/exceed the per-slice thresholds.
- **C2 — drift** — feature/score distributions stay within the drift baseline bounds.
- **C3 — bias / adversarial** — fairness limits hold across protected slices; robust to perturbation + model fault-injection.
- **C4 — metamorphic relation oracle** — the **oracle-free** technique for the ML test-oracle problem: assert relations that must hold between inputs and outputs *without* a labelled ground truth, so a model with no known "correct" answer is still testable. Run **paraphrase-invariance** (a paraphrased resume should score the same band), **round-trip** (translate-and-back / serialize-and-back leaves the band unchanged), and **symmetric** MRs (swapping order-irrelevant inputs leaves the ranking stable). The oracle is the **relation**, not a gold label; a violated invariant is the finding. HR-instance: re-worded but equivalent applications must not change the score band. (Source: lakera.ai — metamorphic relations for ML testing.)
- **C5 — LLM-perf** — serving-performance dimension distinct from quality: measure token-stream **first-token latency** (TTFT) and **inter-token latency** (ITL), **inference p99 under concurrency**, and **GPU / throughput saturation** at target load. Assert against the latency/throughput SLO, not against model correctness. HR-instance: **Vapi voice latency is UX-critical** — TTFT/ITL breaches make the voice agent feel laggy regardless of answer quality, so this gates the voice path. (Source: arXiv — LLM inference performance / serving-latency studies.)

> **Watch (do not gate):** EMERGING — LLM-as-judge as a *secondary* metamorphic-relation generator (auto-proposing candidate invariants to test). Promising for widening C4 coverage but not yet a trusted oracle; record observations, do **not** gate on judge-proposed relations.

## Step sequence (Plan → Act → Verify)
1. **Plan** — bind the selected sub-mode to its oracle; enumerate cases (device combos / contract interactions / eval slices / fault scenarios / rollout steps); scope blast radius and pre-arm rollback.
2. **Act** — execute one case at a time through the sub-mode's harness; inject only controlled, minimized faults; skip-and-continue on a single case's transport failure; honor rate limits.
3. **Verify** — assert each result against the sub-mode oracle (matrix coverage / no contract violation / metrics within threshold / steady-state held / SLO maintained → no rollback trigger); capture evidence per failure.

## Assertions & exit gate
- **mobile:** core journeys pass across the required device/OS matrix; no fragmentation-specific defect.
- **microservices:** 0 contract violations; virtualized deps did not mask a break.
- **AI/ML:** eval metrics ≥ golden thresholds; drift within bounds; bias within fairness limits; robust to perturbation/fault-injection.
- **chaos:** steady-state hypothesis holds under fault; blast radius contained; observability detected the fault.
- **canary:** SLOs hold through each rollout step; auto-rollback fires correctly on breach.
- **Gate:** `selected_submode_oracle_met` — the selected sub-mode's threshold is satisfied; any breach → `fail`.

## Output
Write `artifacts/specialized/report.json` per `shared/report-format.md`, recording which **sub-mode** ran:
`{ flow:"specialized", status, summary{total,passed,failed,skipped}, findings[], gate{name:"selected_submode_oracle_met",passed} }`.
Each finding follows `shared/finding-schema.md`; `oracle` names the sub-mode source (e.g. device matrix row, Pact contract id, eval-set slice, SLO). Evidence = the exact device/case, request/response or metric series.

## Guardrails
Per `shared/guardrails.md`: fault-injection and mutations run ONLY against confirmed NON-PROD (canary excepted, on a guarded slice with rollback armed); minimize blast radius; never trigger real side-effects (mark NOT RUN otherwise); golden/masked data only — no real PII; secrets via env, redacted; cap turns. Unselected sub-modes are NOT RUN.
