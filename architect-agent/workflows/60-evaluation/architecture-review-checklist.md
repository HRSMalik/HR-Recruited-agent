# architecture-review-checklist

**Group:** 60-evaluation  ·  **Runs as:** subagent: ../.claude/agents/architecture-evaluator.md  ·  **Mode:** audit + design  ·  **Default model:** opus

## Purpose

Run a **gate review** of an architecture (existing, proposed, or post-ATAM) against the consolidated hard-oracle checklist — drivers traced, fallacies honored, no un-accepted SPOF, security/privacy controls per boundary, cost bounded, operability designed in — and emit a binary pass/fail verdict with blocking findings for every gap. This is the **release-readiness gate** for an architecture: `architecture-evaluation-atam.md` produces the ATAM scorecard (sensitivity/tradeoff points, scenario analysis); this flow **closes the gate** by walking every hard oracle and the senior-craft soft rubric, producing a prioritized blocking-findings report the controller can act on before the architecture is handed to implementers. It answers: *is this architecture ready to build against?*

## Inputs & preconditions

- From `project-architecture-config.md`: the existing stack + deployment target, SLO/scale targets, compliance regime (e.g. PII / financial / health-data handling, RBAC, audit-logging — as applicable to the project), team topology (Conway), constraints (stack lock, right-size, boring-tech-first), and where the architecture description / ADR log / diagrams live (`architecture/<slug>/`).
- The **drivers** — the prioritized utility tree of 6-part quality-attribute scenarios with response measures, produced by `../00-drivers/quality-attribute-scenarios.md`. If the tree is absent or scenarios lack response measures, the checklist cannot assess traceability or coverage; surface those gaps as `oracle:hard` / `type:driver` findings and halt — do not invent numbers.
- The **architecture description** under review: the design doc + C4 views (Context L1, Container L2, and where present Component L3) + ADRs in `architecture/<slug>/` (design mode), or the as-built codebase scan (audit mode). Preconditions: the source-of-truth docs (BRD / PRD / understanding log named in `project-architecture-config.md`) read; diagram source files (`*.puml`, `*.md` Mermaid, Structurizr DSL) accessible for compile check; the threat model accessible for STRIDE coverage check.
- The **ATAM scorecard** (`artifacts/architecture-evaluation-atam/report.json`) when available — the checklist reuses its risk register and scenario analysis rather than re-deriving them; if absent, the checklist runs in degraded mode and flags the missing scorecard as a precondition gap.
- Precondition: the `architecture-evaluator` is the sole scorer — the writer (`solution-architect`) never self-grades; separate skeptical scorer only (`../shared/guardrails.md` §6).

## Oracle (source of truth)

The consolidated hard-oracle target set from `../shared/quality-attribute-rubric.md`, applied as a **binary gate**: every hard oracle below must be green, or the gap is a **blocking finding** (`oracle:"hard"`). After all hard oracles are green, the senior-craft soft rubric is scored by the evaluator (`oracle:"soft"`); the design passes the soft bar when mean ≥ 0.8. A design that passes every hard oracle but scores < 0.8 on the soft rubric is **advisory-blocked** — surfaced for the controller, not a hard stop.

**Hard (deterministic, BLOCKING — any failure → open blocking finding, loop back to writer):**

| Oracle | Check / threshold |
|--------|-------------------|
| **Driver traceability** | Every ASR traces to a decision; every decision traces to a driver. No orphan requirement (an ASR no decision satisfies); no unjustified decision (a choice no driver demands — that is accidental complexity). Verify via the traceability matrix (`../70-documentation/traceability-mapping.md`). |
| **Response-measure met** | Every prioritized quality-attribute scenario (all `(H,*)` leaves; all `(H,H)` first) has a design response whose response measure is **demonstrably met** by a capacity model, a named pattern's guarantee, or a fitness function — never by assertion. A scenario with no met measure, or a measure met only by assertion, blocks. |
| **No un-accepted SPOF** | Every component on the critical path of an availability-SLO scenario has redundancy/failover, OR the SPOF is an **explicitly signed-off accepted risk** in the register (with a named owner, a blast-radius estimate, and a disposition). Silent SPOFs block; documented and accepted SPOFs are non-blocking. |
| **Failure mode defined** | Every cross-process / cross-service / external call has: a **bounded timeout** (never infinite), a **retry policy** (idempotent + exponential backoff with jitter where safe), and a **fallback or fail-fast**. No unbounded synchronous call chains. Check against `../30-integration/service-communication-resilience.md`. |
| **Consistency stated** | Every write path declares its consistency model (strong / eventual / causal) and, where distributed, its mechanism (saga+compensation / outbox + CDC / 2PC / single-writer). "It's consistent" with no named model blocks. |
| **Fallacies honored** | All 8 fallacies of distributed computing (`../shared/fallacies-and-tradeoffs.md`) are accounted for where they apply. Specifically: every remote call has a timeout+retry (fallacy 1); latency budgets are spent across hops (fallacy 2); payloads are bounded + pagination enforced (fallacy 3); zero-trust authn+authz at every trust boundary (fallacy 4); no hardcoded hosts / service discovery in place (fallacy 5); explicit API versioning + no coordinated-deploy assumption (fallacy 6); egress costs in the cost model (fallacy 7); schema evolution + ACL at foreign-system boundaries (fallacy 8). |
| **Trust boundary secured** | Every trust boundary in the threat model has authn + authz specified; secrets are externalized (env / secret store, never in code or committed diagram source); each STRIDE category (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege) has a named control or an explicitly accepted risk. Check against `../40-cross-cutting/security-architecture.md`. |
| **Diagrams compile** | Every diagram is diagrams-as-code (Structurizr DSL / PlantUML + C4-PlantUML / Mermaid `C4Context`) and **renders without error** when the tool is run. C4 levels are consistent: every Container in L2 that is complex enough to warrant a drill-down appears in a Component (L3) view; names match the ADRs and the design doc exactly. A diagram that does not compile is a broken artifact. Check against `../shared/diagramming-standards.md`. |
| **ADRs complete** | Every significant decision is an ADR (MADR format, `../shared/adr-template.md`) with **context · ≥2 options considered · decision · consequences (positive AND negative) · status**. A decision with no recorded alternatives or no negative consequences blocks. One-way-door decisions are flagged. |
| **Cost bounded** | The design carries an order-of-magnitude cost estimate against the stated budget/constraint; no component is "scale infinitely, cost unstated." Where cost is a stated driver, the estimate is traced to a capacity model (`architecture/<slug>/capacity-model.md`). An unestimated cost where cost is a driver blocks. |
| **Data lifecycle lawful** | Where a compliance regime applies (per `project-architecture-config.md` — e.g. PII / HIPAA / SOC2 / PCI), PII is **classified** (which fields, which stores), **residency** is honored, and **retention + erasure paths** exist. An unclassified-PII store under a regulated regime blocks. Check against `../40-cross-cutting/privacy-compliance-architecture.md`. |
| **Connascence ≤ contract** | Across a quantum/service boundary, **dynamic connascence stronger than Connascence-of-Name** (i.e. ≥ Connascence-of-Meaning / Position / Algorithm / Timing / Value / Identity) is a blocking finding — cross-boundary coupling must be the weakest possible: a named contract (API spec, event schema). Static-strong connascence inside a module is acceptable; across a boundary it is not. Verify with ArchUnitTS / dependency-cruiser / deptrac. |
| **Stamp coupling bounded** | A consumer that receives a payload but uses **< ~20% of its fields** is a stamp-coupling finding — tighten the contract (projection / BFF) or adopt a consumer-driven contract. Verify via Spectral / contract review (`../30-integration/api-design.md`). |
| **API contract clean** | Public / partner contracts **lint clean** (Spectral) and introduce **no un-versioned breaking change** (oasdiff / buf breaking). Check against `../30-integration/api-design.md`. |
| **Supply-chain provenance** | Where a build pipeline is in scope, artifacts carry **SLSA-conformant provenance** (target level stated) and a **signed SBOM**. Verify via `cosign verify-attestation`. Check against `../50-infrastructure/cicd-architecture.md` · `../shared/supply-chain-contract.md`. |

**AI-system hard oracles (apply WHERE an AI / LLM / RAG / agentic component exists — skip entirely for non-AI architectures):**

| Oracle | Check / threshold |
|--------|-------------------|
| **GenAI risk addressed** | The NIST AI 600-1 high-severity dimensions for the use case — **Confabulation, Information Security, Information Integrity, Value-Chain / Data-Provenance** — each have a design control or an explicitly accepted risk. Check against `../90-specialized/genai-risk-assessment.md`. |
| **RAG grounded** | A RAG pipeline declares its **faithfulness / grounding strategy** and a **low-confidence / failure fallback** — no silent hallucinated answer on a decision path. Check against `../90-specialized/rag-evaluation.md`. |
| **Agent boundary controlled** | Every agent↔agent / agent↔tool boundary names its **protocol** (MCP / A2A), **auth model**, and **trust scope**; excessive-agency and tool-poisoning are threat-modeled. Check against `../30-integration/agent-interop-protocol.md` · `../90-specialized/agentic-threat-model.md`. |

**Soft (rubric-scored, ADVISORY — only run after all hard oracles are green; scored 0.0–1.0, mean ≥ 0.8 to pass):**

- **Conceptual integrity** (Brooks) — one coherent set of ideas runs through the whole design: consistent decomposition criteria, consistent naming, consistent patterns for like problems. A system that solves the same problem three ways fails this even if each way works independently.
- **Simplicity / right-sizedness (YAGNI)** — the *simplest* architecture that satisfies the drivers, not the most impressive. No microservices for a CRUD app; no Kafka where a table would do; no multi-region for a system with no availability driver demanding it. Accidental complexity is the cardinal sin; boring, proven technology preferred.
- **Appropriate coupling & cohesion** — high cohesion within a boundary, loose coupling across it; boundaries drawn on business capability / volatility, not technical layers; no distributed monolith (services that must deploy together). The AKF scale cube is invoked to verify the split is on the right axis (x-clone / y-function / z-data).
- **Evolvability / reversibility** — one-way-door decisions are deliberately chosen and justified; two-way-door decisions are made cheaply. The architecture can absorb the *likely* next change (a deferred integration seam, the near-term bounded contexts, per `project-architecture-config.md`) without a rewrite.
- **Operability & observability** — health/readiness endpoints, the three observability pillars (logs / metrics / traces with correlation IDs), OpenTelemetry instrumentation, runbook-able failure modes, independent deployability, graceful degradation under partial failure. Observability is designed in, not bolted on.
- **Tradeoff honesty** — every significant choice records what it costs on the *other* attributes and what it beat (an ADR with only positive consequences is incomplete craft). Sensitivity points and tradeoff points from the ATAM scorecard are surfaced, not buried.

**Severity assignment** (`../shared/quality-attribute-rubric.md`): `critical` = blocks a prioritized `(H,H)` driver (missed availability/security/scale scenario, silent SPOF on a critical path); `major` = materially threatens a `(H,*)` driver or is a one-way-door risk; `minor` = craft/evolvability gap with a clear fix; `cosmetic` = documentation/naming. Severity = f(driver priority, blast radius, reversibility). Security and availability failures that defeat a prioritized scenario default to **major+**.

## Standards & techniques

- **The architecture-review-checklist as consolidated gate** — this flow is the operational checklist that materializes every hard oracle from `../shared/quality-attribute-rubric.md` into a walk-through sequence: each oracle is checked in order, failures emit blocking findings, and the gate is the AND of all oracle verdicts.
- **Review-as-a-gate (pass/fail with blocking findings)** — the output is not a scorecard of nuance; it is a binary pass/fail with a prioritized list of blocking gaps the controller must resolve before the architecture is handed to implementers. An architecture that passes the gate has no open `oracle:"hard"` findings and a soft-rubric mean ≥ 0.8.
- **ATAM (SEI)** (`../shared/evaluation-method.md`) — the checklist reuses the ATAM outputs (sensitivity points, tradeoff points, risk themes) from `architecture-evaluation-atam.md` rather than re-running the analysis. Where the ATAM scorecard is absent, the checklist degrades: it asserts the structural hard oracles it can check mechanically and flags the missing scenario analysis as a blocking gap.
- **ISO/IEC 25010** quality characteristics — the attribute taxonomy that guarantees coverage: no quality attribute that matters is omitted (performance efficiency, reliability, security, maintainability/evolvability, compliance, cost, operability).
- **ISO/IEC/IEEE 42010:2022 (architecture description) + 42030:2019 (architecture evaluation)** — the checklist verifies that the architecture description is complete (stakeholders, concerns, viewpoints, views, rationale) per 42010:2022 and that the evaluation process satisfies the evaluation framework of 42030:2019; C4 views are consistent across levels per `../shared/diagramming-standards.md`.
- **The 8 fallacies of distributed computing** (`../shared/fallacies-and-tradeoffs.md`) — each fallacy maps to a specific hard oracle check; a design that assumes any fallacy away on a `(H,*)` scenario path is a hard-oracle failure.
- **STRIDE** — the per-trust-boundary threat model check; each STRIDE category must have a named control or an explicitly accepted risk per `../40-cross-cutting/security-architecture.md`.
- **MADR (Architecture Decision Records)** (`../shared/adr-template.md`) — the ADR-completeness hard oracle checks for context · ≥2 options · decision · consequences (both valence) · status; one-way-door decisions flagged.
- **Fitness functions** (evolutionary architecture, `fitness-functions.md`) — the checklist confirms that fitness-function specifications exist for every sensitivity-point threshold the ATAM named as automatable (e.g. no-cyclic-dependency rules, latency-budget checks, coupling-metric thresholds). Fitness functions that do not yet have a CI gate are flagged as `minor` findings.
- **AKF scale cube** — used when evaluating the coupling & cohesion soft oracle: verify the decomposition is on the right axis (x=clone, y=function-split, z=data-partition) relative to the scale driver, not an arbitrary split.
- **Well-Architected pillars (AWS/Azure)** — the six pillars (operational excellence, security, reliability, performance efficiency, cost optimization, sustainability) are the soft-oracle cross-check to confirm no pillar is systematically unaddressed; a pillar with zero design attention is a soft-oracle gap (not a hard block unless a driver maps to it).
- **CBAM** (`../shared/evaluation-method.md`) — when two alternative fixes both satisfy a hard oracle, the cheaper one (lower build + run cost against the same response-measure benefit) is preferred and the cost difference is quantified, not asserted.
- **Senior-craft soft bar** (conceptual integrity per Brooks; right-sizedness per YAGNI; Gall's law — start simple, evolve) — the soft rubric operationalizes what a staff/principal architect judges that no checklist fully captures.

## Step sequence

- **audit:** Frame the drivers (read utility tree from `architecture/<slug>/quality-attributes.md`; if absent, restate stated NFRs as 6-part scenarios and flag measureless "-ilities" as `oracle:hard` findings, then proceed in degraded mode) → load the ATAM scorecard from `artifacts/architecture-evaluation-atam/report.json` if present → walk the architecture description + C4 views + ADRs + threat model + cost model, evaluating each hard oracle in checklist order (traceability → response-measures → SPOF → failure-modes → consistency → connascence-≤-contract → stamp-coupling → fallacies → trust boundaries → diagram-compile → ADR completeness → API-contract-clean → cost → data-lifecycle → supply-chain-provenance → [if AI component: GenAI-risk → RAG-grounded → agent-boundary]) → for each failed oracle emit a blocking finding (`oracle:"hard"`, severity per driver priority + blast radius, evidence = the structural fact that fails the check, tradeoff = the cost of closing the gap) → after all hard oracles, run the soft-rubric pass (six dimensions, 0.0–1.0, position-bias-guarded by a separate skeptical evaluator run, penalizing accidental complexity and unjustified novelty) → emit the gate verdict. Read-only: no artifact authored, no source edited.
- **design:** Frame (confirm the utility tree + locate the architecture description under review, read-only) → Explore (not applicable — this flow does not produce new directions; use `architecture-evaluation-atam.md` + `tradeoff-analysis-cbam.md` for option evaluation) → Evaluate (the one skeptical `architecture-evaluator` runs the full hard-oracle walk + soft-rubric score; swaps position on any soft-rubric dimension to kill bias; penalizes accidental complexity and unjustified novelty) → Document (the ONE writer `solution-architect` records the gate verdict in `architecture/<slug>/README.md` — the pass/fail status, the list of blocking findings with ADR-shaped recommendations, the soft-rubric dimension scores; raises new ADRs for any decision the gate review surfaces that wasn't previously recorded) → Verify (the evaluator re-reads the blocking findings against the architecture to confirm each finding's evidence is traceable and the recommendation is ADR-complete; confirms the soft-rubric score was computed without the generator grading its own work) → loop ≤ 5 or pass.

## Assertions & exit gate

The following checks must all be green before the gate passes. Each failure is a concrete blocking finding in the report.

**Hard-oracle assertions (each must be green):**
1. Every ASR in the utility tree traces to a named decision; every decision traces to a `QAS-*` driver — zero orphan requirements, zero unjustified decisions.
2. Every `(H,*)` scenario has a design response with a met response measure proven by a capacity model / named pattern's guarantee / fitness function — no scenario left un-analyzed, no verdict by assertion.
3. Every component on a critical-path availability-SLO scenario has documented redundancy/failover, OR the SPOF is in the signed-off accepted-risk register with blast-radius and owner.
4. Every cross-process / external call has a bounded timeout + idempotent retry policy + fallback or fail-fast — no unbounded synchronous call chains.
5. Every write path declares its consistency model and mechanism (saga / outbox / 2PC / single-writer) — no path is "consistent" by assertion only.
6. All 8 fallacies are accounted for on every `(H,*)` scenario path — no fallacy assumed away.
7. Every trust boundary has authn + authz specified; secrets are externalized; each STRIDE category has a control or accepted risk.
8. Every diagram is diagrams-as-code and renders without error; C4 levels are internally consistent; names match ADRs and design doc.
9. Every significant decision is an ADR with context · ≥2 options · decision · consequences (positive AND negative) · status; one-way-door decisions are flagged.
10. An order-of-magnitude cost estimate exists against a stated budget/constraint; where cost is a driver it traces to the capacity model.
11. Where a compliance regime applies, PII is classified per store; residency is honored; retention and erasure paths exist.
12. Across every quantum/service boundary, dynamic connascence does not exceed Connascence-of-Name; cross-boundary coupling is a named contract. Verified by ArchUnitTS / dependency-cruiser / deptrac.
13. No consumer receives a payload where it uses < ~20% of fields without a projection / BFF / consumer-driven contract tightening the coupling. Verified by Spectral / contract review.
14. All public/partner API contracts lint clean (Spectral) and introduce no un-versioned breaking change (oasdiff / buf breaking).
15. Where a build pipeline is in scope, artifacts carry SLSA-conformant provenance (target level stated) and a signed SBOM verifiable by `cosign verify-attestation`.

**AI-system hard-oracle assertions (apply WHERE an AI / LLM / RAG / agentic component exists):**
16. The NIST AI 600-1 high-severity risk dimensions (Confabulation, Information Security, Information Integrity, Value-Chain / Data-Provenance) each have a design control or an explicitly accepted risk.
17. Every RAG pipeline declares its faithfulness / grounding strategy and a low-confidence / failure fallback — no silent hallucinated answer on a decision path.
18. Every agent↔agent / agent↔tool boundary names its protocol (MCP / A2A), auth model, and trust scope; excessive-agency and tool-poisoning are threat-modeled.

**Soft-rubric assertions (after hard oracles green):**
19. Conceptual integrity, simplicity/right-sizedness, coupling/cohesion, evolvability/reversibility, operability/observability, and tradeoff honesty are scored by the separate skeptical evaluator (not the generator); mean of six dimensions ≥ 0.8.

**Gate:** **hard oracles 1–15 all green (plus 16–18 where an AI component is present) AND soft-rubric mean ≥ 0.8.** A design with any open `oracle:"hard"` finding does not pass, regardless of soft-rubric score. A design that passes all hard oracles but scores < 0.8 on the soft rubric is returned to the writer with advisory-blocking findings; the controller decides whether to ship with advisories or fix first.

## Output

Write `artifacts/architecture-review-checklist/report.json` per `../shared/report-format.md`:

```json
{
  "flow": "architecture-review-checklist",
  "mode": "audit | design",
  "status": "pass | fail | error",
  "scope": "<architecture/<slug> under review>",
  "started_at": "ISO-8601",
  "ended_at": "ISO-8601",
  "drivers": [ /* the prioritized utility-tree scenarios the gate is checked against */ ],
  "summary": { "findings": N, "critical": 0, "major": 0, "minor": 0, "cosmetic": 0, "risks": 0 },
  "findings": [ /* finding objects per ../shared/finding-schema.md — id:ARCH-CHK-NNN, oracle:"hard"|"soft" */ ],
  "verification": {
    "hard_oracles": {
      "traceability": "pass | fail",
      "response_measures_met": "pass | fail",
      "no_unaccepted_spof": "pass | fail",
      "failure_modes_defined": "pass | fail",
      "consistency_stated": "pass | fail",
      "fallacies_honored": "pass | fail",
      "trust_boundaries_secured": "pass | fail",
      "diagrams_compile": "pass | fail",
      "adrs_complete": "pass | fail",
      "cost_bounded": "pass | fail",
      "data_lifecycle_lawful": "pass | fail",
      "connascence_le_contract": "pass | fail",
      "stamp_coupling_bounded": "pass | fail",
      "api_contract_clean": "pass | fail",
      "supply_chain_provenance": "pass | fail",
      "genai_risk_addressed": "pass | fail | n/a",
      "rag_grounded": "pass | fail | n/a",
      "agent_boundary_controlled": "pass | fail | n/a"
    },
    "rubric_score": 0.0,
    "rubric_dimensions": {
      "conceptual_integrity": 0.0,
      "simplicity_right_sizedness": 0.0,
      "coupling_cohesion": 0.0,
      "evolvability_reversibility": 0.0,
      "operability_observability": 0.0,
      "tradeoff_honesty": 0.0
    }
  },
  "gate": { "name": "hard_oracles_green_and_rubric>=0.8", "passed": true | false },
  "notes": [ "blocking findings summary; one-way-door decisions flagged; open driver questions for the controller" ]
}
```

Findings follow `../shared/finding-schema.md` with `id: "ARCH-CHK-NNN"`. Every hard-oracle failure is `oracle:"hard"` with `driver_ref` pointing at the `QAS-*` scenario the failure threatens, `evidence` naming the structural fact (not a vague claim), and a `recommendation` that is ADR-shaped (pattern/topology/decision + the response-measure it satisfies + rejected alternatives). Soft-oracle advisory gaps are `oracle:"soft"` with a dimension name and a concrete improvement suggestion.

In design mode: the gate verdict and blocking-finding summary land in `architecture/<slug>/README.md` (authored by the one writer `solution-architect`); any newly surfaced decision that wasn't previously recorded becomes a new ADR in `architecture/<slug>/adr/` per `../shared/adr-template.md`. The run report stays in `artifacts/architecture-review-checklist/`. Open driver questions (an RTO/availability/scale target not stated in the BRD/PRD that blocks a hard oracle) are listed explicitly for the controller — never silently assumed.

Cross-references to the flows whose outputs this gate consumes:
- `../00-drivers/quality-attribute-scenarios.md` — the utility tree (the oracle target set)
- `architecture-evaluation-atam.md` — the ATAM scorecard (sensitivity/tradeoff points, risk themes) this gate aggregates
- `../40-cross-cutting/security-architecture.md` — the STRIDE threat model per trust boundary
- `../40-cross-cutting/privacy-compliance-architecture.md` — the PII classification + residency + erasure model
- `../70-documentation/traceability-mapping.md` — the ASR↔decision↔component traceability matrix
- `fitness-functions.md` — the automatable characteristic checks this gate confirms exist

## Guardrails

Per `../shared/guardrails.md`: **propose & evaluate — never write product code, never apply infra.** The `architecture-evaluator` is read-only on every artifact it reviews; it produces findings and a gate verdict, never edits the architecture. The one writer (`solution-architect`) records the gate result and raises ADRs; no other agent edits the artifact folder.

- **Ground every finding in a driver.** A hard-oracle finding with no `driver_ref` is a preference, not a finding — tie it to a `QAS-*` or drop it. An unjustified decision is accidental complexity; name the driver it would need to be justified, or recommend its removal.
- **The oracle is external.** The gate verdict comes from the traceability matrix / the capacity model / the fitness functions / the threat model / the diagram-compile result — not from the evaluator's belief that the design "looks good." No number + no traced driver = a preference, not a finding (`../shared/finding-schema.md`).
- **Severity is proportionate.** Severity = f(driver priority + blast radius + reversibility), per the grounding rule in `../shared/quality-attribute-rubric.md`. A cosmetic finding is never `critical`; a silent SPOF on a `(H,H)` availability scenario is never `minor`. The gate is honest — it blocks on real gaps, not cosmetics.
- **Penalize accidental complexity.** The soft-rubric evaluator penalizes over-engineering and unjustified novelty, not just outright failures. The simpler design that meets every driver scores higher than the impressive one that meets the same drivers at higher cost.
- **Separate evaluator, always.** The `architecture-evaluator` scores; the `solution-architect` writes. Never the generator grading its own work. Position bias is killed by dimension-order swapping on the soft rubric.
- **Never write to project memory.** Findings, lessons, and risks go in the returned report and the `architecture/<slug>/README.md` — never into a memory file. The controller curates memory.
- **Bound the loop.** The design-mode verify loop runs ≤ 5 iterations; on iteration 5, if blocking hard-oracle findings remain, `status: fail` is reported and the controller decides the next action.
