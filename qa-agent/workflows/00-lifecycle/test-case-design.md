# test-case-design

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Derive concrete, traceable test cases from requirements using formal black-box techniques. Answers: "What is the minimal set of cases that covers every input class, boundary, and behavior the requirement defines?"

## Inputs & preconditions
- Required artifacts: testable requirements + acceptance criteria, any data dictionary / field constraints, state diagrams or decision rules where the spec defines them.
- Target: a feature or requirement set; no running SUT needed (design, not execution).
- Preconditions: requirements passed `requirements-review` (testable, ACs present); input domains and valid/invalid ranges are stated.

## Oracle (source of truth)
The requirement plus **ISTQB CTFL v4.0** black-box design techniques and their coverage criteria:
- **Equivalence Partitioning (EP)** — one case per valid and each invalid class.
- **Boundary Value Analysis (BVA)** — min, min−1, min, min+1, max−1, max, max+1 (2- and 3-point).
- **Decision Tables** — one column per feasible condition/action rule combination.
- **State-Transition** — cover all valid transitions (0-switch) and flag invalid ones.
- **Pairwise / combinatorial** — all-pairs coverage to bound the case explosion (e.g. via an orthogonal-array / IPOG generator).
- **t-way combinatorial (3+)** — when 2-way is insufficient, raise interaction strength `t` (3-way, 4-way…) per **NIST SP 800-142, Practical Combinatorial Testing**: empirically most failures are triggered by ≤6 interacting parameters, so a t-way covering array bounds the suite while still hitting every t-parameter value combination. Choose `t` from the requirement's failure-trigger depth, not by default.
- **Cause-effect graphing** — translate the spec's causes (inputs/conditions) and effects (outputs/actions) into a boolean graph with AND/OR/NOT and constraint nodes (E/I/O/R), then derive a decision table from the graph. Use it when conditions combine logically and the plain decision table would miss infeasible/forced combinations.
- **Category-partition / Classification-Tree Method (CTM)** — decompose each input into categories, partition each category into disjoint classes, attach constraints (`[property]`, `[if]`, `[error]`, `[single]`), and take the constrained cross-product as the test frame; CTM is the same idea expressed as a tree whose leaves are the classes. Use it to make the partition structure explicit and the combination rules auditable before generating cases.
- **Approval / characterization testing** — for legacy or under-specified behavior with no written oracle, capture current output as an approved snapshot and assert future runs match it. The approved snapshot becomes the oracle only after a human has *read and confirmed* it against the requirement — see the rubber-stamp guard below.
Coverage is measured against the technique, not against whatever the code happens to accept.

### Per-unit case budget (user-configurable — honor the requested count)

The mandate may set **how many test cases to write per unit** (per endpoint, per screen, per requirement) — e.g. "20 test cases per endpoint". When a count `N` is given, **honor it exactly per unit**:
- **Coverage is the floor, never sacrificed.** First generate the technique-complete set for the unit (every valid+invalid partition, boundary ±1, decision rule, transition, class). If that set already exceeds `N`, do **not** drop coverage to hit `N` — emit all of it and note the unit exceeded the requested budget.
- **Fill the remainder to reach `N`** with additional, non-redundant cases drawn (in priority order) from: extra boundary/near-boundary values, additional invalid-input classes, injection/abuse inputs (oversized, type-confusion, NoSQL/SQL-style, encoding), auth/permission variants, and pairwise/t-way combinations of the unit's parameters. Each filler still carries a requirement-derived expected result — never padding for padding's sake.
- **No count given ⇒** produce the minimal technique-complete set (the default behavior above).
- Record the realized count per unit in the report and in `test-cases.md` (e.g. `endpoint X: 20/20`), so requested-vs-delivered is auditable.

### Rubber-stamp anti-pattern guard (approval/characterization)

An approval test you bless without reading is worthless — it pins *whatever the code did*, including its bugs, and turns the oracle into a tautology. Before any approved snapshot is allowed to act as an oracle:
- A human must read the captured output line-by-line and confirm each value against the requirement — record who approved and against which requirement ID.
- An unreviewed (auto-blessed) snapshot is a **placeholder, not an oracle**: cases backed by it carry lowered confidence and a finding, never a pass.
- Re-approval is required whenever the requirement changes — a stale approval that no longer matches the spec is treated as no oracle at all.
- Characterization tests pin *observed* behavior, so they detect change, not correctness; never let one gate a requirement on its own without the human confirmation step above.

## Step sequence (Plan → Act → Verify)
1. **Plan** — classify each requirement input: bounded numeric/range → BVA+EP; discrete combinations of conditions → decision table; conditions that combine with boolean logic/constraints → cause-effect graph; an input that decomposes into categories→classes → category-partition / CTM; lifecycle/status field → state-transition; many independent parameters → pairwise, escalating to t-way (3+) where the requirement's failure-trigger depth demands it; legacy/under-specified behavior with no written oracle → approval/characterization (snapshot held as a placeholder until human-confirmed). List the partitions, boundaries, rules, transitions, parameter sets + interaction strength `t`, and any snapshots-to-confirm to be covered.
2. **Act** — generate cases one technique at a time: each case gets preconditions, steps, test data, and an **expected result drawn from the requirement** (never from the SUT). Tag every case with its requirement ID for traceability. For category-partition/CTM, emit the test frame as the constrained cross-product of classes; for cause-effect, derive the decision table from the graph. Skip-and-continue if a single requirement lacks a derivable oracle. Approval snapshots are emitted as placeholders pending review, never as passing cases.
3. **Verify** — assert completeness: every valid+invalid partition has a case, every boundary (and ±1) is hit, every decision-table rule (including cause-effect–derived rules) and every valid state transition is represented, every category-partition class appears in the frame, pairwise reaches all-pairs coverage and any t-way set reaches full t-way coverage, and every approval snapshot used as an oracle carries a recorded human confirmation (unconfirmed ⇒ not counted as covered).

## Assertions & exit gate
- 100% of identified equivalence partitions (valid and invalid) covered.
- All 2-/3-point boundaries present for each bounded field.
- Every feasible decision-table rule (including cause-effect–derived rules) and every valid state transition has ≥1 case; invalid transitions have negative cases.
- Every category-partition/CTM class appears in the test frame; pairwise reaches all-pairs and any declared t-way set reaches full t-way coverage at the chosen strength.
- Every approval/characterization snapshot used as an oracle is human-confirmed against a requirement ID; an unconfirmed snapshot does not satisfy coverage.
- Every case carries an expected result and a requirement-ID link.
- **Gate:** `technique_coverage_complete` — passes when 0 uncovered partitions/boundaries/rules/transitions/classes/t-way-combinations (an uncovered partition, boundary, class, or t-way combination is **major**; a case with no requirement-derived oracle, or one backed only by an unconfirmed/rubber-stamped snapshot, is **critical**).

## Output
Write `artifacts/test-case-design/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"technique_coverage_complete"}`. Findings (`QA-TCD-NNN`) name the technique + the uncovered element in `oracle`/`evidence`; the generated case suite is emitted as an artifact for `traceability-coverage` to consume.

**ALSO write a human-readable Markdown test-case document — `test-cases.md` (BAKED-IN, required).** Write it as a **structured tracker document matching the repo's existing tracker docs** (glance at a bug-sheet/backlog-style file in the project and mirror its rhythm): title + project + Last-Updated header → `## Summary` count table → feature/requirement sections each with a case table (**ID** `TC-NNN` · **Requirement** · **Technique** · **Preconditions** · **Steps** · **Test data** · **Expected** requirement-derived · **Actual** `—` until run · **Status** Pass/Fail/Blocked/Not-run) → `## Conventions` block. Full template in `shared/report-format.md`. The JSON stays the machine source of truth; keep TC IDs in sync.

## Guardrails
Read-only — `disallowedTools: Edit, Write` outside artifacts. Expected results MUST come from the requirement/oracle; if none exists, lower confidence and flag rather than guess. No SUT calls. Secrets via env. Cap `maxTurns`. Cases are proposals for human review.

## Watch (do not gate)
- **EMERGING — automated t-way generators (ACTS-style covering arrays) and CTM tooling.** Higher-strength covering arrays and classification-tree generators can shrink large parameter suites automatically, but generated suites still inherit the rubber-stamp risk if their expected results are auto-captured rather than requirement-derived. Note where such tooling would help; do not let a tool-generated suite gate a requirement until its oracles are human-confirmed.
