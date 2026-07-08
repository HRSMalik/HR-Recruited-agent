# storage-selection

**Group:** 20-data  ·  **Runs as:** subagent: ../.claude/agents/data-architect.md  ·  **Mode:** audit + design  ·  **Default model:** sonnet

## Purpose

Select the datastore(s) per access pattern — relational / document / key-value / wide-column / graph / search / blob / time-series — and decide single-store vs polyglot persistence. Answers: *which storage family satisfies each access pattern, consistency need, and scale driver, and does adding a second store carry a justifiable operational cost?*

## Inputs & preconditions

- From `project-architecture-config.md`: the existing stack (the incumbent datastore family, its database/schema, and the collections/tables in use today), the deployment target, the compliance regime (if any — e.g. PII or financial data subject to regulatory obligations), the scale/SLO seed (do not assume consumer-scale unless the config states it), and the constraint that introducing a new datastore requires a driver-justified ADR with its operational-cost tradeoff.
- The architecture **drivers**: the prioritized quality-attribute scenarios from `workflows/00-drivers/quality-attribute-scenarios.md` (the utility tree) — specifically: the access patterns per bounded context (point-read by entity ID, tenant-scoped list, audit-log append, document/blob storage, search), the consistency model each write path demands, the latency/throughput targets (per the NFRs in the source-of-truth docs named in `project-architecture-config.md`), and any availability/RTO driver confirmed with the stakeholder. If a driver (RTO, peak concurrency, retention period) is unstated, surface it as an open question — do not invent a number.
- The data model surface from `workflows/20-data/data-modeling.md` (aggregates, normalization decisions, query shapes) — read first; storage selection is downstream of the access patterns the model exposes.
- Preconditions: `project-architecture-config.md` read; the utility tree and the data model are available (or their gaps are recorded as open driver questions); if the system is greenfield or the model is in draft, frame the access patterns from the functional scope in `project-architecture-config.md` and the domain analysis.

## Oracle (source of truth)

The store choice is justified by the **access pattern + a quality-attribute scenario** from the utility tree; each new datastore beyond the existing one carries an **ADR with its operational-cost tradeoff**; the consistency model of each store is stated per write path.

- **hard:**
  - Every store in the design traces to ≥1 access pattern (a concrete read/write shape: point-read by key, range-scan, aggregate, full-text, blob-get, time-range) AND a quality-attribute scenario (`QAS-*`) that the chosen store's family satisfies and the incumbent store does not — or the incumbent store wins and no new store is added.
  - Every store's **CAP/PACELC position is stated**: under a partition (P) it chooses Consistency or Availability, and in normal operation (E) it chooses Latency or Consistency. "It's consistent" with no model named blocks the gate (`shared/fallacies-and-tradeoffs.md` § CAP/PACELC).
  - Every **write path** declares its consistency model (strong / eventual / causal) and its mechanism (single-writer / outbox / saga+compensation / 2PC) — unresolved dual-writes between stores are a hard blocker (`shared/quality-attribute-rubric.md` → Consistency stated).
  - Every **new datastore beyond the existing one** is gated by an ADR (`shared/adr-template.md`): context (which access pattern the incumbent fails), ≥2 considered options, chosen option, consequences positive AND negative (operational cost — connection pool, schema migration discipline, backup coverage, runbook surface, team skills). An ADR with only upside consequences fails the hard oracle.
  - Every store on the critical path of an availability-SLO scenario has a **stated failure mode**: single primary with no standby is an un-accepted SPOF if an RTO/RPO driver has been confirmed; a silent SPOF blocks unless explicitly accepted in the risk register.
  - Where a compliance regime applies (per `project-architecture-config.md` — e.g. PII or financial data): PII fields classified, residency honored, retention/erasure paths exist per store — an unclassified-PII store under an applicable regulatory regime blocks (`shared/quality-attribute-rubric.md` → Data lifecycle lawful).
  - Cost is bounded: every added store carries an order-of-magnitude hosting + operational estimate against the stated budget/constraint; "add Redis, cost unstated" blocks where cost is a driver.

- **soft:**
  - Right-sized — no second datastore without a driver; polyglot persistence only where the access patterns **genuinely diverge** and the operational overhead is justified (the default is the "one boring database until a driver forces another" heuristic — boring, proven, existing stack first per `project-architecture-config.md`). Adding a store to appear sophisticated is the cardinal soft-oracle failure.
  - Each store is the **narrowest family that satisfies the driver**: a full-text search store is not added if a MongoDB text index meets the latency and recall targets at current scale; a key-value cache is not added if the application tier already absorbs the access pattern without a latency breach.
  - Polyglot operational complexity is honestly described — every additional store adds backup coverage, schema-migration discipline (even schema-less stores have implicit schemas), failure-mode handling, monitoring surface, and team on-call burden. The evaluator penalizes designs that list only the access-pattern win and suppress the operational cost.

## Standards & techniques

- **Datastore-family decision by access pattern** — match the primary read/write shape to the storage family it is designed for:
  - *Relational (RDBMS):* transactions across entity types, complex joins, strong consistency, referential integrity, ad-hoc aggregate queries.
  - *Document:* hierarchical, variable-schema documents read and written as a unit; point-read by ID; moderate query flexibility; horizontal scale via sharding. A document store (if the incumbent) fits: nested entity sections, tenant-scoped list, audit-log append.
  - *Key-value:* point-read/write by single key, high-throughput, low latency; no query flexibility. Fits session storage, rate-limit counters, ephemeral state — NOT for ad-hoc queries.
  - *Wide-column (column-family):* sparse columns, time-ordered writes, high-throughput append, analytical scans; not for point-updates by arbitrary field.
  - *Graph:* relationship traversal (N hops), connected data; penalty for flat lookups and bulk analytics.
  - *Search (inverted index — Elasticsearch/OpenSearch):* full-text, faceted, relevance-ranked queries; not the source of truth (denormalized, near-real-time indexed); operational cost of keeping in sync.
  - *Blob / object store:* large unstructured binary (S3 / Azure Blob / GCS); optimized for large sequential reads and write-once retrieval; wrong choice for transactional record-keeping.
  - *Time-series:* monotonically-appended, time-ordered, high-ingest; compression and downsampling for historical; not for point-update by entity key.
- **Polyglot persistence + its operational cost** (Martin Fowler / NOSQL Distilled): using multiple store families is a deliberate decision, not a default. Each store is a separate operational surface — connection pooling, schema evolution, backup/restore, observability, and runbook complexity multiply. Polyglot is justified only when the access-pattern divergence is large enough that the incumbent store's performance or consistency guarantees cannot satisfy a QAS response measure at reasonable cost.
- **"One boring database until a driver forces another"** heuristic (Gall's Law + boring-tech-preferred rule in `project-architecture-config.md`): the right starting default is the fewest stores that satisfy all drivers. Extend to polyglot only when a concrete scenario (a QAS with a measurable response measure) cannot be satisfied by the incumbent. The evaluator actively penalizes accidental complexity here.
- **CAP/PACELC positioning per store** (`shared/fallacies-and-tradeoffs.md` § CAP/PACELC): e.g. a document store run as a replica set with a majority write concern is CP under partition — it prefers consistency and may become unavailable on a primary failure until election. In normal operation it trades latency for consistency at majority-acknowledged writes. State the position for every store in the design (per its actual configuration, per `project-architecture-config.md`); do not leave it implicit.
- **AKF scale cube** (AKF Partners): X-axis (horizontal clone / read replica), Y-axis (functional decomposition / different store per subdomain), Z-axis (data partitioning / sharding). Reach for X-axis scale (read replica, connection pooling) before Y-axis scale (a new store family) or Z-axis (sharding) — each step up the cube adds operational complexity.
- **Normalization ↔ Read performance tradeoff** (`shared/fallacies-and-tradeoffs.md`): denormalization speeds reads but introduces update anomalies and consistency work across copies; state explicitly where denormalization is chosen and what consistency mechanism compensates.
- Cross-references: `workflows/20-data/data-modeling.md` (aggregates + query shapes that drive this selection), `workflows/20-data/partitioning-sharding.md` (partition/shard strategy once the store is chosen), `workflows/20-data/caching-strategy.md` (whether a caching layer eliminates a second-store driver), `shared/fallacies-and-tradeoffs.md` (CAP/PACELC, normalization ↔ read performance, consistency ↔ latency, build ↔ buy).

## Step sequence

- **audit:** Read `project-architecture-config.md` and the existing data model (collections/tables, access patterns documented or inferred from the codebase) → for each store in use, state its CAP/PACELC position and the consistency model per write path → identify access patterns with no current store match (e.g. full-text search, blob storage, time-series telemetry) → check: (a) every store choice traces to a driver, (b) every write path has a stated consistency model, (c) every store on a critical-path availability scenario has a stated failure mode or an accepted-risk entry, (d) PII fields are classified per store, (e) no un-ADR'd store was added without a recorded rationale → emit findings (`ARCH-STOR-NNN`) per `shared/finding-schema.md`, grouped by severity; include the risk register. Read-only, no artifact authored, no source edited.

- **design:** Frame (confirm the access-pattern inventory from `workflows/20-data/data-modeling.md` and the utility tree; identify each pattern's consistency need, latency budget, and scale envelope; list any open driver questions for the controller to resolve) → Explore (≥2 divergent storage topologies — e.g. Option A: extend the incumbent store with a text index + blob attachment support; Option B: incumbent store + a dedicated search store; each as a concrete spec with consistency model, CAP position, and operational cost) → Evaluate (skeptical evaluator scores each option against the utility tree using ATAM; scores each on the decision matrix of high-priority QAS leaves; applies "one boring database" default; penalizes accidental complexity; picks the winner and grafts the best ideas from runners-up; order-swapped to kill position bias per `shared/evaluation-method.md`) → Document (one writer: author the storage-selection ADR(s) in `architecture/<slug>/adr/`, the C4 Container view updated with datastores as diagrams-as-code, the consistency-model statement per write path, and the capacity/cost model snippet per store; reuse known patterns — replica set, read replica, connection pool, blob storage — before proposing anything novel) → Verify (fitness-function checklist: every store has a CAP position stated; every write path has a consistency model; every cross-store write path has a dual-write resolution; every new store has an ADR; PII classified per store; cost estimate present; diagram compiles; evaluator re-scores from the artifacts) → loop ≤10 or pass.

## Assertions & exit gate

- Every store in the design traces to ≥1 concrete access pattern AND a `QAS-*` scenario whose response measure the store satisfies (by capacity model, named pattern guarantee, or fitness function).
- Every store's CAP/PACELC position is stated explicitly; no store is described as "consistent" without naming the model (strong / eventual / causal) and the mechanism.
- Every write path that crosses a store boundary has a stated resolution (single-writer, outbox+CDC, saga+compensation) — no silent dual-writes.
- Every new datastore beyond the incumbent has an ADR with context, ≥2 options, decision, and consequences (positive AND negative including operational cost); no ADR with only upside.
- Every store on the critical path of a confirmed availability-SLO scenario has redundancy/failover documented, OR the SPOF is an explicitly accepted risk in the register.
- PII fields are classified per store; retention/erasure path exists per store where the compliance regime applies.
- Every added store carries an order-of-magnitude cost estimate.
- C4 Container diagram updated with the chosen store(s) as diagrams-as-code; diagram compiles without error (`shared/diagramming-standards.md`).
- No store is added without a driver — the evaluator's soft-oracle check confirms the "one boring database" default held or was overridden by a concrete QAS, not by preference.

**Gate:** hard oracles green (access-pattern traceability, CAP/PACELC stated, consistency per write path, ADR for every new store with full consequences, no silent SPOF, PII classified, cost bounded, diagram compiles) AND (design) rubric mean ≥ 0.8 (right-sized — no accidental complexity, operational cost honestly described, polyglot only where the divergence is real).

## Output

Write `artifacts/storage-selection/report.json` per `shared/report-format.md` — findings (`ARCH-STOR-NNN`) per `shared/finding-schema.md`, `type:"data"`, `oracle:"hard"` for any of: a store with no driver trace, an unstated CAP/PACELC position, an unresolved dual-write, a new store with no ADR, a silent SPOF on an availability-SLO path, unclassified PII, or missing cost model; `oracle:"soft"` for accidental-complexity or right-sizing findings. Include the risk register (type:"risk" items with likelihood×impact). In design mode, the verification block (fitness-function results, hard-oracle pass/fail, rubric score) is appended to the report. Authored architecture artifacts land in `architecture/<slug>/`:
- `adr/NNNN-storage-selection.md` — one MADR ADR per new-store decision (or a single ADR for the full topology if only the incumbent is chosen)
- `diagrams/container-stores.puml` (or `.md` Mermaid) — C4 Container view showing datastores, their families, and the consistency protocol of each relationship
- `capacity-model.md` (snippet) — order-of-magnitude sizing and cost estimate per store against the relevant QAS response measures

Never scattered outside `architecture/<slug>/`; run-report artifacts go to `artifacts/storage-selection/` only.

## Guardrails

Per `shared/guardrails.md`: propose & document the storage design — never write product code (`src/**`, `frontend/**`, `backend/**`), never run a migration, never apply IaC to a live environment. The controller implements; the operator applies. Ground every store recommendation in a driver (a QAS response measure + an access pattern); a store recommendation with no driver is accidental complexity — flag it, don't ship it. Reuse the existing stack (the incumbent store named in `project-architecture-config.md`) before proposing a new store family; the "boring tech preferred" and "one boring database until a driver forces another" rules are binding defaults for the project (`project-architecture-config.md`). Record the tradeoff and the rejected alternatives — an ADR with only positive consequences is incomplete and fails the hard oracle. One writer authors the ADRs and diagrams; the evaluator is read-only and scores from the artifacts, never from the writer's prose claims.
