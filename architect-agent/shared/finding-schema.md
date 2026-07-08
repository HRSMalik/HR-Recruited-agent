# Architecture Finding / Recommendation / Risk Schema

Every issue an architecture flow reports uses this object — machine-readable (gate), human-readable (review), and traceable to a **driver** (the quality-attribute scenario or constraint it serves) and a **component/decision**. An architecture finding is a *decision with a tradeoff*, not an opinion.

```json
{
  "id": "ARCH-<FLOW>-<NNN>",
  "type": "driver | decomposition | data | integration | scalability | availability | performance | security | privacy | observability | cost | operability | evolvability | compliance | documentation | risk",
  "severity": "critical | major | minor | cosmetic",
  "oracle": "hard | soft",
  "driver_ref": "QAS-AVAIL-02 (RTO ≤ 5 min on order-service failover)",
  "iso25010": "Reliability › Recoverability",
  "component": "order-service / payments boundary",
  "decision_ref": "ADR-0007 (saga over 2PC for checkout)",
  "issue": "<one sentence — what's wrong vs the driver/standard, or the decision being made>",
  "evidence": "<the traced driver + the structural/measured fact: 'order-service has a single Postgres primary, no read-replica/failover → RTO unbounded vs QAS-AVAIL-02'>",
  "tradeoff": "<what this costs on other attributes — e.g. 'adding a standby replica raises cost ~18%/mo and adds failover complexity; buys RTO 5→1 min'>",
  "alternatives_rejected": "<the options considered and why not — e.g. 'multi-region active-active rejected: 3× cost, not required by any driver'>",
  "recommendation": "<the concrete decision, ADR-shaped: pattern/topology/tech + the response-measure it now meets>",
  "status": "open"
}
```

**Rules**
- **`id`**: `ARCH-` + flow short-code + counter (e.g. `ARCH-AVAIL-003`, `ARCH-DATA-001`, `ARCH-SEC-002`, `ARCH-WARD-001` for Wardley-map evolution-gap and inertia findings from `shared/wardley-map-template.md`).
- **`oracle`**: `hard` = deterministic gate failure — an un-traced ASR, a scenario with no met response-measure, an un-accepted SPOF, a cross-service call with no timeout/retry/fallback, an unstated consistency model on a write path, a violated fallacy of distributed computing, a missing STRIDE control on a trust boundary, a diagram that doesn't compile, an ADR missing context/options/consequences, unbounded cost. `soft` = rubric/craft judgement (simplicity, conceptual integrity, evolvability, right-sized coupling). Hard findings block; soft findings are advisory above the rubric threshold.
- **`driver_ref`** required for every non-documentation finding — name the quality-attribute scenario (`QAS-…`) or the constraint the finding serves. A finding with **no driver is not a finding** — it's a preference; either tie it to an attribute the system must satisfy or drop it. `iso25010` names the ISO/IEC 25010 quality characteristic for cross-referencing.
- **`evidence`** mandatory — the traced driver + the structural or measured fact (a topology fact, a capacity number, a missing failure path, a flame-of-blast-radius). "Best practice says so" is **not** evidence; the driver it protects is.
- **`tradeoff` + `alternatives_rejected`** mandatory on every `design`/decision finding — an architecture recommendation that doesn't state what it costs and what it beat is incomplete (that is the whole job). An audit finding may carry a lighter `tradeoff` but still names the cost of the fix.
- **`recommendation`** is ADR-shaped: name the pattern / topology / technology and the response-measure it now satisfies, e.g. "introduce an outbox + CDC to remove the dual-write between `order` and the event bus → at-least-once delivery, idempotent consumer; rejects 2PC (latency) and dual-write (lost events)".
- A **risk** (`type:"risk"`) is a finding whose `recommendation` is "accept / mitigate / monitor" rather than a structural change — it carries `severity` = likelihood×impact and names the scenario it threatens.

## Audit output (a flow that reviews rather than designs)
Group findings by `type` then `severity`; return a prioritized list (critical → cosmetic) plus a **risk register** (the `type:"risk"` items) with likelihood×impact. A review flow returns findings + risks only (read-only) — it never authors the artifact or edits source. The controller decides which to act on.
