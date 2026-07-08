# Workflow Template

Every flow in `workflows/` follows this shape. Single responsibility, grounded in a named architecture method/standard, with hard + soft oracles and a verify step. Read `project-architecture-config.md` first — never hardcode a project's stack, SLOs, cloud target, or constraints.

```markdown
# <flow-name>

**Group:** <00-drivers | 10-styles-decomposition | 20-data | 30-integration | 40-cross-cutting | 50-infrastructure | 60-evaluation | 70-documentation | 80-patterns | 90-specialized>
**Runs as:** <inline | subagent: ../.claude/agents/<name>.md>
**Mode:** <audit (read-only review of an existing/proposed architecture) | design (writer + verify loop, authors artifacts)>   ·   **Default model:** <haiku | sonnet | opus>

## Purpose
One or two lines: the architecture responsibility this flow owns and the design question it answers. An architecture flow answers a *decision*, not a *look*.

## Inputs & preconditions
- From `project-architecture-config.md`: the existing stack + deployment target, scale/SLO targets, compliance regime, team topology, constraints, where the architecture description / ADR log / diagram source live.
- The architecture **drivers**: the functional scope + the prioritized quality-attribute scenarios (the utility tree) + constraints + assumptions/risks this decision must satisfy. A flow with no drivers downgrades scope and says so — you cannot evaluate a design without the attributes it's optimizing for.
- Target: the system/subsystem/component (or the greenfield scope) under design or review; the relevant method (ATAM, C4, DDD, Well-Architected, the cloud-pattern catalog).

## Oracle (source of truth)
Name the external truth — a quality-attribute scenario with a **response measure** (`p99 ≤ 200ms`, `RTO ≤ 5min`, `scale to 10k RPS`), a constraint, a named pattern's contract, a fallacy that must not be violated, a fitness-function threshold. Split **hard** (deterministic gate — traceable, measurable, or structurally checkable) vs **soft** (rubric/craft — simplicity, conceptual integrity, evolvability). NEVER "it's a good design" or "it scales" without a number or a traced driver.

## Standards & techniques
The concrete methods/principles this flow applies (cite the source): e.g. the 6-part quality-attribute scenario; C4 levels; DDD bounded contexts; CAP/PACELC; the saga/outbox patterns; the 8 fallacies of distributed computing; AKF scale cube; STRIDE; the Well-Architected pillars; one-way vs two-way-door decisions.

## Step sequence
- **audit:** Frame the drivers → walk the existing/proposed architecture against each quality-attribute scenario and the hard structural checks → emit findings + risks (read-only, no artifact authored, no source edited).
- **design:** Frame (extract/confirm drivers + scenarios, read-only) → Explore (N divergent directions as concrete specs, read-only) → Evaluate (skeptical evaluator scores each vs the utility tree + hard oracles; finds sensitivity/tradeoff points + risks; order-swapped) → Document (ONE writer authors the artifacts — C4-as-code, ADRs, views, threat/capacity model; preserves conceptual integrity; reuses known patterns) → Verify (fitness-functions + diagram-compile + traceability + STRIDE/failure-mode coverage as hard gates; evaluator re-scores from the artifacts) → loop ≤ N or pass.

## Assertions & exit gate
- Concrete checks (every ASR traced to a decision; every scenario has a met response-measure; no un-accepted SPOF; every cross-service call has a timeout/retry/fallback; consistency model stated per write path; STRIDE per trust boundary; diagrams compile; each ADR has context/options/decision/consequences; cost bounded).
- **Gate:** hard oracles green AND (design) rubric mean ≥ 0.8.

## Output
Write `artifacts/<flow>/report.json` per `shared/report-format.md` — findings/risks per `finding-schema.md`, plus the verification block (fitness-function results + traceability coverage + hard-oracle results + rubric score) for design mode. Authored artifacts (ADRs, diagrams, design doc) land in `architecture/<slug>/` per `project-architecture-config.md`, never scattered.

## Guardrails
Per `shared/guardrails.md`: propose & evaluate — never write product code; ground every decision in a driver (no decision without a quality attribute it serves, no requirement without a decision); reuse known patterns before inventing; one writer preserves conceptual integrity; record the tradeoff and the rejected alternatives, never just the winner.
```

**Authoring rules**
- One responsibility per flow. Ground every rule in a named architecture method/standard.
- The oracle is external. Hard where you can trace it, measure it, or structurally check it; soft (rubric) only for genuine craft (simplicity, conceptual integrity, evolvability).
- A "recommendation" is stated as a **decision with its tradeoff and rejected alternatives** (an ADR-shaped statement), actionable and reviewable without re-running the flow.
- "It depends" is never an answer on its own — name *what* it depends on (which driver, which scenario, which constraint) and decide.
