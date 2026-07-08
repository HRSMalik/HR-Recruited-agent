# Software Supply-Chain Contract — SLSA · Sigstore · SBOM · Rekor

Every build that produces a deployable artifact is an attack surface. This contract defines how the fleet authors the supply-chain design target and how the hard oracle (`quality-attribute-rubric.md` → *Supply-chain provenance*) is verified. The fleet proposes the SLSA level, the signing scheme, and the SBOM format; the operator wires the toolchain and runs the pipeline. The fleet never executes the pipeline, never pushes an artifact, and never applies the signing key — it documents the design decision and the verification command so the controller can confirm the contract is met.

---

## 1. Regulatory driver — EU Cyber Resilience Act (CRA)

The **EU Cyber Resilience Act** (Regulation (EU) 2024/2847, entered into force 2024-12-10; vulnerability-reporting obligations apply from **2026-09-11**) imposes two operative obligations relevant to every pipeline design:

1. **Active exploitation disclosure** — a manufacturer must notify ENISA of an actively exploited vulnerability in any product with digital elements within **24 hours** of becoming aware. The SBOM is the artefact that makes it possible to answer "are we affected?" quickly; without one, the 24-hour window is unrealistic.
2. **Security update availability** — updates addressing known vulnerabilities must be made available for the expected product lifetime. The provenance chain (SLSA + signed attestation) establishes *what was built and when*, enabling precise scope determination for each CVE.

CRA is therefore a **hard compliance driver** (`finding-schema.md` `type:"compliance"`) for any system the fleet designs that ships to EU markets or is used by EU customers — including SaaS products where the operator is a "manufacturer" under Art. 3(14). Surface it as a named driver in the `quality-attribute-scenarios.md` utility tree under *Security › Supply-chain integrity* and *Compliance › CRA vulnerability reporting*. Do not assume the driver away; if scope is uncertain, flag it as an open driver question.

---

## 2. SLSA level — stated target, not a vague aspiration

**Reference standard:** SLSA v1.2, approved November 2025 (supply-chain-levels.dev/spec/v1.2). SLSA is not in development; v1.2 is the current normative version. Always cite by version and date to avoid the "in development / moving target" fallacy.

The SLSA specification defines four levels of progressively stronger provenance guarantees:

| Level | Guarantee | Minimum toolchain requirement |
|-------|-----------|-------------------------------|
| **L0** | No provenance | Any local build |
| **L1** | Provenance exists (build script generates it) | Build script emits a provenance document; no signing required |
| **L2** | Provenance is signed by a hosted build service | CI runs on a managed hosted runner; provenance is signed by the service (e.g. GitHub Actions OIDC token); artifact is not self-built by the developer |
| **L3** | Provenance is non-falsifiable (hardened service) | Build service provides strong isolation + non-falsifiable provenance (e.g. `slsa-github-generator` with Sigstore OIDC signing, Rekor transparency log); build instructions are verifiably from source control |

**Contract rule:** the fleet's ADR for a pipeline design **must state the SLSA target level explicitly** — "SLSA L2" or "SLSA L3" — and must justify the choice against the security/compliance driver. A pipeline ADR that says "high supply-chain security" with no SLSA level is **not a decision** and blocks the ADR-complete hard oracle (`quality-attribute-rubric.md`). SLSA L2 is the **minimum bar** for any system handling PII or financial data; SLSA L3 is the target where the compliance regime or a stated security driver demands non-falsifiable provenance (e.g. CRA, FedRAMP-High, or a regulated financial environment). Use CBAM (`evaluation-method.md` → *CBAM*) to justify L3 over L2 only when the security driver requires it — L3 adds pipeline complexity and build latency; L2 is correct for most small-team deployments.

Cross-reference: `50-infrastructure/cicd-architecture.md` → *Supply chain secured at SLSA level ≥ 2* hard oracle.

---

## 3. Build provenance — signed attestation verified by `cosign verify-attestation`

A **provenance attestation** is a signed document that answers: *who built this artifact, from what source, using what build system, at what time, and with what inputs*. It is the machine-readable proof that the artifact was produced by the authorized pipeline, not by a developer's laptop or a compromised build node.

**Toolchain (Sigstore):** The fleet always proposes **Sigstore** as the signing and verification infrastructure. Sigstore is the open-source, CNCF-hosted signing stack used by SLSA, npm, PyPI, and the Linux Foundation. Its components as they appear in a pipeline design:

| Component | Role in the design |
|-----------|--------------------|
| **`cosign`** | Signs OCI container images and attestations; verifies signatures at deploy time. The signing identity is bound to an OIDC token (keyless signing) — no long-lived signing key to rotate or leak. |
| **`slsa-github-generator`** | GitHub Actions reusable workflow that generates SLSA L3 provenance attestations for container images and build artifacts; signs them via Sigstore OIDC. Use for SLSA L3 targets. |
| **Fulcio** | Sigstore's certificate authority — issues short-lived code-signing certificates bound to the OIDC identity (GitHub Actions workflow identity, not a developer identity). No key management burden. |
| **Rekor** | Sigstore's **immutable transparency log** (§4 below). Every signature is appended to Rekor; the log is publicly auditable and append-only. |

**The hard oracle verification command** (wired into the `VERIFY` step of `50-infrastructure/cicd-architecture.md`):

```
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp "^https://github.com/<org>/<repo>/.github/workflows/.*" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  <image-reference>@sha256:<digest>
```

This command is **external and deterministic** — it either exits 0 (attestation present, signature valid, OIDC identity matches the expected workflow) or exits non-zero (block). It is not a prose assertion; it is a runnable gate. The fleet authors this command into the pipeline design's verification block; the operator runs it. An artifact that cannot pass `cosign verify-attestation` **must not be promoted** — this is a hard oracle failure (`oracle:"hard"`, `severity:"critical"`).

**Design rule:** the signed attestation must be stored as an OCI referrer or attached to the image in the registry (not as a sidecar file); the deployment step must retrieve and verify it *before* pulling the image for deployment. Verification at deploy time, not just at build time, closes the TOCTOU window between signing and deployment.

---

## 4. Rekor transparency log — append-only, publicly auditable

**Rekor** is Sigstore's immutable transparency log. Every `cosign sign` and `slsa-github-generator` attestation appends an entry to Rekor. The entry contains a timestamped, cryptographically-linked record of: the artifact digest, the signing certificate (OIDC-bound identity), and the attestation payload hash.

**Why Rekor matters as a design element:**

- **Non-repudiation** — a signed artifact cannot later be claimed "never built" or "signed by someone else"; the Rekor entry is the court-admissible timestamp.
- **Anomaly detection** — the transparency log enables post-hoc auditing: "were any artifacts signed from outside the expected workflow identity?" A log monitor (e.g. `rekor-monitor`) can alert on unexpected signers — an indicator of a supply-chain compromise.
- **CRA vulnerability reporting** — the Rekor log gives an auditor the exact build timestamp and source commit for any artifact, making it possible to scope "were any shipped artifacts built from a commit containing the vulnerable dependency?" within the 24-hour reporting window.

**Design rule:** the fleet's pipeline ADR must name Rekor as the transparency log backend for all Sigstore operations and must include a `rekor-monitor` or equivalent anomaly-detection step (or record the absence as an accepted risk with disposition). The public Rekor instance (`rekor.sigstore.dev`) is correct for open-source projects; a self-hosted Rekor instance may be required for air-gapped or highly-regulated environments — surface as a driver question if the compliance regime demands it.

---

## 5. SBOM — CycloneDX or SPDX, generated at build time, attached as attestation

A **Software Bill of Materials** (SBOM) is a machine-readable inventory of every component, library, and transitive dependency in a delivered artifact. The fleet proposes one of two standard formats:

| Format | Governing body | Primary use |
|--------|----------------|-------------|
| **CycloneDX** (v1.6+) | OWASP | Vulnerability management, VEX (Vulnerability Exploitability eXchange) — the format preferred for CRA compliance workflows |
| **SPDX** (v2.3 / v3.0) | Linux Foundation / ISO/IEC 5962:2021 | License compliance, provenance tracing — the format required by US Executive Order 14028 and NIST guidance |

**Contract rule:** the fleet's design must specify which format is used and why (the ADR choice). CycloneDX is the default for systems under the CRA driver (VEX support is native; tooling for ENISA-compatible reporting is mature). SPDX is correct when US government supply-chain requirements apply. Either format satisfies the hard oracle; the choice must be recorded in an ADR.

**Generation toolchain (name one in every pipeline design):**

- `syft` (Anchore) — container image and filesystem SBOM; produces CycloneDX or SPDX; integrates with `grype` for vulnerability scanning.
- `cdxgen` (OWASP) — native CycloneDX; polyglot (Python, Node, Java, Go); preferred for CRA workflows.
- `trivy sbom` (Aqua) — SBOM as a sub-command of the Trivy scanner; lowest marginal cost when Trivy is already the CVE scanner.

**Attachment:** the SBOM must be attached to the OCI image as a signed attestation (`cosign attest --type cyclonedx` or `--type spdx`) — not as a loose file alongside the image. This makes the SBOM part of the provenance chain: it is retrievable, verifiable, and tied to the exact image digest. A SBOM stored only as an artifact in a CI run's artifact store — and not attached to the image — does not satisfy the hard oracle; the image can be pulled and deployed without the SBOM following it.

**Post-release vulnerability tracking:** the SBOM enables continuous vulnerability monitoring. The pipeline design must include a scheduled rescan step (weekly minimum, or on new CVE publication for a listed component) that feeds results into the issue tracker. For CRA compliance, new critical/high CVEs discovered post-release trigger the 24-hour disclosure obligation — the rescan step is therefore a **compliance control**, not merely a quality signal.

---

## 6. Hard oracle — provenance present + signed + SBOM (wired into cicd-architecture.md VERIFY)

This is the single, deterministic gate that the `VERIFY` step of `50-infrastructure/cicd-architecture.md` enforces before any artifact is promoted to a production-like environment. The oracle has three parts; all three must be green:

| Oracle part | What passes | What blocks |
|-------------|-------------|-------------|
| **Provenance present** | A SLSA provenance attestation exists for the artifact digest being promoted | No attestation attached to the image digest |
| **Signature valid** | `cosign verify-attestation --type slsaprovenance ...` exits 0; the signing certificate's OIDC identity matches the expected workflow path and issuer | Exit non-zero; OIDC identity mismatch; certificate expired or untrusted |
| **SBOM present and signed** | A CycloneDX or SPDX SBOM attestation is attached to the image digest; `cosign verify-attestation --type cyclonedx ...` (or `--type spdx`) exits 0 | No SBOM attestation; SBOM stored only as a CI artifact without image attachment |

Any part failing is `severity:"critical"`, `oracle:"hard"` — the finding blocks promotion. The evidence field in the finding must cite the specific `cosign verify-attestation` exit code and the artifact digest that failed, so the failure is traceable and reproducible.

**Placement in `cicd-architecture.md`:** the VERIFY step runs **before** the image is pulled for deployment, in the pre-promotion gate (staging → prod). It must appear as a named job step in the pipeline YAML design, referencing these three checks by name. A pre-promotion stage with no explicit supply-chain oracle block is a hard-oracle failure (*Supply-chain provenance* in `quality-attribute-rubric.md`).

---

## 7. What the fleet authors vs. what the operator runs

| Fleet (architect-agent) — proposes & documents | Operator (controller/engineer) — executes |
|------------------------------------------------|------------------------------------------|
| The ADR specifying the SLSA level target and the justification | Wires the `slsa-github-generator` reusable workflow into GitHub Actions |
| The pipeline stage design showing where `cosign sign` and `cosign attest` run | Adds `cosign` steps to the actual CI YAML |
| The SBOM generation strategy (format, tool, attachment method) | Runs `syft` / `cdxgen` / `trivy sbom` in the build job |
| The `cosign verify-attestation` command (exact flags, identity regexp, OIDC issuer) as the VERIFY gate spec | Executes `cosign verify-attestation` in the pre-promotion gate |
| The Rekor transparency log as the named backend; the anomaly-detection recommendation | Configures `rekor-monitor` or equivalent; ingests Rekor alerts |
| The CRA compliance controls catalog (disclosure timeline, rescan cadence, VEX workflow) | Operates the rescan job; files ENISA notifications |
| The ADR recording rejected alternatives (local signing rejected — no Rekor non-repudiation; self-hosted Rekor rejected — no public auditability unless air-gapped driver exists) | — |

The fleet **never** runs the pipeline, never pushes a signed artifact, never holds a signing key, and never writes to the Rekor log. It authors the design, the ADR, the VERIFY gate specification, and the compliance controls catalog; the controller builds it.

---

## 8. Cross-references

- `50-infrastructure/cicd-architecture.md` — *Supply chain secured at SLSA level ≥ 2* hard oracle; *Standards & techniques: Supply-chain security (SLSA + SBOM + Sigstore)*; the VERIFY step this contract is wired into.
- `shared/quality-attribute-rubric.md` — *Supply-chain provenance* hard oracle row (provenance present + signed + SBOM); *Data lifecycle lawful* hard oracle (SBOM is the artefact enabling CRA's 24-hour disclosure).
- `shared/finding-schema.md` — `type:"compliance"` + `oracle:"hard"` + `severity:"critical"` for any supply-chain provenance hard-oracle failure; `driver_ref` must cite the CRA obligation or the SLSA-level constraint from the `quality-attribute-scenarios.md` utility tree.
- `shared/adr-template.md` — the SLSA level choice, the signing scheme, the SBOM format, and the Rekor topology are each an ADR with ≥2 considered options, decision, and consequences (positive and negative).
- `40-cross-cutting/security-architecture.md` — the trust boundary the signing key / OIDC identity establishes; STRIDE coverage for the pipeline's signing step (a compromised OIDC token is a *Spoofing* threat against the provenance chain).
