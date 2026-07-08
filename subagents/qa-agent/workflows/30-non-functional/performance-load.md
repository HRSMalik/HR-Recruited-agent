# performance-load

**Category:** 30-non-functional
**Runs as:** subagent: ../.claude/agents/performance-tester.md
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Measure how the SUT behaves under **anticipated** (expected peak) load — latency, throughput, error rate, resource usage — and assert each against its SLO. Answers: "At our expected concurrency, does the system stay within its performance budget?"

## Inputs & preconditions
- Required artifacts: SLO/SLA doc (p95 latency target, error-rate budget, target RPS/concurrency), a load profile (closed/open model, ramp, hold duration), a representative request mix per endpoint.
- Target: base URL/host of a **staging or seeded-sandbox** environment sized prod-like; auth via env-injected token; seeded golden dataset so cache/DB behavior is realistic.
- Preconditions: assert host is **NON-PROD** (STOP and `status:error` on a prod host); confirm seeded data present; warm-up run discarded before measurement; monitoring/APM reachable for resource metrics.

## Oracle (source of truth)
The **SLO thresholds** in the SLA document — never the SUT's own observed numbers. Typical form: `p95 ≤ 300 ms`, `p99 ≤ 800 ms`, `error_rate ≤ 0.1%`, `throughput ≥ target_RPS at target_concurrency`, `CPU < 75% / mem stable`. Latency percentiles are the headline; averages are reported but never gated on.

## Metric checklist (what to measure)
Name every metric against one of three established frameworks so no signal is missed and each maps to an SLO:
- **RED — per request-handling service** (the headline trio for the SUT's API surface): **Rate** (requests/sec), **Errors** (failed requests/sec or %), **Duration** (latency distribution — gate on p95/p99, not mean). RED metrics are the externally-observed user experience and map directly to the SLO oracle.
- **USE — per resource** (CPU, memory, disk, network, connection/thread pools, DB): **Utilization** (% busy), **Saturation** (queue depth / waiting work), **Errors** (resource-level error counts). USE metrics are the resource-side evidence that explains a RED breach (e.g. p95 rises because a pool is saturated).
- **Four Golden Signals** — the umbrella view: **Latency**, **Traffic**, **Errors**, **Saturation**. Use these as the top-level dashboard; RED expands Latency/Traffic/Errors per service, USE expands Saturation per resource.

These are reporting/diagnostic frames, **not new gates** — the exit gate stays anchored to the SLO oracle below. Saturation and Utilization are the correlated-ceiling evidence cited in `suggested_fix`; they are never gated on directly.

## Step sequence (Plan → Act → Verify)
1. **Plan** — translate the load profile into a script: per-endpoint weights, ramp-up → steady-state hold (≥10 min) → ramp-down; pin think-time and pacing; set the target arrival rate (open model) or VU count (closed model). Tag each request group for per-route percentile breakdown.
2. **Act** — run the test with **k6** (`k6 run --out json`), **JMeter** (`-n -t plan.jmx -l results.jtl`), **Gatling**, or **Locust**. Drive load from a host with adequate headroom (verify the generator is not the bottleneck). Capture client-side latency histograms (HdrHistogram, not just mean) and server-side CPU/mem/GC/connection-pool/DB metrics from APM for the same window.
3. **Verify** — compute p50/p95/p99 latency, sustained RPS, and error rate over the steady-state window only (exclude ramp). Compare each metric to its SLO; correlate any breach with a resource ceiling (CPU saturation, pool exhaustion, GC pauses) as evidence.

## Regression-cause oracle (continuous profiling + flame graphs)
A latency gate tells you the SUT **got slower**; it does not tell you **why**. Pair the load run with **continuous profiling** (Grafana Pyroscope or equivalent) so every regression carries a root cause, not just a number.
- **Flame graph as the cause oracle** — a flame graph is a hierarchical visualization of profiling data: the horizontal axis represents 100% of runtime with node width proportional to time (or CPU cycles / allocations) spent in each function, and the vertical axis shows the call hierarchy from root down through nested calls (grafana.com/docs/pyroscope — *Flame graphs*). Pyroscope builds these by sampling stack traces and aggregating CPU-cycle data, giving an intuitive view of where the cost actually sits — the widest frames are the bottleneck functions.
- **Diff the baseline** — capture a profile during the baseline steady-state window and another during the regressed window, then read the **comparison/diff flame graph**: frames that widened between the two runs are the functions that absorbed the new cost. This converts "p95 rose 14%" into "p95 rose 14% because `serialize_candidate()` widened from 6% → 19% of CPU" — an actionable `suggested_fix`, not a bare metric.
- **Grounding rule** — the flame graph is **diagnostic evidence only**, never the gate. It explains a breach the SLO oracle has already declared; it does not redefine pass/fail. Attach the offending frame(s) and the diff to the finding's `evidence`/`suggested_fix`; keep the gate anchored to the SLO percentiles.
- Continuous profiling runs in-process against the same seeded-sandbox SUT — no prod target, no real-world side effects (per Guardrails).

## Assertions & exit gate
- `p95_latency ≤ SLO_p95` and `p99_latency ≤ SLO_p99` over steady state.
- `error_rate ≤ target` (non-2xx/3xx + timeouts), measured at target concurrency.
- Sustained `throughput ≥ target_RPS`; no resource saturation (CPU < ceiling, memory flat, no pool/queue starvation).
- **Gate:** `p95_within_slo_and_errors_within_budget` — passes when p95 ≤ SLO **and** error rate ≤ target at the anticipated load. A breach of p95 under expected load is **major**; SLO-violating error rate or collapse is **critical**.

## Tiered shift-left perf gates (baseline-delta)
Run perf checks at progressively heavier tiers so regressions are caught early and cheap, with each tier failing on a **baseline-delta threshold** — a percentage regression of p95 versus a stored baseline — in addition to the absolute SLO. The baseline is the last green run on the integration branch (a committed `baseline.json`), not the SUT's current numbers; the absolute SLO oracle above is never relaxed by these tiers.
- **Tier 1 — PR / commit (micro):** smoke load on the changed endpoint(s), short hold (1–2 min). Cheap, blocks merge. **Gate:** `p95_delta_vs_baseline ≤ 5%` and absolute `p95 ≤ SLO_p95`.
- **Tier 2 — pre-merge / nightly (component):** representative request mix, ≥5 min hold against seeded-sandbox. **Gate:** `p95_delta_vs_baseline ≤ 10%` and error-rate within budget.
- **Tier 3 — pre-release (full anticipated load):** the full Plan→Act→Verify run above at target concurrency, ≥10 min steady state. **Gate:** the headline `p95_within_slo_and_errors_within_budget`.
- **Threshold `X` is configurable per tier and per route** (read from the SLO/baseline artifact); tighter at Tier 1 because the change surface is small, looser downstream where noise grows. A regression `> X%` over baseline fails the tier **even if still under the absolute SLO** — this is the early-warning that catches slow drift before it breaches the SLO.
- **Baseline hygiene** — only promote a new baseline from a run that passed every gate; record the load profile alongside it so deltas compare like-for-like. A breach pairs with the flame-graph diff above so each shift-left failure ships its own root cause.

**Watch (do not gate):** auto-tuned / statistical baseline-delta thresholds (anomaly-detected per-route `X` instead of a fixed percentage) are emerging — treat any such auto-derived threshold as advisory and keep the gate on the committed baseline + fixed `X` until the approach is proven on this SUT.

## Output
Write `artifacts/performance-load/report.json` per `shared/report-format.md`:
`{ flow:"performance-load", status, summary{total,passed,failed,skipped}, findings[], gate{name:"p95_within_slo_and_errors_within_budget",passed} }`.
Each finding (`QA-PERF-NNN`) names the SLO threshold in `oracle`, puts the observed percentile/RPS/error-rate + the load profile (RPS, VUs, duration) in `evidence`, and points at the correlated resource ceiling in `suggested_fix`.

## Guardrails
Per `shared/guardrails.md`: **never load-test production** — staging/seeded-sandbox only; confirm NON-PROD before generating load or report `status:error`. No outbound real-world side effects (mock email/SMS/payment sinks). Inject auth/secrets via env, redact from report. Back off on 429 from the SUT; cap `maxTurns`. This flow generates write traffic only against seeded data — never prod records.
