# localization-i18n

**Category:** 40-ux-compliance
**Runs as:** inline flow
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Verify internationalization readiness (the code can adapt to any locale) and localization correctness (each shipped locale is right). Answers: "Does the UI render, format, and translate correctly for every supported locale — including RTL and multi-byte scripts?"

## Inputs & preconditions
- Required artifacts: the supported-locale list + locale spec (formats, RTL set), translation resource files (e.g. `*.json` / `.po` / `.arb` / `.resx` message catalogs), the source (default) locale as baseline.
- Target: base URL of a NON-PROD build with locale-switching available, plus the resource files for static inspection.
- Preconditions: locale switch mechanism is reachable; resource keys are extractable; assert the default-locale catalog is complete before comparing others.

## Oracle (source of truth)
The **locale specification** (CLDR-backed expectations: date/time, number grouping/decimal, currency symbol+placement, first day of week, RTL languages) and the **translation resource files** themselves — every visible string must resolve to a catalog key, and each locale's catalog is the truth for that locale's text. NEVER the rendered English string as proof a locale is correct.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate supported locales × key screens; bucket i18n checks (no hardcoded strings, UTF-8 encoding, text expansion/layout, RTL mirroring, format adaptation) vs. L10n checks (translation present/correct, cultural fit, locale-specific behavior).
2. **Act** — **i18n:** grep source/markup for hardcoded user-facing literals (strings not behind a catalog key); run **pseudo-localization** (accented + ~30% expanded) to surface concatenation, truncation, and clipped-layout bugs; switch to an RTL locale (ar/he) and check mirroring + bidi; switch to a multi-byte locale (ja/zh) and check UTF-8 rendering (no mojibake/tofu); verify date/number/currency render per locale. **L10n:** diff each locale catalog against the source for missing/empty keys and untranslated fallbacks; spot-check translation correctness and cultural appropriateness against the resource file. Skip-and-continue per string/screen.
3. **Verify** — assert: 0 hardcoded user-facing strings, every key present in every locale (no fallback-to-English leak), formats match the locale spec, RTL mirrored correctly, no truncation/overlap under pseudo-loc expansion, no encoding corruption. Evidence = the offending key/string + screenshot.

## Assertions & exit gate
- No hardcoded user-facing string; every visible text resolves through a catalog key (i18n).
- Every supported locale's catalog is complete — no missing/empty key, no untranslated fallback.
- Date/number/currency formatting and RTL/bidi rendering match the locale spec; no truncation/overlap/mojibake.
- **Gate:** `i18n_ready_and_locales_complete` — passes when 0 hardcoded strings and 0 missing-translation keys across supported locales (hardcoded string or layout break under pseudo-loc is **major**; a missing/wrong translation is **major**; minor format nit is **minor**).

## Output
Write `artifacts/localization-i18n/report.json` per `shared/report-format.md`:
`{ flow:"localization-i18n", status, summary{total,passed,failed,skipped}, findings[], gate{name:"i18n_ready_and_locales_complete",passed} }`.
Each finding (`QA-I18N-NNN`) cites the locale + spec rule or resource key in `oracle`, the offending string/key + screenshot (pseudo-loc/RTL) in `evidence`, and the fix (externalize string / add key / correct format) in `suggested_fix`.

## Guardrails
Per `shared/guardrails.md`: read-only — `disallowedTools: Edit, Write` on source and catalogs; never auto-edit translations. Judge cultural-fit findings conservatively and flag for a native reviewer rather than asserting — lower confidence on translation-quality calls. Secrets via env; cap `maxTurns`. Recommendations only — locale sign-off needs a native speaker / loc owner.
