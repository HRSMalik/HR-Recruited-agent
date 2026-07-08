# reliability-recovery

**Category:** 30-non-functional
**Runs as:** subagent: ../.claude/agents/performance-tester.md (operational-acceptance flow)
**Default model:** sonnet   ·   **Mode:** mutating-sandbox

## Purpose
Validate resilience under faults: graceful degradation, failover, backup/restore, and disaster recovery (OAT). Answers: "When a dependency or node fails, does the system degrade gracefully, fail over, and can we restore within RTO/RPO?" Optionally exercises controlled chaos fault-injection with a minimized blast radius.

## Inputs & preconditions
- Required artifacts: resilience requirements (RTO, RPO, availability target), failover/HA topology (replicas, regions, LB), backup/restore runbook, degradation contract (which features must stay up vs. shed), observability/SLI dashboards.
- Target: base URL/host of a **staging or seeded-sandbox** mirroring prod topology (replicas, failover wired); auth via env; access to orchestration (k8s/cloud console) to kill/partition components; metrics/log/trace pipeline live.
- Preconditions: assert **NON-PROD** host (STOP and `status:error` on prod); seeded golden data + a known-good backup to restore; a defined, bounded **blast radius** (one node/AZ/dependency at a time) and an abort/rollback switch ready before any fault.

## Oracle (source of truth)
The **resilience requirements** (RTO/RPO, availability, degradation contract) **and observability as oracle** — the SLI dashboards/health signals define "recovered." Concretely: failover succeeds when service health returns within RTO and no requests are lost beyond the error budget; restore succeeds when recovered data matches the golden baseline to within RPO. Never the SUT's self-reported "OK."

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate fault scenarios scoped to the change/topology: primary-node kill, AZ/region failover, dependency outage (DB/cache/queue down or high-latency), network partition, full backup→restore drill, cold DR rebuild. Define the expected behavior + recovery target for each, and pin the blast radius.
2. **Act** — inject one fault at a time under steady background load: kill/cordon a node, sever a dependency, or use a chaos/fault tool (**Chaos Toolkit, Gremlin, AWS FIS, Litmus, Pumba, Chaos Mesh** for orchestration kills/partitions; **Toxiproxy** for per-dependency network faults) for latency/partition; for backup/restore, take a backup, corrupt/drop the seeded DB, and run the restore runbook. For resilience patterns, drive the dependency to each pattern's threshold (see matrix below). Stream SLIs/logs/traces throughout; auto-abort if blast radius exceeds the cap.
3. **Verify** — assert against the oracle: failover completed within RTO with error budget intact; graceful degradation served the must-stay-up features (and shed the rest cleanly, no cascade); restored data matches golden baseline within RPO; system self-healed with no manual residue (zombie connections, stuck leaders).

## Resilience-pattern verification matrix
Resilience patterns must be **asserted, not assumed** — a present circuit-breaker config proves nothing until both its trip and its recovery are observed. Drive each pattern from the dependency side (inject the fault), then assert the client-side behavior against the oracle (SLI signals + the pattern's own state metric). Source patterns from **resilience4j** (CircuitBreaker, Retry, Bulkhead, TimeLimiter) — map each to its observable signal. One fault at a time; sandbox only.

| Pattern (resilience4j) | Inject | Assert (both directions) | Observable signal |
| --- | --- | --- | --- |
| Circuit-breaker | Drive the dependency to the failure-rate/slow-call threshold | **Trips** (CLOSED→OPEN, calls short-circuit, no pile-up on the dead dependency) **AND closes** (OPEN→HALF_OPEN→CLOSED once the dependency recovers and probe calls pass) | breaker state metric, error-budget burn flattens after trip |
| Retry | Make the dependency fail transiently for a bounded window | Retries exhaust per policy **and cause no thundering-herd storm** — jittered backoff, capped attempts, request rate to the dependency stays under cap (no synchronized retry spike on recovery) | downstream request-rate timeseries, retry-count metric |
| Bulkhead | Saturate one dependency's pool/semaphore | **Isolation holds** — the saturated partition rejects/queues within its bound while unrelated calls on other bulkheads stay healthy (no shared-pool exhaustion, no cross-feature cascade) | per-bulkhead saturation + healthy-feature SLIs |
| Timeout→fallback (TimeLimiter) | Hold the dependency past the configured timeout | Call is **cut at the timeout** (not left hanging) **and the fallback fires** — degraded-but-correct response served, caller thread released | latency cut-off at threshold, fallback-served counter |

Each row is a discrete assertion: a missing close (breaker stuck OPEN), a retry storm on recovery, a leaked bulkhead, or a hung call with no fallback each surface as their own finding (`QA-REL-NNN`) — never collapsed into a single "resilience passed."

## Fault-injection tooling & dimensions
Pick the narrowest tool that reproduces the fault within the blast-radius cap:
- **Toxiproxy** — network-layer faults between the SUT and a single dependency (latency, bandwidth throttle, timeout, slclose, peer-reset). Front one dependency at a time through the proxy; toggle the toxic, observe, then clear it — abort one step away.
- **Chaos Mesh** — Kubernetes-native faults (PodChaos kill/cordon, NetworkChaos partition/delay/loss, IOChaos, StressChaos) scoped by label selector to the pinned blast radius.
- (Existing chaos tooling — **Chaos Toolkit, Gremlin, AWS FIS, Litmus, Pumba** — still applies for orchestration-level kills and partitions.)

**Clock-skew fault dimension** — add wall-clock divergence as a first-class fault: skew one node's clock forward/back relative to its peers (NTP drift, container time offset) and assert the system tolerates it without correctness loss — no premature/never-expiring tokens or TTLs, leader election/lease renewal stays stable, no retry-window or backoff math broken by negative deltas, log/trace ordering still reconcilable. Inject on one node only; restore the clock as part of teardown.

## Assertions & exit gate
- Each resilience pattern in the matrix verified in **both directions** — breaker trips AND closes, retry without thundering-herd, bulkhead isolation holds, timeout cuts the call AND the fallback fires.
- Clock-skew on a single node tolerated with no correctness loss (no token/TTL/lease/backoff breakage).
- Failover/recovery time ≤ RTO; data loss ≤ RPO on restore (restored set reconciles to golden baseline).
- Degradation is graceful — designated-critical features stay available, non-critical shed cleanly, no cascading failure.
- Observability fired correct alerts; system returned to baseline health with no manual cleanup.
- **Gate:** `recovers_within_rto_rpo_and_degrades_gracefully` — passes when every scenario recovers within RTO/RPO and degradation is graceful. Data loss beyond RPO, failed restore, or a cascading outage → **critical**; recovery exceeding RTO or a missing/incorrect alert → **major**.

## Output
Write `artifacts/reliability-recovery/report.json` per `shared/report-format.md`:
`{ flow:"reliability-recovery", status, summary{total,passed,failed,skipped}, findings[], gate{name:"recovers_within_rto_rpo_and_degrades_gracefully",passed} }`.
Each finding (`QA-REL-NNN`) names the RTO/RPO/requirement in `oracle`, captures the injected fault + recovery timeline + SLI/alert evidence (and reconciliation diff for restore) in `evidence`, and the remediation (add retry/circuit-breaker, fix runbook step, tune health check) in `suggested_fix`.

## Guardrails
Per `shared/guardrails.md`: **chaos and fault-injection only in the sandbox** — never production; confirm NON-PROD or `status:error`. **Minimize blast radius** (one fault at a time), keep an abort/rollback one step away, and stop on any unbounded cascade. Toxiproxy toxics and Chaos Mesh experiments are scoped to the pinned blast radius and cleared/deleted on teardown; clock-skew is injected on one node only and the clock restored as part of teardown. Restore from the known-good backup and **confirm teardown** in the report. No real-world side effects; secrets via env, redacted; cap `maxTurns`.

**Watch (do not gate):** service-mesh-native fault injection (e.g. Istio/Envoy fault filters, ServiceMesh-level abort/delay) as a Toxiproxy alternative for in-mesh dependencies — note where applicable, but do not add it as a gating assertion yet.
