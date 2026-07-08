# design-tokens

**Group:** 10-tokens-systems
**Runs as:** subagent: ../.claude/agents/design-system-keeper.md
**Mode:** build (writer + verify loop) · audit (conformance scan)   ·   **Default model:** sonnet

## Purpose
Own the token architecture: a three-tier pipeline (primitive → semantic/alias → component) expressed as W3C DTCG JSON, so every colour/space/radius in the UI resolves to a named token, never a raw value.

## Inputs & preconditions
- From `project-design-config.md`: token source file(s) (e.g. `design-tokens/*.tokens.json`), real token names (grep before use), colour rule, theme (light/dark/both).
- Target: the token set + the components/screens that consume it.
- Preconditions: token source readable; existing tokens read and grepped before any new token is invented.

## Oracle (source of truth)
W3C Design Tokens Community Group (DTCG) format spec + the three-tier convention.
- **hard:** no hardcoded hex/space where a token exists (grep the source); every `{alias}` reference resolves to a real token (no dangling refs); component tokens reference a *semantic* token, never a primitive directly; `$value`/`$type` present on every token.
- **hard:** composite tokens (`typography`, `shadow`, `border`, `transition`, `gradient`, `strokeStyle`) are a single bundled `$type` object — never decomposed into loose primitives scattered across the tree; every sub-value either is the correct sub-type or `{alias}`es a token of that sub-type; `$description` present on every token.
- **soft:** ramp completeness, naming clarity, semantic role coverage, `$extensions` hygiene (vendor-namespaced keys), composite sub-value alias reuse over inline literals.

## Standards & techniques
- **Tier 1 primitive:** raw scale values only — `blue-500`, `space-4`, `radius-2`. Never consumed by components directly.
- **Tier 2 semantic/alias:** intent names that `{alias}` a primitive — `color-action-primary` → `{blue-500}`, `space-inset-md` → `{space-4}`.
- **Tier 3 component:** scoped names that `{alias}` a *semantic* — `button-bg-primary` → `{color-action-primary}`. Re-theming swaps tier 2, components inherit.
- DTCG JSON: `{ "$value": "#2563eb", "$type": "color" }`; alias as `{ "$value": "{blue-500}" }`.

## Composite token types (DTCG)
Composite `$type`s bundle several typed sub-values into **one** token object — model the whole concept as a unit, never as loose primitives scattered across the tree. Each sub-value is either a literal of its sub-type or a `{alias}` to a token of that sub-type.
- **`typography`** — `{ fontFamily, fontSize, fontWeight, letterSpacing, lineHeight }`; sub-types: fontFamily, dimension, fontWeight, dimension, number.
- **`shadow`** — `{ color, offsetX, offsetY, blur, spread }` (or an array of these for layered shadows); sub-types: color, dimension ×4.
- **`border`** — `{ color, width, style }`; sub-types: color, dimension, strokeStyle.
- **`transition`** — `{ duration, delay, timingFunction }`; sub-types: duration, duration, cubicBezier.
- **`gradient`** — array of stops, each `{ color, position }`; sub-types: color, number in `[0,1]`.
- **`strokeStyle`** — either a predefined string (`solid` `dashed` `dotted` `double` `groove` `ridge` `outset` `inset`) **or** the object form `{ dashArray: [<dimension>…], lineCap: "round"|"butt"|"square" }`.
```json
"shadow-md": { "$type": "shadow", "$description": "Resting card elevation", "$value": {
  "color": "{color-shadow-ambient}", "offsetX": "{space-0}", "offsetY": "{space-1}",
  "blur": "{space-2}", "spread": "{space-0}" } }
```
- Reuse: composite sub-values should `{alias}` existing primitives/semantics, not inline fresh literals — a hardcoded sub-value is a tier violation just like a hardcoded top-level `$value`.

## Token metadata (DTCG)
- **`$description`** — plain-text string stating the token's purpose. Required on every token (hard) — a composite without it is opaque to consumers and re-themers.
- **`$extensions`** — object for tool/vendor-specific data; keys MUST be vendor-namespaced (reverse-domain, e.g. `"com.acme.figma"`). Tools MUST preserve unknown extension data on read/write — never drop it during edits.
- **Curly-brace alias `{group.token}`** — references a *complete token value*; always resolves to the target's `$value`. This is the primary aliasing mechanism for all three tiers and for composite sub-values.
```json
"button-bg-primary": { "$type": "color", "$description": "Primary button fill",
  "$value": "{color-action-primary}", "$extensions": { "com.acme.figma": { "styleId": "S:abc" } } }
```
- **Watch (do not gate): JSON-Pointer `$ref` aliasing** — the drafts add a property-level reference, `{ "$ref": "#/path/to/target" }` (RFC 6901), able to point *inside* a value (e.g. one channel of a color). It is EMERGING in the spec drafts and tool support is uneven, so flag bare-`$ref` usage as informational only — do not fail the gate on its presence or absence; continue to treat curly-brace aliases as the resolvable hard oracle.

## Step sequence
- **audit:** grep the codebase for hardcoded hex/px where a token exists → resolve every `{alias}` and flag dangling/primitive-referencing-component tokens → emit findings (read-only, no edits).
- **build:** Explore (≥2 token-tree structures, read-only) → Judge (resolution check + naming rubric, order-swapped) → Implement (one writer; edit `.tokens.json` + wire consumers to component tokens only) → Verify (resolve all aliases; grep for orphaned raw values; screenshots every state @ breakpoints; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Every component token aliases a semantic; no component token points at a primitive.
- Every `{alias}` resolves; zero dangling references; zero hardcoded values where a token exists.
- All tokens carry `$value` + `$type` + `$description`.
- Every composite token is a single bundled `$type` object with all required sub-values present and correctly sub-typed (or aliased); no composite decomposed into loose primitives.
- `$extensions` keys are vendor-namespaced and preserved byte-for-byte across edits.
- **Gate:** hard oracles green (resolution + tier discipline + no raw values + composite-bundling + `$description` present) AND (build) rubric mean ≥ 0.8. JSON-Pointer `$ref` usage is Watch-only and never gates.

## Output
Write `artifacts/design-tokens/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: token`, `oracle: hard` for unresolved aliases / tier violations / raw values / decomposed composites / missing `$description`), plus the verification block for build mode. Emit `oracle: soft` for naming/ramp/`$extensions`-hygiene notes, and a Watch (non-gating) note for any JSON-Pointer `$ref` aliasing encountered.

## Guardrails
Per `shared/guardrails.md`: never guess a token name — grep the source (a wrong token silently falls back). Reuse existing primitives before adding new ones. Preserve logic byte-for-byte. Read-only audit makes no edits; one writer for build.
