# per-criterion-evaluation

**Group:** 60-evaluation · **Runs as:** subagent: ../.claude/agents/architecture-evaluator.md · **Mode:** audit + design · **Default model:** sonnet

## Purpose

Score each quality-attribute scenario in its **own isolated evaluator call** — never one holistic verdict — to prevent cross-contamination (halo bias) where strength on one attribute silently inflates the score of an unrelated one. Every score must carry a typed evidence pointer; the per-criterion outputs roll up into the decision matrix transparently, preserving full per-attribute visibility for the controller to judge.

## Inputs & preconditions

- From `project-architecture-config.md`: the architecture-description path, ADR log location, diagram source paths, and the architecture quantum boundaries.
- The **utility tree** (`architecture/<slug>/quality-attributes.md`) produced by `00-drivers/quality-attribute-scenarios.md` — the prioritized, 6-part quality-attribute scenarios with response measures. Every scenario must already be 6-part and end in a measurable response before this flow starts; if scenarios are incomplete, this flow surfaces the gap and halts rather than inventing a number.
- The architecture artifact(s) under evaluation: design doc, C4-as-code diagrams, ADRs, capacity model, threat model. All must be present at their canonical paths in `architecture/<slug>/`; missing artifacts are an error (not a soft finding) and the flow status is `error`, not `fail`.
- For option selection (design mode): the N divergent option specs from `architecture-explorer`, **style-normalized** before any scoring call — formatting, length, vocabulary polish, and prose sophistication stripped so the evaluator judges substance, not presentation style (dominant LLM-judge bias, 0.10–0.76 effect size; `evaluation-method.md §Evaluator discipline`).
- Hard precondition: the `architecture-evaluator` is **not** the same model instance that authored (or co-authored) the artifact under evaluation. Writer and judge must be distinct. If they share a model family, strip identifying style markers from the candidate before judging and emit a `SOFT_WARNING: writer-judge-same-family` in the report.

## Oracle (source of truth)

**hard:**
- Each quality-attribute scenario in the utility tree is scored in a **separate evaluator call** returning `{criterion, scenario_id, score, evidence_pointer, rationale}`. A single holistic call covering multiple scenarios in one response is a hard violation — it re-introduces cross-contamination. The call log (prompt + response per criterion) must be included in the output block so the controller can verify isolation.
- Every score — hard-oracle pass/fail and soft rubric alike — carries at least one typed evidence pointer from the recognized set (`DDQ` / `DGN` / `ADR` / `CML` / `FFR`) as defined in `../shared/evaluation-evidence-protocol.md §1`. A score with no typed pointer is void (`evaluation-evidence-protocol.md §3`); void scores are not zeroes — they are excluded from the mean and flagged as coverage gaps.
- Every `(H,*)` scenario (high business value at any technical-risk level) is covered. The evaluator runs an explicit self-check before emitting: "are all `(H,*)` scenarios present in the output?" If any are absent, the evaluator makes another pass; it does not silently omit them.
- No single blended/aggregate number is emitted without the underlying per-criterion breakdown visible in the same report. An aggregate score that hides per-attribute variance is a hard violation (it defeats the purpose of this flow).

**soft:**
- The per-criterion scores roll up into the decision matrix (`evaluation-method.md §Choosing between options`) transparently: each row is a scenario × option cell with the evidence pointer visible, so the sensitivity points and tradeoff points are readable from the matrix, not buried in narrative.
- The evaluator covered every scored `(H,*)` scenario — confirmed by self-check output — and no `(M,*)` or `(L,*)` scenario is silently promoted to the evaluation focus without a stated reason.
- Where sustainability (CL-07) is not a stated project driver, the dimension is scored N/A and excluded from the mean per the locked checklist anchor in `evaluation-evidence-protocol.md §CL-07`.

## Standards & techniques

- **Per-criterion LLM-judge scoring** (anti cross-contamination): the core discipline; each criterion/scenario gets a fresh call with no prior scores in context, so a strong prior score cannot anchor or inflate the current one. Grounded in the 2024–2026 LLM-as-judge literature on cross-dimension contamination (halo effect in multi-rubric scoring).
- **Evidence-anchored scoring — RULERS-style** (`../shared/evaluation-evidence-protocol.md`): every score cites a locatable, typed pointer (DDQ/DGN/ADR/CML/FFR). Impressions and paraphrases are not pointers. The five pointer kinds are ordered by evidentiary strength: FFR (executable pass/fail) > CML (computed model line) > ADR field > DGN (diagram element) > DDQ (design-doc verbatim quote).
- **Locked checklist with frozen anchors** (`evaluation-evidence-protocol.md §2`, CL-01 through CL-08): the evaluator selects the anchor (0 / 0.5 / 1.0) whose frozen description matches the evidence — it does not re-interpret the bar run-to-run. Any anchor edit requires a version bump and a re-calibration run.
- **ATAM utility-tree scoring** (`../shared/evaluation-method.md §ATAM evaluation`): for each prioritized scenario the evaluator identifies the architectural approach, checks whether the response measure is met (via capacity model / named pattern's guarantee / fitness function), and names sensitivity points and tradeoff points. A scenario with no met response measure is a hard finding.
- **Style normalization** (primary debias, `evaluation-method.md §Evaluator discipline`): strip formatting, length, and vocabulary sophistication before the first scoring call. Applied before any call, not just at aggregation.
- **Self-preference / cross-family guard**: the evaluator is a separate agent from the writer; if the same model family is unavoidable, identifying style markers are stripped and a `SOFT_WARNING` is emitted. Self-preference inflates a writer's own options ~10–25% — not mitigated by prompt instruction alone; separation is the control.
- **External-signal gate on the revise loop** (`evaluation-method.md §External-signal gate on reward-hacking`): the EVALUATE→revise loop may not close more than twice on the evaluator's own re-score. A third close requires an FFR-kind pointer (an executable hard oracle passes) or a human decision. The evaluator's re-score is not an external signal; citing it as one is a hard violation.
- **Judge-panel cap** (if ever used): ≤ 3 judges from ≥ 2 distinct model families; a single disciplined evaluator is the default. Do not multiply judges to achieve a "majority verdict" — 9 correlated judges ≈ 2.2 effective votes.
- **ISO/IEC 25010** quality characteristic taxonomy: used to confirm the scenario set covers the attributes that matter for this system (performance efficiency, reliability, security, maintainability, operability, cost, compliance, sustainability where stated).

## Step sequence

**audit:** Read the utility tree and the architecture artifact(s) → style-normalize the artifact (strip prose polish; preserve structural facts) → for each `(H,*)` scenario in priority order, issue a **separate scoring call** returning `{criterion, scenario_id, score, evidence_pointer, rationale}` → after all `(H,*)` scenarios are scored, repeat for `(M,*)` and `(L,*)` scenarios in order → run the evaluator self-check: confirm every `(H,*)` scenario appears in the output; if any are absent, issue additional calls → check for hard violations (holistic verdict, void score, missing `(H,*)` scenario) → emit findings grouped by severity (critical → cosmetic) and a risk register. Read-only; authors nothing.

**design:** Frame (read the utility tree; if scenarios are incomplete halt with `status: error` and list the missing response measures) → style-normalize the option spec(s) from the explorer — strip length, formatting, vocabulary sophistication → for each option × each `(H,*)` scenario, issue **one scoring call** returning `{criterion, option_id, scenario_id, score, evidence_pointer, rationale}` → repeat for `(M,*)` and `(L,*)` scenarios → run self-check (all `(H,*)` scenarios present in output for every option) → build the **decision matrix**: rows = scenarios (weighted by `(value, risk)` priority), columns = options, cells = `{score, evidence_pointer}` — the matrix is the primary output, not a narrative → identify sensitivity points (a decision where score strongly determines scenario outcome) and tradeoff points (a decision that is a sensitivity point for ≥2 attributes pulling in opposite directions) → check the external-signal gate: if a revise loop was triggered, confirm it closed on an FFR or human decision, not on evaluator re-score alone → emit the decision matrix + per-criterion scorecard + sensitivity/tradeoff points + findings + the gate verdict. Authors `artifacts/per-criterion-evaluation/report.json` only; no product code or architecture source is edited.

## Assertions & exit gate

- Every `(H,*)` scenario in the utility tree has a score entry in the output — confirmed by the self-check log in the report.
- Every score carries at least one typed evidence pointer (DDQ / DGN / ADR / CML / FFR); void scores are flagged and excluded from the mean, not zeroed.
- No holistic single-number verdict is present without the per-criterion breakdown visible in the same report.
- Each scoring call was issued separately (the call log shows one scenario per call); any run that produced per-criterion scores in a single call is a hard violation and `status: fail`.
- The EVALUATE→revise loop closed ≤ 2 times on evaluator re-score alone; any additional close cites an FFR or human-decision signal by id.
- Style normalization was applied before the first scoring call (confirmed in the run log).
- If the evaluator and writer share a model family, `SOFT_WARNING: writer-judge-same-family` appears in the report.
- Soft rubric mean computed only after all hard oracles are green; mean ≥ 0.8 to pass the soft gate.
- **Gate:** hard oracles green (per-criterion isolation enforced; every `(H,*)` scenario scored with a typed evidence pointer; no void score left unresolved; external-signal gate honored) AND (design) rubric mean ≥ 0.8 across non-void dimensions.

## Output

Write `artifacts/per-criterion-evaluation/report.json` per `../shared/report-format.md`. The report includes:

- `"flow": "per-criterion-evaluation"`, `"mode": "audit | design"`, `"status": "pass | fail | error"`.
- `"drivers"`: the prioritized quality-attribute scenarios from the utility tree, each with `id`, `attribute`, `response_measure`, and `priority` (H/H, H/M, etc.).
- `"per_criterion_scores"`: array of `{criterion, scenario_id, option_id (design mode), score, evidence_pointer: {kind, locator, excerpt}, rationale}` — one entry per call, never merged.
- `"decision_matrix"` (design mode only): rows × columns table with cell = `{score, evidence_pointer}`, sensitivity points annotated per cell, tradeoff points named where a decision is a sensitivity point for ≥2 opposing attributes.
- `"self_check"`: `{h_star_scenarios_expected: N, h_star_scenarios_scored: N, all_covered: true|false, missing: []}`.
- `"call_log"`: array of `{call_index, scenario_id, option_id, model, prompt_hash, response_hash}` — confirms per-criterion isolation; auditable.
- `"void_scores"`: array of `{criterion, scenario_id, reason}` — scores excluded from the mean; a report with >1 void fails the stop criterion.
- `"soft_warnings"`: array of strings — e.g. `"writer-judge-same-family"`, `"revise-loop-closed-on-evaluator-word"`.
- `"revise_loop"`: `{iterations: N, closing_signal: "FFR:<id> | human-decision | evaluator-word (violation if >2)"}`.
- `"rubric_score"`: mean across non-void CL dimensions (null if hard oracles failed).
- `"gate"`: `{name: "per-criterion-isolation + hard-oracles-green + rubric>=0.8", passed: true|false}`.
- Findings per `../shared/finding-schema.md` — hard findings (`oracle:"hard"`) block; soft findings (`oracle:"soft"`) are advisory. Each finding carries `driver_ref` (the quality-attribute scenario id it serves), `evidence` (the traced structural or measured fact), and `tradeoff` (what the fix costs on other attributes).

## Guardrails

Per `../shared/guardrails.md`:

- **Propose & evaluate — never write product code.** This flow scores and reports; it authors only `artifacts/per-criterion-evaluation/report.json` and the decision matrix. It does not edit the architecture description, ADRs, or any file under `src/**`, `frontend/**`, or `backend/**`. A score that implies a fix is a finding for the controller to act on, not an instruction for this flow to implement.
- **Ground every score in a driver.** A score that cannot be tied to a named quality-attribute scenario (a `QAS-…` id from the utility tree) is not emitted — it is a preference. If the utility tree is missing a scenario, that is a `type:"driver"` finding, not a reason to invent a scenario mid-evaluation.
- **The oracle is external.** The evidence pointer must localize to a retrievable artifact (DDQ section path / DGN element id / ADR id+field / CML row / FFR tool+check+run-ref). "The design implies…" and "it is clear that…" are impressions; they are not pointers and they void the score.
- **Record the tradeoff and the rejected alternatives.** Every decision finding is ADR-shaped: the pattern / topology / response-measure it now satisfies, what it costs on opposing attributes, and what alternatives were beaten. A recommendation with only upside is incomplete.
- **One writer, evaluator is read-only.** The evaluator has no `Edit` or `Write` access to architecture source. It returns scores, findings, and the decision matrix; the controller decides which findings to act on and the `solution-architect` (one writer) makes the changes.
- **External oracle over self-judgment.** The evaluator never grades its own re-score as an external signal. The revise loop closes on FFR evidence or a human decision only — never on the evaluator asserting "on reflection, the design is sound." See `evaluation-method.md §External-signal gate on reward-hacking`.
