# microcopy

**Group:** 50-content
**Runs as:** inline
**Mode:** build (writer + verify loop) · audit (label scan)   ·   **Default model:** sonnet

## Purpose
Own the words on interactive controls — buttons, links, menu items, field labels — so every label is verb-first and the user can predict the outcome before they click it.

## Inputs & preconditions
- From `project-design-config.md`: component library (Button variants, Input/Select labels), token source, dev-server URL/port + creds, breakpoints, locked content rules.
- Target screen(s): the action surface (form CTAs, menu items, link text); the relevant guidance (NN/g microcopy).
- Preconditions: dev server reachable; existing component labels read before rewriting; the glossary in the design system read so one term per concept holds.

## Oracle (source of truth)
NN/g microcopy guidance — verb-first `{verb}+{noun}` labels, the 3 C's, predict-the-outcome. Translation-ready strings per ICU MessageFormat (phrase.com ICU message format guide).
- **hard:** no bare ambiguous labels (`OK`, `Submit`, `Yes`, `Click here`, `Go`) on a consequential control; every action control leads with a verb; label names the noun it acts on; no runtime sentence-fragment concatenation — every translatable string is one externalized key with **named** placeholders (`{name}`, `{count}`), and count-bearing strings use ICU `plural`.
- **soft:** the 3 C's balance — Clarity, Concision, Character — with **clarity winning** any conflict; reads as natural product voice.

## Standards & techniques
- **Verb-first `{verb}+{noun}`:** `Save changes`, `Send invite`, `Delete account` — never a bare `OK`/`Submit` where the outcome is ambiguous.
- **Predict the outcome:** the label states what happens on click; paired destructive/safe actions name both sides (`Discard draft` / `Keep editing`).
- **3 C's, clarity first:** be clear, then concise, then add character — drop character before clarity, drop concision before clarity.
- **One term per concept:** the same action is labelled identically everywhere (grep the surface for label drift); terms come from the design-system glossary.
- **Translation-ready strings (ICU MessageFormat):** write every label as a whole, externalized message keyed for i18n — never assemble a sentence from concatenated fragments at runtime (`"Delete " + count + " items"`), which strips the context translators need to reorder words and inflect for their language. Cross-link `i18n-foundations.md` for the key-externalization and locale-loading mechanics.
- **Named placeholders, never positional:** interpolate with named tokens (`{name}`, `{count}`) so the meaning survives reordering — `Welcome back, {name}` not `Welcome back, {0}`; a translator must be able to move `{name}` anywhere in the sentence without breaking it.
- **ICU `plural`/`select` for count- and gender/state-dependent copy:** branch inside one message rather than building strings in code. Plural: `{count, plural, one {# item} other {# items}}` (`#` prints the number; add `=0`/`zero`/`few`/`many` where a target locale needs them). Select: `{role, select, admin {Manage team} member {View team} other {View}}` — always include the required `other` fallback.

## Translation-ready strings (standard)
Every user-facing label this flow ships is a translation-ready string, judged against the ICU MessageFormat oracle (phrase.com ICU message format guide). The standard has three non-negotiable pillars; `i18n-foundations.md` owns the key-externalization mechanics, locale loading, and the expansion/RTL budget — this flow owns the *shape of the string itself*.
- **Named placeholders, never positional or concatenated:** interpolate runtime values with named tokens — `{name}`, `{count}`, `{role}` — never positional `{0}`/`{1}` and never `+`-concatenation (`"Welcome back, " + name`). A translator must be free to move `{name}` anywhere in the sentence and to reorder around it for their language; a positional or stitched string strips that freedom and the surrounding context. `Welcome back, {name}` — not `Welcome back, {0}`, not `"Welcome back, " + name`.
- **ICU `plural`/`select`, never hand-pluralized or branched in code:** count- and state-dependent copy branches *inside one message*, not by picking strings in JS. Plural: `{count, plural, one {# unread message} other {# unread messages}}` (`#` prints the number; add `=0`/`zero`/`few`/`many` only where a target locale's grammar needs them). Select: `{status, select, invited {Resend invite} active {Manage access} other {View}}` — the `other` arm is mandatory. Never ship `count + " item" + (count === 1 ? "" : "s")`; English's one-`s` rule does not survive translation.
- **Externalized + keyed, never a literal in markup:** one key = one whole message; no user-facing literal lives inline in a component. The label is looked up by key from the string catalogue `i18n-foundations.md` defines — this flow writes the *value* (verb-first, outcome-predictable, glossary-consistent, ICU-correct) and registers it under a stable key, never a hardcoded string the translator can't see.
- **hard:** every translatable label is one externalized, keyed message with **named** placeholders and ICU `plural` on any count-bearing copy — no positional tokens, no runtime sentence-fragment concatenation, no hand-pluralized `s`, no `other`-less `plural`/`select`.
- **soft:** the message reads naturally in source and survives reordering without sounding stilted; `select` arms and `=0`/empty-state branches cover the states the surface actually has.
- **Watch (do not gate):** richer ICU coverage — `select` for gender/role variants, `selectordinal`, and `=0` empty-state branches — is EMERGING; advisory only, never a hard failure (the locales that need the extra plural/ordinal forms are confirmed and added as targets in `i18n-foundations.md`).

## Step sequence
- **audit:** Enumerate every interactive label on the screen → assert verb-first + outcome-predictable + glossary-consistent against the oracle → emit findings (read-only, no edits).
- **build:** Explore (≥2 label sets, read-only) → Judge (3 C's rubric, clarity-weighted, order-swapped) → Implement (one writer; edit label strings only, reuse Button/Input components) → Verify (screenshots every state @ breakpoints; axe + zero console errors; evaluator re-scores the rendered labels) → loop ≤15 or pass.

## Assertions & exit gate
- No bare `OK`/`Submit`/`Click here` on a consequential control; every action label is verb-first.
- Each concept uses one consistent term across the surface; labels match the glossary.
- No runtime sentence-fragment concatenation; every translatable string is one externalized key with named placeholders (`{name}`, `{count}`); count-bearing copy uses ICU `plural`, not a hand-pluralized `s`.
- **Gate:** hard oracles green (verb-first + no ambiguous labels + term consistency + translation-ready strings) AND (build) rubric mean ≥ 0.8.
- **Watch (do not gate):** richer ICU coverage — `select` for gender/role variants, `selectordinal`, and `=0` empty-state branches — is EMERGING; flag missing branches as advisory only, never a hard failure (locales that need the extra forms are added in `i18n-foundations.md` as targets are confirmed).

## Output
Write `artifacts/microcopy/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: content`, `heuristic: NN/g microcopy`; `oracle: hard` for bare/ambiguous labels, term drift, and non-translation-ready strings — fragment concatenation, positional/missing placeholders, hand-pluralized count copy), plus the verification block for build mode. Emerging ICU `select`/`selectordinal`/`=0` gaps are recorded as advisory findings (not hard), per the Watch note.

## Guardrails
Per `shared/guardrails.md`: change label strings only — never handlers, routes, or validation. Reuse existing Button/Input components and the glossary term before inventing a label. Read-only audit makes no edits; one writer for build; trust the rendered screenshot over the diff.
