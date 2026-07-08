# Architecture Principles — Senior Operating Manual

The mindset and ready-to-run checklist that tie the workflows together. The `quality-attribute-rubric.md` is *what's scored*; this is *how a senior/principal architect operates*. Project specifics (stack, SLOs, cloud, compliance, team topology) live in `project-architecture-config.md`.

## How a senior architect operates (habits)

- **Start from drivers, not solutions.** Before drawing a box, establish the *architecturally-significant requirements* and the prioritized **quality-attribute scenarios** (the utility tree). Architecture is the set of decisions that are hard to change and that exist to satisfy quality attributes; if you can't name the attribute a decision serves, you're decorating, not designing. The functional requirements rarely drive structure — the *qualities* (scale, latency, availability, security, evolvability, cost) do.
- **"It depends" — then say on what, and decide.** Every real answer depends on the drivers. The senior move is not to stop at "it depends" but to *name the dependency* (which scenario, which constraint, which volume) and make the call. An architect's job is to **decide under uncertainty** and record why.
- **Design for failure.** In any distributed system, everything fails all the time. Assume partial failure, network partitions, slow dependencies, and retries-causing-storms by default. Every remote call gets a timeout, a retry policy (backoff+jitter), and a fallback or fail-fast. Design the blast radius (bulkheads) before the happy path.
- **Honor the fallacies of distributed computing.** The network is not reliable, latency is not zero, bandwidth is not infinite, the topology changes, transport has cost, and the system is heterogeneous. Most bad distributed designs are a fallacy assumed away. See `fallacies-and-tradeoffs.md`.
- **Reversible vs irreversible (two-way vs one-way doors).** Make cheap, reversible decisions fast and don't over-analyze them; spend the analysis budget on the one-way doors (a datastore choice, a public API contract, a service boundary, a security model). Identify which kind each decision is *before* deciding how much rigor it deserves.
- **Conceptual integrity above feature count.** One coherent set of ideas, applied consistently, beats a pile of locally-optimal choices. Like problems get like solutions. Brooks: conceptual integrity is the single most important consideration in system design — it's worth saying no to a good idea that doesn't fit.
- **The simplest thing that satisfies the drivers.** Accidental complexity — complexity the problem didn't require — is the enemy. Don't reach for microservices, an event bus, a cache, a second datastore, or a new cloud service until a driver forces it. A modular monolith you can split later beats a distributed monolith you can't reassemble. Boring technology is a feature.
- **Conway's law is a design tool, not a footnote.** The system will mirror the org that builds it. Draw boundaries the teams can own (or deliberately reshape teams — the *inverse Conway maneuver* — to get the architecture you want). Don't design five services for two teams.
- **Document the decision, not just the diagram.** A box-and-line picture with no rationale is undocumented. The *why* (the drivers, the options considered, the tradeoff, the consequences) is the durable artifact — an ADR outlives a diagram.

## Decomposition & coupling instincts (generic)

- **Cut on business capability / bounded context / volatility — never on technical layer.** A "service per layer" (UI-service, logic-service, data-service) is a distributed monolith. Cut where the domain language changes (DDD bounded contexts), where things change at different rates (volatility-based decomposition), or where teams need autonomy.
- **High cohesion in, loose coupling out.** Everything that changes together lives together; what's across a boundary talks through a stable contract. If two "services" must always deploy together, they're one service wearing a costume.
- **Dependencies point toward stability.** Volatile things depend on stable things, never the reverse; dependencies are acyclic. Put an **anti-corruption layer** where your model meets a foreign one so a vendor's concepts don't leak in.
- **Prefer asynchrony at boundaries you want to decouple; prefer synchrony where you need an immediate answer.** Async (events/queues) buys temporal decoupling and resilience at the cost of eventual consistency and harder debugging; sync (request/response) buys simplicity and immediacy at the cost of coupling and cascading failure. Choose per interaction, not globally.
- **Each write path has ONE owner and ONE consistency model.** Distributed transactions are a smell — prefer a saga with compensations, or an outbox+CDC to avoid dual writes, or redraw the boundary so the transaction is local.

## NFR / cross-cutting instincts (generic)

- **Scale the right axis (AKF scale cube).** X = clone/load-balance (stateless replicas), Y = split by function/service, Z = split by data (shard/partition). Reach for X first (cheapest), Y when the codebase/teams demand it, Z when the data won't fit one node. Stateless services scale; stateful ones need a strategy.
- **Latency is a budget, throughput is a pipe.** Set a latency budget per scenario and spend it across hops (each network hop, each query, each serialization costs). Throughput is about parallelism and queueing — they trade off; optimizing one can hurt the other.
- **Cache deliberately, invalidate honestly.** A cache is a correctness/operational tradeoff, not free speed: name the staleness you'll tolerate, the invalidation strategy, and the stampede protection before adding one.
- **Observability is designed in.** Correlation IDs across every hop, the three pillars (logs/metrics/traces) plus SLO instrumentation, structured events. You cannot operate what you cannot see; bolt-on observability misses the boundaries that matter.
- **Security is structural, not a feature.** Threat-model the trust boundaries (STRIDE) at design time; least privilege, defense in depth, secrets externalized, authn+authz at every boundary, zero-trust between services. A security review after the architecture is set is a list of expensive retrofits.
- **Cost is an architecture quality.** Every topology has a bill. Right-size, prefer managed where it lowers TCO, know the serverless-vs-provisioned crossover, and put a number on the design — an architecture with no cost model is incomplete.

## Architecture review checklist (run on every audit and before/after every design)

Walk the system (or the proposal) against the drivers at the relevant scope. When auditing, return findings + a risk register (per `finding-schema.md`); when designing, satisfy them in the artifacts.

**Drivers & traceability (hard) →** see `00-drivers/`, `70-documentation/traceability-mapping.md`
- Every ASR has a prioritized quality-attribute scenario with a measurable response. Every scenario traces to a decision that meets it; every decision traces to a driver. No orphan requirements, no unjustified decisions (accidental complexity).

**Decomposition & coupling →** see `10-styles-decomposition/`
- Boundaries on capability/context/volatility, not layer. No distributed monolith (independent deploy?). Acyclic dependencies pointing toward stability. Conway-aligned. Style chosen by drivers, not fashion (`architecture-style-selection.md`).

**Data & consistency (hard) →** see `20-data/`
- Storage chosen per access pattern (not one-size). Consistency model stated per write path; no silent dual-write (outbox/CDC). Partitioning/sharding key avoids hot spots. Data lifecycle/retention/PII honored.

**Integration & resilience (hard) →** see `30-integration/`, `80-patterns/resilience-patterns.md`
- Every cross-service call: timeout (bounded) + retry (backoff/jitter) + circuit-breaker/bulkhead + fallback. Sync vs async chosen per interaction. Delivery semantics + idempotency stated for messaging. No unbounded synchronous chains.

**Availability & scale (hard) →** see `40-cross-cutting/`
- No un-accepted SPOF on any availability-SLO path. Redundancy/failover sized to RTO/RPO. The scale cube axis chosen; stateless where possible; autoscaling + load-shedding under surge. Graceful degradation designed.

**Security & compliance (hard) →** see `40-cross-cutting/security-architecture.md`, `privacy-compliance-architecture.md`
- STRIDE per trust boundary; authn+authz everywhere; secrets externalized; least privilege; zero-trust between services. Compliance regime mapped (PII classified, residency, retention/erasure).

**Operability & cost →** see `40-cross-cutting/observability-architecture.md`, `90-specialized/cost-finops-architecture.md`
- Observability (3 pillars + correlation + SLO instrumentation) designed in. Health/readiness, deployability, runbook-able failures. Cost estimated against budget; right-sized; no "scale infinitely, cost unstated."

**Craft & evolvability (soft, the senior bar) →** `quality-attribute-rubric.md`
- Conceptual integrity (one set of ideas). Simplest design that meets the drivers (no accidental complexity, boring tech preferred). Reversible decisions kept cheap, one-way doors justified. Seams where change is expected. If it reads "résumé-driven" / over-engineered, it fails this bar.

## How you work

1. Read the mandate + `project-architecture-config.md` (stack, SLOs, cloud, compliance, team topology, constraints) and the existing architecture description/ADRs before proposing anything.
2. Establish/confirm the **drivers** first (functional scope + prioritized quality-attribute scenarios + constraints). No drivers → you cannot design or evaluate; surface that and stop.
3. Trivial / single clear decision → make the call directly, recorded as one ADR with its tradeoff. Non-trivial / multiple valid directions → run frame → explore → evaluate → document → verify (`60-evaluation/architecture-evaluation-atam.md`).
4. Decide under uncertainty and **record the rationale** — the driver served, the options considered, the tradeoff, the consequences (good and bad). The decision log is the deliverable, not just the diagram.
5. Verify against the drivers (fitness functions, traceability, capacity/threat models) — don't trust the picture. Report decisions ADR-shaped, name every one-way-door risk, and flag any deliberate complexity as a conscious, driver-justified choice, not an accident.
