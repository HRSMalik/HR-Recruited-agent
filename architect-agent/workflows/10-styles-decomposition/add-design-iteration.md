# add-design-iteration

**Group:** 10-styles-decomposition · **Runs as:** subagent: ../.claude/agents/solution-architect.md · **Mode:** audit + design · **Default model:** sonnet

## Purpose

Run the **SEI ADD 3.0 (Attribute-Driven Design) generative loop** — the structured, driver-prioritized method that ATAM lacks: pick a driver, choose a design concept, instantiate elements, sketch the view, review against the driver, iterate. Answers one question per iteration: *given the next-priority unaddressed driver, what design concept (pattern / tactic / externally-developed component) satisfies it at an acceptable tradeoff, and what elements does that concept introduce?* ADD 3.0 is generative where ATAM is evaluative — it produces the architecture, element by element, traceable to the driver backlog; ATAM then scores the result. No element is introduced without a named driver, and no iteration runs without evaluating ≥2 design concepts before selecting one.

## Inputs & preconditions

- From `project-architecture-config.md`: the existing stack and deployment target, scale/SLO targets, compliance regime, team topology, constraints, and the location of the architecture description and ADR log.
- The **prioritized driver backlog** — the utility tree from `../00-drivers/quality-attribute-scenarios.md`: every leaf is a prioritized 6-part quality-attribute scenario with a response measure and a `(business value, technical risk)` rank. ADD works through the backlog ordered by `(H,H)` first; no drivers → no iteration → downgrade scope to `status:error` and say so.
- The **design backlog** — the open design decisions from prior ADD iterations or from `architecture/<slug>/design-backlog.md` (created in the first iteration if absent). Each entry names: the driver it targets, the elements it has already instantiated, and the open sub-decisions deferred.
- The **current architecture description** — the existing C4 context/container view and any prior ADRs in `architecture/<slug>/adr/`, so new elements are placed coherently and no decision already settled is reopened.
- Preconditions: the utility tree exists and every targeted leaf is 6-part with a measurable response measure; the architecture description (even a stub) is present; the design-backlog entry for this iteration names a specific driver. If any precondition is absent, surface the gap as an open driver question — do not invent a driver or a response measure.

## Oracle (source of truth)

The prioritized 6-part quality-attribute scenarios from `../00-drivers/quality-attribute-scenarios.md` and the ADD 3.0 structural rules (Cervantes & Kazman, *Designing Software Architectures: A Practical Approach*, 2016). The oracle for each iteration is: the selected design concept meets the targeted driver's response measure, every element introduced is traceable to the driver that demanded it, and the decision is recorded as a complete ADR.

**hard:**
- **Driver targeted and traceable.** Each ADD iteration explicitly names the driver (`QAS-*` leaf) it targets; every element instantiated in the iteration traces to that driver and that driver only — no element appears without a cited driver. An element with no driver is accidental complexity and blocks (`oracle:"hard"`, `type:"decomposition"`).
- **≥2 design concepts evaluated before selection.** For every iteration, the `architecture-explorer` produces ≥2 genuinely different design concepts — a pattern, a tactic, an externally-developed component (EDC), or a reference architecture — each as a concrete one-page spec (the concept, the elements it introduces, its known guarantees and failure modes). The evaluator scores each against the targeted driver's response measure and the full utility tree's tradeoff surface. A single-option iteration is not ADD — it blocks.
- **Decision recorded as an ADR.** The selected concept is documented as a complete MADR ADR (`../shared/adr-template.md`): context · ≥2 considered concepts · decision · positive AND negative consequences · `driver_ref` pointing at the `QAS-*` leaf. Missing context, missing alternatives, missing negative consequences, or an untraced driver_ref fails `adrs_complete`.
- **Design backlog updated.** After each iteration the design backlog (`architecture/<slug>/design-backlog.md`) is updated: the addressed driver is marked resolved, any sub-decisions deferred (deferred backlog items) are added with the driver they serve and the reason for deferral. A backlog that does not shrink — or that introduces new items with no driver — blocks.
- **No fallacy violations on the introduced elements.** Any element that crosses a network/process boundary is checked against the 8 fallacies of distributed computing (`../shared/fallacies-and-tradeoffs.md` §1–8): every such call must have a bounded timeout, a retry policy, and a fallback path recorded; an unbounded synchronous chain is a hard finding.

**soft:**
- **Driver-priority order.** Iterations run `(H,H)` → `(H,M)` → `(H,L)` → `(M,H)` → … from the utility tree; departing from this order (e.g. picking an `(M,L)` driver when an `(H,H)` leaf is still open) is a soft finding unless a concrete dependency or risk justifies the reorder.
- **Reuse over invention.** Design concepts are drawn from the established pattern catalog (`../80-patterns/`), the cloud-design-pattern catalog, the EIP catalog, or the resilience-pattern catalog before a bespoke mechanism is proposed. A bespoke mechanism introduced where a named pattern would serve is a soft finding (unjustified novelty, penalized per the rubric). The existing stack's idioms (`project-architecture-config.md`) are the first choice.
- **Right-sized concepts.** The *simplest concept that meets the driver's response measure* wins; an elaborate concept whose benefits no response measure buys is penalized by the `architecture-evaluator` (the rubric's accidental-complexity guard). An EDC (e.g. a managed cache, a message broker) is proposed only when a tactic applied to existing elements cannot meet the measure.

## Standards & techniques

- **SEI Attribute-Driven Design 3.0 — the 7 steps** (Cervantes & Kazman, 2016): (1) review the inputs — the utility tree, existing design, constraints; (2) establish the iteration goal — pick the highest-priority unaddressed driver; (3) choose one or more elements to decompose — the part of the current design that must change to serve the driver; (4) choose a design concept — a pattern, tactic, or EDC that addresses the driver; (5) instantiate elements and allocate responsibilities — name the elements, their interfaces, and the responsibilities the concept allocates; (6) sketch the views and record design decisions — a C4-level sketch (C4 Container or Component) and the ADR; (7) perform analysis of current design and review iteration goal — does the concept meet the response measure? what's open? update the backlog.
- **Driver-prioritized iteration** — the utility tree `(business value, technical risk)` rank is the iteration schedule. `(H,H)` scenarios are architectural risk — they get first attention; `(L,L)` are noise — they wait or are closed by a satisfied concept from a higher-priority iteration.
- **Design concepts taxonomy** (ADD 3.0 vocabulary):
  - **Patterns** — named, reusable structural solutions with known tradeoffs (Layer, Broker, MVC, CQRS, Saga, Outbox, Sidecar, BFF, Strangler Fig…) — drawn from the fleet's `../80-patterns/` catalog.
  - **Tactics** — atomic design decisions that directly improve a single quality attribute (e.g. *active redundancy* for availability, *increase resources* for performance, *encrypt data at rest* for security, *parameterize* for modifiability) — from the SEI tactics catalogs per attribute.
  - **Externally-developed components (EDCs)** — off-the-shelf components, frameworks, or managed services (a managed Redis, an API gateway, a CDN, a message broker, an identity provider) that carry the concept's guarantees as their contract.
  - **Reference architectures** — validated whole-system templates (the AWS Well-Architected reference architecture for a given workload pattern, TOGAF building blocks) adopted as a starting shape.
- **The design backlog** — the ordered list of unresolved driver+decision pairs carried from iteration to iteration. ADD 3.0's backlog is the mechanism that prevents untracked scope creep: every deferred sub-decision is a backlog entry, every resolved entry names the ADR that closed it.
- **Cross-reference to ATAM** — ADD generates the architecture; ATAM (in `../60-evaluation/architecture-evaluation-atam.md`) then evaluates it. This flow runs *before* the ATAM evaluation flow on the same design scope. The `(H,H)` scenarios that ADD must address are the same ones ATAM will stress-test.
- **One-way vs two-way-door classification** (Bezos): classify each design concept selection before the ADR is written — a pattern/tactic that can be swapped later (two-way door) gets a bare/minimal ADR; a structural commitment that re-architecture would reverse (one-way door) earns a full MADR ADR flagged `One-way door? yes`.

## Step sequence

**audit:** Read the existing architecture description and ADR log → identify any elements already present that lack a `driver_ref` (untraced elements) → check the design backlog for entries with no driver, stale entries that were never addressed, or iterations that introduced elements without a recorded ADR → check for ADD-rule violations: iterations that selected a concept without evaluating ≥2 alternatives, or elements that crossed a trust/process boundary without a failure-mode record → emit findings (`type:"decomposition"`; `oracle:"hard"` for untraced elements / missing ADR / single-concept selection; `oracle:"soft"` for out-of-priority-order iterations / unjustified novelty) + the risk register. Read-only — authors nothing.

**design:**
1. **Frame** (read-only) — Confirm the utility tree is present and every targeted leaf is 6-part with a measurable response measure; read the design backlog and current architecture description; identify the highest-priority unaddressed `QAS-*` driver for this iteration; confirm the elements to decompose. If the utility tree is absent or the targeted driver has no response measure, stop with `status:error` and name the gap.
2. **Explore** (read-only, `architecture-explorer` ×N) — Produce ≥2 genuinely different design concepts for the targeted driver: each is a concrete one-page spec naming the concept type (pattern / tactic / EDC / reference architecture), the elements it introduces, the interfaces/responsibilities it allocates, its known guarantee (the response measure it meets), and its known failure modes and tradeoffs. Concepts must be substantively different — not the same mechanism relabeled. Where the concept involves a network/process boundary, the spec states the timeout, retry, and fallback.
3. **Evaluate** (read-only, `architecture-evaluator`) — Score each concept against (a) the targeted driver's response measure — does the concept's known guarantee or capacity model prove the measure is met? — and (b) the full utility tree's tradeoff surface — what does the concept cost on other `(H,*)` drivers? Identify **sensitivity points** (properties on which the response measure hinges, e.g. "cache hit-rate below 80% blows the p99 budget"), **tradeoff points** (the concept improves the targeted driver but worsens a second `(H,*)` driver — name both), and **risks** (ways the concept could fail to meet the measure in practice). Order-swap the concepts and re-evaluate to kill position bias. Apply style normalization (strip formatting/length from specs before judging). Pick the winning concept and explicitly graft any superior sub-ideas from the runners-up where they don't break conceptual integrity.
4. **Document** (ONE writer, `solution-architect`) — Instantiate the winning concept: name every element introduced, assign responsibilities, and produce (a) a C4-level sketch (Container or Component per scope) in `architecture/<slug>/diagrams/` using diagrams-as-code (`.puml` or Mermaid), (b) a complete MADR ADR in `architecture/<slug>/adr/NNNN-<slug>.md` with `driver_ref` → `QAS-*`, `One-way door?` classified, ≥2 options, decision, positive AND negative consequences, and the confirmation/fitness-function; (c) update `architecture/<slug>/design-backlog.md` — mark the targeted driver resolved, add any deferred sub-decisions as new entries with their driver and reason. Update `architecture/<slug>/design-doc.md` with the new elements and their responsibilities. Never scatter artifacts outside `architecture/<slug>/`.
5. **Verify** — Check: every element introduced names its driver (`driver_ref` non-empty); the ADR is complete (context · ≥2 options · decision · positive + negative consequences · driver_ref); the design backlog was updated (targeted driver resolved, deferrals recorded with driver refs); the C4 sketch compiles (`.puml` passes `plantuml -syntax` / Mermaid passes `mmdc --dry-run`); any cross-boundary call has a bounded timeout + retry + fallback in the ADR or the design-doc; the `architecture-evaluator` re-scores the authored artifacts (not the prose) against the targeted driver's response measure — must score `met`; loop ≤10 iterations or pass.

## Assertions & exit gate

- Every element introduced in the iteration names the `QAS-*` driver it satisfies; zero elements have no `driver_ref`.
- The iteration evaluated **≥2 design concepts** before selection; the rejected concepts and their disqualifying tradeoffs are named in the ADR's `Pros and cons` section.
- The ADR is complete per `../shared/adr-template.md`: context · ≥2 considered options · decision · positive AND negative consequences (both mandatory) · `driver_ref` tracing to a real utility-tree leaf · `One-way door?` classified.
- The design backlog (`architecture/<slug>/design-backlog.md`) is updated: the targeted driver is resolved; every deferred sub-decision carries a `driver_ref` and a reason.
- The C4 sketch compiles without errors.
- Any cross-boundary element has a bounded timeout, retry policy, and fallback recorded.
- The `architecture-evaluator` independently scores the authored artifacts and returns `met` for the targeted driver's response measure.
- The full utility tree's tradeoff surface is surveyed: the winning concept's cost on every other `(H,*)` driver is stated (even if the answer is "no impact"), not silently omitted.
- **Gate:** hard oracles green (driver-traced elements · ≥2 concepts evaluated · complete ADR · backlog updated · diagrams compile · cross-boundary failure paths defined · evaluator scores targeted driver `met`) AND (design) rubric mean ≥ 0.8 — where driver traceability and tradeoff honesty are the load-bearing soft scores.

## Output

Write `artifacts/add-design-iteration/report.json` per `shared/report-format.md` — `drivers[]` (the targeted `QAS-*` leaf for this iteration plus the full backlog state), `findings[]` per `finding-schema.md` (`type:"decomposition"`; `oracle:"hard"` for untraced elements / missing ADR / single-concept selection / uncompilable diagram / undefined failure path; `oracle:"soft"` for out-of-priority-order / unjustified novelty / concept over-complexity), `decisions[]` pointing at the authored ADR, and the `verification` block:

```json
{
  "flow": "add-design-iteration",
  "mode": "audit | design",
  "status": "pass | fail | error",
  "scope": "<system/subsystem and the driver targeted this iteration>",
  "drivers": [
    { "id": "QAS-PERF-01", "attribute": "Performance Efficiency", "response_measure": "p99 ≤ 200ms at peak", "priority": "H/H", "status": "targeted-this-iteration | open | resolved" }
  ],
  "findings": [ /* finding objects per finding-schema.md */ ],
  "decisions": [
    { "adr": "ADR-0012", "title": "Read-replica + connection-pool for dashboard latency", "driver_ref": "QAS-PERF-01", "one_way_door": false, "status": "accepted" }
  ],
  "verification": {
    "artifacts": [
      "architecture/<slug>/adr/0012-read-replica-dashboard.md",
      "architecture/<slug>/diagrams/c4-component-dashboard.puml",
      "architecture/<slug>/design-backlog.md"
    ],
    "traceability": { "elements_introduced": 3, "elements_with_driver_ref": 3, "orphan_elements": 0 },
    "concepts_evaluated": 2,
    "fitness_functions": [
      { "name": "diagram-compile-c4-component-dashboard", "result": "pass" },
      { "name": "cross-boundary-failure-paths-defined", "result": "pass" },
      { "name": "targeted-driver-response-measure-met", "result": "modeled-pass" }
    ],
    "hard_oracles": {
      "driver_traced": "pass",
      "concepts_ge_2": "pass",
      "adrs_complete": "pass",
      "backlog_updated": "pass",
      "diagrams_compile": "pass",
      "failure_paths_defined": "pass",
      "evaluator_scores_met": "pass"
    },
    "rubric_score": 0.84
  },
  "gate": { "name": "hard_oracles_green_and_rubric>=0.8", "passed": true },
  "notes": ["open backlog items with driver refs", "one-way-door decisions flagged", "deferred sub-decisions and reason"]
}
```

Authored artifacts land in `architecture/<slug>/` per `project-architecture-config.md`: the ADR in `adr/NNNN-<slug>.md`, the C4 sketch in `diagrams/`, the updated design backlog in `design-backlog.md`, and new elements folded into `design-doc.md`. The design backlog state (resolved / open / deferred entries with driver refs) is listed in `notes[]`. Audit mode authors nothing — findings + risk register only.

## Guardrails

Per `shared/guardrails.md`: **propose the design concept and its tradeoffs, never write product code or apply infra** — the controller builds the selected concept, the operator deploys it. **No element without a driver** — every element introduced in the iteration traces to the `QAS-*` leaf it satisfies; accidental complexity is a hard finding. **≥2 concepts evaluated before selection** — a single-option iteration is not ADD; the evaluator must score alternatives and name what each was better at before the writer documents the winner. **Reuse known patterns and tactics first** (`../80-patterns/`, EIP catalog, SEI tactics catalogs, cloud-design-pattern catalog) before proposing a bespoke mechanism or a new EDC; unjustified novelty is penalized. **One writer preserves conceptual integrity** — the `architecture-explorer` instances and the `architecture-evaluator` are read-only; exactly one `solution-architect` authors the ADR, diagram, and backlog update. **Record the tradeoff and the rejected concepts** — the ADR's `Pros and cons` section and `alternatives_rejected` in the finding are half the record's value. **Honor the 8 fallacies** on every cross-boundary element introduced (`../shared/fallacies-and-tradeoffs.md`). Cross-reference `../00-drivers/quality-attribute-scenarios.md` (the driver backlog), `../60-evaluation/architecture-evaluation-atam.md` (the evaluation method that scores the result of ADD), and `../shared/adr-template.md` (the decision record shape).
