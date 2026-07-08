# AI Testing Standards — External-Oracle Anchor for `60-ai-ml`

The classic flow groups ground their oracles in published standards — functional/structural testing in **ISTQB CTFL**, process in **ISO/IEC 29119**, web security in **OWASP WSTG**. The AI/ML group cannot: there is no single string to assert against, the system is probabilistic, and "looks right" is not an oracle. This doc is the standards anchor every `60-ai-ml` flow cites *instead of its own judgement*. A finding in this group is only valid when it maps to a named clause below — never because an output "felt" wrong.

Binding on every flow in `workflows/60-ai-ml/`. A flow whose finding cannot be traced to a row here must downgrade to `informational` and say so.

This is a **contract**, not a workflow: it does not run anything. It declares which external standard each `60-ai-ml` flow borrows its oracle from, so two different runs of the same flow reach the same verdict for the same reason. It sits beside `guardrails.md` (what a flow may not do) and `severity-priority-rubric.md` (how bad a finding is); together those three are the non-negotiable spine under every AI/ML flow.

## The four reference frameworks

| # | Framework | Scope it anchors | Authority |
|---|-----------|------------------|-----------|
| **CT-AI** | ISTQB Certified Tester — AI Testing | ML functional performance metrics (accuracy/precision/recall/F1), test oracles for non-deterministic systems, bias & fairness, adversarial/data-poisoning, explainability/interpretability, ML test data quality, neural-network/coverage criteria, metamorphic testing | ISTQB syllabus — https://www.istqb.org/certifications/certified-tester-ai-testing-ct-ai/ |
| **29119-11** | ISO/IEC TR 29119-11 — Testing of AI-based systems | Definitions + the *why AI is hard to test* canon: test oracle problem, non-determinism, data bias, the input space, metamorphic relations, ML acceptance criteria | ISO/IEC TR 29119-11:2020 |
| **AI RMF** | NIST AI Risk Management Framework 1.0 + the GenAI Profile (NIST-AI-600-1) | The Govern/Map/Measure/Manage loop; trustworthiness characteristics (valid & reliable, safe, secure, accountable, explainable, privacy-enhanced, **fair — with harmful bias managed**); GenAI-specific risks (confabulation, harmful bias, info-integrity) | NIST AI RMF 1.0 (2023) + GenAI Profile (2024) |
| **LLM Top-10** | OWASP GenAI LLM Top-10 (2025) | Attacker-facing risk taxonomy for LLM apps — LLM01 Prompt Injection … LLM10 Unbounded Consumption | https://genai.owasp.org/llm-top-10/ |

## Crosswalk — framework clause → which flow applies it

| Framework clause | Anchors flow(s) | How the flow uses it as oracle |
|------------------|-----------------|--------------------------------|
| **CT-AI** ML functional-performance metrics (acc/precision/recall/F1, confusion matrix) | `llm-eval-harness`, `llm-scoring-correctness` | Golden-set scoring thresholds are stated as CT-AI metrics, not ad-hoc; a regression is a metric drop past the stated bar. |
| **CT-AI** test-oracle problem / **29119-11** oracle + metamorphic relations | `llm-judge-eval`, `llm-scoring-correctness` | The LLM-judge and monotonicity/stability checks ARE the metamorphic/derived oracle for "no single correct string." Judge must prove human alignment first (CT-AI: humans remain gold standard). |
| **CT-AI** bias/fairness + **AI RMF** *Fair — harmful bias managed* | `fairness-bias-testing`, `llm-scoring-correctness` (cutoff slice) | Demographic parity / equalized odds / equal opportunity + 4/5ths adverse-impact are the named fairness oracle; counterfactual swaps = CT-AI's invariance test. |
| **CT-AI** adversarial / data-poisoning testing | `llm-red-teaming` | Adversarial-input class for the model layer; pairs with the OWASP rows below for the app layer. |
| **CT-AI** explainability / interpretability | `llm-scoring-correctness`, `llm-judge-eval` | A score/decision must carry a defensible rationale (legal artifact); unexplainable output is a finding. |
| **CT-AI** ML test-data quality + **29119-11** data bias | every flow (precondition) | Golden/labelled sets must be synthetic/consented, masked PII, version-tagged — enforced via `guardrails.md` §2. |
| **AI RMF** Measure function (quantify trustworthiness) | `llm-eval-harness`, `voice-telephony-qa` | The harness IS the Measure step; WER/booking-goal and per-feature metric slices are the measurement record. |
| **AI RMF** *Valid & reliable* + *Safe* | `llm-scoring-correctness`, `voice-telephony-qa` | Stability/calibration (reliable); telephony fault paths + refusal behaviour (safe). |
| **AI RMF GenAI Profile** confabulation / info-integrity | `llm-judge-eval` | The hallucination/faithfulness gate is the confabulation control; reply must stay faithful to source context. |
| **OWASP LLM01** Prompt Injection (direct + indirect) | `llm-red-teaming` | Direct injection + indirect via uploaded/parsed candidate content. |
| **OWASP LLM02** Sensitive Information Disclosure | `llm-red-teaming` | Cross-candidate PII leakage, training-data leakage. |
| **OWASP LLM06** Excessive Agency / **LLM07** System-Prompt Leakage | `llm-red-teaming` | Tool-abuse of booking/calendar/lookup; system-prompt extraction. |
| **OWASP LLM09** Misinformation / **LLM05** Improper Output Handling | `llm-judge-eval`, `llm-red-teaming` | Ungrounded claims (judge gate) and unsafe rendered/acted-on output. |
| **OWASP LLM10** Unbounded Consumption | `llm-red-teaming`, `voice-telephony-qa` | Cost/loop-bomb probes; bounded by `guardrails.md` §5 `maxTurns`. |

## Rules of use

- **Cite the clause in `oracle`.** Every `60-ai-ml` finding names its anchor (e.g. `oracle: "OWASP LLM01"` or `oracle: "CT-AI fairness / 4-5ths rule"`) — same way web findings name a WSTG id. No clause → no finding.
- **Layer the frameworks, don't pick one.** Model-layer behaviour anchors in CT-AI / 29119-11; app/agent-layer attacks anchor in OWASP LLM Top-10; the program-level "did we cover the right risks" question anchors in AI RMF. A complete `60-ai-ml` run touches all three layers.
- **Standards set the oracle, `severity-priority-rubric.md` sets the grade.** This doc decides *whether* a result is a defect; the rubric decides *how bad*. A confirmed LLM01 or a 4/5ths-rule breach defaults to **critical** per that rubric.
- **HR high-risk context.** Automated employment decisions fall under the AI RMF *Fair* characteristic and external law (EEOC 4/5ths, NYC Local Law 144 bias audit, EU AI Act high-risk) — the fairness and scoring flows treat these as hard gates, not advisory.
- **Versions are pinned.** OWASP = 2025 list; AI RMF = 1.0 + GenAI Profile NIST-AI-600-1; ISO = 29119-11:2020; CT-AI = current ISTQB syllabus. When a framework revises, update this doc before flows cite the new edition.
