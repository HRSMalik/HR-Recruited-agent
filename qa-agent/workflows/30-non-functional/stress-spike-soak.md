# stress-spike-soak

**Category:** 30-non-functional
**Runs as:** subagent: ../.claude/agents/performance-tester.md
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Push the SUT **beyond** anticipated load to characterize its limits: find the breaking point (stress), survive a sudden surge and recover (spike), stay healthy under sustained load (soak/endurance), and scale up/down cleanly (scalability). Answers: "Where does it break, does it fail gracefully, and does it leak or degrade over time?"

## Inputs & preconditions
- Required artifacts: degradation thresholds (max acceptable p95/error rate before "degraded"), expected breaking-point band, auto-scaling policy (min/max instances, scale triggers), soak duration (≥2–8 h), RTO/recovery expectation after a spike.
- Target: base URL/host of a **staging or seeded-sandbox** sized prod-like, with autoscaling enabled where relevant; auth via env; APM/metrics + log access for the full window.
- Preconditions: assert **NON-PROD** host (STOP and `status:error` otherwise); seeded golden data present; baseline (`performance-load`) results available so degradation is measured against a known-good point; teardown plan to drop/restore any seeded writes.

## Oracle (source of truth)
**Defined breaking-point band + degradation thresholds** from the capacity/SLA plan — not the SUT's own numbers. Concretely: degradation = first load step where `p95 > degraded_p95` or `error_rate > degraded_pct`; breaking point = load at which throughput plateaus/drops while latency climbs (knee of the curve); soak oracle = "no monotonic upward trend in heap/RSS/handles and no latency drift over the hold"; spike oracle = "errors bounded during surge **and** metrics return to baseline within RTO."

## Step sequence (Plan → Act → Verify)
1. **Plan** — design four profiles with **k6/JMeter/Gatling/Locust**: (a) **stress** — stepwise ramp past target until failure; (b) **spike** — baseline → instantaneous 5–10× surge → drop → observe recovery; (c) **soak** — steady ~70–80% load held for hours; (d) **scalability** — ramp while autoscaler reacts, then scale back down.
2. **Act** — run each profile in isolation against fresh seeded state; for soak, sample memory/RSS/heap/GC/open-handles and per-interval latency on a fixed cadence; for spike, timestamp surge start, first error, and full recovery; for scalability, record instance count, scale-out lag, and per-instance load distribution.
3. **Verify** — locate the breaking-point knee and confirm failure is **graceful** (timeouts/429/shed load, no crash or data corruption); fit soak metric trends and flag any monotonic rise (memory leak) or latency drift; assert spike recovery ≤ RTO; assert autoscaling triggered, balanced load, and scaled back in.

## Assertions & exit gate
- Breaking point ≥ expected band; failure mode is graceful degradation (load-shed/backpressure), not crash/corruption.
- Soak: memory/handles flat over the hold; p95 drift within tolerance — **no leak signature**.
- Spike: error rate bounded during surge; all metrics return to baseline within RTO; no stuck/zombie workers.
- Scalability: autoscaler scales out under load and back in after, with even distribution.
- **Gate:** `breaking_point_and_degradation_within_thresholds` — passes when the breaking point meets the band, degradation is graceful, and no leak/non-recovery is observed. A memory leak or non-recovery after spike is **critical**; premature breaking point or unbounded spike errors is **major**.

## Output
Write `artifacts/stress-spike-soak/report.json` per `shared/report-format.md`:
`{ flow:"stress-spike-soak", status, summary{total,passed,failed,skipped}, findings[], gate{name:"breaking_point_and_degradation_within_thresholds",passed} }`.
Each finding (`QA-STR-NNN`) names the threshold/band in `oracle`, captures the load step + metric trend (e.g. heap-over-time series, recovery clock) in `evidence`, and proposes the fix (pool/limit tuning, leak source, scale policy) in `suggested_fix`.

## Guardrails
Per `shared/guardrails.md`: **never against production** — staging/seeded-sandbox only; confirm NON-PROD or `status:error`. Long soak/stress runs are resource-intensive — cap duration, run off-peak, and ensure the load generator is not the bottleneck. No real-world side effects; secrets via env, redacted. Drop/restore seeded writes and confirm teardown in the report; cap `maxTurns`; back off on sustained 429.
