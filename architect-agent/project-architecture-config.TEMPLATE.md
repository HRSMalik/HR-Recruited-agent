# Project Architecture Config — TEMPLATE

> **Generic structure only — fill per project (or let the orchestrator fill it).** When the
> architect-agent is dropped into a project, the `architecture-orchestrator` **auto-creates** the real
> `project-architecture-config.md` (no `.TEMPLATE` suffix) at the architect-agent root by inspecting
> that project's codebase + docs. This file is just the **section structure + what each section holds** —
> do NOT hardcode one project's stack, SLOs, roles, or docs here. The generic, project-agnostic method
> lives in `shared/` (workflow-template, quality-attribute-rubric, evaluation-method, adr-template,
> diagramming-standards, fallacies-and-tradeoffs, finding-schema, guardrails, report-format, + the v2
> contracts). Route architecture work through the `architecture-orchestrator` (it reads this).

## System under design (the current architecture)
- The **current shape** (monolith / modular-monolith / microservices / event-driven / serverless …) and the **stack** (frontend, backend/services, datastore(s), gateway/proxy, broker/queue if any). Be honest about what exists vs what's planned/mock — do not describe a service that isn't built.
- The existing **module/service boundaries** and the cross-cutting concerns already in place (auth/RBAC, audit, observability). The **architecture-significant** parts of the codebase to read first.

## Architectural drivers (the utility-tree seed — confirm/extend per mandate, never invent)
- The **source-of-truth docs** for requirements (BRD / PRD / an understanding log) — cite the real paths. Source every NFR number from these; **never invent** a response measure.
- Seed the prioritized **quality-attribute scenarios** by attribute (performance, reliability/availability, security, scalability, evolvability, cost, compliance, sustainability) as 6-part scenarios with response measures. Where a target (RTO/RPO, availability, peak load, tenant count) is **not stated**, mark it an **open driver question** — do not assume a number.

## Constraints (hard — do not design around them)
- **Stack / technology locks** — what must stay; the bar for introducing a new datastore/broker/runtime (a driver-justified ADR with its operational-cost tradeoff; default to the existing stack, boring-tech-first).
- **Deployment / delivery constraints**, **phase scope** (what's in vs deferred), and the **team topology** (Conway — draw boundaries the team can operate; note who owns what).

## Deployment & environments
- **Local/dev**: how to run each component (commands, ports, DB). **Prod target**: the intended topology (proxy, managed data, secrets, env-driven origins) and whether it's built yet or a separate deploy ADR.
- **The architect authors the topology/IaC *design* — it never runs `terraform apply` / a migration / a live cloud change** (`shared/guardrails.md`). The operator applies the plan.

## Compliance & security regime
- The **data sensitivity** (PII/PHI/PCI/financial) and the **regulatory regime** (GDPR/HIPAA/PCI/SOC2 …). The existing controls (authn/authz model, RBAC scoping, encryption, audit), the **RBAC role names across layers** (note any FE↔BE naming skew), and the **secrets list** — all externalized via env, never in code/diagram.

## Architecture artifacts — where they live (the deliverable package)
The architect drops the architecture package into **`architecture/<slug>/`** at the repo root — **auto-created if missing** (`mkdir -p architecture/<slug>`), one subfolder per system/subsystem:
```
architecture/<slug>/
├── README.md              overview + decision summary + the utility tree at a glance
├── design-doc.md          the architecture description (arc42 / Views-and-Beyond)
├── quality-attributes.md  the utility tree — prioritized 6-part scenarios with response measures
├── adr/NNNN-*.md          one MADR 4.x ADR per significant decision
├── diagrams/*.puml|*.md   C4 Context/Container/Component/Deployment as diagrams-as-code (Tier-1: Structurizr/LikeC4)
├── threat-model.md        STRIDE (+ OWASP-LLM/MAESTRO for AI) per trust boundary
├── capacity-model.md      back-of-envelope sizing proving each perf/scale response measure
├── fitness-functions.md   the architecture-characteristic checks to enforce in CI
└── tradeoffs.md           option matrix + sensitivity/tradeoff points + the risk register
```
The explore→evaluate→verify *run reports* go to `artifacts/<flow>/` (machine record); the architecture itself lives in `architecture/<slug>/`. List the project's **existing architecture docs** to read first (docs dir, understanding log, existing ADRs) — reuse, don't re-derive.

## Diagram tooling
- The project's **diagrams-as-code** choice (Tier-1 compile-gated: **Structurizr DSL / LikeC4 / PlantUML+C4**; Tier-2 soft-use only: Mermaid — its C4 is experimental — / D2). Keep diagram source in `architecture/<slug>/diagrams/`; verify it renders (the diagram-compile hard oracle) before counting it done. No pasted PNGs. See `shared/diagramming-standards.md`.

## Decision-record conventions
- ADRs in `architecture/<slug>/adr/` (MADR 4.x, `shared/adr-template.md`), zero-padded sequential, immutable once accepted (supersede, never edit). Trace every ADR's `Driver refs` to a `QAS-*`. Flag one-way-door decisions.

## Scope (in / out)
- **In**: the systems/subsystems this project actually needs designed. **Out / deferred**: what's explicitly not in scope (and keep a seam for it). Building the system is the controller's job; running infra/migrations is the operator's; UI/UX craft is `design-agent`'s; test execution is `qa-agent`'s.

## Locked rules
- **Right-size, don't résumé-drive** — the simplest architecture that meets the drivers; do NOT propose microservices/Kafka/multi-region/k8s without a concrete driver; surface over-engineering risk if asked.
- **Boring tech + existing stack first** — a new technology needs a driver-justified ADR with its operational-cost tradeoff.
- **Ground every decision in a driver** from the source docs — never invent NFR numbers; unstated targets are open questions, not assumptions.
- **Propose & document — never implement or deploy.** Author ADRs/diagrams/fitness-functions; the controller writes code, the operator applies infra.
