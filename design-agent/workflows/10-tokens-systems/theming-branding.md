# theming-branding

**Group:** 10-tokens-systems
**Runs as:** subagent: ../.claude/agents/visual-designer.md
**Mode:** build (writer + verify loop)   ·   **Default model:** sonnet

## Purpose
Own themes and per-tenant branding: a theme is a swap of *semantic* token values only — never a fork of components — and every theme preserves the 60-30-10 colour proportion and passes contrast in both light and dark.

## Inputs & preconditions
- From `project-design-config.md`: token source, semantic token names (grep before use), theme (light/dark/both), locked brand rules, runtime branding hook (e.g. CSS-variable injection on login + reset on sign-out).
- Target: the theme/brand set + the screens to verify.
- Preconditions: semantic tokens read; sign-out/role-change reset path confirmed so branding never leaks across sessions.

## Oracle (source of truth)
WCAG 1.4.3 contrast + the 60-30-10 colour-proportion heuristic (Refactoring UI) + the themeable-design-systems model (Brad Frost, *Atomic Design* / bradfrost.com — core + brand-override layering, themes as composable axes not bespoke forks).
- **hard:** light AND dark both pass contrast — text ≥ 4.5:1, large ≥ 3:1, non-text/UI ≥ 3:1 (WCAG 1.4.3 / 1.4.11), measured per theme; theme swaps semantic token values only (no component changes — diff check); branding resets on sign-out/role change; every brand override file sets *only* semantic values that exist in the shared core (no brand-private token names — diff the key set against core); every resolved combination on every composable axis passes contrast — not just the default, every shipped permutation gates; the high-contrast mode passes the elevated AAA-ward thresholds (text ≥ 7:1, large/non-text ≥ 4.5:1) in both light and dark.
- **soft:** 60 neutral / 30 secondary / 10 accent proportion held; accent earns the 10% and isn't sprayed; brand-override files stay thin (only the values that actually differ from core — no copy-paste of the full set).

## Standards & techniques
- **Token-swap theming:** a theme overrides tier-2 semantic values; tier-3 component tokens and components inherit unchanged. Never branch a component per theme.
- **60-30-10:** ~60% calm neutral surface, ~30% secondary, ~10% accent — preserve the ratio across every theme.
- **Runtime branding:** inject brand colours into semantic CSS variables at login; pair every apply with an explicit reset on sign-out and on role change (don't rely on re-render to clear).
- **Layer-cascade resolution (worked example):** the live theme is `core` ← `brands/<active>` ← `scheme/<active>` ← `density/<active>` ← `contrast/<active>`, each merged left-to-right at build, every layer touching only semantic names that exist in core. Read top-down it's one cascade, not one bespoke theme per permutation:
  ```text
  tokens/
  ├── core/                     # the one shared semantic contract
  │   └── color.json            #   --surface, --text, --accent, …
  ├── brands/{acme,globex}/     # axis 1 — re-points brand-differing values only
  ├── scheme/{light,dark}/      # axis 2 — light/dark overrides
  ├── density/{comfortable,compact}/  # axis 3 — spacing/size overrides
  └── contrast/{standard,high}/ # axis 4 — high-contrast is a peer layer, not a filter
  ```
  Resolved root = `<html data-brand="acme" data-scheme="dark" data-density="compact" data-contrast="high">`; the build composes the four active layers over core. Authoring cost stays the *sum* of layers (Σ axes), never the *product* (Π permutations) — adding a brand adds one file under `brands/`, adding an axis adds one sibling directory, and neither multiplies the others (Brad Frost, themeable design systems — bradfrost.com).
- **High-contrast as a peer layer:** `contrast/high/` re-points the same semantic names as `contrast/standard/` to clear the elevated thresholds, and composes *after* scheme so it holds in both light and dark. Author, gate, and screenshot it exactly like a scheme — never an `opacity`/filter shim bolted on at the end, never skipped because "standard already passes."

## Multi-brand & multidimensional theming
The themeable-design-systems shape (Brad Frost): one core token set, brands and modes layer on top — never a wall of bespoke full themes.

- **Multi-brand directory architecture:** a single shared **core** token set holds every semantic name; each brand is a thin **override file** that re-points only the values that differ. Brand is resolved at build (env/flag → which override file loads), not at runtime per request. Layout:
  ```text
  tokens/
  ├── core/                 # the one shared semantic set — every name lives here
  │   ├── color.json
  │   ├── space.json
  │   └── type.json
  └── brands/
      ├── acme/             # override: only the values that differ from core
      │   └── color.json
      └── globex/
          └── color.json
  ```
  Resolution is `core` ← `brands/<active>` merged at build. An override may set a value but may **never** introduce a token name that does not exist in core — that would fork the contract. Adding a brand = adding one thin override file; it touches zero components.
- **Multidimensional theming (composable axes):** treat **brand × colour-scheme (light/dark) × density (comfortable/compact) × contrast (standard/high)** as four *independent* axes that compose, not as a 2×2×2×2 = 16-theme matrix you author by hand. Each axis is its own small override layer keyed off a data-attribute / class on the root (e.g. `data-brand`, `data-scheme`, `data-density`, `data-contrast`); the live theme is the *cascade* of whichever value is active on each axis. Authoring cost is the sum of the axes (4 + 2 + 2 + 2 layers), not their product. Adding a fifth axis stays additive — it never multiplies the others.
- **High-contrast as a first-class mode:** ship `data-contrast="high"` as a real, EAA-driven (European Accessibility Act) token mode designed up front — its own override layer that re-points semantic values to clear the elevated thresholds, in *both* light and dark. It is a first-class axis on equal footing with colour-scheme, never a post-hoc filter, an `opacity` tweak, or a forced-colours afterthought. Author it, gate it, screenshot it like any other theme.

**Watch (do not gate):** EMERGING — CSS relative-colour-syntax / `color-mix()` to *derive* brand and high-contrast overrides from a handful of core seeds instead of hand-listing every value (shrinks override files toward a few anchor tokens). Promising for keeping multi-brand + multidimensional layers thin, but browser-baseline and round-trip contrast behaviour aren't settled — note it, do not make it a hard oracle.

## Step sequence
- **build:** Explore (read-only; map which semantic tokens each theme must override, identify the active axes — brand × scheme × density × contrast — and confirm the core token set is the single shared contract; propose ≥2 palettes) → Judge (contrast pre-check across every shipped axis combination, including high-contrast in both light and dark, + 60-30-10 rubric, order-swapped; verify brand-override key sets match core) → Implement (one writer; edit core semantic values + thin per-brand/per-axis override layers + branding-apply/reset only — no component edits, no brand-private token names) → Verify (Playwright screenshots every state @ breakpoints across each axis permutation — light/dark × standard/high-contrast at minimum; WebAIM/axe contrast per resolved combination, high-contrast measured against the elevated thresholds; zero console errors; confirm reset clears branding on sign-out; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Light and dark each pass every contrast threshold (verified separately).
- Diff shows only core semantic token + thin override-layer + branding-hook changes; components untouched.
- Every brand override file's key set is a subset of core (no brand-private token names introduced).
- Every shipped axis combination (brand × scheme × density × contrast) passes contrast — not just the default permutation.
- High-contrast mode clears the elevated thresholds (text ≥ 7:1, large/non-text ≥ 4.5:1) in both light and dark.
- 60-30-10 proportion preserved; accent rationed.
- Branding applies on login and fully resets on sign-out/role change.
- **Gate:** hard oracles green (contrast on every shipped permutation including high-contrast, brand overrides subset of core, components unchanged) AND rubric mean ≥ 0.8.

## Output
Write `artifacts/theming-branding/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: token`/`accessibility`, `oracle: hard` for any per-permutation contrast failure, a high-contrast-mode threshold miss, a brand override that adds a non-core token name, or a component-fork; `oracle: soft` for proportion/override-thinness), plus the verification block with screenshots tagged per *axis combination* (brand × scheme × density × contrast), not just per theme.

## Guardrails
Per `shared/guardrails.md`: theme by swapping semantic token values, never by forking a component. One shared core token set; brands and axes are thin override layers, resolved at build, that may re-point core values but never introduce brand-private token names. High-contrast is a first-class mode, gated like any theme. Grep real token names. Preserve logic byte-for-byte. One writer; screenshot-verify every shipped permutation.
