# risk-based-prioritization

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Rank what to test first by product risk — likelihood × impact — so finite test effort hits the highest-risk surface first. Answers: "Given limited time, which features/changes carry the most risk and must be tested deepest?"

## Inputs & preconditions
- Required artifacts: feature/change inventory, the change surface (diff/components touched), the RAID log (Risks, Assumptions, Issues, Dependencies), historical defect density per component, business-criticality of each feature.
- Target: the requirement/feature set + change metadata (read-only).
- Preconditions: features are enumerable and each can be assigned a likelihood and impact rating (scale defined in the plan, e.g. 1–5).

## Oracle (source of truth)
The **ISO/IEC/IEEE 29119** risk-based testing approach + a standard **risk matrix**: risk exposure = **likelihood × impact**, where likelihood draws on change frequency, complexity, and historical defect density, and impact draws on business-criticality, user reach, and failure cost (safety/financial/reputational). A **RAID** register frames risks/assumptions/issues/dependencies. Priority order follows risk exposure, NOT developer preference or feature recency.

## Step sequence (Plan → Act → Verify)
1. **Plan** — list every in-scope feature/change; gather its likelihood signals (complexity, churn, past defects) and impact signals (criticality, blast radius, regulatory exposure).
2. **Act** — score one item at a time: likelihood (1–5) × impact (1–5) → risk exposure; place each on the matrix band (low/medium/high/critical); record the rationale and RAID linkage. Skip-and-continue if an item lacks a scorable signal, marking it "unassessed".
3. **Verify** — assert every in-scope item is scored with a documented rationale, the ranking is monotonic in exposure, and high/critical-band items map to a deeper planned test depth (e.g. full BVA + negative + security vs smoke-only).

## Assertions & exit gate
- Every in-scope feature/change has a likelihood, impact, and computed exposure with rationale.
- Ranking is consistent with exposure (no high-impact-high-likelihood item ranked below a low-risk one).
- High/critical-band items are allocated proportionally deeper test coverage in the plan.
- **Gate:** `risk_ranking_complete` — passes when 0 unassessed in-scope items AND high-risk items have matching coverage depth (a high-risk feature left at smoke-only depth is a **major** prioritization finding).

## Output
Write `artifacts/risk-based-prioritization/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"risk_ranking_complete"}` + `notes` carrying the ranked risk register. Findings (`QA-RISK-NNN`) flag unassessed items or coverage/risk mismatches, citing the matrix band in `oracle`. The ranking feeds `test-strategy-plan` and execution order in `test-execution`.

## Guardrails
Read-only — `disallowedTools: Edit, Write` outside artifacts. Scores are recommendations; a human/PO confirms the final risk acceptance. Use only recorded signals (churn, defect history) — don't invent likelihoods; mark "unassessed" when data is missing. Cap `maxTurns`.
