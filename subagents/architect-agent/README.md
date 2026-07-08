# Architect Agent — Multiflow System-Design System

A full-scale, agentic **system-architecture** system: an **orchestrator** decomposes an architecture mandate into discrete, single-responsibility **workflows** (one per architecture responsibility), runs the **frame → explore → evaluate → document → verify** loop where *only one writer authors the architecture* (for conceptual integrity) and a *separate skeptical evaluator* scores it against the drivers, and gates on **hard oracles** (driver traceability, met response-measures, no un-accepted SPOF, defined failure modes, fallacies honored, STRIDE coverage, diagrams-compile, ADR-completeness, bounded cost) before **soft oracles** (simplicity, conceptual integrity, evolvability).

Grounded in the SEI's **ATAM** + utility tree, **ISO/IEC 25010** quality attributes, **ISO/IEC/IEEE 42010** architecture description, Simon Brown's **C4 model**, **arc42** / Views-and-Beyond, **DDD**, the **AWS/Azure Well-Architected** frameworks, the cloud-design-pattern + EIP catalogs, the **8 fallacies of distributed computing**, **evolutionary architecture** (fitness functions), **MADR** decision records, and Anthropic's orchestrator-worker + generator-evaluator harness design. The craft bar (conceptual integrity, right-sizedness, reversible decisions) is the staff/principal-architect judgment a checklist can't encode.

> **Reusable by design.** Everything project-specific (the existing stack, deployment target/cloud, scale & SLO targets, compliance regime, team topology, constraints, where the architecture description / ADR log / diagrams live) lives in `project-architecture-config.md` — fill it (or let the orchestrator auto-bootstrap it) per project and the same agent works anywhere.

This is the third fleet alongside `design-agent/` (UI/UX craft) and `qa-agent/` (verification). Design owns *how a surface looks & behaves*; QA owns *does the built thing work*; **architect owns *what to build and why* — the structural decisions that are expensive to change and exist to satisfy quality attributes.**

---

## Core thesis

Architecture has **two kinds of oracle**, and the architecture itself is judged against the **drivers it must satisfy** — never against how clever it looks on a diagram:

- **Hard oracles** (deterministic, blocking gate): every architecturally-significant requirement traces to a decision and every decision to a driver; every prioritized quality-attribute scenario has a **met, measurable response** (proven by a capacity model / a named pattern's guarantee / a fitness function); no un-accepted single point of failure on an availability-SLO path; every cross-service call has a bounded timeout + retry + fallback; a stated consistency model per write path; the 8 fallacies honored; STRIDE controls per trust boundary; diagrams-as-code that compile; complete ADRs (context · options · decision · consequences); a bounded cost model. A failure here rejects the work and loops back.
- **Soft oracles** (rubric-judged, advisory): conceptual integrity, **simplicity / right-sizedness (no accidental complexity, boring tech preferred)**, appropriate coupling & cohesion, evolvability/reversibility, operability, tradeoff honesty — scored by a **separate skeptical evaluator** that *penalizes over-engineering and unjustified novelty*, never the generator grading itself.

And one structural rule above all: **only one writer authors the core architecture**, so the design has **conceptual integrity** (Brooks) — one coherent set of ideas, not a committee's seams. Proposers, analysts, and the evaluator are read-only; exactly one `solution-architect` writes the architecture description; specialists advise read-only and verify their dimension.

The reflex: **propose the design + its tradeoffs, and verify it against the drivers — the controller builds it.** This fleet never writes product code; it authors *architecture artifacts* (ADRs, C4-as-code, design docs, threat/capacity models, fitness functions) for the controller to implement.

---

## The loop (per architecture task)

```
FRAME    → extract the DRIVERS: functional scope + prioritized quality-attribute scenarios (the utility tree,
           each ending in a response measure) + constraints + assumptions/risks. No drivers → no design.   (read-only)
EXPLORE  → N read-only proposers produce DIVERGENT directions — different styles/decompositions/tech — each a
           concrete spec (views + key decisions + tradeoffs), not the same design recoloured.              (read-only)
EVALUATE → 1 skeptical evaluator (ATAM) scores each vs the utility tree + hard oracles; finds sensitivity &
           tradeoff points + risks; order-swapped to kill bias; picks a winner, grafts from runners-up.     (read-only)
DOCUMENT → 1 writer authors the architecture: C4-as-code, ADRs, the design doc/views, threat & capacity models,
           fitness functions — conceptual integrity preserved, known patterns reused, every decision traced.  (ONE writer)
VERIFY   → fitness-functions + diagram-compile + traceability-completeness + STRIDE/failure-mode coverage +
           capacity model as HARD gates; evaluator re-scores from the artifacts → loop (≤N) or pass.
```

A "new direction" = a genuinely different architecture style / decomposition / consistency-or-deployment model — not the same boxes relabeled.

---

## Architecture

```
                ┌──────────────────────────────────────┐
   mandate ────▶│  ARCHITECTURE ORCHESTRATOR           │
                │  scope (1 / 2-4 / whole-system),      │
                │  frame→explore→evaluate→doc→verify,   │
                │  dispatch, synthesize, gate           │
                └───────────────┬──────────────────────┘
   ┌──────────────────┬─────────┴───────────┬──────────────────────┬─────────────┐
   ▼ (frame, R/O)      ▼ (explore, R/O ×N)    ▼ (document, 1 writer)  ▼ (advise/verify, R/O)  ▼ (gate)
 requirements-      architecture-          solution-architect ──▶  data-architect       architecture-
 analyst            explorer ×N            (THE one writer)        integration-arch.     evaluator
 (drivers +         (divergent dirs)                               infrastructure-arch.  (ATAM skeptic:
  utility tree)         │                        ▲                 security-architect     scenarios, hard
       │                └──── evaluator picks 1 ──┘   loop ≤10×    reliability-architect   oracles, tradeoff
       └──────────────────────────────────────────────────────────┘ (read-only advisors    points, risks)
                          VERIFY: fitness functions, diagram-compile,    feeding the writer,
                          traceability, STRIDE + failure-mode coverage,  + verifying their
                          capacity/cost model                             dimension)
```

---

## Workflow catalog (73)

Each lives in `workflows/<group>/<flow>.md` following `shared/workflow-template.md`. Flows marked **(v2)** were added in the research-driven upgrade.

### 00 · Drivers & framing
1. `architecture-drivers` — functional scope + constraints + the architecturally-significant requirements (ASRs)
2. `quality-attribute-scenarios` — the utility tree: 6-part scenarios with response measures, prioritized (value × risk)
3. `constraints-assumptions-risks` — technical/business/regulatory constraints, assumptions log, RAID
4. `context-scoping` — C4 L1 system context: actors, external systems, boundaries, scope in/out
5. `domain-analysis` — DDD: ubiquitous language, bounded contexts, context map, core/supporting/generic subdomains

### 10 · Architecture styles & decomposition
6. `architecture-style-selection` — monolith / modular-monolith / microservices / event-driven / serverless / SOA / space-based — by drivers, not fashion
7. `decomposition-strategy` — split by capability / subdomain / volatility; the distributed-monolith check
8. `component-design` — layering / hexagonal / clean / onion / ports-and-adapters; the dependency rule
9. `dependency-management` — coupling & cohesion, acyclic dependencies, stable-dependencies principle + the **connascence** hierarchy
10. `api-first-contracts` — contract-first (OpenAPI/AsyncAPI/protobuf as source of truth) + versioning
- `add-design-iteration` — the ADD 3.0 generative loop (driver → ≥2 design concepts → instantiate → review) **(v2)**
- `team-topology-decomposition` — Team Topologies + cognitive load + inverse-Conway as a decomposition driver **(v2)**
- `service-granularity-analysis` — granularity disintegrators vs integrators: whether to split/merge a service **(v2)**

### 20 · Data architecture
11. `data-modeling` — conceptual→logical→physical; aggregates; normalization vs denormalization
12. `storage-selection` — SQL/NoSQL/NewSQL/search/blob — polyglot persistence by access pattern
13. `consistency-transactions` — CAP/PACELC, strong vs eventual, the saga/outbox patterns, idempotency
14. `cqrs-event-sourcing` — read/write separation, event sourcing, materialized views, projections
15. `caching-strategy` — cache-aside/read-/write-through/behind, TTL/invalidation, stampede protection
16. `partitioning-sharding` — partition keys, sharding, replication, hot-spot avoidance, rebalancing
17. `streaming-data` — batch vs stream, lambda/kappa, exactly-once, watermarks, backpressure
18. `data-governance-lifecycle` — ownership, lineage, retention, PII classification, GDPR erasure, archival
- `distributed-transaction-design` — the 8 transactional-saga patterns; default away from the "Horror Story" **(v2)**
- `data-granularity-analysis` — data disintegrators vs integrators: which service owns which data **(v2)**
- `data-mesh` — the 4 principles + data contracts (ODCS); gated by a cost-benefit trigger (not universal) **(v2)**

### 30 · Integration & communication
19. `api-design` — REST (Richardson) / GraphQL (schema, N+1) / gRPC; pagination/filtering/error shapes
20. `api-gateway-bff` — gateway responsibilities, BFF per client, edge concerns (authn, rate-limit, routing)
21. `async-messaging` — queue vs topic vs log; broker selection; delivery semantics; ordering
22. `event-driven-patterns` — notification vs event-carried-state vs sourcing; choreography vs orchestration; dual-write
23. `service-communication-resilience` — sync vs async, timeouts/retries/backoff, circuit-breaker, bulkhead, the fallacies
24. `integration-patterns` — EIP (routing/transformation/endpoints), anti-corruption layer, strangler-fig
- `agent-interop-protocol` — MCP / A2A agent↔agent & agent↔tool integration + protocol trust boundaries **(v2)**

### 40 · Cross-cutting / quality attributes
25. `scalability-architecture` — horizontal vs vertical, stateless design, the AKF scale cube, autoscaling
26. `availability-resilience` — FMEA, redundancy, no-SPOF, graceful degradation, blast radius, chaos-readiness
27. `performance-capacity` — latency budgets, back-of-envelope capacity modeling, USE/RED as design targets
28. `observability-architecture` — logs/metrics/traces + correlation IDs, OpenTelemetry, SLO instrumentation, designed-in
29. `security-architecture` — STRIDE threat modeling, zero-trust, defense-in-depth, authn/authz, secrets, least privilege
30. `privacy-compliance-architecture` — privacy-by-design, data residency, GDPR/HIPAA/SOC2/PCI, LINDDUN
31. `reliability-slo` — SLI/SLO/SLA, error budgets, RTO/RPO, DR strategy (backup→multi-site)
32. `multi-tenancy` — silo/pool/bridge isolation, tenant isolation, noisy-neighbor, per-tenant scaling

### 50 · Infrastructure, deployment & delivery
33. `cloud-well-architected` — the 6 pillars (operational excellence, security, reliability, performance, cost, sustainability); cloud-native vs lift-shift
34. `deployment-topology` — environments, regions/AZs, blue-green / canary / rolling; the C4 deployment view
35. `containerization-orchestration` — containers, Kubernetes topology, service mesh, sidecar, the "do you need k8s" check
36. `infrastructure-as-code` — Terraform/Pulumi/CloudFormation, immutable infra, GitOps, environment parity
37. `cicd-architecture` — pipeline design, trunk-based, progressive delivery, supply-chain security (SLSA + Sigstore)
38. `networking-architecture` — VPC/subnets, ingress/egress, DNS, CDN, service discovery, zero-trust networking
- `platform-engineering` — the Internal Developer Platform as a product: golden paths, self-service, DX metrics **(v2)**

### 60 · Evaluation & governance
39. `architecture-evaluation-atam` — utility tree → analyze approaches → sensitivity/tradeoff points → risks/non-risks → risk themes
40. `tradeoff-analysis-cbam` — quantify cost vs benefit vs risk; decision matrices; one-way vs two-way doors
41. `risk-storming-premortem` — collaborative risk identification, risk matrix, the pre-mortem
42. `fitness-functions` — evolutionary architecture: executable checks (ArchUnitTS / dep-cruiser / conftest / oasdiff) + the 5-dimension taxonomy
43. `architecture-review-checklist` — a gate review against drivers, fallacies, SPOF, security, cost, operability
- `quantum-identification` — cut the architecture quanta so each gets its own utility sub-tree **(v2)**
- `lightweight-evaluation` — right-sized eval menu (Mini-ATAM / ARID / PBAR / TARA) via the risk-driven gate **(v2)**
- `per-criterion-evaluation` — one evaluator call per scenario + evidence pointer (anti cross-contamination) **(v2)**
- `wardley-evaluation` — Wardley map for build-vs-buy-vs-rent positioning (soft input) **(v2)**
- `architecture-conformance` — code↔ADR/layering conformance + smells, static-tool-first, LLM-second **(v2)**

### 70 · Documentation & decision records
44. `architecture-decision-records` — ADR/MADR: context · drivers · options · decision · consequences; the decision log
45. `c4-model-diagrams` — the C4 model as diagrams-as-code (Structurizr/PlantUML/Mermaid); the diagram-compile oracle
46. `architecture-description-arc42` — arc42 / 42010 / Views-and-Beyond: stakeholders, views, rationale
47. `design-doc-rfc` — the design-doc / RFC: problem, goals/non-goals, proposal, alternatives, the review workflow
48. `traceability-mapping` — driver → decision → component → fitness-function matrix; no orphans, no unjustified decisions

### 80 · Pattern playbook
49. `distributed-systems-patterns` — consensus/quorum, leader election, sharding, replication, saga/outbox/CDC, CRDTs, clocks
50. `cloud-design-patterns` — the catalog: retry, circuit-breaker, bulkhead, ambassador, ACL, gateway-aggregation, sidecar, strangler, claim-check, competing-consumers, queue-based load-leveling
51. `resilience-patterns` — timeout/retry/backoff-jitter, circuit-breaker, bulkhead, rate-limiter, load-shedding, graceful degradation, fallback
52. `anti-patterns-fallacies` — the 8 fallacies, distributed monolith, big-ball-of-mud, golden-hammer, premature optimization, accidental complexity

### 90 · Specialized
53. `migration-modernization` — strangler-fig, branch-by-abstraction, monolith↔microservices, the 6 R's, expand-contract
54. `ml-ai-system-architecture` — ML train/serve split, feature store, model registry; the LLM/RAG/agentic architecture (retrieval, vector store, orchestration, eval/guardrail loop), drift
55. `realtime-streaming` — low-latency/real-time, websockets/SSE, event streaming at scale, time-window processing
56. `cost-finops-architecture` — cost modeling, the cost-of-each-decision, FinOps, right-sizing, build-vs-buy, serverless-vs-provisioned economics
57. `edge-iot-architecture` — edge computing, IoT topology, intermittent connectivity, edge-cloud split
- `agentic-threat-model` — OWASP-LLM-Top-10 + MAESTRO + MITRE ATLAS threat modeling for LLM/agentic systems **(v2)**
- `rag-evaluation` — the RAGAS metric battery (faithfulness, context precision/recall) as a RAG oracle **(v2)**
- `genai-risk-assessment` — NIST AI 600-1 GenAI risk dimensions (confabulation, provenance, bias) **(v2)**

---

## Specialized subagents (`agents/`)

The definitions live in `agents/` (canonical, inside this system) and are symlinked into `.claude/agents/` only so the agent registry discovers them.

`architecture-orchestrator` (lead) · `requirements-analyst` (read-only — drivers + utility tree) · `architecture-explorer` (read-only proposer ×N) · `solution-architect` (the ONE writer) · `architecture-evaluator` (skeptical ATAM evaluator) · `data-architect` · `integration-architect` · `infrastructure-architect` · `security-architect` · `reliability-architect` (the five domain specialists — read-only advisors that feed the writer and verify their dimension).

## Running it
**Default to the lightweight tier.** Most architecture asks are a single bounded decision — make the call directly as **one ADR with its tradeoff** (the calling assistant, or a single `solution-architect`, reviewed by the controller). The full `architecture-orchestrator` is **heavier** (frames drivers, fans out explorers, runs an ATAM evaluation, verifies fitness functions) and is reserved for genuine multi-direction or whole-system work.
- **One clear decision (DEFAULT):** record an ADR (context · options · decision · consequences) — no fan-out.
- **"Which way should we build this?" / multiple valid directions:** the orchestrator runs frame→explore→evaluate→document→verify.
- **Whole-system design / a greenfield platform / a migration:** orchestrator frames the utility tree, fans out explorers + domain specialists, pipelines the one writer, gates on hard oracles + the ATAM rubric.

## Contracts (read first)
- `shared/workflow-template.md` — the shape every flow follows
- `shared/finding-schema.md` — the architecture finding/recommendation/risk object (driver-traced, tradeoff-bearing)
- `shared/quality-attribute-rubric.md` — the senior bar + hard vs soft oracles + the grounding rule + scoring
- `shared/architecture-principles.md` — senior operating habits + the review checklist + how-you-work
- `shared/evaluation-method.md` — ATAM / utility tree / CBAM — how the evaluator scores and picks
- `shared/adr-template.md` — the MADR decision-record format (the durable *why*)
- `shared/diagramming-standards.md` — C4 + diagrams-as-code conventions (the shared diagram grammar)
- `shared/fallacies-and-tradeoffs.md` — the 8 fallacies + the canonical tradeoffs you choose but never escape
- `shared/report-format.md` — per-flow `report.json` + roll-up + the `architecture/<slug>/` deliverable package

**Added in the v2 upgrade:**
- `shared/risk-register.md` — the RAID risk object + the **risk-driven effort gate** (how much evaluation a decision earns)
- `shared/evaluation-evidence-protocol.md` — typed evidence pointers + the locked rubric checklist (RULERS-style scoring)
- `shared/transactional-saga-taxonomy.md` — the 8 transactional-saga patterns + the "Horror Story" hard oracle
- `shared/agentic-threat-taxonomy.md` — OWASP-LLM-Top-10 (2025) + MAESTRO + MITRE ATLAS + NIST AI RMF
- `shared/policy-as-code.md` — turning ADR/QA thresholds into executable OPA/conftest gates
- `shared/supply-chain-contract.md` — SLSA (v1.2) + Sigstore/cosign + SBOM provenance
- `shared/data-contract-template.md` — the ODCS data-contract (the data analog of OpenAPI)
- `shared/idp-capability-checklist.md` — the CNCF platform-capability taxonomy (platform-as-product)
- `shared/wardley-map-template.md` — Wardley mapping for build-vs-buy positioning (soft input)
- `project-architecture-config.md` — the per-project abstraction layer (stack, SLOs, cloud, compliance, team topology, constraints, artifact locations)

## Non-goals (out of scope — stated, not accidental)

This is a **system-architecture decision + documentation** agent. It deliberately does NOT cover:
- **Writing product code / implementing the system** — it produces the architecture and the fitness functions; the *controller* builds it (see `guardrails.md`).
- **Applying infrastructure** — it authors the IaC *design* and topology, never runs `terraform apply` / a migration / a live cloud change. The operator applies the plan.
- **UI/UX visual & interaction craft** — that's `design-agent/`'s lane (layout, colour, type, states, motion). This fleet stops at the component/contract boundary, not the pixel.
- **Test execution / QA verification of the built system** — that's `qa-agent/`'s lane (smoke, regression, perf-load, security-scan against a running SUT). This fleet *specifies* the fitness functions and SLOs; QA *runs* the tests.
- **Enterprise-architecture governance as a standing practice** (TOGAF ADM cycles, a live capability model, portfolio roadmapping) — it produces the artifacts (drivers, views, ADRs, tradeoffs) for a system or platform, not a permanent EA office.
- **Org/people design** beyond invoking Conway's law to inform boundaries — it recommends team-aligned boundaries; it does not run the reorg.
