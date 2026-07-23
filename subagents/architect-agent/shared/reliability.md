# Reliability — Evaluation Integrity, Diffing, Error-Safety

Binding on every run. This agent **proposes and documents** architecture; it does **not** run a live
app, so there is no auth/browser/retry dimension. Its reliability is about **evaluation integrity,
grounding, diffing, and error-safety**. Pairs with `guardrails.md` and `run-budget.md`.

## 1. Deterministic-first oracles
Gate on the **deterministic/automatable hard oracles** first, and quote their exact output:
driver-traceability (every ASR↔decision), each prioritized scenario's response-measure met (by capacity
model / pattern guarantee / **fitness function**), no un-accepted SPOF, every cross-service failure mode
defined, STRIDE coverage per trust boundary, **diagrams compile**, ADR-completeness, bounded cost. The
craft (rubric) score is **soft/advisory only**, after the hard oracles are green - elegance never
overrides a missed response-measure or a silent SPOF.

## 2. No invented numbers (grounding)
Never assume an unstated NFR. If a response-measure, SLO, RTO, or peak load is not in a source document,
**surface it as an open driver question and stop** rather than designing/evaluating against a guess
(`architecture-principles.md`). A design justified by an invented number is unreliable by construction.

## 3. Position-bias control (already core - keep it)
`architecture-evaluator` scores each direction **twice and swaps order** to kill position bias, and
penalizes accidental complexity + unjustified novelty. Do not collapse this to a single pass to save a
few turns - it is the guard against a plausible-but-wrong winner.

## 4. Run-over-run diffing (read prior artifacts - never write memory)
Compare this run's evaluation against the **previous run's artifacts** for the same system and classify
findings/risks as **NEW**, **PERSISTING** (already known), or **RESOLVED** (a prior risk now mitigated /
a decision changed). The report leads with NEW and RESOLVED and collapses PERSISTING. No baseline ⇒
everything NEW, note "first pass." Diffing reads prior `artifacts/` only; durable learnings go in the
RETURNED REPORT for the controller to curate - the architect-agent never writes project memory.

## 5. Error-safe reporting (a run never ends with nothing)
If a specialist or the writer throws mid-run, still emit `summary.json` with whatever was produced
(the utility tree, any authored ADRs/diagrams, partial findings), marked partial. Partial is reported as
partial - never dropped, never inflated to "meets every driver."

## 6. Environment learnings -> the report, not memory
Durable facts worth carrying forward (a standing constraint, a recurring tradeoff, a confirmed
one-way-door) go in a **"Known / architecture learnings"** section of the RETURNED REPORT. The
controller curates memory; the agent proposes, never persists.
