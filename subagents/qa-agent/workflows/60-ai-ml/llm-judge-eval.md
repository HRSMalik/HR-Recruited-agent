# llm-judge-eval

**Category:** 60-ai-ml
**Runs as:** subagent: ../.claude/agents/judge-evaluator.md (sub-fans an ensemble judge per model family)
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Score open-ended, free-text agent replies (candidate emails, screening summaries, chat answers) for quality with a **calibrated LLM-as-a-judge** — pointwise grading, pairwise preference, or reference/rubric-based — plus a **hallucination/faithfulness gate**, while actively mitigating judge bias. Answers: "Is this generated reply good and grounded, where exact-match assertions are impossible?" This is the only viable oracle when there is no single correct string; per the source, "Human subject matter experts remain the gold standard," so this flow stands in for them only after proving human alignment.

## Inputs & preconditions
- Required artifacts: a **golden eval set** of prompts with curated **reference answers** + accept/reject labels (synthetic/consented, masked PII); the **rubric** (explicit numeric criteria with anchors); a **human-aligned spot-check subset** (≥ human labels for a sample) to calibrate against; for faithfulness, the **source context/ground-truth documents** each reply must stay faithful to; the generating agent's output handle (batch file or NON-PROD endpoint).
- Target: model build/version of the system-under-test; judge model identities (≥2 distinct families for the ensemble) on a **NON-PROD** path.
- Preconditions: assert NON-PROD (STOP, `status:error` on prod); fix and **record the seed**; freeze rubric + judge prompt + temperature (judge temp ≈ 0 for determinism); confirm the human spot-check labels exist before trusting any judge verdict.

## Oracle (source of truth)
The **rubric + reference answers + source context on the golden set, validated by human-label agreement** — never the judge's unverified say-so. Per the source (emergentmind.com/topics/llm-as-a-judge-evaluations): judging is **pairwise**, **pointwise grading**, or rubric-based with "structured rubrics" and "few-shot, chain-of-thought (CoT) elicitation." Faithfulness = every claim entailed by the source context (no hallucination). **Judge bias is treated as a measurement error to remove**, not a result: "Position Bias" (order primacy/recency, "accuracy shifts exceeding 10%"), "Verbosity Bias" (preferring verbose output "regardless of substantive quality"), "Self-Preference Bias" (favoring output "familiar to its own policy"). The judge is only trusted once its **alignment with human judgment** clears the bar (e.g. Scott's Pi / Fleiss' Kappa / agreement rate from the source's measures) on the spot-check subset.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate cases (happy / edge / adversarial-verbose / known-hallucination traps); bind each to its rubric criteria + reference + source context. Choose mode per task (pairwise for A/B, pointwise for absolute quality). The evaluator **sub-fans one judge per model family** for the ensemble.
2. **Act** — per case: run each judge with the frozen rubric/CoT prompt. **Swap-and-average** every pairwise comparison (score both orders A|B and B|A, average) to cancel position bias; **ensemble-vote** across families to cancel self-preference; run the **faithfulness** pass (claim-by-claim entailment vs. source). Skip-and-continue on a single case's judge error.
3. **Verify** — assert each aggregated verdict against the rubric/reference/faithfulness oracle; compute **human-alignment** on the spot-check subset and assert it clears the bar; flag verbosity-bias by checking score-vs-length correlation. Capture the per-judge scores, both swap orders, and the unfaithful span as evidence for every failure.

## Assertions & exit gate
- Pointwise mean rubric score ≥ policy threshold; pairwise win-rate within band after swap-and-average (position-swap disagreement → flag, don't trust).
- **Faithfulness:** 0 unsupported/hallucinated claims vs. source context on the gated set.
- **Judge validity:** human-alignment on the spot-check subset ≥ agreed floor (Scott's Pi / Kappa / agreement-rate); ensemble inter-judge disagreement below threshold; no significant score↔length correlation (verbosity bias).
- **Gate:** `judge_calibrated_and_passed` — passes only when the judge is **proven aligned to human labels** AND quality ≥ threshold AND zero hallucinations. A hallucinated claim in a candidate-facing reply → **critical**; quality below threshold → **major**; judge **failing alignment / showing position or verbosity bias** → `status:error` (oracle untrustworthy — do not gate on an uncalibrated judge).

## Output
Write `artifacts/llm-judge-eval/report.json` per `shared/report-format.md`:
`{ flow:"llm-judge-eval", status, summary{total,passed,failed,skipped}, findings[], gate{name:"judge_calibrated_and_passed",passed} }`.
Each finding (`QA-JUDGE-NNN`) names the rubric criterion/reference + the source-context span in `oracle`, puts the per-judge scores, both swap orders, human-alignment stat, and the unfaithful claim + seed/fixture id in `evidence`, the aggregated verdict vs. threshold in `actual`, and a remediation (tighten rubric anchors, add CoT, broaden ensemble, recalibrate to humans, fix prompt) in `suggested_fix`.

## Guardrails
Per `shared/guardrails.md`: seeded-sandbox only — judge against the golden set on a NON-PROD path; confirm NON-PROD or `status:error`. Eval prompts/references are **synthetic/consented and masked** — never real candidate PII in fixtures or the report (redact). Record seed + judge model ids + frozen rubric/prompt in every finding for deterministic repro. Read-only on the SUT (no retrain/write); cap `maxTurns`; respect judge-LLM rate limits (back off on 429). The judge is an aided oracle, not a human — a qualified human owns final sign-off on anything candidate-facing, and an uncalibrated judge never gates a release.

## Watch (do not gate)
Emerging only, do not fail the gate: multi-agent persona-judge panels ("several evaluator agents, each simulating a distinct persona"); debiasing frameworks (e.g. PINE) and prompt-perturbation/scoring-bias probes (rubric order, numeric-vs-Roman IDs); reward-hacking where the SUT learns to game the judge. Note these for the human reviewer.
