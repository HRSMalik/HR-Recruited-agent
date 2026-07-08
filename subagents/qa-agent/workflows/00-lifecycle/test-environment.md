# test-environment

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** haiku   ·   **Mode:** read-only

## Purpose
Provision and verify a prod-like, NON-PROD test environment before execution: config, dependencies, seeded data, and virtualized/stubbed external services. Answers: "Is the environment correctly configured, reachable, isolated from production, and ready to run the suite?"

## Inputs & preconditions
- Required artifacts: the environment spec from the test plan (versions, services, config, dependency matrix), the expected dependency/version baseline, infra-as-code or compose/manifest if present.
- Target: the candidate test environment base URL / host / cluster + health/readiness endpoints, env-var/config snapshot.
- Preconditions to assert before acting: the host is **NON-PROD** (reject prod hostnames/DSNs → `status:error`); endpoints are reachable; required seeded data (from `test-data-management`) is present.

## Oracle (source of truth)
The environment specification in the test plan (29119-3 environment clause): exact service versions, config keys, feature flags, dependency versions, and the **prod-parity** baseline. External dependencies that must not be hit live are defined by the **service-virtualization** contract (stubs/mocks must be up and returning canned responses). NEVER infer "ready" from the SUT merely returning 200.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate verifiable preconditions: NON-PROD assertion, health/readiness probes, config-key presence, dependency versions, virtualized-service availability, seeded-data presence, clock/timezone/locale sanity.
2. **Act** — probe one precondition at a time read-only: GET health/readiness, diff resolved config + dependency versions against the baseline, ping each stubbed dependency, confirm fixture ids exist. Skip-and-continue, recording each result.
3. **Verify** — assert each probe against the spec: versions match the baseline, all required config keys set, all stubs reachable, NON-PROD confirmed, seed data present.

## Assertions & exit gate
- NON-PROD confirmed (target host/DSN is not production).
- Health/readiness endpoints return ready; all declared dependencies resolve at the baselined versions.
- All required config keys/feature flags present; virtualized services up; seeded fixtures present.
- **Gate:** `env_ready_and_nonprod` — passes when NON-PROD confirmed AND 0 missing/mismatched preconditions (pointing at prod or a down core dependency is **blocker**; a version/config drift is **major**).

## Output
Write `artifacts/test-environment/report.json` per `shared/report-format.md`: status, summary, findings[], `gate{name:"env_ready_and_nonprod"}`. Findings (`QA-ENV-NNN`) record the failed probe, expected vs actual version/config in `oracle`/`actual`, redacting any secret/DSN. `status:error` (not `fail`) if the env is unreachable or prod-detected.

## Guardrails
Read-only probes only — `disallowedTools: Edit, Write`; no mutating HTTP/DB. Hard STOP if a production host/connection string is detected. Never echo secrets/DSNs into the report (redact). Respect rate limits; back off on 429. Cheap model (haiku). Cap `maxTurns`.

## Ephemeral provisioning mode (Testcontainers)

When the environment spec calls for disposable, per-run dependencies (DB, cache, queue, virtualized service) rather than a long-lived shared host, provision them as ephemeral containers spun up at suite start and torn down at suite end. This is still a NON-PROD, sandboxed target — the same non-destructive conventions apply, and the oracle is unchanged: readiness is asserted against the spec (versions, config, virtualization contract), never inferred from a 200.

In this mode the precondition set shifts but the gate does not:
- **NON-PROD is intrinsic** — an ephemeral container started for this run is non-prod by construction, but still assert it (no prod DSN injected into the container env).
- **Connection target is resolved at runtime**, not baselined — the host and mapped port come from the started container, so the "reachable endpoint" probe reads them from the container handle rather than from a fixed base URL.
- **Pin the dependency version to the prod-parity baseline** — the image tag is the version oracle; a `:latest`-tagged container fails the version-match assertion the same way a drifted shared host would.
- **Readiness is an explicit wait**, not a fixed sleep — probe the container's own readiness signal (log line / health command / port-accepting check) before the seeded-data and config probes run.

The exit gate is still `env_ready_and_nonprod`: NON-PROD confirmed AND 0 missing/mismatched preconditions, now evaluated against the started containers. Teardown is the suite's responsibility, not this read-only flow's.

## Flaky anti-patterns to avoid (ephemeral mode)

Each of these makes the provisioned environment non-deterministic and turns a green gate into a coin-flip. Treat any of them found in the environment-as-code as a **major** finding against the spec (source: docker.com/blog/testcontainers-best-practices).

- **`:latest` image tag** — non-deterministic and unrepeatable: a new upstream push silently changes the dependency under test and diverges from the prod version. Pin the tag to the prod-parity baseline (e.g. `postgres:15.2`) so the image *is* the version oracle.
- **Fixed host ports** — a hardcoded host port (e.g. `5432:5432`) collides with anything already bound on the host and breaks parallel/CI runs. Expose the container port and read the dynamically mapped host port from the container at runtime.
- **Hardcoded connection strings** — a baked-in `localhost`/DSN fails the moment the daemon is remote (Testcontainers Cloud, CI runner) and isn't portable. Build the connection string from the running container's resolved host + mapped port; never assume `localhost`.
- **Missing readiness waits** — connecting before the container has finished initializing (or relying on an arbitrary `sleep`) is the classic flake. Use an explicit readiness/wait strategy (log-message / port-ready / health check) and gate every downstream probe on it.

> **Watch (do not gate):** framework-native Testcontainers integrations (Spring Boot, Quarkus DevServices, Micronaut TestResources) and remote/Testcontainers-Cloud execution are EMERGING in this flow — note their presence but do not add new gate conditions for them yet.
