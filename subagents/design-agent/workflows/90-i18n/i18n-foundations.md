# i18n-foundations

**Group:** 90-i18n
**Runs as:** subagent: ../.claude/agents/design-reviewer.md (audit) · ../.claude/agents/design-judge.md (build verify) — extend, don't replace; one writer applies
**Mode:** audit (i18n-readiness scan) · build (localize + verify loop)   ·   **Default model:** sonnet

## Purpose
Own design-side internationalization: make every screen render correctly in any configured locale and writing direction — declared language/direction, direction-agnostic layout, locale-aware formatting, translation-ready strings, and culturally-safe non-text assets — fixing it with markup/style/formatting only, never by changing app logic.

## Inputs & preconditions
- From `project-design-config.md`: default direction + the locale(s) to support (and which are RTL), the locale rule, token source (spacing/size), component library, dev-server URL/port + login creds, breakpoints, locked rules.
- Target screen(s); the oracle = the web.dev Internationalization guide (https://web.dev/learn/design/internationalization) plus the platform Intl + CSS logical-property specs it cites.
- Preconditions: dev server reachable; the configured locales + direction read from config (never assume `en`/`ltr`); existing spacing tokens and string catalogue read before editing layout or extracting copy.

## Oracle (source of truth)
The web.dev i18n guide and the specs it references — `lang`/`dir`, BCP-47, CSS logical properties, the `Intl` API — asserted against the rendered page in each configured locale, not by prose.
- **hard:**
  - **Declared language + direction** — `<html lang>` is a valid BCP-47 tag matching the active locale and `<html dir>` matches the locale's direction; any locale-switched subtree carries its own `lang`/`dir`.
  - **Direction-agnostic layout** — spacing/positioning use CSS **logical** properties (`margin-inline`, `padding-block`, `inset-inline-start`, `text-align: start`) not physical `left`/`right`; in an RTL locale the layout, directional icons, and progress/order mirror correctly with no clipped or overlapping content.
  - **Locale-aware formatting** — numbers, dates, currency, and relative time render via `Intl.*` (`NumberFormat`/`DateTimeFormat`/`RelativeTimeFormat`) bound to the active locale — never hand-built `toFixed`/`split('/')`/string concatenation.
  - **Translation-readiness** — no horizontal clipping/overflow with a ~30–40% text-expansion budget (verified via pseudo-localization); user-facing strings are externalized + keyed (no hardcoded literals in markup) with ICU plural/select for count/gender; no sentence assembled by concatenating fragments.
- **soft:** expanded strings still read with a clear hierarchy (no awkward wraps/truncation at the budget); mirrored RTL layout feels native, not flipped-and-broken; chosen non-text assets carry no locale-specific or culturally-loaded meaning.

## Standards & techniques (cite the principle)
- **Declare it:** `lang` + `dir` on `<html>` (and on any mixed-direction subtree); locales identified with BCP-47 tags (`es-419`, `ar-EG`), not bare `es`/`ar`.
- **Logical over physical:** `margin/padding/inset/border-*-inline|block`, `text-align: start/end`, logical `float`; reserve physical `left`/`right` only for genuinely physical things; let `dir` drive mirroring instead of an RTL stylesheet of overrides.
- **Format with `Intl`, never by hand:** `Intl.NumberFormat` (incl. `style:'currency'` + the locale's currency), `Intl.DateTimeFormat`, `Intl.RelativeTimeFormat`, `Intl.PluralRules`/`Intl.ListFormat` — locale decides separators, ordering, grouping, and currency placement.
- **Translation-ready copy:** externalized keyed strings (one key = one full sentence), ICU `{count, plural, ...}` / `{gender, select, ...}` for grammar, interpolated variables — never concatenate "You have " + n + " items"; design containers for ~30–40% expansion and verify with pseudo-localization (accented + padded text) before real translations exist.
- **Localize non-text assets:** flag icons containing baked-in text/letters; review culturally-loaded colour + imagery (red ≠ "danger"/"error" in every culture; gestures, flags-as-language, imagery) and gate semantics on a label/token, not the asset alone.
- **Locale-aware form fields:** address/name/phone fields adapt to locale (no fixed "State"/"ZIP" or single first/last assumption; flexible postal/phone formats) instead of a US-only shape.

## Step sequence
- **audit:** load the target in each configured locale + direction @ breakpoints → assert `lang`/`dir` + BCP-47, logical-property usage + RTL mirroring, `Intl` formatting, externalized/keyed strings with ICU plurals, and form-field locale-fit → run pseudo-localization to expose expansion overflow + any hardcoded literal → review non-text assets for embedded text / cultural meaning → emit findings (read-only, no edits), each naming the locale + the rule it breaks.
- **build:** Explore (≥2 fix strategies — e.g. logical-property refactor vs `dir`-driven mirroring, read-only) → Judge (declared-language + direction-agnostic + Intl-formatted + expansion-safe rubric, order-swapped) → Implement (one writer; set `lang`/`dir`, swap physical→logical properties, route formatting through `Intl`, externalize + key strings with ICU plural/select, fix locale-unaware form fields, replace text-baked/culturally-loaded assets — markup/style/format only, reuse components/tokens) → Verify (Playwright screenshots in each locale incl. one RTL + a pseudo-localized pass @ breakpoints; axe-core incl. valid `lang` + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- `<html lang>` is valid BCP-47 for the active locale and `<html dir>` matches its direction; mixed-direction subtrees declare their own `lang`/`dir`.
- Spacing/positioning use logical properties; RTL renders mirrored with no overflow/clipping; pseudo-localized + ~30–40%-expanded text never clips or breaks layout at any breakpoint.
- Numbers/dates/currency/relative-time go through `Intl` bound to the active locale; user-facing strings are externalized + keyed with ICU plural/select and no concatenation; address/name/phone fields fit the locale.
- Sizes/spacing resolve to tokens (never raw px where a token exists); logic files unchanged (diff check).
- **Gate:** hard oracles green (lang/dir + logical/RTL + Intl + expansion/keyed-strings + axe + console) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/i18n-foundations/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: content` for strings/concatenation/asset-text, `type: responsive` for expansion-overflow/RTL-clipping, `type: heuristic` for missing logical properties or `Intl`; `oracle: hard` for wrong/missing `lang`/`dir`, physical-property leakage in RTL, hand-built formatting, or clipped expanded text; record the `locale` + `viewport` on every finding; `evidence` = screenshot@locale@viewport / the offending markup/style / the hardcoded literal), plus the verification block (per-locale + RTL + pseudo-localized screenshots, hard-oracle results, rubric score) for build mode.

> **Watch (do not gate):** EMERGING — CSS `text-spacing-trim` / east-Asian punctuation trimming, `Intl.DurationFormat`, and the `:dir()` pseudo-class have uneven support across the configured targets. Use behind feature-detection as a richer layer; flag absence as advisory only, never a hard oracle, and never a reason to drop the logical-property + `Intl` baseline.

## Guardrails
Per `shared/guardrails.md`: change `lang`/`dir`, swap physical→logical CSS, route values through `Intl`, and externalize/key strings — never touch event logic, data flow, validation, or API calls (preserve behaviour byte-for-byte); if honest localization needs a logic/data change (e.g. a locale-specific validation rule), stop and flag it, don't silently alter behaviour. Reuse spacing/size tokens and existing components before inventing; grep the token source, never guess a name. Read-only audit makes no edits; one writer for build; trust the per-locale screenshot (and the pseudo-localized pass) over the diff; delete temp Playwright scripts after.
