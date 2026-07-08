# security

**Category:** 30-non-functional
**Runs as:** subagent: ../.claude/agents/security-scanner.md (sub-fans a worker per endpoint)
**Default model:** sonnet   ·   **Mode:** seeded-sandbox

## Purpose
Shift-left **SAST** on the source plus **DAST** against the running app to surface OWASP Top 10 and related classes: authn/authz bypass, IDOR, injection (SQL/NoSQL/command), XSS, secrets exposure, CORS misconfiguration, and missing security headers. Answers: "Can this build be exploited, and does any high/critical finding survive an adversarial recheck?"

## Inputs & preconditions
- Required artifacts: source tree + dependency manifests (for SAST), endpoint inventory / OpenAPI spec, roles & auth matrix (which role may touch which resource), an owned set of test accounts across privilege tiers.
- Target: base URL/host of a **staging or seeded-sandbox** build; auth tokens per role via env; CI access to run SAST on the commit under review.
- Preconditions: assert **NON-PROD** host (STOP and `status:error` on prod); seeded golden data with synthetic PII only (never real PII); active-scan authorization on file for the target.

## Oracle (source of truth)
External standards, never the app's own response: **OWASP Top 10 (2021)** + **OWASP WSTG** test IDs + **OWASP ASVS** verification levels, **CWE** identifiers, and the **roles/auth matrix** for access-control checks. A vuln is confirmed when it maps to a WSTG/CWE class and is reproducible, not because a scanner flagged it.

## OWASP API Security Top-10 (2023) matrix
Per-endpoint API audit, layered on the web checks above. The scanner sub-fans a worker per route and exercises each class with **multi-identity fixtures** — owned token for user **A** replayed against user **B**'s object/route — never a real cross-tenant breach. Oracle is the published API risk class, not the app's own response; a finding is confirmed only when A's credential demonstrably reaches B's data and it maps to the class below.

| API risk | Probe (multi-identity, sandbox-only) | Oracle id |
| --- | --- | --- |
| **BOLA** (API1) — broken object-level authz | Swap object IDs in path/query/body; replay A's token against B's `id` and assert deny | API1:2023 / CWE-639 |
| **BFLA** (API5) — broken function-level authz | Call admin/privileged functions with A's lower-tier token; assert deny | API5:2023 / CWE-285 |
| **BOPLA** (API3) — broken object-property-level authz / mass-assignment | POST/PATCH with extra/protected properties (`role`, `is_admin`, `owner_id`); assert ignored, never bound | API3:2023 / CWE-915 |
| **Unrestricted resource consumption** (API4) | Oversized payloads, deep pagination, unbounded `limit`, fan-out params; assert quota/rate caps hold | API4:2023 / CWE-770 |
| **SSRF** (API7) | URL/webhook/import params pointed at internal hosts + cloud metadata (see server-side family below) | API7:2023 / CWE-918 |
| **Shadow / undocumented endpoints** (API9) — improper inventory | Diff live routes vs OpenAPI/inventory; probe deprecated/`v1`/debug paths absent from spec; assert no auth gap | API9:2023 / CWE-1059 |

Source: owasp.org/API-Security/editions/2023. Throttle every consumption probe to the sandbox's rate limits — prove the class, never exhaust the host.

## JWT + OAuth2/OIDC flow testing
Token and flow integrity for any bearer/OIDC-protected route. All tampering is against owned tokens on the sandbox; the oracle is the rejection the standard mandates, not a 200/500 from the app.

- **JWT tampering** — assert each is **rejected**: forged/invalid **signature**; wrong **`iss`** and wrong **`aud`**; expired **`exp`** (and `nbf`); the **`alg:none`** downgrade and HS/RS key-confusion (sign with the public key as an HMAC secret). A token that survives any of these is a critical authn-bypass finding.
- **Per-endpoint scope assertions** — for each route, call with a token **missing the required scope/claim** and assert deny; call with the exact scope and assert allow. Map route → required scope from the auth matrix; flag any route that accepts an under-scoped token.
- **Flow coverage** — exercise **authorization-code** (with PKCE; assert `state`/`code` single-use and redirect-URI allow-listing), **client-credentials** (machine-to-machine scope boundaries), and **refresh** (assert rotation + reuse-detection revokes the family). Confirm refused redirect URIs and replayed codes are rejected.

Oracle: signature/`iss`/`aud`/`exp`/`alg` semantics per the JWT + OAuth2/OIDC specs and the per-route scope matrix. Redact every token in evidence.

## OWASP LLM Top-10 (2025) + server-side injection family
For any LLM-backed surface (resume parsing, screening, chat, summarization), the deep red-team oracle and probe set live in **`llm-red-teaming.md`** (cross-link) — this flow defers prompt-injection, insecure output handling, sensitive-info disclosure, excessive agency and the rest of the **OWASP LLM Top-10 (2025)** to that workflow and only confirms the gate result here. Source: genai.owasp.org.

The **server-side injection family** is exercised here as part of the endpoint audit (oracle = the published class + CWE, reproducible PoC):

| Class | Probe (sandbox-only) | Oracle |
| --- | --- | --- |
| **SSRF** | URL/import/webhook params → internal hosts; assert egress allow-list holds | CWE-918 |
| **Cloud-metadata SSRF** | Same params → `169.254.169.254` / metadata endpoints; assert blocked, no creds returned | CWE-918 |
| **XXE** | XML/SVG/DOCX upload with external entity + parameter entity; assert parser disables DTD/external entities | CWE-611 |
| **SSTI** | Template-eval payloads in rendered fields (`{{7*7}}` / `${...}` / `#{...}`); assert no server-side evaluation | CWE-1336 / CWE-94 |

**IaC / container misconfig scanning** runs alongside SAST/SCA: **Trivy** (image + filesystem CVEs, secrets, misconfig) and **Checkov** (Terraform/CloudFormation/K8s/Dockerfile policy). Findings map to the tool's policy id + CWE; a high/critical IaC misconfig with no accepted mitigation gates the same as a code finding.

> **Watch (do not gate):** EMERGING — agentic/MCP tool-abuse and tool-poisoning probes (chained tool-call privilege escalation) are tracked under `llm-red-teaming.md` as they mature; record observations as notes, do not gate the build on them yet.

## Step sequence (Plan → Act → Verify)
1. **Plan** — run **SAST** (SonarQube, Snyk Code, Semgrep) on the commit and **SCA** (Snyk, OWASP Dependency-Check) on manifests; enumerate every endpoint and the auth matrix; the scanner subagent **sub-fans one worker per endpoint** for a deep audit, scoped to that route's params + privilege tiers.
2. **Act** — per endpoint worker: run **DAST** (OWASP ZAP active scan, Burp Suite) plus targeted manual probes — IDOR (swap object IDs across accounts), authz/authn bypass (call privileged routes with low-priv/no token), injection (SQL/NoSQL/command payloads), reflected/stored XSS, CORS (`Origin:` reflection + `Access-Control-Allow-Credentials`), header audit (`CSP`, `HSTS`, `X-Frame-Options`, `X-Content-Type-Options`), and secrets exposure (Gitleaks/TruffleHog on source + responses/error pages).
3. **Verify** — map each candidate to a WSTG/CWE oracle and confirm exploitability with a minimal PoC. For **every high/critical finding, an adversarial verifier subagent** re-attempts the exploit from a clean context to eliminate scanner false positives before it is admitted.

## Assertions & exit gate
- No injection (SQLi/NoSQLi/cmd), no IDOR/broken object-level authz, no authn/authz bypass against the role matrix.
- No reflected/stored XSS; CORS not wildcard-with-credentials; required security headers present; no secrets in source, responses, or error pages; no high/critical SCA CVE without an accepted mitigation.
- **Gate:** `no_high_or_critical_findings` — passes only when zero high/critical survive adversarial verification. Any **exploitable** vuln (injection, RCE, auth bypass, IDOR exposing PII) → **critical**; a mitigated/low-likelihood issue (missing header with no exploit path) → **major/minor**.

## Output
Write `artifacts/security/report.json` per `shared/report-format.md`:
`{ flow:"security", status, summary{total,passed,failed,skipped}, findings[], gate{name:"no_high_or_critical_findings",passed} }`.
Each finding (`QA-SEC-NNN`) names the OWASP/WSTG/CWE id in `oracle`, includes the **redacted** request/response PoC + verifier confirmation in `evidence`, and the remediation (parameterize query, enforce object-level authz, set header) in `suggested_fix`.

## Guardrails
Per `shared/guardrails.md`: active scanning **only** against the sandbox with authorization — never production; confirm NON-PROD or `status:error`. Never exfiltrate or log real PII/secrets — **redact every token, key, and payload** in the report. Scope each endpoint worker's credentials least-privilege so they don't leak into the orchestrator. Throttle scans to respect rate limits; cap `maxTurns`; do not weaponize a PoC beyond proving the class.
