# Quality-Attribute Rubric — the Senior Architecture Bar + Oracles

Two layers: **hard oracles** gate deterministically; **soft oracles** are rubric-scored by a separate skeptical evaluator (`architecture-evaluator`). Never let taste — or a vendor's "best practice" — override a hard-oracle failure, and never let elegance override a missed quality-attribute response measure. The architecture is judged against the **drivers it must satisfy** (ISO/IEC 25010 quality characteristics, made concrete as quality-attribute scenarios), never against how clever it looks on a diagram.

## The grounding rule (read first)

An architecture decision is only as good as the **quality-attribute scenario** it serves. Every scenario is 6-part and ends in a **measurable response**: *source · stimulus · artifact · environment · response · response-measure*. "It's scalable / secure / resilient" is not an oracle; "sustains 10k RPS at p99 ≤ 200ms with error-rate ≤ 0.1% during a single-AZ loss" is. If a claim has no number and no traced driver, it is a preference, not a finding (see `finding-schema.md`).

## Hard oracles (deterministic, BLOCKING)

Any failure → reject, loop back to the writer. Checked first, before any soft scoring. Each is traceable, measurable, or structurally checkable — not a matter of taste. Where a tool can *execute* the check it is named in the **Executable gate** column (see `60-evaluation/fitness-functions.md` for wiring).

| Oracle | Check / threshold | Executable gate |
|--------|-------------------|-----------------|
| **Driver traceability** | Every architecturally-significant requirement (ASR) traces to a decision, and every decision traces to a driver. No orphan requirement; no unjustified decision (accidental complexity). | `traceability-mapping.md` matrix |
| **Response-measure met** | Every prioritized quality-attribute scenario has a concrete design response whose response-measure the design demonstrably meets (by capacity model, by a named pattern's guarantee, or by a fitness function). A scenario with no met measure blocks. | capacity-model / fitness function |
| **No un-accepted SPOF** | Every component on the critical path of an availability-SLO scenario has redundancy/failover, OR the SPOF is an explicit, signed-off accepted risk in the register. Silent SPOFs block. | FMEA review |
| **Failure mode defined** | Every cross-process / cross-service / external call has explicit failure handling: bounded timeout, retry (backoff+jitter where safe), and a fallback or fail-fast. No unbounded synchronous call chains. | review / arch-conformance |
| **Consistency stated** | Every write path declares its consistency model (strong/eventual/causal) and, where distributed, its mechanism (saga+compensation / outbox / 2PC / single-writer). No silent dual-write. | review · `transactional-saga-taxonomy.md` |
| **Connascence ≤ contract** | Across a quantum/service boundary, **dynamic connascence stronger than Connascence-of-Name** (i.e. ≥ Connascence-of-Meaning/Position/Algorithm/Timing/Value/Identity) is a finding — cross-boundary coupling must be the weakest possible (a named contract). Static-strong connascence inside a module is fine; across a boundary it is not. | ArchUnitTS / dependency-cruiser / deptrac |
| **Stamp coupling bounded** | A consumer that receives a payload but uses **< ~20% of its fields** (stamp coupling) is a finding — tighten the contract (projection/BFF) or use a consumer-driven contract. | Spectral / contract review |
| **Fallacies honored** | The 8 fallacies of distributed computing are not assumed away (unreliable network, non-zero latency, finite bandwidth, partial failure, changing topology, transport cost, heterogeneity). See `fallacies-and-tradeoffs.md`. | review |
| **Trust boundary secured** | Every trust boundary has authn + authz; secrets externalized (never in code/diagram); each STRIDE category has a control or accepted risk. For AI components, the **OWASP-LLM-Top-10 + MAESTRO** sweep also applies. See `40-cross-cutting/security-architecture.md`. | conftest / threat-model review |
| **Diagram compiles** | Every diagram is **diagrams-as-code** (Structurizr DSL / LikeC4 — Tier-1; never an experimental renderer) and renders without error; C4 levels are consistent. See `diagramming-standards.md`. | `structurizr` / `likec4 build` exit 0 |
| **ADR complete** | Every significant decision is a MADR 4.x ADR with context · decision drivers · ≥2 considered options · decision · consequences (positive AND negative) · status. See `adr-template.md`. | conftest on ADR front-matter |
| **API contract clean** | Public/partner contracts lint clean and introduce no un-versioned breaking change. See `30-integration/api-design.md`. | Spectral lint + oasdiff/buf breaking |
| **Cost bounded** | Order-of-magnitude cost estimate against a stated budget/constraint; no "scale infinitely, cost unstated." | cost-model review |
| **Data lifecycle lawful** | Under a compliance regime (GDPR/HIPAA/PCI/SOC2), PII is classified, residency honored, retention/erasure paths exist. An unclassified-PII store under a regulated regime blocks. | conftest / data-contract |
| **Supply-chain provenance** | Where a build pipeline is in scope, artifacts carry SLSA-conformant provenance (target level stated) and a signed SBOM. See `50-infrastructure/cicd-architecture.md` · `shared/supply-chain-contract.md`. | `cosign verify-attestation` |

### AI-system hard oracles (apply when the design has an LLM / RAG / agentic component)
| Oracle | Check / threshold | Reference |
|--------|-------------------|-----------|
| **GenAI risk addressed** | The NIST AI 600-1 high-severity dimensions for the use case — **Confabulation, Information Security, Information Integrity, Value-Chain/Data-Provenance** — each have a design control or an accepted risk. | `90-specialized/genai-risk-assessment.md` |
| **RAG grounded** | A RAG pipeline declares its faithfulness/grounding strategy and a low-confidence/failure fallback (no silent hallucinated answer on a decision path). | `90-specialized/rag-evaluation.md` |
| **Agent boundary controlled** | Every agent↔agent / agent↔tool boundary names its protocol (MCP/A2A), auth model, and trust scope; excessive-agency + tool-poisoning are threat-modeled. | `30-integration/agent-interop-protocol.md` · `90-specialized/agentic-threat-model.md` |

## Soft oracles (rubric-scored, ADVISORY — only after hard oracles are green)

Scored 0.0–1.0 by the separate skeptical evaluator. **Each score cites a typed evidence pointer** (a quote / diagram node / ADR id / capacity-model line) against a **locked checklist** with score anchors — never a free-floating impression (RULERS-style; see `shared/evaluation-evidence-protocol.md` and the *Evaluator discipline* section of `evaluation-method.md`). Mean ≥ 0.8 to pass. The senior architecture bar:

- **Conceptual integrity** — one coherent set of ideas runs through the whole design (Brooks). Consistent decomposition criteria, naming, and patterns for like problems. Solving the same problem three ways fails this even if each way works.
- **Simplicity / right-sizedness (YAGNI)** — the *simplest* architecture that satisfies the drivers, not the most impressive. No microservices for a CRUD app; no Kafka where a table would do; no multi-region with no availability driver. Accidental complexity is the cardinal sin. Boring, proven tech preferred over novel where no driver demands novelty.
- **Appropriate coupling & cohesion** — high cohesion within a boundary, loose coupling across it (lowest-strength connascence at boundaries); boundaries on capability/volatility, not technical layers; no distributed monolith; acyclic dependencies toward stability.
- **Evolvability / reversibility** — the design preserves options. One-way doors are deliberately chosen and justified; two-way doors are made cheaply and not over-analyzed. The architecture absorbs the *likely* next change without a rewrite (an ACL, a contract, a seam).
- **Team-aligned (cognitive load)** — boundaries fit team cognitive load and the team topology (Conway): no team owning more bounded contexts than it can hold, no service straddling two teams. A decomposition the org can't operate is a soft failure even if technically clean. See `10-styles-decomposition/team-topology-decomposition.md`.
- **Operability & observability** — designed to be run: health/readiness, the three pillars with correlation, runbook-able failures, independent automatable deployability, graceful degradation. Observability designed in, not bolted on.
- **Sustainability** — where it is a stated driver, an **SCI** (Software Carbon Intensity, ISO/IEC 21031:2024) estimate per functional unit and carbon-aware design choices (demand shaping, region/time shifting) are considered. Soft + uncertainty-flagged (embodied carbon is hard to source) — never a hard gate unless the project sets one. See `80-patterns/` carbon-aware patterns.
- **Tradeoff honesty** — every significant choice records what it costs on the *other* attributes and what it beat. Upside-only is incomplete craft; the rationale, not just the decision, is documented.

## Finding severity (for audits)

`critical` blocks a driver (a missed availability/security/scale scenario, a silent SPOF on a critical path) · `major` materially threatens a driver or is a one-way-door risk · `minor` craft/evolvability gap with a clear fix · `cosmetic` documentation/naming. Severity = f(driver priority, blast radius, reversibility). Security/availability failures that defeat a prioritized scenario default to **major+**.

## LLM-as-judge guardrails (for the evaluator)
The full discipline lives in `evaluation-method.md` → *Evaluator discipline & debiasing*. Headline order (by current effect size):
- **Style/formatting bias is now dominant** — style-normalize the candidate (strip length/polish/vocabulary) before judging. This is the primary debias.
- **Self-preference** — a separate evaluator, never the generator grading itself; prefer a different model family from the writer, else strip identifying style markers.
- **Per-criterion, evidence-anchored scoring** — one call per scenario, each score citing typed evidence against the locked checklist.
- **Length/sophistication & vendor/novelty bias** — do NOT reward the more elaborate architecture or the fashionable stack; the simpler design that meets every driver scores *higher*. Penalize accidental complexity explicitly.
- **Position/order bias** — small in frontier judges; swap-and-judge-twice only for small/open-weight judges or close calls.
