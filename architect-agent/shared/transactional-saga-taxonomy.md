# Transactional Saga Taxonomy — 8 Patterns (Richards & Ford)

The canonical reference for classifying and choosing a cross-service transaction strategy. Grounded in Richards & Ford, *Software Architecture: The Hard Parts* (ch. 12). Every distributed transaction a flow designs or audits is mapped to exactly one of the eight named patterns by three binary dimensions; the classification drives the finding severity, default preference, and any required written justification. A design that leaves its saga pattern unnamed is a `hard` oracle failure (`finding-schema.md` → `oracle:"hard"`, `type:"data"`).

---

## Part 1 — The Three Binary Dimensions

A saga is fully characterized by choosing one side of each axis. All three are **independent** — any combination is possible, yielding exactly 2³ = 8 named patterns.

### Dimension 1 — Communication (sync | async)

| Side | Meaning | Fallacy relevance |
|---|---|---|
| **Synchronous** | Each participant call waits for a response before proceeding. The saga coordinator (or caller) blocks on every hop. | Violates Fallacy 1 (reliable network) and Fallacy 2 (zero latency) hardest — every blocked call is a cascading-failure surface. |
| **Asynchronous** | Messages are placed on a durable channel (queue/broker); participants consume independently. The saga does not block. | Requires durable messaging infra (broker, dead-letter handling, idempotent consumers). Couples in time and space differently — eliminates synchronous blast radius but adds delivery-guarantee complexity. |

### Dimension 2 — Consistency (atomic | eventual)

| Side | Meaning | CAP/PACELC position |
|---|---|---|
| **Atomic** | All participants commit or all roll back; the saga enforces global atomicity across services (compensating transactions for rollback). The system appears single-unit to callers. | Sits at the C pole of PACELC: buys strict correctness, pays with latency and coupling. Compensating transactions must be **explicitly designed and tested** — they are not automatic. |
| **Eventual** | Services apply changes locally and the system converges to consistency over time. Partial states are visible during in-flight execution. | Sits at the L/A pole: buys latency and availability, pays with transient inconsistency. Requires idempotency at every step and a reconciliation or out-of-band error strategy. |

### Dimension 3 — Coordination (orchestrated | choreographed)

| Side | Meaning | Coupling profile |
|---|---|---|
| **Orchestrated** | A central saga orchestrator drives the flow: it knows the sequence, calls each participant, and issues compensations. The happy-path and the error-path are both **visible in one place**. | Temporal coupling between orchestrator and participants. The orchestrator is a design-time coupling point (must know all participants) but not a runtime SPOF if made resilient. |
| **Choreographed** | Each service reacts to an event emitted by the previous participant; there is no central coordinator. The flow is **implicit** — it emerges from the event graph. | Services are loosely coupled in design but the end-to-end flow is invisible without cross-cutting tracing. Error handling is distributed and harder to reason about; compensations must be triggered by events, not by a single authority. |

---

## Part 2 — The 8 Named Patterns

Dimensions are written as: *communication + consistency + coordination*.

### 1. Epic Saga — sync + atomic + orchestrated

**Characterization:** A central orchestrator drives a fully synchronous chain of blocking calls; every participant must commit before the saga proceeds, and rollback is compensated end-to-end. The gold standard for correctness, the worst for everything else.

| Attribute | Rating | Notes |
|---|---|---|
| Consistency | High | Global atomicity enforced; compensations must be pre-designed |
| Responsiveness / Scalability | Very Low | Each hop blocks the chain; total latency = Σ participant latencies; fan-out on failure |
| Coupling | High | Orchestrator and all participants are synchronously coupled; a slow participant freezes the saga |
| Complexity | High | Compensating transactions per step; error paths are visible but numerous |
| Recoverability | Medium | Rollback path is explicit (orchestrator drives compensations) but compensation failures compound |

**Use when:** strict atomicity is a hard regulatory or financial driver AND latency is not a constraint AND participant count is small (≤ 3–4). Rare in practice; most "we need atomic" cases do not survive the latency analysis.

---

### 2. Phone Tag Saga — sync + atomic + choreographed

**Characterization:** Each service calls the next synchronously in a chain; there is no orchestrator — each participant is responsible for forwarding the call. Atomicity is intended but each hop's compensation is that service's own responsibility, making global rollback the hardest orchestration problem in the taxonomy.

| Attribute | Rating | Notes |
|---|---|---|
| Consistency | Medium–High | Atomic intent, but compensation is fully distributed — easy to lose a rollback leg |
| Responsiveness / Scalability | Very Low | Same chain-blocking as Epic Saga |
| Coupling | Very High | Every service must know its downstream; a change to any participant requires updating its caller |
| Complexity | Very High | No single authority over the error path; debugging a failed rollback requires tracing across every hop |
| Recoverability | Low | Compensation must be triggered by the failing service outward; no central authority to retry |

**Use when:** almost never preferred; arises from organic service-to-service growth before a proper saga pattern is established. Flag as a finding if found in a new design.

---

### 3. Fairy Tale Saga — sync + eventual + orchestrated

**Characterization:** A central orchestrator drives synchronous calls but accepts eventual consistency — participants apply changes locally without global rollback; the orchestrator monitors and reconciles. The blocking cost remains; the compensating-transaction machinery is lighter.

| Attribute | Rating | Notes |
|---|---|---|
| Consistency | Medium | Eventual; transient partial states visible; orchestrator tracks convergence |
| Responsiveness / Scalability | Low | Synchronous blocking still present; better than Epic only in that compensation is simpler |
| Coupling | Medium | Orchestrator couples to all participants; participants do not couple to each other |
| Complexity | Medium | Simpler than atomic variants (no full rollback machinery); reconciliation logic still needed |
| Recoverability | Medium–High | Orchestrator can retry/reconcile; eventual model absorbs partial failures gracefully |

**Use when:** a central coordinator is wanted (visible flow, single error authority) but strict atomicity cannot be justified by latency or availability drivers. A reasonable default when sync is forced by existing tech constraints.

---

### 4. Time Travel Saga — sync + eventual + choreographed

**Characterization:** Services call each other synchronously in a chain, each accepting eventual consistency locally. There is no orchestrator — the flow is implicit in the call chain. The name captures the disorientation of debugging an eventual-consistent chain with no central trace.

| Attribute | Rating | Notes |
|---|---|---|
| Consistency | Medium | Eventual; transient states visible; no authority to track overall convergence |
| Responsiveness / Scalability | Low | Synchronous chain; same blocking cost as Phone Tag |
| Coupling | High | Each service must know and call its downstream |
| Complexity | High | No visibility into the overall flow; tracing requires cross-service correlation |
| Recoverability | Low–Medium | Each service must detect and handle its own failures; no reconciliation authority |

**Use when:** avoid; an unintended outcome of incremental service decomposition without saga discipline. Refactor toward Fairy Tale (add an orchestrator) or Parallel Saga (go async).

---

### 5. Fantasy Fiction Saga — async + atomic + orchestrated

**Characterization:** An orchestrator drives participants via a durable async channel; atomicity is enforced through compensating transactions on the async path. The orchestrator is decoupled in time from participants but still owns the rollback sequence.

| Attribute | Rating | Notes |
|---|---|---|
| Consistency | High | Global atomic intent; compensations are orchestrator-driven and explicit |
| Responsiveness / Scalability | Medium | Non-blocking send; but compensating-transaction complexity is full (same as Epic Saga) |
| Coupling | Medium | Orchestrator is design-time coupled to participants; participants are runtime-decoupled from each other |
| Complexity | Very High | Async delivery + idempotency + compensating transactions + durable orchestrator state = highest implementation cost |
| Recoverability | Medium–High | Orchestrator can retry message delivery; compensation path is explicit |

**Use when:** atomicity is a hard driver AND the system can absorb the async infrastructure cost (durable broker, idempotent consumers, persistent orchestrator state). Rare; validate the atomic driver rigorously before committing to this complexity.

---

### 6. Horror Story — async + atomic + choreographed

**Characterization:** The worst-rated pattern in the taxonomy. Participants communicate asynchronously, atomic consistency is intended, and there is no orchestrator — compensation is each service's own responsibility triggered by events. Combining async delivery, global rollback, and distributed coordination produces a system where correctness proofs are intractable in practice.

| Attribute | Rating | Notes |
|---|---|---|
| Consistency | Low | Atomic intent with no central authority; compensation races and message-loss make global rollback near-impossible to guarantee |
| Responsiveness / Scalability | Medium | Non-blocking; scalability is decent — but at a correctness cost that offsets it |
| Coupling | Low (design), Very High (implicit) | Loose design-time coupling but the implicit event contract is a hidden tight coupling that breaks on any schema change |
| Complexity | Extreme | Every service must implement its own compensation trigger; distributed debugging of a failed rollback is the hardest operational problem in this taxonomy |
| Recoverability | Very Low | No authority to detect or drive a complete rollback; a lost compensation event leaves the system in a permanent partial state |

**HARD ORACLE — Horror Story requires explicit written justification.** A design that lands on async + atomic + choreographed **must** carry an ADR (`adr-template.md`) stating: (a) why atomicity is a non-negotiable hard driver (traced to a `QAS-…` scenario), (b) why asynchronous communication is required, and (c) why a central orchestrator cannot be introduced. Absence of that ADR is a `critical` finding (`oracle:"hard"`, `severity:"critical"`, `type:"data"`). In all other cases, prefer eventual + orchestrated (Parallel Saga or Fairy Tale Saga).

---

### 7. Parallel Saga — async + eventual + orchestrated

**Characterization:** The **default preferred pattern** for most distributed transaction scenarios. An orchestrator drives participants via a durable async channel; eventual consistency is accepted; participants can operate in parallel once dispatched. The orchestrator provides visibility and a single error/reconciliation authority without the cost of global rollback.

| Attribute | Rating | Notes |
|---|---|---|
| Consistency | Medium | Eventual; transient partial states visible; orchestrator tracks convergence and triggers reconciliation |
| Responsiveness / Scalability | High | Non-blocking async dispatch; participants can execute in parallel where the data graph permits |
| Coupling | Low–Medium | Orchestrator is design-time coupled to the flow; participants are decoupled from each other |
| Complexity | Medium | Idempotency required; orchestrator state must be durable; simpler than any atomic variant |
| Recoverability | High | Orchestrator retries, monitors, and reconciles; eventual model absorbs transient failures |

**Default preference:** absent a hard driver for atomicity or synchrony, Parallel Saga is the target pattern. Cross-reference `20-data/consistency-transactions.md` for outbox/CDC/saga implementation patterns when sizing the orchestrator and the idempotency strategy.

---

### 8. Anthology Saga — async + eventual + choreographed

**Characterization:** Fully decoupled — participants exchange async events, eventual consistency is accepted, and there is no orchestrator. Each service reacts to events and emits its own. The end-to-end flow is invisible without cross-cutting observability; error handling is entirely distributed.

| Attribute | Rating | Notes |
|---|---|---|
| Consistency | Medium | Eventual; no authority tracking overall convergence — reconciliation must be out-of-band |
| Responsiveness / Scalability | Very High | Maximum parallelism; no orchestrator bottleneck |
| Coupling | Very Low | Services know only their event contracts; no design-time coupling to the flow |
| Complexity | High | End-to-end flow is implicit; distributed tracing is mandatory; error handling is fragmented |
| Recoverability | Medium | Each service retries locally; no authority to detect a stuck saga; saga completion detection requires a dedicated monitor or timeout |

**Use when:** extreme scalability and autonomy are the primary drivers, and the team has mature distributed tracing (e.g. OpenTelemetry with saga-span correlation) to compensate for the invisible flow. Validate that a saga-completion monitor exists before accepting this pattern.

---

## Part 3 — Pattern Comparison Matrix

| Pattern | Sync/Async | Consistency | Coordination | Consistency ★ | Resp/Scale ★ | Coupling ★ | Complexity ★ | Recoverability ★ |
|---|---|---|---|---|---|---|---|---|
| Epic Saga | Sync | Atomic | Orchestrated | ●●●●● | ●○○○○ | ●●●○○ | ●●●●○ | ●●●○○ |
| Phone Tag Saga | Sync | Atomic | Choreographed | ●●●○○ | ●○○○○ | ●●●●● | ●●●●● | ●●○○○ |
| Fairy Tale Saga | Sync | Eventual | Orchestrated | ●●●○○ | ●●○○○ | ●●●○○ | ●●●○○ | ●●●○○ |
| Time Travel Saga | Sync | Eventual | Choreographed | ●●●○○ | ●●○○○ | ●●●●○ | ●●●●○ | ●●○○○ |
| Fantasy Fiction Saga | Async | Atomic | Orchestrated | ●●●●● | ●●●○○ | ●●●○○ | ●●●●● | ●●●●○ |
| **Horror Story** | Async | Atomic | Choreographed | ●○○○○ | ●●●○○ | ●●○○○ | ●●●●● | ●○○○○ |
| **Parallel Saga** *(preferred)* | Async | Eventual | Orchestrated | ●●●○○ | ●●●●○ | ●●○○○ | ●●●○○ | ●●●●● |
| Anthology Saga | Async | Eventual | Choreographed | ●●●○○ | ●●●●● | ●○○○○ | ●●●●○ | ●●●○○ |

★ = filled dots out of 5; higher = better on that attribute.

---

## Part 4 — Decision Procedure

When a flow reaches a distributed transaction decision:

1. **Assert the consistency driver.** Is global atomic consistency a hard driver (traced to a `QAS-…` scenario, a regulatory requirement, or a financial integrity constraint)? If no → choose eventual; if yes → justify the cost explicitly.
2. **Assert the communication driver.** Is synchronous call-and-wait required (caller blocks on the result, SLA demands inline response)? If no → choose async (better responsiveness and resilience); if yes → justify.
3. **Assert the coordination driver.** Is there a reason a central orchestrator cannot be introduced (extreme service autonomy, org boundary, broker-only access)? If no → choose orchestrated (visible flow, single error authority); if yes → justify.
4. **Map to the pattern name** from the three answers. Record it in the ADR.
5. **Apply the Horror Story gate:** if the result is Horror Story, an ADR with answers to (a), (b), (c) above is mandatory before proceeding.
6. **Default guidance:** if no hard drivers force a choice, land on **Parallel Saga** (async + eventual + orchestrated).

---

## Part 5 — Oracles and Cross-References

### Hard Oracles (block on failure)

- **Unnamed pattern:** a design that describes a distributed transaction without naming its saga pattern → `critical`, `oracle:"hard"`.
- **Horror Story without ADR:** landing on async + atomic + choreographed with no written justification → `critical`, `oracle:"hard"`.
- **Atomic without compensation design:** choosing any atomic variant without documented compensating transactions per step → `critical`, `oracle:"hard"`.
- **Eventual without idempotency strategy:** choosing any eventual variant without a stated idempotency mechanism at each participant → `major`, `oracle:"hard"`.

### Soft Oracles (advisory)

- A synchronous pattern is chosen where async would suffice (no inline-response driver) → `minor`, `oracle:"soft"` — recommend async variant.
- Choreography is chosen where participant count > 3 (flow becomes non-obvious) → `minor`, `oracle:"soft"` — recommend orchestrated variant.
- Anthology Saga is chosen without documented saga-completion monitor → `major`, `oracle:"soft"`.

### Cross-References

| Topic | Path |
|---|---|
| Consistency models, 2PC vs saga, idempotency | `workflows/20-data/consistency-transactions.md` |
| Distributed transaction design patterns (outbox, transactional inbox, CDC) | `workflows/20-data/consistency-transactions.md` |
| Broader distributed-systems patterns (circuit breaker, retry, saga, choreography vs orchestration) | `workflows/80-patterns/distributed-systems-patterns.md` |
| CAP / PACELC, sync ↔ async canonical tradeoff | `shared/fallacies-and-tradeoffs.md` |
| Finding format for saga violations | `shared/finding-schema.md` |
| ADR format for Horror Story justification | `shared/adr-template.md` |
| Responsiveness / consistency quality scenarios | `workflows/00-drivers/quality-attribute-scenarios.md` |
