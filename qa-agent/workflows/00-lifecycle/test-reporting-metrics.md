# test-reporting-metrics

**Category:** 00-lifecycle
**Runs as:** inline flow
**Default model:** haiku   ·   **Mode:** read-only

## Purpose
Compute the quality metrics over a run/release and emit a dashboard + machine-readable summary. Answers: "What is our defect density, escape rate, coverage, pass/fail trend, and detect/fix speed — and are they trending the right way?"

## Inputs & preconditions
- Required artifacts: per-flow `report.json` files (esp. `test-execution`, `defect-triage`, `traceability-coverage`), historical metrics for trend, KLOC/size or story-point denominator, production-incident/escaped-defect log.
- Target: the `artifacts/` tree + the historical metrics store (read-only).
- Preconditions: at least the current run's reports exist; for trend/MTTD/MTTR, prior-run history is available (else mark those metrics single-point).

## Oracle (source of truth)
Standard, defined metric formulas (ISO/IEC/IEEE 29119-3 reporting + industry-standard definitions):
- **Defect density** = defects ÷ size (KLOC or story points).
- **Defect escape / leakage rate** = defects found in prod ÷ (prod + pre-release defects).
- **Coverage** = requirements (or code) exercised ÷ total (from `traceability-coverage`).
- **Pass/fail rate & trend** = passed ÷ executed, across runs.
- **MTTD** = mean(detected_at − introduced_at); **MTTR** = mean(closed_at − reported_at).
Metrics are computed from recorded data, never estimated — a missing denominator is reported as such.

## Step sequence (Plan → Act → Verify)
1. **Plan** — list target metrics + the exact inputs each needs; identify any missing denominator (size, prod-defect log) up front.
2. **Act** — compute each metric one at a time from the aggregated reports; join against history to compute deltas/trend; render a dashboard view + a `summary.json`. Skip-and-continue, marking any metric with missing inputs as `n/a` with the reason.
3. **Verify** — assert each computed metric is reproducible from the cited source numbers (recompute-and-match), trends reference ≥2 data points, and no metric is fabricated when inputs are absent.

## Assertions & exit gate
- Every reported metric traces to source counts in the per-flow reports (recomputable).
- Trend metrics cite ≥2 runs; single-point metrics are labeled as such.
- Missing-input metrics are `n/a` with a reason, not invented.
- **Gate:** `metrics_reproducible` — passes when 0 metrics lack a traceable source (a fabricated/unsourced metric is **major** — it misleads the release decision). This flow reports; it does not by itself block release (that's `release-readiness`).

## Output
Write `artifacts/test-reporting-metrics/report.json` per `shared/report-format.md` plus the roll-up `artifacts/summary.json` (run_id, findings_by_severity, gate) per report-format. Dashboard/metric tables emitted as artifacts. Findings (`QA-MET-NNN`) flag unsourced/missing metrics with the missing input in `oracle`/`notes`.

## Guardrails
Read-only aggregation — `disallowedTools: Edit, Write` outside artifacts. Never fabricate a metric when inputs are missing — mark `n/a`. Do not leak PII/secrets from underlying reports into the dashboard (redact). Cheap model (haiku). Cap `maxTurns`.
