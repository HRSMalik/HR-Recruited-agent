# design-system-governance

**Group:** 10-tokens-systems
**Runs as:** subagent: ../.claude/agents/design-system-keeper.md
**Mode:** audit (read-only)   ·   **Default model:** sonnet

## Purpose
Own the lifecycle of the design system: versioned changes (SemVer), explicit deprecation with an EOL, managed migration guides, and drift detection — so the token/component set evolves without silently breaking consumers.

## Inputs & preconditions
- From `project-design-config.md`: token source, components dir, available components/tokens (grep before claiming drift), locked rules.
- Target: the token + component set and its version history/changelog.
- Preconditions: current and previous versions readable; consumers grep-able to detect drift.

## Oracle (source of truth)
Semantic Versioning + a deprecation-with-EOL policy + token/component conformance as the drift baseline.
- **hard:** version bump matches the change class — major = breaking (removed/renamed token, changed component contract), minor = additive (new token/variant), patch = fix (value tweak, no API change); every deprecated token/component carries a `$deprecated`/EOL note AND a migration target; drift = a consumer using a hardcoded value or a non-existent token (grep proves it).
- **soft:** changelog clarity, migration-guide completeness, deprecation lead time.

## Standards & techniques
- **SemVer:** major.minor.patch — never ship a breaking removal as a minor; never bump major for an additive token.
- **Deprecation:** mark, don't delete — annotate the token/component as deprecated, name the replacement, set an EOL version; remove only at the next major after the EOL.
- **Managed migration:** a breaking change ships with a migration guide mapping old → new token/component.
- **Drift detection:** grep consumers for hardcoded values and dangling/non-existent token names against the current source of truth.

## Step sequence
- **audit:** diff current vs previous version → classify each change (breaking/additive/fix) and assert the bump matches → list deprecated items lacking an EOL or replacement → grep consumers for drift (hardcoded values, ghost tokens) → emit a prioritized findings list (read-only, no edits).

## Assertions & exit gate
- Version bump class matches the diff (no breaking change hidden in a minor/patch).
- Every deprecation has a replacement target and an EOL version.
- A migration guide exists for every breaking change.
- Zero drift: no consumer hardcodes a value where a token exists; no consumer references a non-existent token.
- **Gate:** hard oracles green — correct SemVer class, complete deprecations, zero drift.

## Output
Write `artifacts/design-system-governance/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: token`/`heuristic`, `oracle: hard` for SemVer mismatch / missing EOL / drift), grouped by severity (critical → cosmetic). Audit emits findings only — no writes.

## Guardrails
Per `shared/guardrails.md`: read-only — this flow audits, never edits. Mark deprecations, never silently delete. Grep the real source before claiming drift (a guessed token name produces false drift). Preserve logic.
