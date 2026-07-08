# Evaluation Evidence Protocol — Typed Evidence + Locked Checklist (RULERS-Style)

The `architecture-evaluator` is an LLM judge, and LLM judges drift: they re-interpret rubric bars run-to-run, award soft scores on free-floating impressions, and let a strong dimension silently inflate a weak one. This file closes those gaps. It defines the **typed evidence pointer** kinds the evaluator must cite for every soft score, the **locked ternary checklist** (0 / 0.5 / 1.0) with frozen per-anchor descriptions so interpretation cannot shift, the voiding rule (no pointer = void score), and the calibration procedure for aligning the evaluator's outputs to reference scores. Cross-refs: `quality-attribute-rubric.md` (the soft criteria being scored) · `evaluation-method.md` (the evaluator's broader discipline and anti-bias rules).

---

## 1. Typed Evidence Pointer Kinds

Every soft score emitted by the evaluator must carry at least one **typed evidence pointer** selected from the set below. "Typed" means the evaluator names the kind and provides the locator — so a reader (human or automated gate) can retrieve the cited artifact independently and verify the claim. A score without a pointer of a recognized kind is void (§3).

### 1.1 Design-doc quote (`DDQ`)

A verbatim excerpt from the architecture description document being evaluated, followed by its section or heading path.

Format: `DDQ: "<exact quote>" [<doc-name> §<section-path>]`

Example: `DDQ: "All writes to the claim store are funnelled through the outbox collector before any downstream notification fires." [arch-description.md §4.2 — Consistency Strategy]`

Rules: The quote must be the minimum excerpt that supports the claim; do not summarize or paraphrase (paraphrase is an impression, not a pointer). If the section path is absent, the pointer is incomplete and scores as void.

### 1.2 Diagram node / edge id (`DGN`)

A named node, edge, or relationship in a diagrams-as-code source (Structurizr DSL or LikeC4 — per `diagramming-standards.md`). The locator is `<diagram-file>#<element-id>`.

Format: `DGN: <diagram-file>#<element-id> [<human-readable label>]`

Example: `DGN: c4-container.dsl#rel_api_cache [API → Redis: read-through on claim lookup]`

Rules: The diagram must be the compiled source, not a rendered image; the element-id must resolve in the file. A reference to "the diagram shows…" without an element-id is an impression, not a pointer.

### 1.3 ADR id (`ADR`)

A reference to a numbered ADR in `docs/architecture/decisions/` (MADR 4.x format, per `adr-template.md`). The pointer names the ADR id and the specific field (Context / Decision / Consequences) being cited.

Format: `ADR: ADR-<NNN> [<title>] §<field>`

Example: `ADR: ADR-0012 [Saga over 2PC for checkout] §Consequences — negative`

Rules: The ADR must exist at its canonical path. Citing an ADR without naming the field still locates the document but is a weak pointer; the evaluator should name the field where the cited fact lives.

### 1.4 Capacity-model line (`CML`)

A line or row in a capacity model document (`docs/architecture/capacity-model.*` or the inline table inside `00-drivers/quality-attribute-scenarios.md`). The pointer names the file, the scenario or row label, and the computed value being cited.

Format: `CML: <file>#<row-or-scenario-label>: <value-and-unit>`

Example: `CML: capacity-model.md#QAS-PERF-01: p99 = 142ms at 8000 RPS (3× core-count headroom)`

Rules: The model must be present in the repository; the cited number must be reproducible from the inputs in that row. A capacity claim backed only by "the team estimates…" in prose is a DDQ, not a CML; log it accordingly — the strength difference matters when calibrating (§4).

### 1.5 Fitness-function result (`FFR`)

The pass/fail outcome of an executable fitness function, conftest, dependency-cruiser rule, Spectral lint, ArchUnitTS check, or structurizr/LikeC4 build recorded in CI. The pointer names the tool, the check id or rule name, and the exit status.

Format: `FFR: <tool>#<check-id> → <PASS|FAIL> [<run-ref or commit>]`

Example: `FFR: depcruise#no-circular-between-quanta → PASS [CI run 8841, commit a3041d6]`

Rules: The run-ref must be traceable (a CI run URL, a commit sha, or a local output file path). A claim that "the tests pass" without a named check and run-ref is an impression. FFR is the strongest pointer kind — it is the only kind that also satisfies the external-signal gate in `evaluation-method.md` §Evaluator discipline (the EVALUATE→revise loop may not close on evaluator-word alone; it needs an FFR or a human decision).

---

## 2. Locked Checklist — Ternary Anchored Scale

Each soft criterion from `quality-attribute-rubric.md §Soft oracles` is serialized here as a **locked checklist item**: a 0 / 0.5 / 1.0 ternary with frozen descriptions for each anchor. The evaluator selects the anchor whose description matches the evidence; it does not re-interpret the bar. Adding or rewriting anchors requires a version bump to this file and a re-calibration run (§4).

The checklist is scored **per criterion per quantum** (one scoring call per item, per `evaluation-method.md §Per-criterion scoring`). The evaluator emits `{criterion, score, evidence_pointer, rationale}` for each row. A missing row is a silent omission — the evaluator self-check must confirm all rows are present before emitting (§Evaluator discipline, `evaluation-method.md`).

---

### CL-01 — Conceptual Integrity

*Is one coherent set of ideas, decomposition criteria, and patterns applied consistently across the design?*

| Score | Anchor (frozen) |
|-------|-----------------|
| **1.0** | A single stated decomposition principle (e.g. domain capability, volatility axis) is applied to ALL bounded contexts and service boundaries without exception. Identical problems (e.g. async notification, write path) are solved the same way throughout. Any deviation from the pattern is explicitly justified in an ADR. |
| **0.5** | The stated principle covers most of the design but 1–2 boundaries deviate without a recorded justification, OR two equivalent patterns exist for the same problem class in different parts of the system with no stated reason for the split. |
| **0.0** | No single decomposition principle can be identified, OR the same class of problem (e.g. saga vs dual-write) is handled inconsistently across multiple contexts with no rationale, OR a pattern is named in the intro and violated systematically in the detail. |

---

### CL-02 — Simplicity / Right-sizedness (YAGNI)

*Is this the simplest architecture that satisfies the stated drivers — no accidental complexity?*

| Score | Anchor (frozen) |
|-------|-----------------|
| **1.0** | Every architectural element traces to a named driver or quality-attribute scenario. No pattern is introduced that is not demanded by a driver (no Kafka where a table would do, no microservice decomposition where a modular monolith meets every scenario). Boring, proven technology is preferred where no driver demands novelty — and where novel tech is chosen, the driver justifying it is named. |
| **0.5** | Most elements trace to a driver, but 1–2 are gold-plating or speculative (e.g. an event-sourcing store where only audit-log is required, an extra caching layer where no latency scenario demands it). The accidental complexity is present but bounded — no driver is endangered. |
| **0.0** | Significant complexity exists with no driver: multiple layers that could be collapsed, a distributed architecture where a single deployable would meet every scenario, novel technology chosen without a forcing function. Accidental complexity outweighs driver-demanded complexity. |

---

### CL-03 — Appropriate Coupling and Cohesion

*Are boundaries drawn on capability/volatility, cross-boundary connascence minimized, and no distributed monolith present?*

| Score | Anchor (frozen) |
|-------|-----------------|
| **1.0** | Every boundary separates capabilities that change at different rates or for different reasons. Cross-boundary coupling is Connascence-of-Name (contract/interface only). No service spans two domains with unrelated volatility. No choreography-hiding orchestration that couples callers to internals. Acyclic dependency graph across quanta — traceable by diagram or fitness function. |
| **0.5** | Most boundaries are well-drawn, but 1–2 cross-boundary calls carry Connascence-of-Meaning or Connascence-of-Position (e.g. positional parameter tuple shared across a boundary, field-meaning assumed without a schema). OR a minor cycle exists between two quanta that is noted but tolerated with a comment. |
| **0.0** | Boundaries are drawn on technical layers rather than capability (classic big-ball-of-mud layering), OR strong dynamic connascence (Connascence-of-Timing, Connascence-of-Identity) crosses a service boundary, OR the dependency graph has cycles that span independently-deployable units. |

---

### CL-04 — Evolvability / Reversibility

*Does the design preserve options, and are one-way doors deliberately chosen and justified?*

| Score | Anchor (frozen) |
|-------|-----------------|
| **1.0** | Every one-way-door decision (irreversible data format, a platform lock-in, a public API contract) is named as such in its ADR and the rejection of alternatives is recorded with cost reasoning. Two-way-door decisions are treated lightly. Anti-corruption layers or seams are placed at all boundaries where a foreign system or volatile dependency could change. The *likely next change* (named in the requirements or risk register) can be absorbed without a cross-cutting rewrite. |
| **0.5** | Most decisions are reversible or justified, but 1 one-way-door decision has no ADR or no alternatives-rejected reasoning. OR the design places no seam at a foreign boundary that the risk register flags as volatile. |
| **0.0** | Multiple one-way-door decisions are made without ADRs or without any alternatives considered. OR the design is built around a single-vendor, single-protocol assumption at every layer with no acknowledged lock-in tradeoff. OR a named likely-next-change would require a cross-cutting rewrite. |

---

### CL-05 — Team-Aligned / Cognitive Load

*Do the bounded-context boundaries fit team topology and cognitive load constraints?*

| Score | Anchor (frozen) |
|-------|-----------------|
| **1.0** | Each independently-deployable unit is owned by at most one team with a bounded-context responsibility that fits within a team's cognitive load (Skelton/Pais: ≤ 5–7 domains per team). Interfaces between teams are explicit (X-as-a-Service, facilitating, or collaboration-mode) and match the interaction mode named in the team topology design. Conway alignment is stated or the inverse-Conway maneuver is documented. |
| **0.5** | Most boundaries match team ownership, but 1 service straddles two teams with no stated responsibility split, OR the team topology is not referenced and the evaluator cannot confirm alignment — the design is silent on it rather than contradicting it. |
| **0.0** | Boundaries are drawn without any reference to team ownership, and the decomposition would require multiple teams to coordinate on every release of a service. OR a single team is assigned more bounded contexts than the cognitive-load heuristic allows with no acknowledgment. |

---

### CL-06 — Operability and Observability

*Is the system designed to be run? Are the three observability pillars, health/readiness, and graceful degradation present?*

| Score | Anchor (frozen) |
|-------|-----------------|
| **1.0** | Structured logs, metrics (RED: Rate, Errors, Duration), and distributed traces with a correlation ID strategy are designed in (not "we'll add monitoring later"). Every service exposes a health and readiness endpoint. Runbook-able failure modes are called out (what breaks, how to detect, how to recover). Each quantum is independently automatable-deployable (no manual steps). Graceful degradation paths are named for every critical scenario (what the user sees when a dependency is down). |
| **0.5** | Most pillars are addressed, but one is missing or only aspirational ("we intend to add tracing"). OR health/readiness exists but the readiness probe logic isn't specified (always-ready defeats the purpose). OR graceful degradation is described for the happy path but not for the 1–2 highest-risk dependency failures. |
| **0.0** | Observability is absent or deferred with no design decision — "we'll add monitoring." OR there are no health endpoints and no failure-mode runbook. OR the deployment model requires coordinated manual steps across services. |

---

### CL-07 — Sustainability

*Where sustainability is a stated driver, is an SCI estimate present and are carbon-aware design choices considered?*

| Score | Anchor (frozen) |
|-------|-----------------|
| **1.0** | An SCI (Software Carbon Intensity, ISO/IEC 21031:2024) estimate per functional unit is present, with sources cited for embodied carbon where material. Carbon-aware design choices are documented (demand shaping, time/region shifting, right-sizing). Uncertainty is flagged where embodied-carbon data is unavailable. |
| **0.5** | Sustainability is acknowledged as a driver and at least one design choice is made with carbon in mind (e.g. region selection, instance right-sizing), but no SCI estimate is attempted and no uncertainty is flagged. |
| **0.0** | Sustainability is a stated project driver, yet the architecture document contains no mention of it — no estimate, no design choices, no acknowledged deferral. (If sustainability is NOT a stated driver, score this dimension N/A and omit it from the mean.) |

---

### CL-08 — Tradeoff Honesty

*Does every significant decision record what it costs on the other attributes and what alternatives it beat?*

| Score | Anchor (frozen) |
|-------|-----------------|
| **1.0** | Every architecture decision of material impact (style selection, data-store choice, communication pattern, a named tradeoff point from the ATAM walk) has a corresponding ADR that names (a) what the chosen option costs on the opposing attribute(s), and (b) what each rejected alternative was better at. "Upside-only" rationale — recording only why the chosen option is good — scores no higher than 0.5. |
| **0.5** | Most decisions have ADRs with tradeoffs, but 1–2 significant decisions have "alternatives considered: none" or list alternatives without naming what each was better at. |
| **0.0** | ADRs are absent for significant decisions, OR the ADRs present record only the winning option's merits with no cost and no rejected-alternatives reasoning. This is the cardinal craft failure: the rationale, not just the decision, is the deliverable. |

---

## 3. Voiding Rule

**A soft score is void if it carries no typed evidence pointer.** Void scores are not zeroes — they are excluded from the dimension mean and flagged as a coverage gap: `VOID: CL-<NN> — no typed evidence pointer; excluded from mean`. A report with more than one void dimension does not satisfy the evaluator's stop criterion (all dimensions scored); the evaluator must make another pass or declare that the evidence cannot be located and the score is irresolvable.

The voiding rule applies to all five pointer kinds equally. An evaluator may cite more than one pointer per score (a DDQ and a CML together is stronger than either alone), but one valid pointer is the minimum. Impressions, summaries, and references to "the design" without a locator are not pointers.

---

## 4. Calibration to Human / Reference Scores

Calibration prevents systematic drift — where the evaluator consistently over-scores conceptual integrity or under-scores tradeoff honesty relative to a senior architect's judgment.

### 4.1 Reference set

Maintain a calibration reference set at `docs/architecture/evaluation-calibration/`. Each entry is a historical evaluation with: the candidate document, the human (senior architect) scores per CL dimension with their evidence pointers, and the evaluator's scores for the same document. The reference set starts with ≥ 3 entries before the locked checklist is considered calibrated.

### 4.2 Calibration procedure

Before a new evaluation run (or after any anchor is edited), the evaluator scores one document from the reference set **blind** (without seeing the reference scores). Compute the per-dimension absolute deviation |evaluator − human|. A dimension is miscalibrated if deviation ≥ 0.5 across two or more reference documents. Miscalibration triggers an anchor review: read the anchor at the score boundary and tighten the description until the ambiguity that caused the deviation is closed.

### 4.3 Recalibration triggers

- Any edit to a frozen anchor description in §2 above — version-bump this file and run the calibration procedure before using the new anchors in a live evaluation.
- A dimension that receives a 0.5 score in ≥ 60% of evaluated documents — the 0.5 anchor is too wide; tighten it.
- A dimension that receives no scores below 0.5 across 10+ evaluations — either the designs being reviewed are uniformly excellent (confirm with human) or the 0.0 anchor is set too low; investigate.

### 4.4 Calibration output format

```
Calibration run: <date> · Document: <doc-name> · Evaluator: <model-id>
| Dimension | Human | Evaluator | |Δ| | Evidence match |
|-----------|-------|-----------|-----|----------------|
| CL-01     | 0.5   | 1.0       | 0.5 | MISMATCH — anchor ambiguity at 0.5/1.0 boundary |
| CL-02     | 1.0   | 1.0       | 0.0 | OK |
…
Result: <CALIBRATED | MISCALIBRATED — trigger anchor review on CL-NN>
```

---

## 5. Integration with the Broader Evaluation Process

This protocol is a **sub-protocol of `evaluation-method.md`** — it governs the evidence and scoring mechanics that `evaluation-method.md §Evaluator discipline` references as "the locked checklist." The call sequence is:

1. Hard oracles (`quality-attribute-rubric.md §Hard oracles`) — run first; any failure blocks before soft scoring begins.
2. Soft scoring (this file) — per-criterion, per-quantum, one call per CL dimension. Each call produces `{criterion, quantum, score, evidence_pointer(s), rationale}`.
3. Mean check — after all dimensions are scored (no voids), compute the mean. Mean ≥ 0.8 passes the soft-oracle gate per `quality-attribute-rubric.md §Soft oracles`.
4. Output — the evaluator emits the full scorecard: dimension scores with pointers, the mean, any voids, and the pass/fail verdict. Findings at or below 0.5 on any dimension are escalated as advisory findings in `finding-schema.md` format (`oracle:"soft"`).
5. Revise loop — if a revise is triggered, it may only re-close after an FFR-kind pointer (an executable hard oracle passes) or a human decision (`evaluation-method.md §External-signal gate`). The evaluator's own re-score is not an external signal.
