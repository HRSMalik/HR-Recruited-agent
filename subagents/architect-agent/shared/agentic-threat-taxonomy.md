# Agentic Threat Taxonomy — STRIDE + LINDDUN Extended for LLM and Agentic Systems

Every threat-modeling flow that touches an AI/ML component, a retrieval-augmented system, an LLM-backed service, or a multi-agent orchestration must ground its analysis in this taxonomy. Classical STRIDE (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege) and LINDDUN (Linkability, Identifiability, Non-repudiation, Detectability, Disclosure of information, Unawareness, Non-compliance) remain the baseline for trust-boundary enumeration. This contract extends them with four industry-standard lenses that cover the novel attack surface introduced by foundation models, embedding spaces, agentic autonomy, and the adversarial ML technique catalog: (1) the OWASP Top 10 for LLM Applications 2025 (published November 2024) for application-layer controls; (2) the Cloud Security Alliance MAESTRO 7-layer agentic threat framework for layered risk decomposition; (3) MITRE ATLAS (Adversarial Threat Landscape for AI Systems) for technique-level tracking of ML-specific attacks; and (4) NIST AI RMF 1.0 + AI 600-1 Generative AI Profile for governance and risk-management framing. Flows use this file as their threat catalog; findings follow `finding-schema.md`; architectural controls are recorded as ADRs; coverage gaps on a trust boundary are hard-oracle failures (`quality-attribute-rubric.md`). Cross-ref: `workflows/40-cross-cutting/security-architecture.md` (STRIDE sweep, zero-trust, defense-in-depth).

---

## Part 1 — OWASP Top 10 for LLM Applications 2025

The authoritative application-layer vulnerability list for LLM-integrated systems. Each entry states the threat mechanism, the architectural trust boundaries it crosses, and the minimum design control the `security-architect` must verify is present. An uncovered item on a trust boundary that is in-scope for that threat is a `critical` / `oracle:"hard"` finding.

### LLM01 — Prompt Injection

**Mechanism.** Attacker-controlled input — direct (user turn) or indirect (retrieved documents, tool output, external web content) — overrides the developer's intended instructions to the model, redirecting model behavior to serve attacker goals. Indirect prompt injection is especially dangerous in agentic systems where the model reads untrusted data (emails, web pages, database rows) as part of a reasoning loop. Combines elements of STRIDE-Tampering (altering the effective instruction set) and STRIDE-Elevation of Privilege (gaining capabilities the system prompt was designed to restrict).

**Trust-boundary crossings.** User → LLM; external data source → LLM (via retrieval or tool call); tool output → orchestrator.

**Design control.** (a) Treat every input source at a separate trust level; never mix instruction-plane and data-plane in a single prompt template without explicit structural delimiters that the model cannot be instructed to ignore (e.g., system-prompt fence + input-sanitization layer). (b) For indirect injection: validate, strip, and contextually escape all retrieved content before it enters the model context; prefer structured over free-text retrieval. (c) Apply an LLM-as-judge output filter or a rule-based policy layer (e.g., an OPA guardrail) that evaluates model output before it reaches any tool invocation or user-facing surface. (d) Log the raw user input and the model's final instruction-trace for repudiation audits (LINDDUN Non-repudiation). **Oracle:** every data-ingestion path to the model is tagged with a trust tier; no path admits untrusted content into the instruction plane without a sanitization + output-validation step — verifiable by tracing the data-flow diagram.

---

### LLM02 — Sensitive Information Disclosure

**Mechanism.** The model surfaces training-memorized data (PII, API keys, medical records, source code), confidential context-window content (system prompts, other users' session content in a multi-tenant system), or retrieval-augmented documents the caller should not access. Maps to STRIDE-Information Disclosure and LINDDUN-Disclosure of Information.

**Trust-boundary crossings.** LLM output → user; retrieval store → LLM context.

**Design control.** (a) Apply attribute-based access control (ABAC) at the retrieval layer — retrieve only documents the requesting identity is authorized to read, enforced *before* they enter the model context (not by asking the model to filter them). (b) Implement output scanning for PII/secret patterns (regex + ML classifier) as a post-generation step before delivery. (c) Enforce context-window isolation per tenant/session: separate vector namespaces, separate conversation stores, no cross-session context bleed. (d) Never include long-lived credentials or secrets in the system prompt; inject via bound environment references readable only by the runtime. **Oracle:** a retrieval authorization bypass attempt (cross-tenant document fetch) returns empty or an authorization error — traceable in the retrieval-layer access log, not left to the model's judgment.

---

### LLM03 — Supply Chain

**Mechanism.** Compromise of a base model (pre-training poisoning, malicious fine-tune artifact in a registry), an embedding model, a third-party plugin/tool, a prompt library, or the ML dependency stack (PyPI packages, Hugging Face Hub artifacts, ONNX/TensorRT exports). Combines STRIDE-Tampering (artifact integrity) with supply-chain threats cataloged in MITRE ATLAS (AML.T0010 — ML Supply Chain Compromise).

**Trust-boundary crossings.** Model registry → serving infrastructure; third-party tooling → orchestration layer.

**Design control.** (a) Pin model artifact digests (SHA-256 of weights checkpoint) in the deployment manifest; verify digest at load time before serving. (b) Apply SLSA Level 2+ to the ML pipeline: provenance attestations on training datasets and fine-tuned model artifacts stored in a model registry (e.g., MLflow, Vertex AI Model Registry). (c) Audit third-party plugins and tools against a known-good allowlist; enforce no-network for plugin sandboxes where possible. (d) Run a dependency vulnerability scan (Dependabot / Safety / OSV-Scanner) on the inference-service dependency tree in CI. **Oracle:** model artifact digest matches the signed manifest at every deployment — verifiable by the CD pipeline gate log; the gate must emit a pass/fail record naming the artifact, the expected digest, and the observed digest.

---

### LLM04 — Data and Model Poisoning

**Mechanism.** Adversarial manipulation of training data, fine-tuning datasets, or RLHF preference data to embed backdoors (trigger→behavior associations), degrade model reliability on specific inputs, or bias outputs toward attacker-preferred content. Closely mapped to MITRE ATLAS AML.T0019 (Training Data Poisoning) and AML.T0043 (Craft Adversarial Data).

**Trust-boundary crossings.** External/crowdsourced data → training pipeline; human annotators → RLHF feedback store.

**Design control.** (a) Curate training and fine-tuning datasets from verified, provenance-tracked sources; maintain dataset lineage metadata (source, date, hash, annotation method). (b) Apply statistical anomaly detection on fine-tuning datasets before use: out-of-distribution label distributions, unusually high label agreement on specific rare triggers, sudden distribution shift. (c) Separate the annotation pipeline from production annotation access; apply a two-reviewer rule for RLHF preference labels on sensitive capability domains. (d) Post-train: run backdoor/trojan detection scans (e.g., ART's backdoor detection, activation clustering analysis) against the final model before promotion to serving. (e) For RAG pipelines: treat the knowledge base as mutable attack surface — apply data-integrity hashes on indexed documents and alert on unexpected bulk mutation. **Oracle:** the dataset lineage graph is machine-readable and complete (every training artifact has a source + hash + annotation provenance entry); verified by the model registry's provenance attestation, not by assertion.

---

### LLM05 — Improper Output Handling

**Mechanism.** Application code that consumes LLM output treats it as trusted: passing model-generated SQL/shell/HTML/JSON to downstream executors without sanitization. This is a second-order injection — the model's output is the attack vector for classical injection (SQL injection, XSS, command injection, SSRF) in whatever system consumes it. Maps to STRIDE-Elevation of Privilege and STRIDE-Tampering on the downstream executor.

**Trust-boundary crossings.** LLM output → application code → database / OS / browser / external API.

**Design control.** (a) Treat LLM output as *untrusted user input* at every downstream consumption point; apply the same sanitization, parameterization, and escaping you would for user-supplied data. (b) For SQL generation: use parameterized queries, never `format()`-string concatenation. (c) For HTML/Markdown rendering: escape model output before rendering in a browser (no `innerHTML` on raw model output). (d) For shell/command execution (agentic tools): use an allowlist of permitted commands + argument schemas; never pass raw model text to `exec()`/`subprocess.run(shell=True)`. (e) Define a strict JSON schema for every structured output and validate against it before use. **Oracle:** every code path that consumes model output and passes it to a downstream executor is enumerated in the data-flow diagram, and each is associated with a named sanitization/validation step — traceable by static analysis or code review.

---

### LLM06 — Excessive Agency

**Mechanism.** The model (or an autonomous agent) is granted more permissions, tool access, or autonomous action scope than the task requires. When combined with a prompt injection or model error, the excessive permissions amplify blast radius: the agent deletes records, sends emails, makes API calls, or mutates infrastructure it should never have touched. A pure application of the principle of least privilege failure — STRIDE-Elevation of Privilege in the agentic context.

**Trust-boundary crossings.** Agent → tool API; orchestrator → sub-agent; agent → external service.

**Design control.** (a) Grant each agent/tool the narrowest permission scope that satisfies the task — scope tool access per agent role, not per agent binary. (b) Classify actions by reversibility: read-only, reversible-write, irreversible-write. Gate irreversible-write actions behind an explicit human-in-the-loop confirmation step (a structured approval token the orchestrator must receive before the tool is invoked). (c) Implement a per-session action budget (max N tool calls, max M external API calls) enforced by the orchestrator, not the model. (d) Log every tool invocation with the agent identity, tool name, input arguments, and output — full audit trail for repudiation. (e) Prefer read-before-write: agents confirm the current state before mutating it; prefer two-phase (plan + execute) over single-pass execution for irreversible actions. **Oracle:** for each tool in the agent's tool manifest, document the scope of access granted and verify it is the minimum required — checked against the least-privilege matrix in the security ADR; no tool grants write access to a resource the agent's task does not require writes on.

---

### LLM07 — System Prompt Leakage (2025)

**Mechanism.** The model can be induced — through direct prompting, jailbreaking, or indirect injection — to reveal the contents of its system prompt, exposing proprietary instructions, persona configuration, security rules, or operational secrets embedded there. Maps to STRIDE-Information Disclosure and LINDDUN-Disclosure of Information.

**Trust-boundary crossings.** LLM context → user output.

**Design control.** (a) Assume the system prompt is not a secret channel — treat it as low-confidentiality; do not place long-lived credentials, PII, or high-value proprietary IP in the system prompt. (b) Add an explicit instruction in the system prompt not to repeat, quote, or paraphrase the prompt; while not a hard control (the model can be instructed away from it), it raises the bar. (c) Apply output scanning for system-prompt fingerprints (known key phrases, instruction patterns) as a post-generation filter. (d) Separate behavioral configuration from the system prompt: use function-calling schema and tool definitions for capabilities; reserve the system prompt for minimal persona + safety framing only. (e) Rotate and version system prompts; treat any leaked prompt as a "secret rotation" event requiring an update. **Oracle:** a red-team probe (20 standardized jailbreak + extraction attempts from OWASP LLM01/07 test suite) against the production system returns no verbatim system-prompt quote — pass/fail, logged by the `security-architect`'s verification step.

---

### LLM08 — Vector and Embedding Weaknesses (2025)

**Mechanism.** Attacks targeting the vector database / embedding layer of RAG systems: (a) *embedding inversion* — recovering approximate original text from stored embeddings; (b) *poisoning* — inserting adversarial documents whose embeddings are semantically proximate to sensitive queries, hijacking retrieval; (c) *model extraction* — querying the embedding endpoint to reconstruct a model surrogate. Also covers inadequate access control on the vector store allowing cross-tenant retrieval (see LLM02). Maps to MITRE ATLAS AML.T0025 (Model Inversion) and AML.T0016 (Obtain Capabilities: ML Artifacts).

**Trust-boundary crossings.** External document ingestion → embedding pipeline → vector store; user query → embedding model → vector store.

**Design control.** (a) Treat the vector store as a data store with full ABAC — enforce namespace/tenant isolation at the vector-DB query level, not at the application layer alone. (b) Protect against embedding inversion: add differential-privacy noise to stored embeddings at a level calibrated to the sensitivity of the source documents (accept some retrieval precision loss as the tradeoff). (c) Anomaly-detect bulk or systematic embedding queries that resemble model-extraction sweeps (high-volume, diverse queries from a single identity in a short window → rate-limit + alert). (d) Apply document authenticity checks at ingestion: only index documents from trusted, verified sources; reject documents whose embeddings cluster unnaturally close to high-sensitivity query centroids (statistical outlier gate). (e) Monitor retrieval accuracy as an operational SLO; a poisoning attack degrades it — make it observable. **Oracle:** cross-tenant document retrieval (a query under identity A that should surface only identity B's documents) returns zero results — verified by the retrieval authorization fitness function (`tests/fitness/rag-authz-isolation.test.ts` or equivalent).

---

### LLM09 — Misinformation

**Mechanism.** The model generates plausible-sounding but factually incorrect, outdated, or fabricated content (hallucination) that the application presents as authoritative. In high-stakes domains (legal, medical, financial, insurance) this is a liability and compliance risk, not just a UX issue. Maps to NIST AI RMF — Trustworthiness → Accuracy and Reliability; AI 600-1 § 2.5 (Confabulation).

**Trust-boundary crossings.** LLM output → user-facing application → end-user decision.

**Design control.** (a) Ground high-stakes outputs in retrieved, cited sources (RAG with citation) — the model output must reference a specific document chunk the user or auditor can inspect. (b) Apply a confidence-gating step: if the model's response cannot be grounded in retrieved context with similarity above a threshold, respond with "I don't have verified information on this" rather than hallucinating. (c) For critical facts (claim amounts, coverage terms, legal citations), implement a retrieval-verification pass: retrieve the claim from the authoritative source and compare with the model's output; flag divergence. (d) Instrument hallucination rate as a model-quality SLO (using a held-out QA evaluation set evaluated nightly); set an alert threshold. (e) Include a disclosure to end-users that outputs are AI-generated and should be verified for high-stakes decisions. **Oracle:** on a held-out factual QA evaluation set (≥ 200 questions with authoritative ground-truth answers), the model's factual accuracy is ≥ the threshold defined under the `ai_component.reliability_slo.factual_accuracy_pct` key in `project-architecture-config.md`; if that key is absent the default floor is 80 % and the missing key is itself a `major` finding. Measured nightly by the model-eval pipeline and the result is a required input to the VERIFY gate.

---

### LLM10 — Unbounded Consumption

**Mechanism.** Denial of service through resource exhaustion: excessively long prompts, recursive tool calls, prompt-triggered compute-intensive generation, or large context-window abuse that spikes inference cost and degrades availability for legitimate users. In a multi-tenant system it also enables a noisy-neighbor attack. Combines STRIDE-Denial of Service with cost-amplification (NIST AI RMF — Trustworthiness → Reliability).

**Trust-boundary crossings.** User request → inference endpoint; tool-call output → model context (recursive expansion).

**Design control.** (a) Enforce input token limits per request at the API gateway, before the model is invoked — reject or truncate above a hard ceiling. (b) Cap output token generation per request and per session (max-tokens parameter, enforced by the inference runtime). (c) Implement per-user / per-tenant rate limits on the inference endpoint (requests/minute, tokens/day) with a backpressure queue and a 429 response; wire the rate-limiter to the alerting system. (d) For agentic loops: enforce a hard cap on recursive tool-call depth and total tool invocations per root request — the orchestrator must count and enforce, not rely on the model's self-termination. (e) Monitor inference cost per tenant as a FinOps metric; set a per-tenant cost budget alert. **Oracle:** a load test delivering N concurrent requests each at the max-token ceiling sustains p99 inference latency ≤ the QAS target and total cost stays within the defined budget envelope — verified by the performance-capacity flow (`workflows/40-cross-cutting/performance-capacity.md`).

---

## Part 2 — MAESTRO: 7-Layer Agentic Threat Framework (Cloud Security Alliance)

MAESTRO (Multi-Agent Environment Security Threat and Risk Ontology) from the CSA AI Safety Working Group decomposes agentic systems into seven layers, each with its own threat surface. Use MAESTRO to ensure threat coverage is complete and layer-appropriate — an agentic STRIDE sweep that stops at the application boundary misses layers 1–3 and 7.

| Layer | Name | Threat Surface | Minimum Coverage Requirement |
|---|---|---|---|
| **L1** | Foundation Model | Pre-training data poisoning; model inversion; adversarial inputs; jailbreak/alignment failure; model extraction (ATLAS AML.T0040). | Document which foundation model(s) are used, their provenance, fine-tuning lineage, and alignment/safety evaluation results. Assess LLM03, LLM04, LLM07. |
| **L2** | Data | Training/fine-tuning datasets, knowledge bases, RAG corpora, vector stores, prompt templates stored as data. Poisoning, unauthorized access, exfiltration, integrity tampering. | Access control + integrity verification on every data store; dataset provenance lineage. Assess LLM02, LLM04, LLM08. |
| **L3** | Agent Frameworks | The orchestration framework (LangChain, AutoGen, CrewAI, custom): tool definitions, plugin manifests, chain/workflow configurations, memory/state management. Supply chain risk in framework dependencies; misconfigured tool permissions; unsafe deserialization of agent state. | Pin framework versions + audit tool manifests for excessive-agency grants. Assess LLM03, LLM06. |
| **L4** | Deployment Infrastructure | Container runtime, Kubernetes/serverless, inference hardware (GPU), secrets management, network ingress/egress. Classical infra threats + GPU-specific side-channels, inference service exposure. | Standard cloud-security controls (zero-trust networking, secrets-in-Vault, image digest pinning, RBAC) plus inference-endpoint authentication. Cross-ref `workflows/40-cross-cutting/security-architecture.md`. |
| **L5** | Observability & Monitoring | Logging pipeline, tracing backend, evaluation systems, dashboards. Threats: log injection (corrupt the audit trail), monitoring blind spots (agent actions not logged), adversarial evaluation gaming. | Every agent action is logged with identity + tool + input + output; logs are tamper-evident (append-only store, signed). Assess LLM05 (output consumed by monitoring), repudiation (STRIDE-R). |
| **L6** | Security Controls | The guardrail/policy layer: output classifiers, OPA policy, content filters, rate limiters, human-in-the-loop gates. Threats: guardrail bypass (jailbreak, indirect injection routed around the filter), adversarial inputs that confuse the classifier. | Adversarial evaluation of every guardrail (red-team using OWASP LLM01–10 probe set) before production promotion; guardrail coverage mapped to threat controls. |
| **L7** | Agent Ecosystem | Multi-agent topologies: agent-to-agent communication, sub-agent delegation, external API integrations, third-party plugin marketplace. Trust propagation failures (an agent trusts a sub-agent's claims without re-authentication), confused-deputy attacks, cascading permission escalation. | Every inter-agent call is authenticated (not ambient trust); sub-agent outputs are treated as untrusted input by the receiving agent; each agent has its own least-privilege tool scope (not inherited from orchestrator). Assess LLM06, LLM01 (indirect injection via sub-agent output). |

**How to use MAESTRO in a threat-modeling flow.** Walk the architecture's component diagram layer by layer (L1 → L7). For each layer, enumerate the components present, list the applicable threats, and confirm the minimum coverage requirement above is satisfied. Record uncovered layers as `type:"security"`, `severity:"critical"`, `oracle:"hard"` findings.

---

## Part 3 — MITRE ATLAS: Adversarial ML Technique Catalog

MITRE ATLAS (Adversarial Threat Landscape for AI Systems, atlas.mitre.org) is the ML-specific analog of MITRE ATT&CK — a tactics × techniques × sub-techniques matrix for adversarial attacks on ML systems. Reference it when sweeping ML components for technique-level threat coverage; do not reassemble the full matrix here — cite the technique IDs.

### Tactics and key techniques to sweep per ML component

| Tactic | Representative Techniques | Sweep target |
|---|---|---|
| **ML Model Access** | AML.T0040 (ML Model Inference API Access), AML.T0041 (Develop Capabilities: ML Artifacts) | Inference endpoint — is it publicly accessible without authn? Is there an unauthenticated model-info endpoint? |
| **Reconnaissance** | AML.T0000 (Search for Victim's AI Artifacts), AML.T0002 (Acquire Public ML Artifacts) | Is the model family/version discoverable from public metadata? Does a fingerprinting query reveal the base model? |
| **Resource Development** | AML.T0016 (Obtain Capabilities: ML Artifacts), AML.T0017 (Develop Adversarial Examples) | Does the attacker need model weights or API access to build adversarial examples? Is the API rate-limited to slow surrogate model training? |
| **Initial Access** | AML.T0043 (Craft Adversarial Data — supply chain), AML.T0051.000 (LLM Prompt Injection) | Supply chain ingestion path; user-facing prompt input. |
| **ML Attack Staging** | AML.T0025 (Model Inversion), AML.T0024 (Exfiltration via API), AML.T0020 (Poison Training Data) | Training pipeline; embedding store; model registry. |
| **Impact** | AML.T0029 (Denial of ML Service), AML.T0031 (Erode Model Integrity), AML.T0047 (Influence Operations) | Inference availability; model accuracy degradation; generated disinformation in output. |

**Application rule.** For every ML component in the architecture (foundation model, fine-tuned model, embedding model, reranker, classifier/guardrail), run the ATLAS tactic sweep above. For each applicable technique, document: (a) whether the attack path is present, (b) the control in place, and (c) the ATLAS technique ID. An ML component with no ATLAS sweep documented is a `type:"security"` / `severity:"major"` finding.

---

## Part 4 — NIST AI RMF 1.0 + AI 600-1 Generative AI Profile

NIST AI RMF 1.0 (January 2023) defines four functions — **Govern, Map, Measure, Manage** — as the risk-management lifecycle for AI systems. NIST AI 600-1 (Generative AI Profile, July 2024) extends the RMF with 12 unique risks specific to generative AI. Use this framing to position architecture controls within the risk-management governance structure.

### AI RMF Core Functions → Architecture responsibilities

| Function | What it requires | Architecture artifact |
|---|---|---|
| **Govern** | Establish AI risk policies, accountability structures, and human oversight requirements. Assign AI risk ownership. | AI risk policy documented; human-in-the-loop gates specified per decision class (reversible vs irreversible agent actions). Cross-ref ADR for LLM06 control. |
| **Map** | Identify the AI system's context, intended use, affected stakeholders, and potential harms. Enumerate the threat surface. | Architecture context diagram (C4 L1); stakeholder table; MAESTRO layer sweep; ATLAS sweep. |
| **Measure** | Define and collect metrics to evaluate risk — accuracy, hallucination rate, fairness, robustness, security. | Model quality SLOs (hallucination rate, factual accuracy on eval set — LLM09 control); adversarial robustness evaluation; bias evaluation report. |
| **Manage** | Act on measured risks: mitigate, accept, transfer, or avoid. Establish incident response for AI failures. | Risk register (ADR-shaped, with accepted/mitigated/monitored disposition per threat); AI incident response runbook cross-linked to the on-call playbook. |

### AI 600-1 Generative AI Unique Risks → Control mapping

| AI 600-1 Risk | Definition | Control |
|---|---|---|
| **Confabulation** | Model generates plausible but factually incorrect content. | RAG + citation grounding; confidence gating; factual accuracy SLO. (→ LLM09) |
| **Data Privacy** | Training data or context contains PII; outputs reveal private information. | PII classification of training data; output PII scanning; ABAC at retrieval. (→ LLM02) |
| **Harmful Bias / Homogenization** | Model outputs exhibit demographic bias or converge on a narrow worldview. | Bias evaluation suite in the model-quality pipeline; diverse evaluation set; fairness SLO. |
| **Human-AI Configuration** | Over-reliance on AI; lack of appropriate human oversight of AI decisions. | Mandatory human-in-the-loop gates for irreversible actions; confidence disclosure to end-users. (→ LLM06) |
| **Information Integrity** | AI-generated content used to spread disinformation; lack of provenance. | Watermarking / provenance tagging of AI-generated content; disclosure obligation in the UX. (→ LLM09) |
| **Information Security** | Novel attack surface from model endpoints, context, and agent actions. | Full OWASP LLM01–10 coverage; MAESTRO sweep; ATLAS sweep. (→ all OWASP entries above) |
| **Intellectual Property** | Model reproduces copyrighted training material verbatim. | Output memorization detection (n-gram similarity against training corpus); IP risk policy. |
| **Obscene / Harmful Content** | Unintended generation of harmful, offensive, or illegal content. | Content safety classifier as a post-generation guardrail (L6); red-team content evaluation. |
| **Overconsumption** | Unbounded compute/cost consumption. | Token limits, rate limiting, per-tenant cost budgets. (→ LLM10) |
| **Privacy** | Beyond data privacy: inference of private attributes from model outputs or embeddings. | Embedding differential privacy; output inference controls; user consent flows. (→ LLM08) |
| **Value Chain / Third-Party Risks** | Dependencies on third-party models, plugins, data suppliers, and APIs introduce uncontrolled risk. | Third-party AI vendor risk assessment; plugin allowlist; model registry provenance. (→ LLM03) |
| **Unreliable or Unsafe Behavior** | Unsafe or unpredictable agentic actions, especially in novel contexts. | Agentic action budget + sandboxing; formal pre/post-condition specification for tool invocations; chaos/fault-injection testing of the agentic loop. (→ LLM06, LLM10) |

---

## Threat-Modeling Execution Rules (binding on all flows that use this taxonomy)

**1. Assign each threat to a trust boundary.** Every threat in this taxonomy must be anchored to a specific trust boundary in the data-flow diagram. A threat not assigned to a boundary is not documented — it is invisible. Use the C4 L2/L3 container/component diagram (`workflows/70-documentation/c4-model-diagrams.md`) as the base.

**2. Cover all four frameworks per ML component.** For each ML component (model, embedding, RAG pipeline, agent, multi-agent topology): complete the OWASP LLM01–10 sweep, the MAESTRO L1–L7 layer sweep, the ATLAS tactic sweep, and the AI 600-1 risk mapping. Partial coverage on an in-scope component is a `critical` / `oracle:"hard"` finding.

**3. Every threat must resolve to a control or an accepted risk.** A documented threat with no control and no explicit accepted-risk ADR is a `critical` finding. Controls are architectural (not aspirational): they are named patterns, specific system components, or verifiable configuration — not "we will add monitoring."

**4. Accepted risks are ADR-shaped.** If a threat is accepted (not mitigated), record an ADR: threat ID, decision to accept, rationale, consequences, and the conditions under which the acceptance must be re-evaluated (e.g., "accepted for MVP because we have no RAG component; re-evaluate when retrieval is added").

**5. Verification by the security-architect is a hard gate.** Per `guardrails.md` § 5, the security dimension of the verification step runs the OWASP LLM red-team probe set and the ATLAS technique checklist against the live or staged system. A failed probe result (an injection succeeds, a cross-tenant retrieval returns data, a system prompt is disclosed) is a `critical` / `oracle:"hard"` failure that blocks the VERIFY → pass transition. Cross-ref `workflows/40-cross-cutting/security-architecture.md` for the full STRIDE integration and the threat-model artifact format.
