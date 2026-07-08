# QA Agent — Multiflow Autonomous QA System

A full-scale, agentic QA system: one **orchestrator** decomposes a QA mandate into discrete, independently-runnable **workflows** (one per QA responsibility), runs them with a **Plan → Act → Verify** loop against a deployed system-under-test (SUT), and synthesizes structured findings into a single gating report.

Architecture and flow taxonomy are grounded in ISTQB CTFL v4.0, ISO/IEC/IEEE 29119, IEEE 829, OWASP WSTG, W3C WCAG, Martin Fowler's test pyramid, Anthropic's multi-agent research-system design, and the Claude Code subagent spec. See `shared/` for the contracts every flow obeys.

---

## Architecture

```
   trigger (PR / pre-deploy / manual)
        │
        ▼
  ┌─────────────────────────────────────────────┐
  │ ORCHESTRATOR (qa-orchestrator)               │
  │ - reads mandate + change surface             │
  │ - effort-scales: which flows, order          │
  │ - deterministic gate logic                   │
  │ - persists plan; merges findings             │
  └───────────────┬─────────────────────────────┘
        fan-out (parallel, independent flows)
   ┌────────┬────────┬────────┬────────┬────────┐
   ▼        ▼        ▼        ▼        ▼        ▼
 smoke   api-     regression security perf   exploratory ...
 (Haiku) contract  (post-    (sub-fan (vs    (browser)
          (Sonnet)  smoke)    /endpt)  SLOs)
   │        │        │        │        │        │
   └─ each flow: Plan→Act→Verify, grounded oracle, guardrails ─┘
                  │ writes artifacts/<flow>/report.json
                  ▼
        ┌───────────────────────────┐
        │ SYNTHESIZER + CRITIC      │  adversarial recheck of
        │ merge · severity/priority │  high-severity findings
        │ emit JUnit XML + summary  │
        └────────────┬──────────────┘
                     ▼
            QUALITY GATE → pass / fail
```

**Design principles (non-negotiable):**
- **Deterministic skeleton, model-driven within a flow.** Which flows run + gate logic are deterministic; reasoning happens *inside* a flow.
- **Grounded oracles.** Truth comes from the spec / baseline / SLO / golden DB — **never** the SUT's own output. (LLM-written assertions otherwise lock current bugs in as "expected".)
- **Isolated workers, supervisor-only coordination.** Flows don't talk to each other; each writes `artifacts/<flow>/report.json`; the orchestrator merges.
- **Least privilege + non-destructive.** Read-only flows deny Edit/Write; `PreToolUse` guard blocks destructive DB/HTTP; never test against production data — use seeded/golden DBs.
- **Cost-aware.** Cheap flows → Haiku; cap `maxTurns`; multi-agent runs cost ~15× chat tokens — gate on value.

---

## Flow catalog (49 workflows)

Each lives in `workflows/<category>/<flow>.md` following `shared/workflow-template.md`.

### 00 · Lifecycle / Process
1. `requirements-review` — BRD / user-story ambiguity & testability review
2. `test-strategy-plan` — test strategy + plan generation (IEEE 829 / 29119-3)
3. `test-case-design` — EP, BVA, decision-table, state-transition, pairwise
4. `test-data-management` — subsetting, masking, synthetic generation
5. `test-environment` — provision & verify prod-like env
6. `test-execution` — orchestrate manual + automated runs
7. `defect-triage` — log, severity/priority, lifecycle tracking
8. `regression-suite-maintenance` — curate, prune, de-flake
9. `test-reporting-metrics` — dashboards, coverage, defect metrics
10. `release-readiness` — exit-criteria check, sign-off, closure
11. `risk-based-prioritization` — RAID / risk matrix
12. `traceability-coverage` — requirement→test traceability & gaps

### 10 · Functional test types
13. `smoke` — build-verification
14. `sanity` — targeted change verification
15. `functional` — specification-based
16. `confirmation-retest` — verify a fix resolved the defect
17. `regression` — guard unchanged behavior
18. `exploratory` — charter-based autonomous bug hunting
19. `negative-boundary` — invalid inputs, edge/boundary, error handling
- `property-based` — invariant/round-trip/metamorphic PBT with randomized generation + shrinking **(new)**

### 20 · Interface, data & integration
20. `api-contract` — REST/GraphQL/gRPC schema + status + CRUD
21. `contract-testing` — consumer-driven (Pact)
22. `service-virtualization` — mocking/stubbing dependencies
23. `event-queue-testing` — async messaging, ordering, idempotency, DLQ
24. `database-validation` — integrity, constraints, CRUD, reconciliation
25. `etl-pipeline` — extract/transform/load correctness
- `schema-fuzzing` — Schemathesis/Dredd: spec-derived valid+malformed requests, response conformance **(new)**
- `spec-compatibility` — static breaking-change diff (oasdiff/buf/Spectral), PR-gated **(new)**
- `schema-migration` — forward+rollback, expand-contract zero-downtime **(new)**
- `data-quality` — six DQ dimensions + freshness/distribution (Great Expectations/Soda) **(new)**
- `email-deliverability-qa` — template/links/compliance via a test-double mail sink **(new)**
- `booking-calendar-qa` — timezone/DST, double-booking races, reschedule/no-show round-trip **(new)**

### 30 · Non-functional
26. `performance-load` — latency/throughput vs SLOs
27. `stress-spike-soak` — breaking point, surges, endurance, scalability
28. `security` — SAST/DAST, OWASP Top 10, authz/authn, injection, secrets
29. `reliability-recovery` — resilience, failover, backup/restore, DR

### 40 · UX & compliance
30. `accessibility` — WCAG A/AA (POUR)
31. `usability` — ease-of-use, task success
32. `localization-i18n` — locale/encoding/RTL/format + translation
33. `cross-browser-compat` — browsers, OS, devices, responsive

### 50 · Automation & platform
34. `ci-quality-gates` — gating, flaky-test management, parallelization
35. `specialized` — mobile, microservices, AI/ML model, chaos, canary/prod (shift-right)
- `mutation-testing` — mutation score as suite-adequacy gate (kills coverage-theatre) **(new)**

### 60 · AI / ML (new)

- `llm-eval-harness` — golden-dataset eval, CI-gated, prompt-regression on every model/prompt change
- `llm-judge-eval` — calibrated LLM-as-judge + hallucination/faithfulness gate + judge-bias mitigation
- `fairness-bias-testing` — demographic parity / equalized odds across protected attributes (hiring-AI legal)
- `llm-red-teaming` — prompt-injection / jailbreak / excessive-agency vs OWASP LLM Top-10
- `voice-telephony-qa` — Vapi: WER, barge-in, call-drop/reconnect, completed-call booking outcome
- `llm-scoring-correctness` — the screening score as a decision instrument: calibration, monotonicity, drift, adverse impact

---

## Specialized subagents

Flows that benefit from isolation are also exposed as Claude Code subagents in `agents/` (symlinked into `.claude/agents/` for discovery): `qa-orchestrator`, `api-contract-tester`, `security-scanner`, `performance-tester`, `regression-tester`, `smoke-tester`, `data-integrity-tester`, `exploratory-tester`, `accessibility-tester`, `llm-eval-tester` (60-ai-ml), `migration-validator`, `event-queue-tester`, `etl-validator`. Each runs in its own context, scoped to least-privilege tools, and returns a structured report.

## Running it

- **Single flow:** invoke the matching subagent (e.g. `api-contract-tester`) with the SUT base URL + spec path.
- **Full sweep:** the `qa-orchestrator` reads the mandate, fans out the relevant flows, and emits the gating report.
- **CI:** run headless (`claude -p` / Claude Agent SDK) → flows emit JSON → render JUnit XML → CI gate blocks on any failed gate or open critical finding. PR gate ≤ 5–10 min (smoke + fast API regression); slow E2E/perf nightly.

## Contracts (read these first)
- `project-qa-config.md` — **the per-project QA brain** (SUT URLs/ports, start command, test creds, stack, oracles, CI gates, scope) — at the qa-agent root; auto-created per project by the `qa-orchestrator`.
- `shared/workflow-template.md` — the shape every flow file follows
- `shared/finding-schema.md` — the finding/defect object
- `shared/severity-priority-rubric.md` — severity (agent sets) vs priority (human finalizes)
- `shared/report-format.md` — per-flow `report.json` + JUnit XML mapping
- `shared/guardrails.md` — non-destructive / sandbox / secrets / cost rules
- `shared/tool-cookbook.md` — concrete command idioms (curl, inline JSON asserts, bash-& concurrency, grep-verify, k6/ZAP/gitleaks, semantic-similarity)
- `shared/ai-testing-standards.md` — ISTQB CT-AI / ISO 29119-11 / NIST AI RMF / OWASP LLM Top-10 crosswalk (the 60-ai-ml anchor)
- `shared/non-determinism-strategy.md` — run-N / pass-rate / "temp=0 ≠ deterministic" gating for LLM flows
- `shared/hermeticity-and-test-sizing.md` — hermeticity + test sizing + order-independence (flake prevention)
