# property-based

**Category:** 10-functional
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only (or seeded-sandbox for stateful command sequences)

## Purpose
Property-based testing (Hypothesis / fast-check / jqwik): instead of enumerating fixed examples, state a **property that must hold for every input**, generate hundreds of randomized cases against it, and on the first failure **shrink** to a minimal counterexample. The generative complement to enumerated EP/BVA in `test-case-design.md` — that flow picks representative points by hand; this one searches the whole input space and reports the smallest input that breaks the property. Answers — "does this invariant survive inputs no human thought to write down?"

## Inputs & preconditions
- Required artifacts: the **stated property/invariant** for the function/endpoint (round-trip pair, structural invariant, or a metamorphic relation between two runs), plus the input domain (types, ranges, generators) — typically from the spec or `test-case-design.md` partitions.
- Target: the function under test (import) or endpoint base URL + auth via env; build/commit recorded.
- Preconditions: smoke passed; the property is **falsifiable and externally grounded** (not "whatever the SUT returns"); a fixed RNG seed is pinned for replay; stateful sequences run only against a seeded sandbox.

## Oracle (source of truth)
The **stated property/invariant** — per https://hypothesis.readthedocs.io. Three families:
- **Round-trip** — `decode(encode(x)) == x`, `parse(serialize(x)) == x`, normalize-idempotence `f(f(x)) == f(x)`.
- **Invariant** — a structural fact that holds for all outputs: sortedness, count preservation, `min ≤ result ≤ max`, no duplicates, totals reconcile.
- **Metamorphic** — a relation between runs when no single-output oracle exists: `f(x) == f(permute(x))`, monotonicity, `sum(filter(p, xs)) ≤ sum(xs)`.
The property is the oracle. NEVER assert that the current output is correct merely because the SUT produced it.

## Step sequence (Plan → Act → Verify)
1. **Plan** — for the change surface, write each property as a generator (`@given(...)` / `fc.assert` / `@Property`) bound to the input domain; pin `seed`/`derandomize` and `max_examples` for reproducibility; list the round-trip / invariant / metamorphic relations to cover.
2. **Act** — run the generators; on a falsifying case let the framework **shrink** to the minimal counterexample and capture it; skip-and-continue across independent properties so one failing property does not abort the rest.
3. **Verify** — confirm each property held across all generated cases; for every failure record the **shrunk minimal input**, the property violated, and the deterministic seed so a developer reproduces it in one run.

### Stateful command-sequence sub-section
For systems with internal state (a cart, a hiring pipeline, a parser with modes), use the framework's **stateful/model-based** mode (`RuleBasedStateMachine` / `fc.commands` / `@StatefulProvider`): generate a random *sequence of operations*, run it against the SUT while a tiny in-memory **model** tracks expected state, and assert a class invariant after every step (e.g. "stage transitions only follow the allowed graph", "item count never negative"). On failure the framework shrinks the **command sequence** to the shortest reproducing trace. Command sequences mutate state → run **only against a seeded sandbox**, never live data.

## Assertions & exit gate
- Every property holds for all `max_examples` generated inputs (round-trip, invariant, and metamorphic alike).
- Each falsification yields a **shrunk minimal counterexample** plus its seed — not a giant random blob.
- Stateful runs: the class invariant holds after every command in every generated sequence; failures shrink to the shortest trace.
- Triage each falsification via `failure_class` before carding — a property that merely re-encodes current behavior is a `test_assertion_issue`, not a defect.
- **Gate:** `all_properties_hold` — pass only if no property has a surviving (post-shrink) counterexample; any real-bug counterexample → `fail`.

## Output
Write `artifacts/property-based/report.json` per `shared/report-format.md`:
`{ flow:"property-based", status, summary{total,passed,failed,skipped}, findings[], gate{name:"all_properties_hold",passed} }`.
Findings per `shared/finding-schema.md`; `oracle` = the named property (e.g. "round-trip: parse∘serialize == id"); a broken round-trip/invariant on valid generated input is **major** (data corruption or lost records on a core path → **critical**); `steps_to_reproduce` MUST include the **shrunk minimal input + the pinned seed**; for stateful failures, evidence = the shortest failing command sequence.

## Guardrails
Per `shared/guardrails.md`: read-only on live targets; stateful/mutating command sequences only against a seeded sandbox (`<db>-qa`, seeded → run → torn down, confirm teardown); pin the RNG seed and `max_examples` so every run is deterministic and replayable; cap generated examples so a run stays cost-bounded; secrets via env; redact any secret surfaced in a shrunk input; `maxTurns: 30`.

> **Watch (do not gate):** coverage-guided / fuzz-style generation (e.g. Hypothesis `target()` metric-driven exploration, Atheris) can find inputs random sampling misses — track as an emerging technique; do not add to the gate yet.
