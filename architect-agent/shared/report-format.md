# Report Format

A structured JSON every flow writes, plus an orchestrator roll-up. Audits emit findings + a risk register; design flows emit findings + the authored artifacts + a verification result. The human-facing deliverable (ADRs, diagrams, design doc) lands in `architecture/<slug>/`; the machine record lands in `artifacts/<flow>/`.

## Per-flow report — `artifacts/<flow>/report.json`

```json
{
  "flow": "architecture-style-selection",
  "mode": "audit | design",
  "status": "pass | fail | error",
  "scope": "checkout subsystem",
  "started_at": "ISO-8601",
  "ended_at": "ISO-8601",
  "drivers": [
    { "id": "QAS-SCALE-01", "attribute": "Performance Efficiency", "response_measure": "10k RPS @ p99 ≤ 200ms", "priority": "H/H" },
    { "id": "QAS-AVAIL-02", "attribute": "Reliability", "response_measure": "RTO ≤ 5 min on AZ loss", "priority": "H/M" }
  ],
  "summary": { "findings": 5, "critical": 0, "major": 2, "minor": 2, "cosmetic": 1, "risks": 3 },
  "findings": [ /* finding/risk objects — see finding-schema.md */ ],
  "decisions": [
    { "adr": "ADR-0007", "title": "Saga over 2PC for checkout", "driver_ref": "QAS-AVAIL-02", "status": "accepted" }
  ],
  "verification": {
    "artifacts": ["architecture/checkout/design-doc.md", "architecture/checkout/c4-container.puml", "architecture/checkout/adr/0007-saga-over-2pc.md"],
    "traceability": { "asrs": 12, "traced": 12, "orphan_requirements": 0, "unjustified_decisions": 0 },
    "fitness_functions": [ { "name": "no-cyclic-deps", "result": "pass" }, { "name": "p99-budget-checkout", "result": "modeled-pass" } ],
    "hard_oracles": { "traceability": "pass", "response_measures_met": "pass", "no_unaccepted_spof": "pass", "failure_modes_defined": "pass", "consistency_stated": "pass", "fallacies_honored": "pass", "trust_boundaries_secured": "pass", "diagrams_compile": "pass", "adrs_complete": "pass", "cost_bounded": "pass" },
    "rubric_score": 0.85
  },
  "gate": { "name": "hard_oracles_green_and_rubric>=0.8", "passed": true },
  "notes": ["assumptions, anything deferred and why, the one-way-door decisions flagged"]
}
```

- `mode: audit` → read-only review; `verification` may be just the traceability + hard-oracle reads against the *existing* architecture, no artifact authored.
- `mode: design` → went through the writer + the verify loop; `rubric_score` from the evaluator; `artifacts` lists the authored files in `architecture/<slug>/`.
- `status: error` ≠ `fail`: `error` = the flow couldn't run (no drivers available, architecture description missing, scope undefined). Never infer a pass.

## Orchestrator roll-up — `artifacts/summary.json`

```json
{
  "run_id": "<id>",
  "mandate": "<what was asked>",
  "scope": "<system / subsystem>",
  "drivers": [ /* the consolidated utility tree — prioritized quality-attribute scenarios */ ],
  "flows": [ { "flow": "...", "mode": "...", "status": "...", "gate_passed": true } ],
  "decisions": [ /* the consolidated ADR index with driver_refs */ ],
  "findings_by_severity": { "critical": 0, "major": 2, "minor": 4, "cosmetic": 2 },
  "risk_register": [ { "id": "ARCH-AVAIL-009", "risk": "single Redis node on session path", "likelihood": "M", "impact": "H", "disposition": "mitigate", "scenario": "QAS-AVAIL-02" } ],
  "hard_oracles": "all green | <which failed>",
  "artifacts_dir": "architecture/<slug>/",
  "gate": { "passed": true, "reason": "all hard oracles green; every prioritized scenario met; mean rubric 0.85" }
}
```

## The human-facing deliverable — `architecture/<slug>/`

The design analog of the qa-agent's `test-cases.md` and the design-agent's PDF book. When a design run authors an architecture, it drops a coherent **architecture package** (auto-create `architecture/` if missing — `mkdir -p architecture/<slug>`):

```
architecture/<slug>/
├── README.md              overview + the decision summary + the driver/utility-tree at a glance
├── design-doc.md          the architecture description (arc42 / Views-and-Beyond): context, views, rationale, risks
├── quality-attributes.md  the utility tree — prioritized 6-part scenarios with response measures
├── adr/                    one ADR per significant decision (MADR format — see adr-template.md)
│   └── NNNN-<slug>.md
├── diagrams/              diagrams-as-code (C4 Context/Container/Component/Deployment) — *.puml / *.md (Mermaid)
├── threat-model.md        STRIDE per trust boundary (where security is a driver)
├── capacity-model.md      back-of-the-envelope sizing proving each performance/scale response measure
├── fitness-functions.md   the executable/automatable architecture-characteristic checks to enforce in CI
└── tradeoffs.md           the option comparison matrix + sensitivity/tradeoff points + the risk register
```

- **Deliverable = the architecture package**, not a single diagram. Diagrams are **diagrams-as-code** (compile-checked, version-controllable) — never a pasted image. Optionally compile the package into a single `<slug>.pdf` book (headless Chrome / pandoc) for review parity with the design fleet, but the markdown+diagram source is the source of truth.
- The explore→evaluate→verify *run reports* stay in `artifacts/<flow>/` (machine record); the architecture itself goes in `architecture/<slug>/`. Never scatter ADRs/diagrams elsewhere.

## Conventions
- Every finding carries its `driver_ref`; a finding with no driver is dropped (it's a preference).
- A design flow that didn't pass the verify loop is `status: fail` with the failing hard oracle named (e.g. "QAS-SCALE-01 response-measure unmet — no capacity model").
- The orchestrator gate fails on: any failed flow gate, any open `hard` finding, any prioritized scenario with no met response-measure, any un-accepted SPOF on an availability-SLO path, or any decision authored without an ADR.
- Severity is set by the agent; **priority/disposition** (accept/mitigate/monitor) on risks is *proposed* but the final call is the controller's/human's.
