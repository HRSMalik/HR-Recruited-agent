# llm-scoring-correctness

**Category:** 60-ai-ml
**Runs as:** subagent: ../.claude/agents/scoring-validator.md (sub-fans a worker per reliability dimension)
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Validate the candidate **screening score** as a **decision instrument** — not chatbot quality (see `llm-eval-harness`), not output-level fairness wording (see `fairness-bias-testing`). Treats the score as the product's money-path and a **legal artifact (CRITIC surface G2)** and asserts its psychometric soundness: **monotonicity** (a strictly-stronger resume never scores lower), **stability** (same resume re-run lands the same band), **rank-ordering** vs a human-graded gold set, **calibration** (does 0.8 mean ~80%?), **threshold/cutoff correctness**, **score drift** across prompt/model versions, and **decision-level adverse impact (4/5ths)** at the cutoff. Answers: "Can a hire/reject decision be defended on this score?"

## Inputs & preconditions
- Required artifacts: a **human-labelled gold set** — resumes with rubric grades + a reference rank order + the documented cutoff/band definitions; the score-producing handle (batch scorer) and its prompt + model id; the **prior baseline score distribution** (per req/role) for drift; the statistical reliability policy (τ, ICC, ECE, calibration-slope, 4/5ths bands); a small set of **monotone resume pairs** (A strictly dominates B on every rubric axis).
- Target: build/version + a **NON-PROD** batch-scoring handle; protected-attribute columns present for the cutoff adverse-impact slice.
- Preconditions: assert NON-PROD (STOP, `status:error` on prod); assert the gold set version + cutoff definitions are pinned and present; per `shared/non-determinism-strategy.md` fix the **run-N** count + temperature/seed before scoring (scores are stochastic — one run is not a measurement); assert each protected group clears a **minimum sample size** at the cutoff (skip-and-note small-N).

## Oracle (source of truth)
The **human-labelled gold set + statistical reliability thresholds** — never the scorer's own confidence. Rank-ordering: **Kendall τ ≥ 0.7** (and Spearman ρ ≥ 0.7) of model order vs. the human reference order. Stability: re-run **band agreement = 100%** and within-band score **ICC ≥ 0.9 / max spread ≤ band-width** across N runs. Monotonicity: every dominating pair scores **A ≥ B** (zero inversions). Calibration: **ECE ≤ 0.05** and calibration **slope ∈ [0.9, 1.1]** on a reliability curve (predicted band-rate vs. observed gold pass-rate). Threshold: the documented cutoff reproduces the gold accept/reject set within tolerance. Drift: per-req score-distribution shift (PSI / mean delta) within the policy band vs. baseline. Adverse impact: selection-rate **ratio ≥ 0.80 (4/5ths)** at the cutoff per group vs. reference. The model's output is the thing under test, never the standard it is judged against.

## Step sequence (Plan → Act → Verify)
1. **Plan** — load the pinned gold set, cutoff definitions, and baseline; bind each dimension to its threshold. The validator **sub-fans one worker per dimension** — monotonicity, stability, rank/calibration, threshold, drift, adverse-impact — each scoped to its gold slice. On any **prompt or model change**, force the full drift + rank + calibration suite, baseline-compared.
2. **Act** — score the gold set **run-N times** at the fixed seed, capturing each score + band + the trace (final prompt, model id, token/latency). Score the monotone dominating pairs; re-score the stability slice N times; recompute Kendall τ / Spearman, the reliability curve + ECE/slope, the cutoff confusion vs. gold, the PSI/mean-delta vs. baseline, and the per-group selection ratio at the cutoff. Skip-and-continue on a single case's scoring error (record as skipped with reason).
3. **Verify** — assert every statistic against its oracle band; flag any monotonicity inversion, band flip across runs, τ/ICC/ECE/slope breach, cutoff misclassification beyond tolerance, drift outside band, or 4/5ths breach. Attach the failing pair/case, gold reference, model actual + per-run spread, the curve/τ value, and baseline delta as evidence for every failure.

## Assertions & exit gate
- **Monotonicity:** 0 inversions on dominating pairs (A ≥ B always).
- **Stability:** 100% band agreement and within-band ICC ≥ 0.9 across N re-runs of the same resume.
- **Rank-ordering:** Kendall τ ≥ 0.7 and Spearman ρ ≥ 0.7 vs. the human gold order.
- **Calibration:** ECE ≤ 0.05 and slope ∈ [0.9, 1.1] on the reliability curve.
- **Threshold:** the documented cutoff reproduces the gold accept/reject set within tolerance.
- **Drift:** per-req distribution shift within the policy band vs. baseline on any prompt/model change.
- **Adverse impact:** selection-rate ratio ≥ 0.80 at the cutoff for every group vs. reference.
- **Gate:** `scoring_reliability_met` — passes only when **all** of the above clear band. A monotonicity inversion, a band flip on re-run, τ below bar, miscalibration that moves decisions, an uncontrolled drift on a shipped prompt, or a 4/5ths breach at the cutoff → **critical** (the decision instrument is unsound / legal exposure). A within-margin τ dip, mild miscalibration not crossing the cutoff, or drift trending but in-band → **major**.

## Output
Write `artifacts/llm-scoring-correctness/report.json` per `shared/report-format.md`:
`{ flow:"llm-scoring-correctness", status, summary{total,passed,failed,skipped}, findings[], gate{name:"scoring_reliability_met",passed} }`.
Each finding (`QA-SCORE-NNN`) names the metric + gold version + threshold in `oracle` (e.g. "Kendall τ ≥ 0.7 vs gold-rank v2, run-5"), puts the failing pair/case + gold reference + per-run scores + the τ/ECE/curve/ratio value + baseline delta in `evidence`, the measured statistic vs. bound + affected slice/group in `actual`, and a remediation (rubric/prompt fix, temperature pin, score recalibration, cutoff re-derivation, retrain) in `suggested_fix`. Tag adverse-impact and calibration findings as legal-artifact inputs for the bias-audit trail; tag a `test_assertion_issue` where the gold label or cutoff definition is itself stale rather than the scorer being wrong.

## Guardrails
Per `shared/guardrails.md`: seeded-sandbox only — score the pinned gold set on a NON-PROD handle; confirm NON-PROD or `status:error`. Gold resumes + protected attributes are **synthetic/consented and masked** — never real candidate PII in fixtures or the report (redact). Record the gold version + seed + run-N + cutoff id in every finding for deterministic repro; report per-group sample sizes and mark small-N slices low-confidence. **Read-only on the model** (score-and-measure, no retrain/threshold-write to prod); respect LLM rate limits and back off on 429; cap `maxTurns`. Findings feed the formal scoring-validation + bias audit — a qualified human owns the legal sign-off, not this flow.

## Watch (do not gate)
Emerging only, do not fail the gate: **gold-set staleness/leakage** as prompts are tuned toward the fixtures; **near-cutoff knife-edge** cases where tiny score noise flips a decision (surface for cutoff hysteresis review); **construct validity** — whether the rubric the gold encodes still predicts on-the-job success. Note these for the score owner; do not block release.
