# tone-voice

**Group:** 50-content
**Runs as:** inline
**Mode:** build (writer + verify loop) · audit (consistency scan)   ·   **Default model:** sonnet

## Purpose
Own the product's documented voice and its situational tone, so a new writer could reproduce the copy's character from a profile — voice stays constant, tone flexes to the moment.

## Inputs & preconditions
- From `project-design-config.md`: locked brand rules, the design-system glossary location, token source, dev-server URL/port + creds, breakpoints.
- Target: the screen's copy surfaces (headings, body, labels, errors, empty states); the tone profile + glossary in the design system.
- Preconditions: dev server reachable; the documented tone profile + glossary read before judging; existing copy read so one-term-per-concept holds.

## Oracle (source of truth)
NN/g voice-and-tone framework — voice constant, tone situational — plus the project's documented tone profile.
- **hard:** one term per concept across the surface (grep for synonym drift); glossary terms used as written; no off-profile register (e.g. jokey copy on an error, per the profile's anti-tone words).
- **soft:** tone placed correctly on NN/g's 4 dimensions for the context; reads as one consistent voice; matches the profile's target words, avoids its anti-tone words.

## Standards & techniques
- **NN/g 4 tone dimensions:** formal↔casual, serious↔funny, respectful↔irreverent, matter-of-fact↔enthusiastic — pick a point per dimension per context (celebration vs. error vs. neutral form).
- **Voice constant, tone situational:** the personality holds; the dial moves — serious + matter-of-fact on an error, warmer on success.
- **Target / anti-tone words:** the profile lists words to lean into and words to avoid; copy honours both.
- **One term per concept:** a single canonical word per concept, sourced from the **design-system glossary**, never a thesaurus of synonyms.

## Step sequence
- **audit:** Pull the documented tone profile + glossary → scan the surface for synonym drift, off-profile register, and anti-tone words → emit findings (read-only, no edits).
- **build:** Explore (≥2 tone passes, read-only) → Judge (4-dimension placement + voice-consistency rubric, order-swapped) → Implement (one writer; copy strings only, terms from glossary) → Verify (screenshot copy states @ breakpoints; axe + zero console errors; evaluator re-scores against the profile) → loop ≤15 or pass.

## Assertions & exit gate
- One term per concept; glossary terms used verbatim; no anti-tone words present.
- Tone sits correctly on the 4 dimensions for each context while voice stays constant.
- **Gate:** hard oracles green (term consistency + on-profile register) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/tone-voice/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: content`, `heuristic: NN/g voice & tone`; `oracle: hard` for term drift and off-profile/anti-tone register), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: change copy strings only — never logic. The glossary lives in the design system — reuse its terms, never coin a synonym. The tone profile is the soft oracle: a new writer must be able to reproduce the copy from it. Read-only audit makes no edits; one writer for build.
