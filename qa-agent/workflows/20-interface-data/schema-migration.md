# schema-migration

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/migration-validator.md
**Default model:** sonnet   ·   **Mode:** mutating-sandbox

## Purpose
Prove a database schema migration is reversible and lossless before it touches a real environment: forward apply, rollback/undo, expand-contract zero-downtime sequencing, and cross-env drift detection (Flyway/Liquibase changelogs). Answers "can we ship this migration without data loss or downtime, and can we undo it?"

## Inputs & preconditions
- Required artifacts: the migration changeset (Flyway `V__`/`U__` SQL or Liquibase changelog with a declared `rollback`), the **pre-migration DDL** (baseline schema), the intended **post-migration DDL**, and a **seeded data snapshot** with known row counts + checksums.
- Target: a disposable seeded sandbox DB (e.g. `<db>-qa`) on a local/staging instance; connection string + credentials via env. NEVER a shared/prod DB.
- Preconditions: connection succeeds; host/DB name asserted NON-PROD before any DDL; snapshot loaded and its baseline counts/checksums captured; rollback script exists for every forward changeset (a forward change with no declared undo is itself a finding — Liquibase: "if it can't be easily rolled back, it shouldn't be deployed").

## Oracle (source of truth)
The **pre/post schema DDL** (what tables/columns/constraints/indexes must exist after forward, and that the schema returns *exactly* to baseline after rollback) plus the **seeded data snapshot** (row counts + per-column checksums that must survive forward+rollback unchanged). NEVER "whatever the migrated table now holds."

## Step sequence (Plan → Act → Verify)
1. **Plan** — restore the snapshot into the sandbox; record baseline schema fingerprint + row counts + checksums. Classify each changeset as additive / backfill / switch / contract; flag any state-based (declarative) diff that could silently drop a column.
2. **Act** — drive the expand-contract sequence in order on the sandbox: **additive** (new nullable columns/tables, no breakage to old code) → **backfill** (populate new from old) → **switch** (reads/writes move to new shape) → **contract** (drop the old, the only destructive step). Then run the **rollback/undo** for each applied changeset in reverse. Skip-and-continue per changeset; capture the failing SQL on error. For drift: diff the sandbox's post-migration fingerprint against the *declared* post DDL and against each env's recorded changelog state.
3. **Verify** — after forward: assert post-schema fingerprint equals the intended post DDL and no snapshot row is lost/corrupted (additive/backfill/switch are non-destructive; contract drops only the intended objects). After rollback: assert schema fingerprint + row counts + checksums are **bit-for-bit equal to baseline**. Assert no env shows out-of-process drift vs its changelog.

## Assertions & exit gate
- Forward apply succeeds; post-schema fingerprint == intended post DDL.
- Every applied changeset has a rollback that runs clean; post-rollback schema + data == baseline (0 row delta, identical checksums).
- Expand-contract order holds: no destructive op (DROP/contract) runs before its switch step; additive/backfill/switch preserve all baseline data.
- No cross-env drift: each environment's applied-changelog state matches the intended sequence (no out-of-process changes).
- **Gate:** `migration_reversible_and_lossless` — forward+rollback both clean AND post-rollback state == baseline AND 0 unexplained data loss AND 0 drift.

## Output
Write `artifacts/schema-migration/report.json` per `shared/report-format.md`:
`{ flow, status, summary{...}, findings[], gate{name:"migration_reversible_and_lossless",passed} }`.
Each finding follows `shared/finding-schema.md`; `oracle` = the DDL object or snapshot metric (e.g. `post.ddl: candidates.email NOT NULL` or `snapshot: candidates row_count=5000, checksum=…`). Evidence = the failing changeset id + SQL, baseline-vs-post counts/checksums, and the schema-fingerprint diff. Record the snapshot/seed id. Severity: an irreversible or data-losing migration is **critical** (no workaround once shipped); a missing rollback script is **major**.

## Watch (do not gate)
Note but don't fail the gate: long-running backfills that may lock tables at prod scale (flag for a separate performance flow), and state-based vs migration-based tooling choice — record if a declarative diff was the source so a human reviews the destructive-change risk.

## Guardrails
Per `shared/guardrails.md`: MUTATING — runs ONLY against the confirmed seeded sandbox restored from the snapshot, never live/prod (the PreToolUse hook blocks DROP/TRUNCATE/DELETE against non-sandbox hosts). Drop and re-restore the sandbox between forward and rollback trials so each run starts from the identical baseline; confirm teardown in the report. No real PII in the snapshot or evidence — synthesize/mask; emit counts/checksums, not row contents. Connection string redacted. Idempotent, rollback one step away. Cap turns.
