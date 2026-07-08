# event-queue-testing

**Category:** 20-interface-data
**Runs as:** subagent: ../.claude/agents/event-queue-tester.md
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Verify async messaging over Kafka / RabbitMQ / SNS-SQS: messages are published, conform to schema, are delivered with the right ordering and idempotency, and that failures route to a dead-letter queue — honoring the declared delivery semantics (at-least-once vs exactly-once).

## Inputs & preconditions
- Required artifacts: message/event schemas (Avro/Protobuf/JSON Schema, ideally from a schema registry); the topic/queue topology + declared delivery semantics; producer/consumer service builds.
- Target: a seeded-sandbox broker (local/staging Kafka/RabbitMQ/SQS), with dedicated test topics/queues and a configured DLQ.
- Preconditions: broker reachable; test topics/queues + DLQ provisioned; consumer group offsets reset to a known point; sandbox host confirmed NON-PROD.

## Oracle (source of truth)
The **message schema** (registry/contract), the **topology + delivery-semantics spec** (ordering guarantees, idempotency key, retry/DLQ policy). NEVER infer correctness from whatever the consumer happened to accept.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate cases: valid publish, schema-invalid publish (must be rejected/DLQ'd), ordered key sequence, duplicate delivery (idempotency), poison message (→ DLQ after N retries), and semantics check (no loss for at-least-once; no dup-effect for exactly-once).
2. **Act** — produce seeded events one case at a time to the test topic/queue; for ordering, produce a numbered sequence on one partition key; for idempotency, republish the same message id; for poison, send a malformed payload. Consume from the test consumer group; drain the DLQ.
3. **Verify** — assert each consumed message validates against the schema; ordering preserved within the partition key; duplicate produced exactly one downstream effect; poison message landed in DLQ after the configured retries with no consumer crash; no published message silently lost.

## Assertions & exit gate
- Every message validates against its registered schema; schema-invalid messages are rejected/DLQ'd, never silently accepted.
- Per-key ordering matches the produced sequence (where the topology guarantees it).
- Idempotency: a redelivered/duplicate message produces exactly one effect.
- Poison messages reach the DLQ after the declared retry count; no consumer crash or infinite redelivery.
- Delivery semantics hold: at-least-once → no loss; exactly-once → no duplicate side effect.
- **Gate:** `messaging_contract_holds` — schema + ordering + idempotency + DLQ assertions all pass.

## Output
Write `artifacts/event-queue-testing/report.json` per `shared/report-format.md`:
`{ flow, status, summary{...}, findings[], gate{name:"messaging_contract_holds",passed} }`.
Each finding follows `shared/finding-schema.md`; include the seed/fixture id and message keys for deterministic repro. `oracle` = schema id + semantics spec. Evidence = produced payload, consumed payload, offsets/partition, DLQ contents.

## Schema-evolution & registry compatibility
Beyond per-message validation, verify that a **new schema version** is safe to register against the topic's declared compatibility mode — a producer/consumer upgrade must not break the other side at the contract level, before a single message is produced.

**Oracle:** the schema registry's configured **compatibility mode** for the subject + the **AsyncAPI** document (channels, messages, payloads, versions) as the contract for which schema each topic carries. NEVER infer compatibility from whatever the upgraded consumer happened to deserialize. Compatibility semantics per `docs.confluent.io` schema-registry → schema-evolution.

**Modes & what each checks (Confluent):**
- **BACKWARD** — new schema can read data written with the *latest* prior version. Allows: add optional field (with default), remove a field. New consumers read old data.
- **BACKWARD_TRANSITIVE** — same, but checked against *all* prior versions, not just the latest.
- **FORWARD** — data written with the *new* schema is readable by consumers on the *latest* prior version. Allows: add a field, remove an optional field. Old consumers read new data.
- **FORWARD_TRANSITIVE** — forward, checked against *all* prior versions.
- **FULL** — both backward and forward between *adjacent* versions: effectively only add/remove optional fields with defaults.
- **FULL_TRANSITIVE** — FULL across *all* prior versions.

**Step sequence (Plan → Act → Verify):**
1. **Plan** — for the subject under test, read its configured compatibility mode and the AsyncAPI-declared current version. Enumerate candidate next-schemas: a compatible change (add optional field w/ default) and a violating change appropriate to the mode (e.g. drop a required field under BACKWARD; add a no-default required field under FORWARD; either under FULL). For transitive modes, include a change that passes vs the latest version but fails against an *older* one.
2. **Act** — against the sandbox registry subject, run a compatibility check (registry `test-compatibility` / `compatibility` endpoint or equivalent) for each candidate schema. Do not register the violating candidates as the live version; checks are read-only against the subject.
3. **Verify** — the compatible candidate reports compatible; each violating candidate is reported incompatible and is *not* accepted; transitive modes reject the older-version violation that non-transitive would have passed.

**Assertions:**
- Compatibility result matches the declared mode for every candidate: compatible changes pass, violating changes are rejected — never silently accepted.
- AsyncAPI is the version-of-record: the topic's live schema matches the AsyncAPI-declared payload/version for that channel.
- Transitive modes are enforced across *all* prior versions, not only the latest.
- **Gate:** `schema_compatibility_holds` — declared mode enforced for every candidate; AsyncAPI version-of-record matches.

> **Watch (do not gate):** EMERGING — registry-side per-field migration rules / data contract `metadata` + `ruleSet` (CEL transforms) for cross-incompatible upgrades. Note coverage if the subject declares rules; do not gate on it yet.

## Failure-mode delivery cases
These extend the semantics check with the failure conditions that actually break exactly-once in practice. Oracle remains the **delivery-semantics spec + AsyncAPI**, never observed consumer behavior.

- **Exactly-once under failure** — produce a transactional batch, then inject a failure *between* the downstream effect and the offset commit (kill the consumer / abort the transaction mid-flight). On restart, assert the effect occurred **exactly once** — no duplicate side effect from the replayed-but-uncommitted batch, no lost effect from the aborted one. A consumer that double-applies on replay fails the gate.
- **Consumer rebalance** — with a multi-consumer group, force a rebalance mid-consumption (add/remove a member, or revoke a partition) while in-flight messages are unacked. Assert per-key ordering survives reassignment and that the in-flight message is processed exactly once by exactly one member — not dropped on revoke, not double-processed by the new owner.
- **Transactional outbox** — for a producer using the outbox pattern, seed a row in the outbox table inside the same DB transaction as the business write, then let the relay publish it. Assert: committed business write ⇒ exactly one published event; rolled-back business write ⇒ **no** event published; relay crash after publish but before marking the row sent ⇒ at-most-one duplicate that the consumer's idempotency key collapses to a single effect.

Add to the **Plan** enumeration and report each as its own finding (seed/fixture id, message keys, injected-failure point, offsets). Fold the pass/fail into the existing `messaging_contract_holds` gate.

## Guardrails
Per `shared/guardrails.md`: seeded-sandbox broker only — confirm NON-PROD before producing; dedicated test topics, never shared/prod ones; compatibility checks run read-only against a sandbox registry subject — never register/evolve a prod subject. Synthetic payloads, no real PII. Inject failures only via the sandbox (kill test consumers, abort test transactions) — never against shared infra. Tear down test topics/reset offsets after the run and confirm in the report. Secrets via env. Cap turns.
