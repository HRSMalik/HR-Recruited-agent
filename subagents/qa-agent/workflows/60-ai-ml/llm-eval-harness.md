# llm-eval-harness

**Category:** 60-ai-ml
**Runs as:** subagent: ../.claude/agents/llm-eval-tester.md (sub-fans a worker per LLM feature)
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Run a **golden-dataset eval harness** over every LLM feature: feed each versioned test case to the feature, collect the response **plus its trace** (prompt, retrieved context, tool calls, model id), and score it against the oracle with task-appropriate metrics. Answers: "On a fixed golden set, does this LLM feature still meet its quality bar — and did this prompt/model change regress it?" Per **DeepEval — what is an eval harness** (https://www.deepeval.com/blog/what-is-an-eval-harness): an eval harness is the standardized dataset → run → metric → score loop that makes LLM quality CI-gated and comparable across versions, not a one-off vibe check. HR instance: the **resume-screen** extractor/scorer, the candidate **chat** assistant, and the **Vapi voice agent** — each gets its own golden slice and metric set.

## Inputs & preconditions
- Required artifacts: a **versioned golden eval set** (input + expected output / reference answer / rubric, with a dataset version tag) per feature; the metric policy mapping each case to **exact-match**, **semantic-similarity**, or **LLM-as-judge** with its pass threshold; the current prompt + model id under test; the prior baseline scores for regression comparison.
- Target: build/version + a **NON-PROD** invocation handle for each feature (batch scorer for resume-screen; sandbox chat endpoint; **mocked/sandbox Vapi** — transcript-in/transcript-out, never a real outbound call).
- Preconditions: assert NON-PROD (STOP, `status:error` on prod); assert the golden set version is pinned and present; per `shared/non-determinism-strategy.md` set the **run-N** count and **pass-rate threshold** before acting; record the sampling temperature/seed.

## Oracle (source of truth)
The **versioned golden set + its task-specific metrics**, never the model's self-assessment. Each case names its metric: **exact/structural match** (resume-screen JSON fields — name, years, skills, screen verdict), **semantic similarity** (chat answer ≥ similarity threshold to the reference), or **LLM-as-judge** scored against an explicit rubric (faithfulness, relevancy, task-completion, tone/safety) per DeepEval. A case passes only when its metric clears the per-case threshold on the golden reference — and, per the non-determinism strategy, when the **pass-rate across N runs ≥ the configured threshold** (LLM outputs are stochastic; one green run is not a pass).

## Step sequence (Plan → Act → Verify)
1. **Plan** — load the pinned golden set, bind each case to its metric + threshold, and scope to the change surface when a diff is given. The tester **sub-fans one worker per feature** (resume-screen / chat / Vapi), each scoped to its golden slice. On any **prompt or model change**, force the full **PROMPT-REGRESSION** suite for the touched feature, baseline-compared.
2. **Act** — per feature worker: invoke the feature **run-N times** per case, capturing the response **and the full trace** (final prompt, retrieved context, tool calls, model id, latency, token count). Skip-and-continue on a single case's invocation error, recording it as skipped with the reason.
3. **Verify** — score each run with its metric against the golden reference, compute the per-case **pass-rate over N**, and assert it clears the threshold; for prompt/model changes, diff every score against the baseline and flag any net regression. Attach the failing input, golden expected, model actual, trace, and judge rationale as evidence for every failure.

## Assertions & exit gate
- Every golden case clears its metric threshold (exact-match / semantic ≥ τ / judge ≥ rubric bar) at **pass-rate ≥ N-threshold** across runs.
- Resume-screen output is schema-valid and field-correct vs. the golden record; chat answers are faithful + relevant to retrieved context (no hallucinated facts); Vapi transcripts complete the scripted task and stay on-policy.
- **Prompt-regression:** no case regresses below baseline on any prompt/model change.
- **Gate:** `golden_eval_pass_rate_met` — passes only when all cases clear threshold at the required pass-rate **and** zero regressions vs. baseline. A drop below threshold on a core capability (wrong screen verdict, hallucinated chat fact, failed voice task) → **critical**; a within-margin score dip or single-metric softening → **major**.

## Output
Write `artifacts/llm-eval-harness/report.json` per `shared/report-format.md`:
`{ flow:"llm-eval-harness", status, summary{total,passed,failed,skipped}, findings[], gate{name:"golden_eval_pass_rate_met",passed} }`.
Each finding (`QA-EVAL-NNN`) names the metric + golden dataset version + threshold in `oracle` (e.g. "judge faithfulness ≥ 0.8 on golden v3, run-5 pass-rate ≥ 0.8"), puts the case input + expected + actual + **trace** + judge rationale + per-run pass-rate in `evidence`, the measured score vs. bound (and baseline delta for regressions) in `actual`, and a remediation (prompt fix, retrieval tuning, model pin, add/repair golden case) in `suggested_fix`. Tag any `test_assertion_issue` where the golden reference itself is stale rather than the model being wrong.

## Guardrails
Per `shared/guardrails.md`: seeded-sandbox only — invoke against the pinned golden set on NON-PROD handles; confirm NON-PROD or `status:error`. **Vapi runs mocked** (transcript-in/transcript-out) — never place a real outbound call, email, or SMS as a side effect; mark a real-call test NOT RUN with how it would be sandboxed. Golden data is synthetic/consented — never real candidate PII in fixtures or the report (redact). Record the dataset version + seed + run-N in every finding for deterministic repro. Read-only on the model (invoke + score, no retrain/write); respect LLM rate limits and back off on 429; cap `maxTurns` — judge-model fan-out is the dominant cost, so reuse one judge config per worker.

## Watch (do not gate)
Emerging only, do not fail the gate: **judge drift** (the LLM-judge model itself updates and shifts scores — pin and meta-eval it); **golden-set staleness/leakage** as prompts are tuned toward the fixtures; **trace-only failure modes** (right answer, wrong tool path) worth surfacing for the owner. Note these; do not block release on them.
