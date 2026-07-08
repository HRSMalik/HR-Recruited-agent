# IDP Capability Checklist — Internal Developer Platform (CNCF Platform Engineering)

The fleet uses this checklist to evaluate, scope, or propose an Internal Developer Platform (IDP). Grounded in the **CNCF "Platforms" Whitepaper** (2023) and the **CNCF Platform Engineering Maturity Model**, it defines what a credible IDP must cover, how to score current-state maturity per capability area, and the DX metrics that tell you whether the platform is working. Use it as the capability-coverage oracle in any `50-infrastructure/` or `90-specialized/` flow that touches IDP, platform engineering, developer portals, or golden-path tooling. Cross-ref: `workflows/50-infrastructure/platform-engineering.md` (flow that uses this checklist as its hard gate), `workflows/10-styles-decomposition/team-topology-decomposition.md` (the team topology that shapes IDP ownership).

---

## Core Definitions

**Platform-as-a-product (PaaP):** The platform team treats the internal developer population as *customers* and the IDP as a *product* — it has a roadmap, a product owner, SLOs, a feedback loop (surveys, usage telemetry, support tickets), and a backlog prioritized by developer pain, not by what the ops team finds interesting. Platforms imposed without a product mindset become shelfware; adoption and shadow-IT rate are the leading signals of failure.

**Golden path (also "paved road"):** A curated, pre-validated, self-service route through a capability area — an opinionated template, a workflow, or a wizard that delivers the *right* outcome for 80% of teams without them needing to know the underlying infrastructure. A golden path is not a mandate: teams *can* go off it, but the path is so much easier that they rarely need to. The platform's job is to keep the golden path current and to close the gap between "using the path" and "doing the thing" to near-zero.

**DX metrics (the platform's hard oracle):** The three leading indicators the platform team tracks and publishes:
- **Time-to-first-deploy (TTFD):** Wall-clock from "new team member / new service created" to first artifact in the lowest non-prod environment. Target is usually ≤ 1 day; above 1 week signals the onboarding path is broken.
- **Lead time for change (LTC):** Median elapsed time from `git commit` (or ticket start, depending on convention) to the artifact running in production. The DORA "lead time for changes" metric.
- **Shadow-IT rate:** Fraction of production capability areas where a team has *bypassed the platform* and provisioned their own tooling (separate CI, bespoke secrets store, hand-rolled observability). High shadow-IT is the market signal that the platform is not meeting developer needs; it is measured via infra inventory scans and cost-center attribution, not self-report.

Supporting DX metrics (secondary):
- **Cognitive load score:** Survey-based; team's subjective time spent on platform/toil vs product work.
- **Platform NPS:** Net Promoter Score from developer surveys (platform is a product; measure customer satisfaction).
- **On-call handoff rate:** Fraction of platform incidents that spill into application-team on-call (low = platform team has good SLOs).

---

## Capability Areas — Coverage Checklist

For each area, a current-state audit or a platform proposal must answer: **(a)** what exists today, **(b)** maturity level (None / Ad-hoc / Managed / Self-service / Optimized), **(c)** the gap vs the project's quality-attribute drivers, and **(d)** the golden-path proposal (if missing).

### 1. Developer Onboarding & Golden Paths

Scope: new-engineer setup, new-service scaffolding, local dev environment, contributing guide, inner-loop tooling.

Checklist items:
- [ ] A single "day-one" guide that takes a new engineer from `git clone` to a running local dev stack in ≤ 30 min (oracle: TTFD ≤ 1 day).
- [ ] Service/app scaffolding templates (cookiecutter, `create-app`, Backstage scaffolder, or equivalent) that emit a repo already wired to CI, observability, and secrets — no manual post-scaffold config.
- [ ] Golden path for the project's primary language/stack (see `project-architecture-config.md`); deviations from stack require an explicit off-ramp ADR.
- [ ] `README` freshness oracle: the getting-started section runs end-to-end in CI (a weekly smoke that clones + follows the guide in a clean container) — a README that lies is worse than none.
- [ ] Inner-loop dev setup documented and automated: local env vars, mock/seed data, hot-reload.

### 2. Application Development & Delivery — CI/CD

Scope: pipelines, build, test, artifact management, promotion gates, deployment automation. Cross-ref `workflows/50-infrastructure/cicd-architecture.md`.

Checklist items:
- [ ] A canonical CI pipeline template (golden-path CI): lint → unit test → build → container image push → integration test → security scan, reusable across services without copy-paste.
- [ ] Deployment pipeline: staging → production promotion with an explicit gate (manual approval OR automated fitness-function gate — not both simultaneously required without driver).
- [ ] Artifact registry with image signing / provenance attestation (SLSA level ≥ 2 if the project has a supply-chain driver).
- [ ] Pipeline as code (Jenkinsfile / GitHub Actions workflow / Tekton Pipeline) versioned alongside the service — no click-ops pipelines.
- [ ] Lead time for changes (LTC) measured and published from pipeline telemetry; DORA four-key metrics visible to the team (LTC, deployment frequency, change failure rate, MTTR).
- [ ] Branch strategy + promotion model matches the project's declared VCS/promotion strategy in `project-architecture-config.md` (§ Deployment & environments or equivalent); no force-push on protected branches. Do NOT read a project-memory file for this — the config file is the contract boundary (`guardrails.md §8`).

### 3. Infrastructure Orchestration & Provisioning

Scope: compute, networking, storage, IaC, environment parity, immutable infra. Cross-ref `workflows/50-infrastructure/infrastructure-as-code.md`, `deployment-topology.md`.

Checklist items:
- [ ] Infrastructure provisioned via IaC (Terraform / Pulumi / Helm / CDK) — no snowflake environments; every environment is reproducible from code.
- [ ] Self-service infra: developers can request a new environment or scale a resource via a PR to the IaC repo (or a portal UI that submits a PR) — no ops ticket required for routine provisioning.
- [ ] Environment parity: dev, staging, and production use the same container images, the same config shape (env var names), and the same infra primitives (no "works on my machine" divergence). Parity gaps are tracked as findings.
- [ ] Container orchestration strategy is documented (Docker Compose for local / k8s for staging+prod / managed container service) with the rationale ADR (see `workflows/50-infrastructure/containerization-orchestration.md`).
- [ ] Drift detection: infra state is reconciled automatically or on a schedule; manual changes outside IaC are flagged (terraform plan / drift report in CI).

### 4. Environment Management

Scope: ephemeral environments, environment lifecycle, promotion, namespace/tenant isolation.

Checklist items:
- [ ] Environment inventory is explicit: named environments, their purpose, their SLO, and who owns them — documented, not tribal knowledge.
- [ ] Ephemeral environments (preview / PR environments): each PR can spin up an isolated stack for review and is torn down on merge/close. Absent a driver that makes this too expensive, ephemeral envs are the golden path for PR review.
- [ ] Environment promotion is gated (automated tests or explicit approval), never via direct production push.
- [ ] Namespace / tenant isolation is enforced at the infra level (k8s namespaces, VPC isolation, or equivalent) — not just by convention.
- [ ] Environment cost is bounded: ephemeral environments have a TTL or an explicit cleanup policy; no orphaned environments in the cost bill.

### 5. Observability & Dashboards

Scope: logs, metrics, traces, alerting, SLO/SLI dashboards, on-call runbooks. Cross-ref `workflows/40-cross-cutting/observability-architecture.md`.

Checklist items:
- [ ] The three pillars shipped out of the golden-path template: structured logs (JSON, correlation ID propagated), metrics (RED: Rate, Errors, Duration per service), distributed traces (OpenTelemetry instrumented).
- [ ] Observability is automatic for services that follow the golden path — no per-team setup required; an uninstrumented service is a deviation.
- [ ] SLO/SLI defined per service (availability %, p99 latency, error rate) and tracked in a dashboard visible to the team and the platform team; alerting fires before the error budget is exhausted.
- [ ] Runbooks linked from alerts: an alert with no runbook is a hard oracle failure (on-call responders cannot act).
- [ ] Alerting fatigue monitored: alert-to-page ratio tracked; a high ratio (most alerts do not page) is a signal that the alerting threshold is wrong, not that on-call is fine.
- [ ] Log retention and trace sampling policy documented and driver-justified (compliance drives retention floors; cost drives sampling).

### 6. Secrets & Identity

Scope: secrets management, service identity, mTLS, credential rotation, RBAC/IAM. Cross-ref `workflows/40-cross-cutting/security-architecture.md`.

Checklist items:
- [ ] No secrets in source code, no secrets in environment variable files committed to the repo. Oracle: a pre-commit / CI secret-scan (truffleHog / detect-secrets / gitleaks) is mandatory.
- [ ] Secrets managed by a dedicated store (Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault) — not `.env` files injected manually per environment.
- [ ] Secrets injected at runtime via the platform (sidecar, init container, or provider-backed CSI driver) — the application reads from an env var or mounted file; it never calls the secrets API directly.
- [ ] Service identity: each service has a non-human identity (workload identity / IRSA / pod identity / mTLS certificate) used for service-to-service and service-to-cloud-resource authz — no shared credentials.
- [ ] Credential rotation is automated (or a documented, tested runbook with a rotation interval ≤ the project's compliance requirement).
- [ ] RBAC model for platform access is documented: who can read / write / delete per environment, and the policy is enforced at the IAM level, not by convention.

### 7. Service Catalog (e.g. Backstage)

Scope: service discovery, ownership registry, dependency map, API catalog, TechDocs. CNCF reference: Backstage / Port / OpsLevel.

Checklist items:
- [ ] Every production service has a catalog entry: owner team, on-call rotation, SLO, repo link, runbook, downstream dependencies.
- [ ] API catalog: every internal API registered with its schema (OpenAPI / AsyncAPI), version, and consuming teams — enables impact analysis before a breaking change.
- [ ] Ownership is enforced: a service with no registered owner is a hard oracle failure (who is paged when it breaks?).
- [ ] TechDocs / ADR catalog: architecture decision records are discoverable via the service catalog or a linked docs site — not buried in a repo subdirectory that no one knows to look in.
- [ ] Dependency graph is generated from catalog data: upstream/downstream service map enables blast-radius assessment and change-impact analysis.
- [ ] New-service scaffolding (§1) auto-registers the new service in the catalog with the scaffolding author as the initial owner.

### 8. Cost & FinOps Visibility

Scope: cloud cost attribution, showback/chargeback, optimization alerts, budget gates. Cross-ref `workflows/90-specialized/cost-finops-architecture.md`.

Checklist items:
- [ ] Cloud costs are tagged to the service/team/environment level — untagged resources are a hard oracle failure (you cannot optimize what you cannot attribute).
- [ ] Cost dashboard visible to application teams (showback at minimum) so developers can see the cost consequence of a resource choice — this is the primary FinOps lever for a platform.
- [ ] Budget alerts: each environment has a spend cap; breaching it triggers an alert to the team and the platform, not a surprise bill at end of month.
- [ ] Cost is an input to ADR decisions: the `capacity-model.md` and the cloud-posture ADRs reference the monthly cost estimate for each option (`evaluation-method.md` → CBAM).
- [ ] Orphan resource cleanup: a weekly scan identifies resources with no owner tag / catalog entry and raises a cost finding; no silent sprawl.

### 9. Security & Policy Guardrails

Scope: policy-as-code, supply chain security, CVE scanning, compliance gates, network policy. Cross-ref `workflows/40-cross-cutting/security-architecture.md`.

Checklist items:
- [ ] Policy-as-code enforced in CI: OPA / Kyverno / Sentinel rules block non-compliant IaC before it merges (e.g. public S3 buckets, privileged containers, missing resource limits).
- [ ] Container image scanning in the CI golden path: CVE scan blocks deploy on CRITICAL severity with a documented exception process (not a skip flag left in by default).
- [ ] SBOM (Software Bill of Materials) generated per artifact at build time; stored alongside the image in the artifact registry — required if any compliance driver names supply-chain.
- [ ] Network policy enforced: default-deny + explicit allow rules between services; cross-service traffic not in the catalog is blocked, not just monitored.
- [ ] Compliance gates mapped to the project's regime (SOC 2, HIPAA, ISO 27001, etc. per `project-architecture-config.md`): each gate has an owner, a check, and an audit trail.
- [ ] Penetration test / threat model review cadence is defined and tracked (not just done once at launch).

### 10. API & Integration Platform

Scope: API gateway, internal service mesh, event bus / message broker, external integration, contract testing. Cross-ref `workflows/30-integration/`.

Checklist items:
- [ ] A single API gateway / ingress layer for external traffic: the golden path for exposing a new endpoint is "add a route to the gateway config" not "open a new port."
- [ ] Internal service communication has a defined style (REST / gRPC / async events) and a golden-path library or sidecar (not each team choosing independently).
- [ ] Consumer-driven contract tests (Pact or equivalent) enforced in CI for any service-to-service API that is not behind the gateway — a producer cannot break a consumer without the test catching it.
- [ ] Event bus / message broker (if applicable): schema registry enforced; producers cannot publish a breaking schema change without a version bump and a consumer migration plan.
- [ ] External integration anti-corruption layers (ACLs) are documented per foreign system: the system's schema is translated at the boundary, not leaked into the domain model.

### 11. Data Platform

Scope: data stores, migrations, backup/restore, data access policies, analytics / BI access. Cross-ref `workflows/20-data/`.

Checklist items:
- [ ] Database provisioning is on the golden path: new data store created via IaC + catalog entry + backup policy attached at creation, not ad-hoc.
- [ ] Schema migrations are versioned and automated (Flyway / Alembic / Atlas) — no manual DDL applied to production; migration scripts reviewed in PR.
- [ ] Backup and restore tested on a schedule: a backup that has not been restored in a test is not a backup (TTAR — time-to-actual-restore measured, not just backup success logged).
- [ ] Data access policy enforced: PII fields tagged in the schema registry; access to tagged fields requires an explicit IAM grant and is logged.
- [ ] Analytics / BI access decoupled from the operational store: read replicas or a separate analytics sink (OLAP / data warehouse) serves reporting queries; no analyst queries hitting the production OLTP primary.

### 12. Support & Documentation

Scope: platform docs, runbooks, internal support channels, SLA for platform support, incident playbooks.

Checklist items:
- [ ] Platform docs are versioned, searchable, and accurate — freshness oracle (§1) applies here too.
- [ ] Platform team has a published SLA for support requests: e.g. P1 (platform down) ≤ 1 hr response, P2 (degraded) ≤ 4 hr, P3 (question/new feature) ≤ 2 days.
- [ ] Incident playbooks per platform component: runbook linked from every alert (§5); a platform component with no playbook is a hard oracle failure.
- [ ] Feedback loop documented: how a developer reports a platform bug or requests a new golden path; backlog is visible (platform as a product — backlog is a public artifact, not a black box).
- [ ] Platform changelog: teams know what changed in the platform and when; breaking changes in the platform are communicated with a migration guide ≥ 2 sprints in advance.

---

## Maturity Scale

| Level | Label | Signal |
|---|---|---|
| 0 | None | Capability does not exist; developers work around the gap (shadow-IT). |
| 1 | Ad-hoc | Exists but as hero knowledge or manual steps; not reproducible by a newcomer. |
| 2 | Managed | Documented and repeatable; requires a ticket / ops team to execute. |
| 3 | Self-service | Developer can execute the capability independently via the platform, no ops ticket. |
| 4 | Optimized | Self-service + measurably improving (DX metrics tracked, feedback loop closed, golden path kept current). |

Target: **≥ Level 3** on §1–6 and §9 before declaring IDP operational. §7 (catalog), §8 (FinOps), §10–12 may be Level 2 in early platform maturity with an explicit gap-and-roadmap ADR.

---

## Hard Oracles (gate the IDP proposal)

These must be met before the platform proposal is marked `VERIFIED`:

- **DX oracle:** TTFD ≤ 1 day (or the project-specific target in `project-architecture-config.md`); above 1 week is a hard block.
- **Ownership oracle:** Every production service in the catalog has an owner and a runbook; any orphan is a blocking finding.
- **Secret-scan oracle:** No secrets in any repo checked by the pre-commit / CI secret scanner; any finding is a critical block.
- **Backup-restore oracle:** Backup restore has been executed and timed within the last 30 days (or the project's RPO interval); an untested backup is a hard finding.
- **Policy-gate oracle:** At least one policy-as-code check is enforced in CI; a platform with zero automated policy enforcement is Level 1 at best.

Soft oracles (advisory, tracked as findings but non-blocking):
- Platform NPS ≥ 30 (or improving quarter-over-quarter).
- Shadow-IT rate ≤ 10% of capability areas.
- LTC improving (DORA elite: ≤ 1 day median; DORA high: ≤ 1 week).

---

## How Flows Use This File

- **`50-infrastructure/platform-engineering.md`** uses §1–12 as the structured capability-coverage gate in its VERIFY step: each capability area gets a current-state maturity score and a gap-finding if below Level 3. Any hard oracle failure blocks the flow. **NOTE: this workflow does not yet exist** — the gate mechanism is declared but unenforced until `workflows/50-infrastructure/platform-engineering.md` is authored; that file is the declared primary consumer of this checklist and must be created before this checklist can serve as a live hard gate.
- **`10-styles-decomposition/team-topology-decomposition.md`** references §PaaP + §1 (golden paths) when evaluating whether the team topology supports a platform team (Stream-Aligned + Platform topology per Skelton/Pais) vs an enabling team that temporarily fills platform gaps. **NOTE: this workflow does not yet exist** — the cross-reference is a stub; the folder (`workflows/10-styles-decomposition/`) contains five other decomposition workflows but not this one; author it before relying on this integration point.
- **`finding-schema.md`** formats all capability gaps as findings: `type: "operability"` or `type: "scalability"` per area, `oracle: "hard"` for the five hard gates above, `oracle: "soft"` for the DX metric and NPS oracles.
- **`evaluation-method.md`** → CBAM applies when the platform proposal involves a build-vs-buy decision (e.g. self-hosted Backstage vs a managed portal like Port/OpsLevel): quantify the benefit (shadow-IT reduction, TTFD delta) against the build+run cost over a 3-year horizon.
