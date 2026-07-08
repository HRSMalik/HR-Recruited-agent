# etl-pipeline

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/etl-validator.md
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Validate ETL/data-pipeline correctness end to end: extract loses nothing and preserves types, transform applies business rules / format standardization / aggregations correctly, load populates the target accurately — finishing with a source-to-target reconciliation report.

## Inputs & preconditions
- Required artifacts: source schema, target schema, and the **mapping spec** (column-to-column rules, transformations, aggregation definitions).
- Target: seeded source dataset (golden, known expected outputs) + a sandbox target store; access to run/trigger the pipeline.
- Preconditions: source + target reachable and NON-PROD; golden fixture loaded into source; target empty or reset to a known state before a load.

## Oracle (source of truth)
The **source/target schemas** + the **mapping spec** — the declared row counts, type mappings, transformation rules, and aggregation results. Combined with the golden dataset's known expected outputs. NEVER "whatever the pipeline wrote is correct."

## Step sequence (Plan → Act → Verify)
1. **Plan** — break checks by stage: extract (row count + type match, no truncation), transform (each business rule, format standardization e.g. date/case/units, each aggregation), load (target populated, no dup/missing rows, target types match).
2. **Act** — run the pipeline on the seeded golden source into the sandbox target. Capture extract counts, sample transformed records, and final target counts. Re-run once to check idempotency/no-duplication where the pipeline claims it.
3. **Verify** — assert extract count == source count and no field truncated; each transformed value equals the rule's expected output; aggregations equal independently-computed expected sums/groups; target row count + checksums reconcile against source per the mapping; no duplicates from a re-run.

## Assertions & exit gate
- Extract: target-of-extract count == source count; no truncation; types preserved per mapping.
- Transform: each business rule, format standardization, and aggregation matches the golden expected output.
- Load: target fully and correctly populated; no missing/duplicate rows; target types per schema.
- Reconciliation: source↔target counts + checksums match within the mapping spec's tolerance.
- **Gate:** `etl_reconciled` — extract/transform/load assertions pass AND reconciliation matches with 0 data loss.

## Output
Write `artifacts/etl-pipeline/report.json` per `shared/report-format.md`:
`{ flow, status, summary{...}, findings[], gate{name:"etl_reconciled",passed} }`, plus a reconciliation table (per-stage counts/checksums) in `notes` or an attached artifact.
Each finding follows `shared/finding-schema.md`; `oracle` = mapping-spec rule id + golden expected value. Evidence = source value, transformed/loaded value, the rule applied, and the stage counts. Record the golden fixture id.

## Guardrails
Per `shared/guardrails.md`: runs on a seeded NON-PROD sandbox target only — confirm host before loading; never write to a production warehouse. Golden data is synthetic/masked, no real PII. Reset/drop the sandbox target after the run, teardown confirmed in the report. Secrets via env, redacted. Cap turns.
