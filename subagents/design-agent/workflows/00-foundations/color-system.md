# color-system

**Group:** 00-foundations
**Runs as:** subagent: ../.claude/agents/visual-designer.md
**Mode:** build (writer + verify loop) · audit (ramp + contrast scan)   ·   **Default model:** sonnet

## Purpose
Own the colour ramps and semantic roles: accessible 50–900 shades per hue mapped to light/dark roles, so every surface, border, and text pairing has a named token that passes contrast.

## Inputs & preconditions
- From `project-design-config.md`: brand/palette, token source + real token names (grep before use), theme (light/dark/both), colour rule, locked brand rules.
- Target: the ramp set + the screens/components consuming it.
- Preconditions: token source readable; existing ramps/roles read before inventing a shade.

## Oracle (source of truth)
WCAG 1.4.3 Contrast (Minimum) + 1.4.11 Non-text Contrast + Material 3 tonal roles.
- **hard:** every text pairing ≥ 4.5:1 (≥ 3:1 large), every UI/border pairing ≥ 3:1, verified light AND dark via the contrast checker; every shade resolves to a real token (grep source).
- **soft:** ramp completeness and even tonal spacing; semantic-role coverage (no screen reaching for a raw shade).

## Standards & techniques
- **Design the grayscale first**, then hues — neutrals carry most of the surface.
- **5–9 shades per colour** (50–900): light steps for fills/backgrounds, mid steps for borders, dark steps for text.
- **Material 3 tonal roles:** map each ramp to semantic roles — `surface`, `on-surface`, `primary`, `on-primary`, `border`, `muted` — paired so on-roles always clear their surface.
- Apply locked brand rules (e.g. accent hue rationed as chrome, not flooded).

## Modern CSS colour — derive in the stylesheet, not in JS
Prefer native CSS colour over JS-injected tints (e.g. runtime `setProperty` ramp building). Deriving in the cascade keeps one source of truth, removes a render-blocking JS hop, and survives SSR/no-JS. Contrast stays the **hard oracle** in every case below — a derived shade is a *candidate*, not a pass; re-run the contrast checker (light AND dark) on every pairing it touches before it ships.

- **OKLCH ramps — perceptually-uniform steps.** Build 50–900 by stepping lightness `l` on a fixed `c`/`h`, so tonal spacing reads even to the eye instead of even in sRGB. This directly serves the soft oracle (even tonal spacing) and the grayscale-first rule.
  ```css
  --primary-500: oklch(0.62 0.17 256);
  --primary-400: oklch(0.70 0.16 256);   /* +0.08 L, same C/H */
  --primary-600: oklch(0.54 0.17 256);   /* −0.08 L */
  ```
- **`color-mix()` — derive interaction states from a base token.** Compute hover/active/disabled by mixing the base toward a neutral, never as new hand-picked hex. Keeps states tied to the role token, so a brand change ripples once.
  ```css
  --primary-hover:    color-mix(in oklch, var(--primary-500), black 12%);
  --primary-active:   color-mix(in oklch, var(--primary-500), black 22%);
  --primary-disabled: color-mix(in oklch, var(--primary-500), var(--surface) 60%);
  ```
- **Relative colour syntax — `from <base> …`.** `oklch(from var(--base) …)` destructures the base into channels (`l c h alpha`) you can `calc()` on, generating lighter/darker/alpha variants from one token (MDN, *Relative colors*). Use it as the CSS-native replacement for JS-computed tints.
  ```css
  --primary-lighter: oklch(from var(--primary-500) calc(l + 0.08) c h);
  --primary-darker:  oklch(from var(--primary-500) calc(l - 0.08) c h);
  --primary-ghost:   oklch(from var(--primary-500) l c h / 0.12);
  ```
  Feature-detect before committing a path: `@supports (color: oklch(from white l c h)) { … }`.
- **`light-dark()` + `color-scheme` — a CSS-only theming path.** Set `color-scheme: light dark` on the root and resolve each role token with `light-dark(<light>, <dark>)`, replacing a JS `applyBranding`/theme-swap. Both legs still owe a contrast pass — `light-dark()` removes the JS, not the dual-theme verification.
  ```css
  :root { color-scheme: light dark; }
  --surface:    light-dark(oklch(0.98 0 0), oklch(0.20 0 0));
  --on-surface: light-dark(oklch(0.20 0 0), oklch(0.96 0 0));
  ```

**Watch (do not gate):** OKLCH, `color-mix()`, relative colour syntax, and `light-dark()` are emerging in `00-foundations` — recommend them, feature-detect them, but never make their presence a gate condition. Ship a resolved fallback token where support is unconfirmed; the only thing that gates is contrast.

## Step sequence
- **audit:** enumerate every text/UI pairing across the screen → run the contrast checker on each (light + dark) → flag any pairing < threshold or any raw shade used where a role token exists → emit findings (read-only).
- **build:** Explore (≥2 ramp/role mappings, read-only) → Judge (contrast pass-rate + role-coverage rubric, order-swapped) → Implement (one writer; define ramps + role tokens, wire surfaces/text/borders to roles) → Verify (Playwright screenshots every state @ breakpoints; contrast check every pairing light+dark; axe + zero console errors; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Grayscale defined first; 5–9 shades per hue; light=fill / mid=border / dark=text discipline holds.
- Every text ≥ 4.5:1, every UI/border ≥ 3:1, both themes; no raw shade where a role token exists.
- **Gate:** hard oracles green (contrast light+dark + token conformance) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/color-system/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: accessibility` + `wcag_ref: 1.4.3`/`1.4.11` for contrast, `type: token` for raw-shade use), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: never hardcode hex where a role token exists — grep the source, never guess a token. Reuse existing shades before adding one. Preserve logic byte-for-byte. Read-only audit makes no edits; one writer for build.
