# ADR Template — Architecture Decision Record (MADR)

Every architecturally-significant decision is recorded as an ADR. An ADR captures the **decision, its drivers, the options considered, and the consequences** — the *why* that outlives the diagram. Based on **MADR 4.0.0** (the format renamed "Markdown *Any* Decision Records") and Michael Nygard's original ADR pattern. One decision per file; ADRs are immutable once `accepted` — you supersede, never edit history.

**MADR 4.x tiers — right-size the record to the decision** (don't force the full template on a two-way door): **full** (all sections — for one-way doors), **minimal** (context · decision drivers · options · outcome · consequences), **bare** (just the decision + consequences), **bare-minimal** (a one-line decision). The risk-driven gate (`evaluation-method.md`) sets the tier: high-risk/irreversible → full; reversible → bare/minimal.

## File & lifecycle conventions
- **Location:** `architecture/<slug>/adr/NNNN-<kebab-title>.md` (per `project-architecture-config.md`; some projects use `docs/adr/`).
- **Numbering:** zero-padded sequential (`0001`, `0002`, …) — never reused.
- **Status lifecycle:** `proposed` → `accepted` → (later) `deprecated` / `superseded by ADR-NNNN`. A rejected option's ADR stays as `rejected` for the record.
- **Immutability:** once `accepted`, the decision is history. A change is a **new ADR** that supersedes the old one (link both ways). This is what makes the log a decision *trail*, not a wiki page.

## The template

```markdown
# ADR-NNNN: <short decision title, e.g. "Saga over 2PC for checkout consistency">

- **Status:** proposed | accepted | rejected | deprecated | superseded by ADR-NNNN
- **Date:** YYYY-MM-DD
- **Decision-makers:** <roles/people>   ← MADR 4.x renamed `Deciders` → `decision-makers`
- **Driver refs:** QAS-AVAIL-02 (RTO ≤ 5 min), QAS-DATA-01 (no lost orders)   ← traces to the utility tree
- **One-way door?** yes | no   ← is this hard to reverse? (sets how much rigor it deserved)

## Context and problem statement
What forces are at play — the drivers (quality-attribute scenarios), the constraints, the assumptions. State the problem as a question: "How should checkout maintain order/payment consistency across two services without a distributed lock?" Name the architecturally-significant requirement(s) this decision must satisfy.

## Decision drivers
- <driver 1 — the scenario/constraint, with its response measure>
- <driver 2 …>
(These are the criteria the options are judged against. Every driver here should appear in the utility tree.)

## Considered options
1. **<Option A>** — one line.
2. **<Option B>** — one line.
3. **<Option C>** — one line.
(At least two genuine options. A decision with one option is not a decision.)

## Decision outcome
**Chosen: <Option B>**, because <it best satisfies the highest-priority drivers — name them — at an acceptable tradeoff>.

**Confirmation:** <how compliance with this decision will be confirmed — the fitness function / conftest policy / contract test / review that enforces it. MADR 4.x renamed "Validation" → "Confirmation"; tie it to an executable gate where possible.>

### Consequences
- **Positive:** <what this buys — the response measures now met>.
- **Negative:** <what this costs — the attributes it worsens, the new complexity, the new failure modes>. *(Mandatory — an ADR with only positive consequences is incomplete.)*
- **Follow-ups / fitness functions:** <the checks to enforce this decision in CI — e.g. "consumer must be idempotent (contract test)", "no synchronous call from order→payment (dependency rule)">.

## Pros and cons of the options
### <Option A>
- Good: … · Bad: … · Tradeoff against drivers: …
### <Option B> (chosen)
- Good: … · Bad: … · Tradeoff against drivers: …
### <Option C>
- Good: … · Bad: … · Tradeoff against drivers: …

## Links
- Supersedes / superseded by: ADR-NNNN
- Related: ADR-NNNN, `architecture/<slug>/design-doc.md`, the QAS in `quality-attributes.md`
```

## Authoring rules (these are the hard-oracle for `adrs_complete`)
- **Context, ≥2 options, decision, and consequences (positive AND negative) are all mandatory.** Missing any one fails the `adrs_complete` hard oracle (`quality-attribute-rubric.md`).
- **Trace to a driver.** `Driver refs` must point at real utility-tree scenarios/constraints. A decision with no driver is accidental complexity — don't write the ADR, remove the decision.
- **Record the rejected options and *why*** — the rejected alternatives are half the value; they stop the team re-litigating settled ground.
- **State the tradeoff**, not just the win — what the chosen option costs on the other attributes.
- **Flag one-way doors.** If the decision is expensive to reverse, say so — it justifies the analysis depth and warns future maintainers.
- **Tooling (optional, soft).** Scaffold with `adr-tools` for consistent numbering/templating; when drafting a new ADR, give the author the **last K≈3 recent ADRs** as context (consistency beats a heavyweight RAG index). A publication site (e.g. Log4brains) is *publish-only* and must never gate (some tools are lightly maintained — wrap in graceful failure).
- Keep it short and durable — an ADR is a record, not an essay. The diagram lives in `diagrams/`; the ADR is the *reasoning*.
