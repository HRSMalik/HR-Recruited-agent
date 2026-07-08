# defect-triage

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Turn raw failures into well-formed, deduplicated defects: assign severity, propose priority, attach a root-cause hint, and place each on the defect lifecycle. Answers: "For every failure, is it a unique, actionable, correctly-classified defect with a recommended path?"

## Inputs & preconditions
- Required artifacts: failing findings from execution flows (`test-execution`, functional/api/security flows), the existing defect store (open + recently-closed) for dedupe, severity rubric.
- Target: the defect tracker / store (read for dedupe; write only to the QA defect store, not the SUT).
- Preconditions: each incoming failure carries evidence + steps_to_reproduce (no evidence → it's a note, rejected as a defect per finding-schema).

## Oracle (source of truth)
`shared/finding-schema.md` (required defect fields), `shared/severity-priority-rubric.md` (severity = technical impact, set by agent; priority = business urgency, **proposed** only), and the **ISTQB / IEEE 1044** defect lifecycle: `New → Assigned → Fixed → Retest → Closed`, with `Reopened` and `Rejected/Duplicate/Deferred` branches. Severity is decided by impact×scope against the rubric, not by reporter sentiment.

## Step sequence (Plan → Act → Verify)
1. **Plan** — collect all failed findings; group candidates for dedupe by signature (same endpoint/component + same error class + similar stack/symptom).
2. **Act** — for each unique failure: assign **severity** (blocker/critical/major/minor/trivial per rubric), emit `priority:"proposed"` + a `suggested_priority` rationale (blocker/critical→P1, major→P2, minor→P3, trivial→P4), add a root-cause hint (e.g. "null not guarded", "off-by-one boundary", "missing authz check"), set lifecycle state `New`/`Assigned`, and link duplicates to a canonical id. Skip-and-continue on a malformed input finding.
3. **Verify** — assert every defect is schema-complete, severity matches the rubric definition, duplicates collapse to one canonical id, and no defect lacks reproduction/evidence.

## Assertions & exit gate
- Every defect conforms to the finding schema (id, severity, evidence, steps, expected, actual, oracle).
- Severity assigned objectively per rubric; priority is `proposed` (never finalized by the agent).
- Duplicates deduplicated to a single canonical id; each defect has a lifecycle state + root-cause hint.
- **Gate:** `all_defects_well_formed` — passes when 0 schema-incomplete defects AND 0 un-deduped duplicates (a misclassified critical or an evidence-less "defect" is itself a **major** process finding).

## Output
Write `artifacts/defect-triage/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"all_defects_well_formed"}`. Each triaged defect (`QA-DEF-NNN`) carries severity, `priority:"proposed"` + rationale, lifecycle `status`, root-cause hint in `suggested_fix`, and duplicate-link in `evidence`. `findings_by_severity` feeds the orchestrator roll-up.

## Guardrails
Read-only against the SUT — writes only to the QA defect store, never the application DB. Agent sets severity but only **proposes** priority; a human finalizes P-levels and assignment (`assigned_to` stays null unless a human sets it). Redact secrets/PII in evidence. Cap `maxTurns`.
