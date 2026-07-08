# Risk Register & Risk-Driven Effort Gate

The risk register is the architect-agent fleet's forcing function for *proportionate* evaluation effort. Drawing on Fairbanks' *Just Enough Software Architecture* — the core insight that architecture work should be calibrated to the risk it retires — and the RAID (Risks, Assumptions, Issues, Dependencies) model, this contract defines the canonical risk object the fleet populates, the likelihood×impact matrix that governs severity, the disposition taxonomy, and the gate rule that routes each risk to the correct evaluation method from `evaluation-method.md`. The register is not a compliance artifact; it is the mechanism that prevents both over-engineering (running full ATAM on a reversible decision) and negligence (a single ADR on a bet-the-system one-way door). Every risk object in a flow's output is typed against the schema below; every evaluation-method selection is justified by citing the register's highest-impact items.

---

## 1. The Risk Object

Each risk identified by any fleet flow is serialised as:

```json
{
  "id": "RISK-<DOMAIN>-<NNN>",
  "description": "<one sentence — the uncertain event or condition and its architectural locus>",
  "likelihood": "H | M | L",
  "impact": "H | M | L",
  "severity": "<derived from matrix — see §2>",
  "disposition": "accept | mitigate | transfer | avoid",
  "qas_ref": "<QAS-id(s) or constraint id this risk threatens — required>",
  "one_way_door": true,
  "open": true,
  "mitigation_note": "<if disposition=mitigate: the structural control or ADR that addresses it; if accept: the rationale>",
  "finding_ref": "<ARCH-<FLOW>-<NNN> from finding-schema.md if a finding was raised for this risk>"
}
```

**Field rules:**

- **`id`**: `RISK-` + a short domain token matching `finding-schema.md`'s `type` vocabulary (e.g. `RISK-AVAIL-001`, `RISK-SEC-003`, `RISK-DATA-002`) + zero-padded counter.
- **`description`**: names the *uncertain event* (what could go wrong), not the solution — e.g. "Postgres single primary: no standby → unbounded RTO on primary failure" not "we need a replica."
- **`likelihood` / `impact`**: each `H`, `M`, or `L`. Likelihood is the assessed probability of the event occurring given the current architecture; impact is the consequence severity against the system's quality-attribute drivers. Both must be grounded in a structural or operational fact, not intuition (e.g. "L because the component is behind a circuit breaker with a tested fallback").
- **`severity`**: derived from the likelihood×impact matrix (§2) — do not set independently.
- **`disposition`**: one of the four canonical RAID dispositions:
  - **accept** — the cost of mitigation exceeds the expected loss; the risk is consciously held. Requires an explicit rationale and a monitoring trigger.
  - **mitigate** — a structural control, pattern, or constraint reduces likelihood or impact to an acceptable level; cite the ADR or mechanism.
  - **transfer** — moved to another party (an SLA, insurance, a managed service's availability guarantee). The transfer target must be named.
  - **avoid** — the architectural decision that would create the risk is not taken; the driver is satisfied a different way.
- **`qas_ref`**: required. A risk with no quality-attribute scenario or constraint it threatens is not a risk — it is an opinion. Cross-references `00-drivers/quality-attribute-scenarios.md`.
- **`one_way_door`**: `true` if the decision that creates or forecloses this risk is difficult or costly to reverse (switching a data-store engine, choosing an event-sourcing model, committing to a choreography-first topology). One-way-door risks are always escalated to at least Lightweight-ATAM regardless of likelihood×impact score (§4).
- **`open`**: `true` until a disposition of accept or avoid is recorded, or a mitigating ADR is accepted and verified. Closed items (`open: false`) are retained for traceability — they are the audit trail that a risk was *considered*, not just never raised.
- **`mitigation_note`**: required when `disposition ≠ accept`; references the ADR id or the named pattern (e.g. "ADR-0011 — outbox + CDC removes the dual-write; converts this to at-least-once delivery with idempotent consumer").
- **`finding_ref`**: cross-links to the `finding-schema.md` object for the same issue when a formal finding was raised. A risk may exist in the register without a finding (accepted risks, early-design unknowns); a finding of `type:"risk"` must have a corresponding register entry.

---

## 2. Likelihood × Impact Matrix

Severity is a function of both axes. The nine-cell matrix collapses to three fleet-actionable bands:

| | Impact H | Impact M | Impact L |
|---|---|---|---|
| **Likelihood H** | **Critical** | **High** | Medium |
| **Likelihood M** | **High** | Medium | Low |
| **Likelihood L** | Medium | Low | Low |

- **Critical** (H×H): blocks release of the affected architecture quantum; requires a mitigation ADR before the design is considered complete. Always triggers at minimum a Lightweight-ATAM pass.
- **High** (H×M or M×H): significant — requires explicit disposition + mitigation note. One-way-door status escalates to full ATAM regardless.
- **Medium** (H×L, M×M, L×H): review and disposition; accept is permissible with a monitoring trigger named.
- **Low** (M×L, L×M, L×L): record and accept unless a mitigation is cheap; no evaluation escalation.

---

## 3. Disposition Taxonomy (RAID-aligned)

The four dispositions correspond to the canonical RAID risk-response strategies:

| Disposition | When to use | What the register must carry |
|---|---|---|
| **accept** | Cost of control > expected loss; driver does not demand the scenario be bulletproofed | Explicit rationale + a named monitoring trigger (metric, alert, or review cadence) |
| **mitigate** | A structural control reduces likelihood or impact to the next-lower band | ADR id or named pattern; the *residual* likelihood×impact after the control |
| **transfer** | A third-party SLA, managed service, or insurance absorbs the impact | Named transfer target; evidence the SLA covers the driver's response measure |
| **avoid** | The triggering decision is not made; an alternative architectural direction is chosen | The ADR that records the rejected option and the chosen direction |

A risk disposition of **mitigate without a named control** is not a disposition — it is a wish. The `mitigation_note` must name a concrete structural mechanism (pattern, ADR, fitness function) or the risk remains `open`.

---

## 4. The Risk-Driven Effort Gate

This gate answers: *which evaluation method does this risk justify?* It is the entry-condition rule for `evaluation-method.md`'s lightweight menu. Evaluate it before committing to any evaluation path.

### Step 1 — Populate (or refresh) the register

Before selecting a method, the `architecture-evaluator` (or the `solution-architect` during design) reads:
1. `constraints-assumptions-risks.md` (project-level C/A/R log — the RAID inputs).
2. The current `risk-register.md` snapshot (this file's running instance in `architecture/<slug>/`).
3. Any `type:"risk"` findings from prior audit flows.

New risks from the current analysis are added; stale risks whose disposition is verified are closed.

### Step 2 — Identify the gate criteria

Two criteria escalate evaluation effort independently; *either* alone is sufficient:

**Criterion A — Severity band of open risks**

| Highest open severity | Minimum method |
|---|---|
| Critical | Lightweight-ATAM (or full ATAM if ≥ 2 Critical items or one-way-door) |
| High | Lightweight-ATAM |
| Medium | Single ADR per decision |
| Low | Single ADR or inline tradeoff note |

**Criterion B — One-way-door flag**

Any open risk with `one_way_door: true` triggers **at minimum Lightweight-ATAM** regardless of severity band. A one-way-door decision with Critical severity triggers **full ATAM + CBAM** unless the stakeholder group explicitly accepts the lighter path and records the rationale.

### Step 3 — Select from the evaluation menu

Map the result of Step 2 to `evaluation-method.md`'s lightweight menu:

| Gate outcome | Evaluation method |
|---|---|
| All open risks Low, no one-way doors | **Single ADR** with tradeoff recorded |
| Any Medium open risk OR one-way-door (any severity) | **Lightweight-ATAM** (Mini-ATAM, internal team, bounded `(H,*)` scenario set) |
| Any High open risk | **Lightweight-ATAM**; escalate to full ATAM if one-way-door also present |
| ≥ 1 Critical open risk OR one-way-door + High | **Full ATAM** (multi-stakeholder, complete utility tree); CBAM when two compliant options exist and cost differs |
| Evaluating an *implemented* system (not a design) | **TARA** / metric + fitness-function scan regardless of register state |
| A pattern/style choice with bounded scope | **PBAR** against `80-patterns/`; escalate per above if risks are High+ |

### Step 4 — Document the gate decision

Record the gate outcome in the evaluation report or ADR:

```
Risk-gate: highest open severity = <band>; one-way-door = <true|false>
→ Selected method: <method name from evaluation-method.md>
→ Justification: <cite the register items that drove the selection>
```

This trace is mandatory. A method selection with no gate justification fails the `driver_ref` rule in `finding-schema.md` (the evaluation choice is itself an architectural decision that must be grounded).

---

## 5. Entry Conditions — When ATAM/CBAM Run

Full ATAM and CBAM are resource-intensive; running them outside their justified band wastes stakeholder time and degrades adoption (the over-process failure mode named in `evaluation-method.md`). Entry conditions are strict:

**Full ATAM runs only when:**
- The register contains ≥ 1 Critical open risk, OR
- The register contains ≥ 1 one-way-door risk AND it is High or Critical severity, OR
- The decision scope covers a bet-the-system platform choice or a boundary that will be costly to redraw.

**CBAM runs only when:**
- Full ATAM is already justified (see above), AND
- Two or more candidate architectures both satisfy the drivers (the choice is a cost-vs-benefit tradeoff among compliant options, not a functional gap).

**Lightweight-ATAM runs when:**
- Any open risk is High or above, OR
- Any one-way-door risk is present (any severity), OR
- A screen/subsystem is being evaluated with limited stakeholder availability (the default for most sprint-level decisions).

**Single ADR runs when:**
- All open risks are Low or Medium and no one-way doors, AND
- The decision is bounded and reversible.

A run that applies full ATAM below the High threshold is flagged as over-process (a soft finding). A run that applies a single ADR to a one-way-door Critical risk is flagged as under-process (a hard finding — it violates the `evaluation-method.md` risk-driven gate).

---

## 6. Cross-References

| Reference | What it provides |
|---|---|
| `constraints-assumptions-risks.md` | Project-level RAID inputs; source of initial risk population and constraint context |
| `evaluation-method.md` | The lightweight-menu table this gate selects from; the full ATAM, CBAM, Lightweight-ATAM, and ADR method descriptions |
| `finding-schema.md` | The `type:"risk"` finding object; the `severity` vocabulary (critical/major/minor) — note the register uses likelihood×impact-derived severity bands, which the evaluator maps to finding severity when raising a formal finding |
| `quality-attribute-rubric.md` | The hard and soft oracles the register's `qas_ref` items are scored against |
| `00-drivers/quality-attribute-scenarios.md` | The canonical QAS ids used in `qas_ref` fields |
| `adr-template.md` | The ADR format that records a `mitigate` or `avoid` disposition's chosen direction and rejected alternatives |
