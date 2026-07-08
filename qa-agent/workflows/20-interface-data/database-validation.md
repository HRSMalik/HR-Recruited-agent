# database-validation

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/database-validator.md
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Validate data integrity at the database layer: schema constraints, referential integrity, CRUD correctness, stored-procedure logic, and source-to-target reconciliation (row counts + checksums). Reads on live; mutations only on a seeded sandbox.

## Inputs & preconditions
- Required artifacts: the DB schema (DDL / migrations), the data-mapping spec (for reconciliation), and stored-procedure specs where logic is tested.
- Target: connection string + read credentials (via env); for mutation cases a seeded sandbox DB (e.g. `<db>-qa`).
- Preconditions: connection succeeds; host/DB name asserted NON-PROD before any write; seeded fixtures present for CRUD/proc cases; reconciliation source + target both reachable.

## Oracle (source of truth)
The **schema** (constraint, FK, type, nullability, unique/index definitions) and the **mapping spec** (expected source↔target row counts and column transformations). For stored procs, the documented expected output for given inputs. NEVER "the data is whatever the table holds."

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate checks: NOT NULL / UNIQUE / CHECK / type constraints, every FK (no orphans), CRUD round-trip per key table, each stored proc's input→output cases, and reconciliation pairs (source vs target).
2. **Act** — run read-only SELECTs to detect constraint/FK violations (orphaned children, dup keys, nulls in NOT NULL, out-of-domain values). On the seeded sandbox only: execute CRUD round-trips and call stored procs with fixture inputs. For reconciliation, compute `COUNT(*)` and column checksums on both sides.
3. **Verify** — assert no orphaned/duplicate/null/out-of-range rows; CRUD writes persist and read back correctly then roll back; proc outputs equal expected; source and target counts + checksums match within tolerance.

## Assertions & exit gate
- 0 referential-integrity violations (no orphaned FKs); 0 constraint violations (null/unique/check/type).
- CRUD round-trip on the sandbox is consistent (write → read matches → delete cleans up).
- Stored-proc outputs equal the documented expected results.
- Source↔target row counts and checksums reconcile within the mapping spec's tolerance.
- **Gate:** `data_integrity_intact` — 0 integrity/constraint violations AND reconciliation matches.

## Output
Write `artifacts/database-validation/report.json` per `shared/report-format.md`:
`{ flow, status, summary{...}, findings[], gate{name:"data_integrity_intact",passed} }`.
Each finding follows `shared/finding-schema.md`; `oracle` = schema object / mapping-spec row (e.g. `schema.sql: candidates.job_id FK → jobs.id`). Evidence = the offending query + sample violating rows (PK only) + counts/checksums. Record the seed id for sandbox cases.

## DB cross-validation (recompute-and-compare oracle)
The sharpest check this flow owns: for any endpoint that returns a computed value (counts, aggregates, scores, metrics), do NOT just shape/type-check the response —

1. query the underlying table(s) directly,
2. apply the **same** filters the API applies,
3. **recompute the metric independently** (in SQL or python),
4. compare to the live API response.
This catches the bug class that shape/type checks cannot: a response that is **syntactically correct but numerically wrong**. The recomputation is the external oracle — never accept the API's number as its own proof. (See `shared/tool-cookbook.md` for the `curl | python3` assertion idiom.)

## Guardrails
Per `shared/guardrails.md`: read-only on live (`disallowedTools: Edit, Write`; SELECT-only — the PreToolUse hook blocks INSERT/UPDATE/DELETE/DROP/TRUNCATE against live). Mutations ONLY on the confirmed seeded sandbox, dropped/restored after, teardown confirmed in the report. No real PII in evidence — emit keys/counts, not row contents. Connection string redacted. Cap turns.
