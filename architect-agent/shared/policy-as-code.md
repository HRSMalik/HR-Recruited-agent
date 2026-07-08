# Policy-as-Code — Turning ADR Thresholds into Executable OPA/Conftest Gates

Quality-attribute thresholds and ADR decisions have no enforcement value unless a machine can check them on every change. This contract defines how the fleet turns its ADRs and quality-attribute scenarios into a **Rego policy library** that the operator runs under `conftest` in CI, making the hard oracles in `quality-attribute-rubric.md` physically executable rather than prose commitments. The fleet **authors the policy specs** — naming the package, the rule, the assertion, and the driver it guards — and the operator installs and runs `conftest` in the pipeline. The fleet never applies infra, never runs `conftest` itself, and never edits product source; it proposes, documents, and verifies (`guardrails.md` §1, §7).

---

## 1. What conftest gates

`conftest` evaluates Rego policies against structured inputs. The fleet authors one or more policies per **input domain** — each domain maps to an artifact the CI pipeline already produces or can be produced cheaply without a live environment:

| Input domain | Artifact passed to `conftest` | How produced |
|---|---|---|
| **Terraform plan** | `terraform show -json tfplan.binary > tfplan.json` | `terraform plan -out=tfplan.binary` in the pipeline |
| **Kubernetes manifests** | raw YAML files or Helm-rendered output (`helm template`) | rendered at plan/build time |
| **OpenAPI specifications** | `openapi.yaml` / `openapi.json` at the root of the API service | committed to source; also linted by Spectral (cross-link `30-integration/api-design.md`) |
| **ADR front-matter** | YAML front-matter block extracted from each `adr/NNNN-*.md` file | a thin shell snippet (`grep -A20 '^---' file | head -20`) or a pre-commit hook yields JSON |
| **Dockerfiles** | Dockerfile text passed through `conftest` using the Dockerfile input type | present in source |

Each domain gets its own **package namespace** (`data.<project>.<domain>.*`, where `<project>` is the project's package prefix per `project-architecture-config.md`) so policies are composable and independently testable. A `conftest test` suite runs policies against fixture inputs (a minimal valid Terraform plan JSON, a minimal ADR YAML) as the unit-test layer; the pipeline runs `conftest verify` against real artifacts as the integration gate.

---

## 2. Rego policy library — organized by quality attribute

Every package names its **driver reference** (`QAS-*` or `ADR-NNNN`) in a comment at the top so the policy is traceable in both directions: from the driver to the enforcing rule, and from a failing check back to the decision that demanded it. A policy with no driver reference is a preference; the fleet does not author it (`guardrails.md` §2).

### 2.1 Security — `data.<project>.security.*`

**Drivers:** `QAS-SEC-*`; `ADR-*` covering zero-trust, secrets management, and least privilege (cross-link `40-cross-cutting/security-architecture.md`).

**`data.<project>.security.terraform`** — Terraform-plan policies

```rego
# driver: QAS-SEC-01 (no public object storage), ADR-SEC-001 (zero-trust storage posture)
# oracle: hard — "Trust boundary secured" (quality-attribute-rubric.md)
package data.<project>.security.terraform

import future.keywords.if
import future.keywords.contains

# DENY: any storage bucket / blob container with public access enabled
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type in {"aws_s3_bucket_acl", "google_storage_bucket_acl", "azurerm_storage_container"}
    resource.change.after.predefined_acl in {"publicRead", "publicReadWrite", "public-read", "public-read-write"}
    msg := sprintf("POLICY SEC-TF-001 [QAS-SEC-01]: resource %v has public ACL '%v' — storage must not be publicly readable without an explicit exemption tag 'public_access_exemption=true'",
                   [resource.address, resource.change.after.predefined_acl])
}

# DENY: S3 bucket without server-side encryption configured
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    not resource.change.after.server_side_encryption_configuration
    msg := sprintf("POLICY SEC-TF-002 [QAS-SEC-01]: S3 bucket %v has no server-side encryption configuration", [resource.address])
}

# DENY: secrets as literals in Terraform variable defaults or resource attribute values
# (grep-equivalent — checks for common secret-shaped attribute names with non-null, non-reference values)
deny contains msg if {
    resource := input.resource_changes[_]
    sensitive_keys := {"password", "secret", "secret_key", "api_key", "private_key", "access_key"}
    key := sensitive_keys[_]
    val := resource.change.after[key]
    is_string(val)
    not startswith(val, "var.")
    not startswith(val, "data.")
    msg := sprintf("POLICY SEC-TF-003 [ADR-SEC-001]: resource %v has a literal value for '%v' — secrets must be injected via a secret-store reference, never hardcoded",
                   [resource.address, key])
}

# DENY: IAM wildcard grants (AWS)
deny contains msg if {
    resource := input.resource_changes[_]
    resource.type in {"aws_iam_policy", "aws_iam_role_policy"}
    statement := resource.change.after.policy.Statement[_]
    statement.Effect == "Allow"
    statement.Action == "*"
    statement.Resource == "*"
    msg := sprintf("POLICY SEC-TF-004 [QAS-SEC-02]: IAM policy %v grants Action=* Resource=* — least-privilege is required; scope the grant to the minimum actions and resources",
                   [resource.address])
}
```

**`data.<project>.security.k8s`** — Kubernetes manifest policies

```rego
# driver: QAS-SEC-03 (no privileged containers), ADR-SEC-002 (container security posture)
package data.<project>.security.k8s

import future.keywords.if
import future.keywords.contains

deny contains msg if {
    container := input.spec.containers[_]
    container.securityContext.privileged == true
    msg := sprintf("POLICY SEC-K8S-001 [QAS-SEC-03]: container '%v' runs privileged — containers must not be privileged; set securityContext.privileged=false",
                   [container.name])
}

deny contains msg if {
    container := input.spec.containers[_]
    container.image
    endswith(container.image, ":latest")
    msg := sprintf("POLICY SEC-K8S-002 [ADR-SEC-002]: container '%v' uses ':latest' tag — images must be pinned to an immutable digest or version tag for reproducibility and supply-chain integrity",
                   [container.image])
}

deny contains msg if {
    container := input.spec.containers[_]
    env := container.env[_]
    sensitive_names := {"PASSWORD", "SECRET", "API_KEY", "PRIVATE_KEY", "JWT_SECRET", "AES_KEY"}
    sensitive_names[env.name]
    env.value
    not env.valueFrom
    msg := sprintf("POLICY SEC-K8S-003 [ADR-SEC-001]: container '%v' has secret '%v' as a literal env value — secrets must use valueFrom.secretKeyRef or valueFrom.configMapKeyRef pointing to a K8s Secret",
                   [container.name, env.name])
}
```

**`data.<project>.security.dockerfile`** — Dockerfile policies

```rego
# driver: ADR-SEC-002 (container hardening), QAS-SEC-03
package data.<project>.security.dockerfile

import future.keywords.if
import future.keywords.contains

# conftest uses the "dockerfile" input type which parses the Dockerfile into stages/instructions
deny contains msg if {
    instruction := input.Stages[_].Commands[_]
    instruction.Cmd == "user"
    lower(instruction.Value[0]) == "root"
    msg := "POLICY SEC-DF-001 [QAS-SEC-03]: Dockerfile sets USER root — containers must run as a non-root user; add 'USER <uid>' to the final stage"
}

deny contains msg if {
    stage := input.Stages[_]
    not any_user_instruction(stage.Commands)
    msg := sprintf("POLICY SEC-DF-002 [QAS-SEC-03]: Dockerfile stage '%v' has no USER instruction — all final image stages must declare a non-root USER",
                   [stage.Name])
}

any_user_instruction(commands) if {
    cmd := commands[_]
    cmd.Cmd == "user"
}
```

---

### 2.2 Reliability — `data.<project>.reliability.*`

**Drivers:** `QAS-AVAIL-*`, `QAS-REL-*`; ADRs covering replica counts, health checks, and failover (`50-infrastructure/deployment-topology.md`, `40-cross-cutting/availability-resilience.md`).

**`data.<project>.reliability.k8s`**

```rego
# driver: QAS-AVAIL-01 (≥99.9% availability on SLO paths; no SPOF on critical path)
# oracle: hard — "No un-accepted SPOF" (quality-attribute-rubric.md)
package data.<project>.reliability.k8s

import future.keywords.if
import future.keywords.contains

# SLO paths are identified by the label: slo_path="true"
# driver: if a Deployment is on an SLO path, replicas must be ≥ 2
deny contains msg if {
    input.kind == "Deployment"
    input.metadata.labels["slo_path"] == "true"
    replicas := input.spec.replicas
    replicas < 2
    msg := sprintf("POLICY REL-K8S-001 [QAS-AVAIL-01]: Deployment '%v' is on an SLO path (label slo_path=true) but has only %v replica(s) — SLO-path deployments must have replicas ≥ 2 to eliminate a SPOF",
                   [input.metadata.name, replicas])
}

# Liveness and readiness probes required on SLO-path containers
deny contains msg if {
    input.kind == "Deployment"
    input.metadata.labels["slo_path"] == "true"
    container := input.spec.template.spec.containers[_]
    not container.livenessProbe
    msg := sprintf("POLICY REL-K8S-002 [QAS-AVAIL-01]: container '%v' in SLO-path Deployment '%v' has no livenessProbe — health probes are required so the orchestrator can restart unhealthy instances",
                   [container.name, input.metadata.name])
}

deny contains msg if {
    input.kind == "Deployment"
    input.metadata.labels["slo_path"] == "true"
    container := input.spec.template.spec.containers[_]
    not container.readinessProbe
    msg := sprintf("POLICY REL-K8S-003 [QAS-AVAIL-01]: container '%v' in SLO-path Deployment '%v' has no readinessProbe — traffic must not route to an unready container",
                   [container.name, input.metadata.name])
}

# PodDisruptionBudget required for SLO-path Deployments (guards against voluntary disruption draining the replicas)
warn contains msg if {
    input.kind == "Deployment"
    input.metadata.labels["slo_path"] == "true"
    not pdb_exists_for(input.metadata.name)
    msg := sprintf("POLICY REL-K8S-004 [QAS-AVAIL-01] (warn): Deployment '%v' is on an SLO path but no PodDisruptionBudget is present in this manifest set — add a PDB with minAvailable ≥ 1 to prevent draining all replicas during node maintenance",
                   [input.metadata.name])
}

# pdb_exists_for is resolved by conftest's multi-input mode — when the full manifest set is passed,
# a PDB whose spec.selector matches the Deployment label should be present.
# Simplification: treat as a warn (advisory) since cross-manifest resolution requires the full set.
pdb_exists_for(_) := false  # override with real cross-manifest lookup when full set is available
```

---

### 2.3 Compliance — `data.<project>.compliance.*`

**Drivers:** `QAS-COMP-*`; ADR covering data classification and PII handling; compliance regime per `project-architecture-config.md` (e.g. PII + payment/financial data — cross-link `40-cross-cutting/privacy-compliance-architecture.md`).

**`data.<project>.compliance.terraform`**

```rego
# driver: QAS-COMP-01 (PII must be classified; data lifecycle lawful under applicable regime)
# oracle: hard — "Data lifecycle lawful" (quality-attribute-rubric.md)
package data.<project>.compliance.terraform

import future.keywords.if
import future.keywords.contains

# Every data store that may hold PII must carry a 'data_classification' tag
pii_store_types := {
    "aws_dynamodb_table", "aws_rds_cluster", "aws_rds_instance",
    "google_sql_database_instance", "azurerm_cosmosdb_account",
    "aws_s3_bucket", "google_storage_bucket"
}

deny contains msg if {
    resource := input.resource_changes[_]
    pii_store_types[resource.type]
    not resource.change.after.tags["data_classification"]
    msg := sprintf("POLICY COMP-TF-001 [QAS-COMP-01]: data store %v (%v) has no 'data_classification' tag — every store that may hold PII or financial data must declare its classification (e.g. 'pii', 'financial', 'internal', 'public')",
                   [resource.address, resource.type])
}

# PII-classified stores must have encryption at rest enabled
deny contains msg if {
    resource := input.resource_changes[_]
    pii_store_types[resource.type]
    resource.change.after.tags["data_classification"] in {"pii", "financial"}
    not resource.change.after.storage_encrypted
    not resource.change.after.encrypted
    not resource.change.after.server_side_encryption_configuration
    msg := sprintf("POLICY COMP-TF-002 [QAS-COMP-01]: PII/financial store %v has no encryption-at-rest configured — regulated data stores must encrypt at rest",
                   [resource.address])
}

# Retention policy: PII stores must declare a retention tag so the erasure path is traceable
deny contains msg if {
    resource := input.resource_changes[_]
    pii_store_types[resource.type]
    resource.change.after.tags["data_classification"] in {"pii", "financial"}
    not resource.change.after.tags["data_retention_days"]
    msg := sprintf("POLICY COMP-TF-003 [QAS-COMP-01]: PII/financial store %v has no 'data_retention_days' tag — retention/erasure path must be declared for regulated data",
                   [resource.address])
}
```

---

### 2.4 Documentation — `data.<project>.documentation.*`

**Drivers:** `oracle:"hard"` — "ADR complete" (`quality-attribute-rubric.md`); every architecturally-significant decision must be a MADR 4.x ADR with context · decision drivers · ≥2 considered options · decision · consequences · status (`adr-template.md`).

**`data.<project>.documentation.adr`** — ADR front-matter completeness

The CI step extracts the YAML front-matter block from each `adr/NNNN-*.md` file and passes it as JSON to `conftest`. A minimal extractor:

```bash
# in CI — run for each ADR file; outputs JSON to a temp file for conftest
python3 -c "
import sys, json, re
text = open(sys.argv[1]).read()
m = re.search(r'^---\s*\n(.*?)\n---', text, re.DOTALL | re.MULTILINE)
if m:
    import yaml; print(json.dumps(yaml.safe_load(m.group(1))))
else:
    print('{}')
" "$adr_file" > /tmp/adr_meta.json
conftest test --policy policies/documentation/ /tmp/adr_meta.json
```

```rego
# driver: "ADR complete" hard oracle (quality-attribute-rubric.md), adr-template.md
package data.<project>.documentation.adr

import future.keywords.if
import future.keywords.contains

required_fields := {"status", "date", "decision-makers", "driver_refs", "one-way-door"}

deny contains msg if {
    field := required_fields[_]
    not input[field]
    msg := sprintf("POLICY DOC-ADR-001: ADR front-matter is missing required field '%v' — every MADR 4.x ADR must declare: status, date, decision-makers, driver_refs (traced to QAS-*), and one-way-door (yes|no)",
                   [field])
}

# status must be a recognized lifecycle value
valid_statuses := {"proposed", "accepted", "rejected", "deprecated", "superseded"}

deny contains msg if {
    input.status
    not valid_statuses[input.status]
    msg := sprintf("POLICY DOC-ADR-002: ADR front-matter has invalid status '%v' — must be one of: proposed, accepted, rejected, deprecated, superseded",
                   [input.status])
}

# driver_refs must be non-empty (each accepted/proposed ADR must trace to at least one QAS-* or constraint)
deny contains msg if {
    input.status in {"proposed", "accepted"}
    not input.driver_refs
    msg := "POLICY DOC-ADR-003: accepted/proposed ADR has no driver_refs — every decision must trace to a quality-attribute scenario (QAS-*) or constraint; a decision with no driver is accidental complexity"
}

deny contains msg if {
    input.status in {"proposed", "accepted"}
    count(input.driver_refs) == 0
    msg := "POLICY DOC-ADR-004: accepted/proposed ADR has an empty driver_refs list — at least one QAS-* or constraint reference is required"
}
```

The body completeness check (≥2 options, consequences section) is performed by the `architecture-evaluator` as a structural document review rather than a Rego gate, because the body is free-form Markdown. The Rego gate covers the **machine-readable front-matter**; the rubric covers the prose completeness.

---

## 3. How each policy traces to a driver and ADR

Every rule in the library carries two references in its comment header — a `QAS-*` (the quality-attribute scenario from the utility tree) and an `ADR-*` (the decision the rule enforces). This makes the traceability bidirectional:

- **Driver → policy:** from `architecture/<slug>/quality-attributes.md`, every `(H,*)` security/reliability/compliance/documentation scenario has at least one Rego rule in the library that guards it. An `(H,*)` scenario with no guarding rule is reported as a `critical` gap in the fitness-functions flow (`60-evaluation/fitness-functions.md`).
- **ADR → policy:** every ADR whose `Follow-ups / fitness functions` block names a conftest check has a corresponding package + rule in this library. The ADR is the why; the Rego rule is the guard that stops the why from silently eroding (the *function-per-ADR pattern*, `60-evaluation/fitness-functions.md`).
- **Policy → driver/ADR:** the operator can trace any failing `conftest` output back to the QAS and ADR by reading the policy ID embedded in the message (e.g. `POLICY SEC-TF-001 [QAS-SEC-01]`).

The **policy traceability matrix** is maintained in `architecture/<slug>/fitness-functions.md` alongside the broader fitness-function register, with one row per rule:

| Policy ID | Package | Driver ref | ADR ref | Input domain | CI stage |
|---|---|---|---|---|---|
| SEC-TF-001 | `security.terraform` | QAS-SEC-01 | ADR-SEC-001 | Terraform plan JSON | plan-gate |
| REL-K8S-001 | `reliability.k8s` | QAS-AVAIL-01 | ADR-AVAIL-003 | K8s manifests | manifest-lint |
| COMP-TF-001 | `compliance.terraform` | QAS-COMP-01 | ADR-COMP-001 | Terraform plan JSON | plan-gate |
| DOC-ADR-001 | `documentation.adr` | rubric: ADR complete | — | ADR front-matter JSON | pre-commit + PR gate |

---

## 4. Wiring into 40-cross-cutting and 50-infrastructure VERIFY

The policy library is the **executable form of the named hard oracles** in `quality-attribute-rubric.md`. The VERIFY step of the `40-cross-cutting` and `50-infrastructure` workflows runs `conftest` as its primary structural gate:

**`40-cross-cutting` flows (security, compliance, privacy):**
- `security-architecture.md` VERIFY step: after the solution-architect authors the threat model and ADRs, the `architecture-evaluator` runs `conftest verify` against the security and compliance policy packages over the current Terraform plan + K8s manifests. A `deny` output is a `hard`-oracle failure (`oracle:"hard"`, `severity:critical` for SEC-TF-003 secret-literal / SEC-K8S-003; `severity:major` for SEC-TF-001 public storage, REL-K8S-001 replica count). The VERIFY step does not proceed to the soft rubric until all `deny` rules are silent.
- `privacy-compliance-architecture.md` VERIFY step: runs the `compliance.terraform` package. A missing `data_classification` tag or missing encryption-at-rest on a PII store is a `critical` hard-oracle failure blocking the gate.

**`50-infrastructure` flows (IaC, CI/CD, containerization):**
- `infrastructure-as-code.md` VERIFY step: the policy gate (`conftest`) is the first check — before `terraform plan` is accepted, the plan JSON is evaluated against `security.terraform` + `compliance.terraform`. The `infrastructure-as-code.md` hard oracle *"Policy gate (policy-as-code): every plan passes a policy-as-code check before apply"* is satisfied specifically by this Rego library running under `conftest`.
- `cicd-architecture.md` pipeline stages that run conftest:
  - **`pre-commit`:** `documentation.adr` package — checks front-matter completeness on any modified ADR file (fast, zero-dependency, runs locally via `conftest` CLI).
  - **`plan-gate`** (after `terraform plan -out`): `security.terraform` + `compliance.terraform`.
  - **`manifest-lint`** (after `helm template` or kustomize build): `security.k8s` + `reliability.k8s`.
  - **`dockerfile-lint`** (on any Dockerfile change): `security.dockerfile`.
  - Gate semantics: any `deny` in a triggered stage **fails the build** (`exit 1`); `warn` is advisory but logged and reported in the PR summary. No `conftest allow` bypass is permitted without a human-authored exemption tag on the resource and a corresponding ADR note.

**How the fleet delivers these:**
1. The `solution-architect` (one writer) authors the Rego source files into `architecture/<slug>/policies/` — the policy library is an architecture artifact, not product code (`guardrails.md` §1).
2. The `architecture-evaluator` verifies that every `(H,*)` security/reliability/compliance leaf of the utility tree and every structural ADR maps to at least one policy rule — no ungoverned hard oracle.
3. The operator copies (or symlinks) `architecture/<slug>/policies/` into the CI pipeline's policy directory and wires the `conftest` invocations per the stage mapping above. The fleet never modifies the actual pipeline config or runs `conftest apply`-equivalent commands.

---

## 5. Authoring rules — constraints for the fleet

The following constraints apply when the fleet authors new Rego rules, so the library stays grounded and maintainable:

- **One package per input-domain × quality-attribute pair.** Do not mix input domains (Terraform plan and K8s manifest) in a single package — `conftest` passes one input at a time per invocation.
- **Driver reference is mandatory.** Every rule's comment header must cite the `QAS-*` or `ADR-*` it enforces. A rule with no driver reference is not authored — it would be accidental complexity made executable.
- **Use `deny` for hard oracles, `warn` for advisory.** `deny` exits non-zero and blocks the pipeline; `warn` logs but does not fail. Map `deny` to `oracle:"hard"` findings and `warn` to `oracle:"soft"` findings in `finding-schema.md`.
- **Policy IDs are stable and unique.** Format: `<DOMAIN>-<SUBDOMAIN>-NNN` (e.g. `SEC-TF-001`). Once assigned, an ID is immutable; a replaced rule gets a new ID and the old one is deprecated with a comment.
- **Rego style:** use `future.keywords.if` and `future.keywords.contains` for readability; prefer `deny contains msg if { ... }` over `deny[msg] { ... }` (the former is the OPA v1 idiomatic form). Keep each rule focused on a single assertion — do not bundle multiple distinct denials in one rule body.
- **Fixture tests required.** For each new rule, the fleet authors a companion OPA unit test (`<package>_test.rego`) with at least one passing fixture and one failing fixture. This is a verification artifact (`tests/policies/`) not product code.
- **Right-size to the project.** For a project whose stack (per `project-architecture-config.md`) is a modular monolith with a single primary data store and no multi-region topology, do not author multi-region, service-mesh, or cross-AZ Rego policies absent a driver that demands them — that is accidental complexity made executable (`quality-attribute-rubric.md` → simplicity; `guardrails.md` §2).

---

## Cross-references

- `shared/quality-attribute-rubric.md` — the hard oracles this library enforces (Trust boundary secured, Data lifecycle lawful, ADR complete, No un-accepted SPOF, Supply-chain provenance)
- `60-evaluation/fitness-functions.md` — the fitness-function register where each policy rule is listed with its `driver_ref`, `decision_ref`, `CI stage`, and `failure message`; the policy traceability matrix lives here
- `40-cross-cutting/security-architecture.md` — STRIDE threat model and zero-trust controls that the `security.terraform` + `security.k8s` packages enforce
- `40-cross-cutting/privacy-compliance-architecture.md` — PII classification and data-lifecycle requirements enforced by `compliance.terraform`
- `50-infrastructure/infrastructure-as-code.md` — the IaC policy-gate hard oracle that this library satisfies
- `50-infrastructure/cicd-architecture.md` — the pipeline stages into which `conftest` invocations are wired
- `shared/adr-template.md` — the `Follow-ups / fitness functions` block in each ADR names the policy rule ID that enforces it
- `shared/guardrails.md` §1, §2, §7 — the fleet authors specs, never applies; every rule traces to a driver; read-only on live environments
