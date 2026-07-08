# Fallacies & Canonical Tradeoffs — the Things That Are Always True

The fixed reference every flow grounds against — the architecture analog of "tabular numerals right-align." These are not opinions; they are the durable laws of distributed systems and the tradeoffs you cannot escape, only choose. A design that *assumes one of these away* fails the `fallacies_honored` hard oracle (`quality-attribute-rubric.md`).

## The 8 Fallacies of Distributed Computing (Deutsch/Gosling)

Every one is a false assumption naïve designs make. For each, the design must show it *accounts* for the reality where the fallacy applies:

1. **The network is reliable.** → It isn't. Every remote call can fail or be lost. *Account:* timeouts, retries (idempotent + backoff/jitter), circuit breakers, fallbacks; design the partial-failure path, not just the happy path.
2. **Latency is zero.** → Every hop costs ms→s. *Account:* a latency budget per scenario spent across hops; minimize chatty round-trips; batch/coalesce; co-locate where latency-sensitive; async where you can't.
3. **Bandwidth is infinite.** → Payloads and fan-out cost. *Account:* pagination, projections (don't ship the whole object), compression, backpressure, claim-check for large payloads.
4. **The network is secure.** → It's hostile. *Account:* zero-trust between services, mTLS/authn+authz at every boundary, encrypt in transit, never trust the caller's identity claim un-verified.
5. **Topology doesn't change.** → Nodes come and go, IPs move, services rescale. *Account:* service discovery, no hardcoded hosts, connection re-establishment, graceful handling of rebalancing.
6. **There is one administrator.** → Many owners, many policies. *Account:* explicit contracts/versioning between teams, no assumption of coordinated deploys, backward/forward-compatible changes.
7. **Transport cost is zero.** → Serialization, marshaling, and egress cost CPU and money. *Account:* efficient formats where it matters, awareness of cross-AZ/region egress charges in the cost model.
8. **The network is homogeneous.** → Mixed stacks, versions, protocols. *Account:* standard interop formats, schema evolution, anti-corruption layers at foreign boundaries.

## CAP / PACELC (the consistency law)
- **CAP:** under a network **P**artition, you choose **C**onsistency *or* **A**vailability — you cannot have both during the partition. State which, per write path.
- **PACELC** (the fuller statement): on **P**artition, choose **A**/**C**; **E**lse (normal operation), choose **L**atency *or* **C**onsistency. Synchronous replication buys consistency at latency's expense; async buys latency at consistency's. There is no free lunch — name your point on the curve per data store.

## Canonical tradeoffs you choose, never escape
- **Consistency ↔ Availability/Latency** (CAP/PACELC) — strong consistency costs availability under partition and latency always.
- **Latency ↔ Throughput** — batching/queueing raises throughput but adds latency; optimizing tail latency can cap throughput.
- **Coupling ↔ Autonomy** — shared databases/sync calls are simple but couple; events/queues decouple but add eventual consistency and operational complexity.
- **Strict ↔ loose contracts** — a strict contract (versioned schema, gRPC/protobuf, exact shape) catches breakage early but couples producer and consumer and slows independent evolution; a loose contract (name/value pairs, consumer-driven) evolves freely but defers breakage to runtime. Choose per boundary; pair loose contracts with **consumer-driven contract tests**. Beware **stamp coupling** — passing a big payload where the consumer uses a fraction of the fields couples them to the whole shape; project to what's used (a BFF/DTO) so `fields-consumed / fields-received` stays high (the rubric flags < ~20%).
- **Performance ↔ Simplicity** — caches, denormalization, and read models speed reads but add invalidation/consistency complexity and more moving parts.
- **Flexibility ↔ Simplicity (YAGNI)** — every extension point, abstraction, and config knob is future-proofing you pay for now; add seams only where change is *likely*, not everywhere.
- **Build ↔ Buy** — building fits exactly but costs to build+own; buying/managed is faster and lower-TCO but cedes control and adds a dependency. Default to managed/boring unless a driver demands bespoke.
- **Cost ↔ Resilience/Performance** — redundancy, multi-region, headroom, and lower latency all cost money; size them to the *driver*, not to the maximum.
- **Normalization ↔ Read performance** — normalized data is correct and write-cheap but read-expensive (joins/fan-out); denormalized is read-cheap but introduces update anomalies and consistency work.
- **Synchronous ↔ Asynchronous** — sync is simple and immediate but couples and cascades failures; async is resilient and decoupled but eventually consistent and harder to trace.
- **Orchestration ↔ Choreography** — central orchestration is visible and controllable but a coupling point; choreography (events) is decoupled but the end-to-end flow is implicit and harder to reason about.

## Laws & heuristics worth invoking by name
- **Conway's Law** — system structure mirrors org structure; use the inverse-Conway maneuver to *get* the architecture you want.
- **Brooks — conceptual integrity** is the most important property of a system design; worth saying no to good ideas that don't fit.
- **Gall's Law** — a complex system that works evolved from a simple system that worked; you can't design a complex system correct from scratch — start simple.
- **Postel's Law** — be conservative in what you send, liberal in what you accept (interface robustness) — but beware it can hide contract drift; pair with strict schema validation at trust boundaries.
- **Metcalfe / fan-out reality** — N services with M dependencies create N×M failure surface; coupling cost grows super-linearly. Fewer, well-bounded services beat many chatty ones.
- **The Eight Fallacies + "design for failure"** — partial failure is the *normal* state of a distributed system, not the exception.
- **Reflection-loop reward hacking (agentic-process caution)** — a generator↔evaluator loop with no external signal *degrades*: intrinsic self-correction can make answers worse and the pair can converge on a mutually-agreeable wrong answer (Huang et al., ICLR 2024). Applies to the fleet's own EVALUATE→revise loop: it must not close more than twice without an **external signal** (a passing executable fitness function / conftest / diagram-compile, or a human decision). See `evaluation-method.md` → external-signal gate.

## How flows use this file
- The `fallacies_honored` hard oracle checks the design against §1–8 wherever the fallacy applies.
- `architecture-style-selection`, `decomposition-strategy`, `consistency-transactions`, and `service-communication-resilience` cite the canonical tradeoffs to justify a choice — naming the tradeoff *and the point chosen on it* is the deliverable.
- The `architecture-evaluator` uses the tradeoff list to locate **tradeoff points** (a decision that helps one attribute and hurts another) — the heart of the ATAM report (`evaluation-method.md`).
