# sanity

**Category:** 10-functional
**Runs as:** inline flow
**Default model:** haiku   ·   **Mode:** read-only

## Purpose
Narrow, deep verification of a *specific* change or fix after a new build (ISTQB *sanity testing*): confirm the changed function works as intended at the rationality level, so a full regression can be deferred or scoped. Answers — "is it sane to keep testing this change, or is it already broken?"

## Inputs & preconditions
- Required artifacts: the change description / commit / ticket, and the change's **intended behavior** (the AC of the fix or feature under change).
- Target: base URL + auth via env; the build that contains the change (record the commit).
- Preconditions: smoke already passed; the changed surface is identifiable (diff, endpoint, or feature flag); read-only against a non-prod build.

## Oracle (source of truth)
The **intended behavior of the change** — the fix's expected effect / the new feature's AC as written in the ticket. NOT the SUT's current output, and NOT the broad spec (that is `functional`'s job); sanity is scoped strictly to what changed.

## Step sequence (Plan → Act → Verify)
1. **Plan** — derive 3–8 deep checks that exercise the changed behavior end-to-end (the core positive path of the change plus its one or two most adjacent interactions). Deliberately ignore unrelated areas.
2. **Act** — execute each check against the changed endpoint/flow; one at a time; skip-and-continue. Read-only probes only.
3. **Verify** — assert observed behavior matches the *intended* change behavior; if it does not, stop deep-testing this build and flag it as not-sane (recommend a rebuild rather than running full regression).

## Assertions & exit gate
- The changed behavior is present and correct per the ticket (e.g. "filter `status=active` now excludes archived" returns only active rows).
- No obvious irrationality on the changed surface (changed endpoint returns the documented shape, not an error).
- **Gate:** `change_behaves_as_intended` — pass if every scoped check matches the intended behavior; any mismatch → `fail`, and the orchestrator skips/holds the wider regression for this build.

## Output
Write `artifacts/sanity/report.json` per `shared/report-format.md`:
`{ flow:"sanity", status, summary{...}, findings[], gate{name:"change_behaves_as_intended",passed} }`.
Findings per `shared/finding-schema.md`; `oracle` field names the ticket/AC id; a broken change is typically **major** (workaround: revert), evidence = request/response showing the deviation.

## Guardrails
Per `shared/guardrails.md`: read-only; no mutations on the live build; secrets via env; `maxTurns: 14`. Sanity is a fast gate, not a full pass — if it tempts you to test unchanged areas, stop: that scope belongs to `regression`.
