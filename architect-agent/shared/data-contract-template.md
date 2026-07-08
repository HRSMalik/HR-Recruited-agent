# Data Contract Template — ODCS v3.x (Open Data Contract Standard)

The data contract is the producer↔consumer agreement for a dataset — the data-plane analog of OpenAPI for APIs. Governed by the **Open Data Contract Standard (ODCS)**, a LF AI & Data / Bitol project (v3.1.0, Dec 2025; canonical: https://github.com/bitol-io/open-data-contract-standard), a data contract is a versioned, machine-readable YAML/JSON document that a **data producer** publishes alongside a dataset and against which **data consumers** test. It turns implicit, undocumented assumptions ("the `amount` field is always non-null and in a fixed currency's minor unit") into explicit, executable obligations. Because it is versioned and gate-able in CI, a producer cannot silently break a consumer — a schema change, a dropped field, or a degraded SLA is surfaced as a contract violation before it reaches production. Use this template as the authoritative fill-in guide for any data contract the `data-architect` or `solution-architect` authors; cross-reference `workflows/20-data/data-governance-lifecycle.md` for the classification, retention, erasure, and lineage obligations the security/classification section must align with — including the domain-ownership and data-as-a-product obligations that apply when a Data Mesh topology is in use.

> **When to produce a contract.** A data contract is warranted wherever a named producer team publishes a dataset consumed by ≥1 downstream team/system — especially across bounded-context boundaries (`workflows/00-drivers/domain-analysis.md`). For a single-team, single-context data flow, a lightweight schema annotation suffices; escalate to a full ODCS contract when: (a) the producer and consumer are different teams, (b) the dataset carries PII/PHI/PCI or financial data, (c) an SLA is owed, or (d) the dataset is published as a data product (Data Mesh). Every contract decision is an ADR (`shared/adr-template.md`) — name the tradeoff between strict-contract rigor (early breakage detection, coupling) and loose-contract flexibility (independent evolution, deferred breakage; see `shared/fallacies-and-tradeoffs.md` → strict ↔ loose contracts).

---

## Section 1 — Fundamentals / Metadata

The header block identifies the contract uniquely and establishes governance provenance. Required fields:

```yaml
apiVersion: v3.0.0                          # ODCS spec version — pin to a major.minor
kind: DataContract
id: dc-<domain>-<dataset>-<NNN>             # Stable UUID or slug; never reuse after deprecation
name: "<human-readable dataset name>"
version: "1.0.0"                            # SemVer: MAJOR on breaking schema change,
                                            # MINOR on additive change, PATCH on doc/threshold fix
status: draft | active | deprecated        # Lifecycle gate — only `active` contracts are enforced in CI
domain: "<bounded-context name>"           # Aligns to the domain map in domain-analysis.md
description: |
  One paragraph: what data this is, the business capability it serves,
  and the primary consumer use-cases. No prose padding.
tenant: "<org or team identifier>"
tags:                                       # Free-form; used for discovery and filtering
  - pii
  - core-entity
  - financial
```

**Traceability:** every contract carries a `driver_ref` comment pointing to the quality-attribute scenario (`QAS-*`) or constraint that justifies its existence. A contract with no driver is a preference, not a hard artifact.

---

## Section 2 — Schema (Datasets / Fields / Types)

The schema section is the structural core — the producer's commitment to the shape of the data. ODCS calls the top-level grouping a **dataset** (a logical table, topic, or collection) and its members **fields**.

```yaml
schema:
  - name: "<dataset_name>"                  # e.g. orders, order_events, payment_transactions
    physicalName: "<actual_table_or_topic>" # The real identifier in the store (may differ from logical name)
    description: "<one sentence: what this dataset represents>"
    physicalType: table | topic | object | view | stream
    partitioned: true | false
    partitionedOn: "<field_name>"           # Only if partitioned

    fields:
      - name: "<field_name>"
        logicalType: string | integer | long | decimal | boolean | date | timestamp | uuid | object | array
        physicalType: "<store-native type, e.g. VARCHAR(255), INT8, BSONTYPE>"
        description: "<what the field means, its unit/currency, and any domain constraints>"
        required: true | false              # Hard contract: producer guarantees non-null when true
        unique: true | false
        primaryKey: true | false
        partitionKey: true | false
        classification: public | internal | confidential | pii | phi | pci
        # ^ aligns to data-governance-lifecycle.md four-tier classification scheme
        piiType: "<e.g. email | ssn | dob | bank_account | name>"  # Only when classification = pii/phi/pci
        example: "<a realistic, anonymized example value>"
        tags:
          - "<searchable tag>"
        # Nested objects or arrays:
        fields: []                          # Recursive for nested structures
```

**Rules:**
- Every field with `classification: pii | phi | pci` **must** carry a `piiType` — an omission blocks (aligns to the `data-governance-lifecycle.md` hard oracle: every regulated field is classified at the field level).
- `physicalType` pins the contract to the store's actual wire type; a type-widening change (e.g. `INT4` → `INT8`) is additive (MINOR bump); type-narrowing or semantic reinterpretation is breaking (MAJOR bump).
- `required: true` is a **hard guarantee** — consumer tests assert non-null at runtime. Downgrading from `required: true` to `false` is a breaking change (MAJOR bump).

---

## Section 3 — Data Quality Rules

The quality section makes freshness, completeness, validity, and threshold obligations explicit and executable. Reference the six DAMA DMBOK dimensions: **Completeness · Uniqueness · Timeliness · Validity · Accuracy · Consistency**.

```yaml
quality:
  - rule: "<rule_id: e.g. DQ-ORDERS-001>"
    dimension: completeness | uniqueness | timeliness | validity | accuracy | consistency
    field: "<dataset_name>.<field_name>"    # Omit for dataset-level rules
    description: "<what the rule checks in plain English>"
    type: sql | spark | great_expectations | custom
    engine: "<tooling, e.g. Great Expectations, dbt test, custom Python>"
    query: |
      -- The executable check; must be runnable against the physical dataset
      SELECT COUNT(*) FROM orders WHERE amount IS NULL
    threshold:
      operator: "< | > | = | >= | <="
      value: 0                             # Numeric threshold; breach = contract violation
      severity: error | warning            # error = hard block; warning = advisory
    driver_ref: "QAS-DATA-002"             # The QAS that mandates this rule
    tags: []
```

**Canonical quality rules to cover for any regulated dataset:**
| Rule | Dimension | Threshold example |
|---|---|---|
| No null on required PII fields | Completeness | `null_count = 0` |
| Entity IDs (e.g. order/invoice numbers) are unique across the dataset | Uniqueness | `duplicate_count = 0` |
| Events arrive within SLA window | Timeliness | `max_lag_minutes ≤ 30` |
| `amount` is a positive integer (minor currency unit) | Validity | `invalid_count = 0` |
| Payment totals match source documents | Accuracy | `mismatch_rate < 0.001` |
| Status transitions follow the state machine | Consistency | `illegal_transition_count = 0` |

Quality rules are **gated in CI** — an `error`-severity breach blocks the producer's pipeline; a `warning` fires an alert but does not block. Every rule carries a `driver_ref`; a rule with no driver is removed from the hard gate.

---

## Section 4 — SLA (Availability / Latency / Retention)

The SLA section is the operational commitment — what the producer promises about delivery and access.

```yaml
sla:
  availability:
    percentage: 99.9                        # Uptime commitment over a rolling 30-day window
    driver_ref: "QAS-AVAIL-01"
  latency:
    - type: batch | streaming | api
      metric: p50 | p95 | p99 | max
      maxMs: 30000                          # 30 s — example for a batch pipeline
      driver_ref: "QAS-PERF-03"
  freshness:
    maxAgeMinutes: 60                       # Data must not be older than N minutes at query time
    driver_ref: "QAS-FRESH-01"
  retention:
    periodDays: 2555                        # 7 years — example for regulated/financial data
    archivalPath: "<cold store location or mechanism>"
    hardDeleteAt: "<retention_end + 30 days — for regulated PII>"
    driver_ref: "QAS-COMPLIANCE-02"        # Must align to data-governance-lifecycle.md erasure path
  support:
    responseTimeSla: "4h"                   # Producer response to a consumer-filed contract violation
    contactChannel: "<slack channel / email / ticket queue>"
```

**SLA ↔ cost tradeoff (mandatory ADR if p99 < 500 ms or availability > 99.95%):** tight SLAs demand more infrastructure redundancy, more frequent pipeline runs, and more complex monitoring. Every SLA commitment traces to a quality-attribute scenario with a measurable response measure; an SLA tighter than the driver demands is accidental over-engineering (`shared/fallacies-and-tradeoffs.md` → cost ↔ resilience/performance).

---

## Section 5 — Security & Classification

Security and classification declarations govern who can access the data and under what conditions. This section must align with the `data-governance-lifecycle.md` four-tier scheme and the threat model (`architecture/<slug>/threat-model.md`).

```yaml
security:
  classification: public | internal | confidential | regulated
  # `regulated` = at least one field carries pii | phi | pci — triggers full governance obligations

  piiPresent: true | false
  phiPresent: true | false
  pciPresent: true | false

  encryptionAtRest: true | false
  encryptionInTransit: true | false
  keyManagement: "<e.g. AWS KMS CMK, HashiCorp Vault, Azure Key Vault>"

  accessControl:
    model: rbac | abac | acl
    minRole: "<minimum role required to read — per the project's RBAC roles in `project-architecture-config.md`, e.g. data.reader>"
    consumerWhitelist:
      - "<service-account or team identifier>"
    auditLogging: true | false              # Mandatory true for any regulated classification

  erasure:
    strategy: hard-delete | anonymization | pseudonymization
    procedure: "<link to the runnable erasure job or ADR>"
    driver_ref: "QAS-COMPLIANCE-03"        # Must align to data-governance-lifecycle.md erasure path

  residency:
    regions:
      - "<e.g. us-east-1>"                 # All stores and replicas must fall within this list
    driver_ref: "<stated compliance constraint or QAS-*>"
    # Omit the residency block only if no residency constraint is stated — do not silently leave it out
```

**Hard rules (aligned with `data-governance-lifecycle.md`):**
- Any field tagged `classification: pii | phi | pci` at the schema level mandates `security.piiPresent: true` (or the appropriate flag) at the contract level — a mismatch blocks.
- `auditLogging: true` is mandatory for any contract with `classification: regulated`; `false` on a regulated contract is a critical finding (`finding-schema.md` type `"privacy"`).
- The `erasure.procedure` must point to a runnable artifact, not a prose note; "TBD" blocks.

---

## Section 6 — Pricing & Ownership

Pricing is optional for internal data products but mandatory when the data product is published on a data marketplace (Data Mesh self-serve platform — see `workflows/20-data/data-governance-lifecycle.md` → Data ownership + stewardship + data-product lifecycle).

```yaml
price:
  priceAmount: 0.00                         # 0 for internal; non-zero for a charged data product
  priceCurrency: USD
  priceUnit: per-call | per-row | per-month | flat
  billingContact: "<team or cost center>"

ownership:
  dataOwner: "<role name — the accountable business role, not a person's name>"
  # Aligns to data-governance-lifecycle.md: one named data owner per bounded context
  dataSteward: "<role responsible for day-to-day quality + classification maintenance>"
  producingTeam: "<team identifier>"
  producingSystem: "<service or pipeline name>"
  sourceOfTruth: "<canonical upstream — per the project's stack in `project-architecture-config.md`, e.g. 'primary datastore collection/table, owning service repo'>"
```

**Ownership is not the DBA or "the team"** — it is a named business role with accountability that survives team changes (`data-governance-lifecycle.md` → Data ownership + stewardship). A contract with `dataOwner: "Engineering"` fails the governance oracle.

---

## Section 7 — Roles & Consumer Registry

The roles section declares who has read/write obligations and records which consumers have accepted the contract. A consumer registering against a contract version is an explicit dependency declaration — the producer cannot drop a field or tighten an SLA without notifying registered consumers.

```yaml
roles:
  - role: data-owner
    description: "Accountable for data accuracy, access policy, and lifecycle decisions."
    assignedTo: "<role name>"

  - role: data-steward
    description: "Responsible for day-to-day quality, classification maintenance, and contract updates."
    assignedTo: "<role name>"

  - role: data-producer
    description: "The team/service that writes to the dataset and is bound by the contract's SLA and schema."
    assignedTo: "<team or service-account>"

  - role: data-consumer
    description: "A team or service that reads from the dataset and is protected by the contract."
    assignedTo: "<team or service-account>"
    contractVersionAccepted: "1.0.0"        # The version the consumer has tested against
    contactChannel: "<slack / email>"

consumers:
  - name: "<consumer service or team>"
    contractVersionAccepted: "1.0.0"
    usedFields:
      - "<dataset_name>.<field_name>"       # Explicit field-level consumption declaration
      # Stamp-coupling check: if usedFields / totalFields < ~20%, flag as stamp coupling
      # (fallacies-and-tradeoffs.md → stamp coupling); produce a projection contract instead
    testSuiteRef: "<path to consumer-driven contract test suite>"
```

**Consumer-driven contract tests** (Pact or equivalent) are the executable oracle for the consumer side — the producer's CI must not break a passing consumer test suite. The `testSuiteRef` is the path or repo URL; "none" is not acceptable for an `active`-status contract carrying PII or an SLA.

---

## Section 8 — Contract Lifecycle & Versioning Policy

```yaml
lifecycle:
  created: "<ISO-8601 date>"
  lastReviewed: "<ISO-8601 date>"
  nextReviewDue: "<ISO-8601 date>"           # Minimum: annual; quarterly for regulated datasets
  changeLog:
    - version: "1.0.0"
      date: "<ISO-8601>"
      author: "<role>"
      changes: "Initial contract."
    - version: "1.1.0"
      date: "<ISO-8601>"
      author: "<role>"
      changes: "Added field order_currency; softened freshness SLA from 30 to 60 min (driver QAS-FRESH-01 updated)."

  breakingChangePolicy: |
    A MAJOR version bump is required for: field removal, required→optional demotion,
    type-narrowing, SLA tightening beyond 20%, reclassification of PII status,
    or change of erasure strategy. Breaking changes require 30-day advance notice
    to all registered consumers and a parallel-run period (both versions active).
    Minor/patch changes take effect at the next pipeline run.

  deprecationPolicy: |
    A contract moves to `deprecated` status with 90 days' notice to registered consumers.
    During the deprecation window the producer continues to honor all SLA and schema
    guarantees. At the end of the window the contract moves to `retired` and the
    dataset is no longer guaranteed available.
```

---

## How architecture flows use this template

- **`data-architect` (design mode, `workflows/20-data/`):** authors a filled-in ODCS contract as `architecture/<slug>/data-contracts/<dc-id>.yaml` whenever a dataset crosses a bounded-context boundary or carries PII/PHI/PCI — the contract is the formal deliverable alongside the data-modeling artifact. Cross-references `workflows/20-data/data-governance-lifecycle.md` to ensure the `security.erasure` and `security.residency` blocks align with the governance design.
- **`data-architect` (audit mode):** checks existing datasets for the presence and completeness of a contract; an inter-context dataset with no contract is a `major` hard finding (`finding-schema.md`, type `"data"`); a contract missing `driver_ref` on a quality rule is a `minor` hard finding.
- **`architecture-evaluator` (`workflows/60-evaluation/`):** uses the contract as an external oracle — a consumer-driven contract test that passes is an **external signal** that closes the evaluate→revise loop (`evaluation-method.md` → external-signal gate). A failing test is a hard finding that blocks.
- **`solution-architect` (any flow):** when a decomposition boundary is drawn (`workflows/10-styles-decomposition/decomposition-strategy.md`), any dataset that crosses the boundary gets a contract stub as part of the design doc — even if only Section 1 + 2 are filled in at design time. The full contract is completed before the dataset goes `active`.
- **Data Mesh context (`workflows/20-data/data-governance-lifecycle.md` → domain ownership + data-product lifecycle):** each domain publishes its data products with a full ODCS contract. The self-serve platform enforces the contract at publish time; consumers discover products via the contract registry. Without a contract, a dataset is not a data product — it is an implementation detail that leaks.

**Hard oracle (binding on all flows):** any dataset that (a) crosses a bounded-context boundary, (b) carries a PII/PHI/PCI field, or (c) carries an explicit SLA — and lacks an `active`-status ODCS contract — is a `major` hard finding. A contract in `draft` status used in production is a `critical` hard finding. A contract whose `security.erasure.procedure` is `"TBD"` for a regulated dataset is a `critical` hard finding.
