# test-data-management

**Category:** 00-lifecycle
**Runs as:** subagent: ../.claude/agents/data-integrity-tester.md
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Provision the test data each suite needs — representative, edge-covering, and privacy-safe — via subsetting, masking/anonymization, and synthetic generation. Answers: "Do we have the right data, with no real PII, to exercise every designed case?"

## Inputs & preconditions
- Required artifacts: the case suite (from `test-case-design`), data dictionary / schema + referential constraints, the partitions/boundaries needing fixtures, applicable privacy regime.
- Target: an **isolated, NON-PROD** seed DB (e.g. `<db>-qa` on local/staging) + a connection string from env.
- Preconditions to assert before acting: host/DB is confirmed NON-PROD (STOP + `status:error` if a prod connection string appears); the schema is reachable; the target DB is empty or owned by QA.

## Oracle (source of truth)
The designed cases' data requirements + the schema's referential-integrity constraints, plus privacy law: **GDPR** (pseudonymisation Art. 4(5) / data minimisation Art. 5) and **HIPAA Safe Harbor** de-identification (18 identifiers removed). Masking must be **format-preserving** and **referentially consistent** (same source value → same masked value across tables). Real production PII is NEVER a valid fixture.

## Step sequence (Plan → Act → Verify)
1. **Plan** — for each partition/boundary, decide source: **subset** a representative slice (consistent foreign keys), **mask/anonymize** sensitive fields (deterministic FPE/tokenization for emails, names, SSNs, DOBs), or **synthesize** edge data (max-length strings, unicode/RTL, leap dates, nulls, boundary numerics) where production lacks the case.
2. **Act** — seed the sandbox DB one fixture set at a time; apply masking before any sensitive value lands; record a fixture/seed id per set. Skip-and-continue if one fixture violates a constraint, logging it.
3. **Verify** — assert no real PII remains (scan against a PII/identifier detector + the 18 HIPAA identifiers), referential integrity holds across masked tables, and every designed case has a matching fixture id.

## Assertions & exit gate
- 0 real-PII values in seeded data (GDPR/HIPAA de-identification satisfied; masking is consistent + format-preserving).
- Referential integrity intact after subsetting/masking (no orphaned FKs).
- Every designed partition/boundary has a corresponding, addressable fixture id.
- **Gate:** `data_safe_and_complete` — passes when 0 PII leaks AND 0 missing fixtures (any real-PII leak is **critical**; a broken FK or missing fixture is **major**).

## Output
Write `artifacts/test-data-management/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"data_safe_and_complete"}`. Findings (`QA-TDM-NNN`) record fixture/seed ids (deterministic repro), the constraint or identifier violated in `oracle`, and **never** the offending raw PII value (redact in evidence). `notes` confirms teardown plan.

## Fixture construction (C13)
Build fixtures with the **Object Mother + Test Data Builder hybrid** (per reflectoring.io, "objectmother-fluent-builder"). The two patterns cover different needs and compose cleanly:
- **Object Mother** — named factory functions returning canonical, business-meaningful instances (`a_screened_candidate()`, `a_rejected_applicant()`, `a_candidate_with_no_resume()`). One name per partition/boundary from `test-case-design`, so a case maps to a fixture by intent, not by ad-hoc field-poking.
- **Test Data Builder** — a fluent builder under each mother for the per-case deviation: `a_screened_candidate().with_dob("2000-02-29").with_email_unicode().build()`. The builder owns sane defaults for every required + FK field, so a case sets only the one attribute it exercises and the rest stay referentially consistent.
- **Hybrid rule** — the mother seeds the canonical baseline; the builder applies the boundary delta. Mothers stay few and named; builders absorb combinatorial variation. Each `build()` still routes through the masking/synthesis path below — a builder NEVER emits a raw production value, and defaults are synthetic, not copied rows.

Keep mothers/builders pure (input in, fixture out, no side effects until the seed step) and addressable by the same fixture/seed id recorded in step 2, so repro stays deterministic.

## PII provenance & masking-effectiveness controls (CRITIC G6)
Masking-is-applied is necessary but NOT sufficient — using real candidate PII in a QA sandbox is **itself a GDPR violation** (Art. 5/6: no lawful basis for processing production personal data in test), so the gate also needs a *provenance* proof and a *de-identification quality* proof, not just a "no raw PII found" scan.

- **Positive control — PII provenance.** Assert affirmatively that NO real candidate PII ever reached the test environment, not merely that none survived masking. Tag every fixture's origin (`synthetic` | `subset-then-masked`) at the seed step and verify the set against an allowlist; any row whose lineage is `production-raw` or untagged is a leak. This is a positive control: a known synthetic canary plus a provenance-tagged corpus must both pass, proving the pipeline actually classifies origin rather than silently passing.
- **Masking-effectiveness — re-identification risk.** A format-preserving mask can still leak via linkage. Verify **k-anonymity** (k ≥ 5 as the working floor) over quasi-identifier combinations (DOB + postcode + role + employer), and flag singleton/near-singleton equivalence classes as a re-identification finding even when every direct identifier is masked.
- **Synthetic realism-vs-leakage trade-off.** Synthetic generators trained/seeded on production carry a leakage risk inversely traded against realism: too realistic → memorised real records resurface; too sanitised → the fixture stops exercising the case. Record the chosen point in `notes` and treat any synthetic value that exact-matches a production record as a leak, not a coincidence.

Add these to the exit gate as gating sub-checks: provenance positive-control and k-anonymity floor are **critical** (a re-identifiable or production-origin fixture is a real-PII leak in substance); the realism/leakage trade-off is recorded but **major**. Redact the offending quasi-identifier tuple in evidence — log the equivalence-class size and field names, never the raw values.

**Watch (do not gate):** differential-privacy budgets and membership-inference scoring on synthetic generators are emerging de-identification measures — note them in `notes` when a generator is used, but do not gate on them yet.

## Guardrails
Seeded-sandbox only; assert NON-PROD before any write; mutations restricted to `<db>-qa`, dropped/restored after use (confirm teardown in report). NEVER copy real PII into fixtures — mask or synthesize. Redact secrets/PII from `report.json` and logs. Connection strings via env. Cap `maxTurns`.
