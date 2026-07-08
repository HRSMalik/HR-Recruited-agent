# transactional-email-design

**Group:** 90-channels
**Runs as:** subagent: ../.claude/agents/design-orchestrator.md (proposer references it; one writer applies)
**Mode:** audit (email-render scan) · build (re-build template + verify)   ·   **Default model:** sonnet

## Purpose
Own the email surface as a first-class channel with its OWN physics — the modern-CSS axis of the web flows does NOT apply here. Make a transactional message (e.g. application received, interview invite, password reset, offer letter) render intact, accessibly, and on-brand across the major clients, where the layout engine is a 20-year-old table renderer, not a browser.

## Inputs & preconditions
- From `project-design-config.md`: brand/palette + locked brand rules, the token *values* (resolve each token to its literal hex/px — inlined email can't reference a CSS variable or external stylesheet), logo asset, sender domain, dev-server/preview URL for the template, and which clients matter.
- Target: the transactional template(s) under review; the message's single primary action; standard = Litmus Email Design Best Practices (https://www.litmus.com/blog/email-design-best-practices).
- Preconditions: an email-render harness reachable (Litmus/Email-on-Acid, or a client matrix); the template's HTML source + the brand token values read before editing — inline literals, never invent a hue.

## Oracle (source of truth)
The Litmus best-practices guide, verified by rendering the email across the client matrix (Outlook desktop/Word engine, Gmail web + app stripping `<head>` styles, Apple Mail, iOS, dark-mode clients) — not by previewing in one browser.
- **hard:**
  - **Structure that survives stripping** — `<table role="presentation">`-based layout (NO fl/grid/float), every layout style INLINED on the element (Gmail discards `<head>`/`<style>`), single content column capped ~600px, `bulletproof` buttons (table-cell anchor with padding + VML fallback for Outlook), not background-image-dependent CTAs.
  - **Plain-text alternative** — a real `text/plain` part is sent alongside the HTML (multipart/alternative), not an auto-stripped afterthought.
  - **Accessibility** — `lang` set; meaningful `alt` on every `<img>` (logo, icons) and `alt=""` on decorative ones; a logical heading/reading order; `role="presentation"` on layout tables so AT doesn't read them as data; link text is descriptive (no bare "click here"); body-text contrast ≥ 4.5:1 (≥3:1 large) in BOTH light and the dark-mode render.
  - **Taxonomy honoured** — this is treated as **transactional** (triggered, one-to-one, account/action-related): one primary action, no promotional cross-sell blocks or marketing-only footer that would mislead the transactional classification.
- **soft:** images-off still communicates the message and CTA (alt + live text carry it); hierarchy reads in ~3s; dark-mode render is deliberate, not accidentally inverted; brand colour rationed per the locked rules.

## Standards & techniques (email physics, cite the principle)
- **Tables, not modern CSS:** nested `<table role="presentation">` for structure; widths in fixed px on cells; no `display:flex/grid`, no `position`, no floats, no external/`<link>` stylesheets — clients strip or ignore them.
- **Inline everything:** every colour/border/padding/font style lives in a `style=""` attribute on the element (resolved literal value), because Gmail drops the `<head>`. A `<style>` block is at best a progressive enhancement, never load-bearing.
- **~600px content width:** single column ~600px so it fits the Outlook reading pane and scales to mobile; fluid-hybrid (`max-width` + ghost tables) for responsiveness without media-query reliance.
- **Bulletproof buttons:** the CTA is a padded table-cell `<a>` with a solid background colour (+ Outlook VML roundrect), never an `<img>` button and never dependent on a background image — it must work with images off.
- **Dark mode + `prefers-color-scheme` caveats:** support is partial and inconsistent (Apple Mail/iOS honour `prefers-color-scheme`; many Gmail/Outlook contexts force-invert regardless); supply `meta name="color-scheme"` / `supported-color-schemes`, design colours that survive auto-inversion, and verify the actual dark render rather than trusting the media query.
- **Client quirks:** Outlook (Word engine) ignores `margin`/`border-radius`/background-image and needs VML + cellpadding spacing + a fixed-width ghost table; Gmail strips `<head>` styles and clips messages over ~102KB; iOS auto-links dates/addresses. Account for each in the matrix, don't assume one render.
- **Plain-text + alt text:** ship a genuine plain-text part mirroring the message + CTA URL; descriptive `alt` on every meaningful image so the message stands with images blocked (the common default).
- **Watch (do not gate):** the **AMP for Email** interactive layer and CSS-variable / `@media`-driven theming in email are EMERGING and unevenly supported (and AMP requires a separate registered MIME part). Offer them only as an enhancement layered on top of the inlined-table + plain-text baseline; flag their absence as advisory, never a hard oracle, and never a reason to drop the plain-text part or inline fallback.

## Step sequence
- **audit:** render the live template across the client matrix (incl. a dark-mode client) + an images-off pass → assert table/`role="presentation"` structure, fully inlined styles, ~600px column, bulletproof button, real plain-text part, `lang` + meaningful/empty alt, descriptive links, body contrast ≥4.5:1 in light AND dark, and transactional-vs-marketing classification → emit findings (read-only, no edits), each with the offending client render.
- **build:** Explore (≥2 table-layout/inlining specs for the same message, read-only) → Judge (survives-stripping + accessibility + transactional-taxonomy rubric, order-swapped) → Implement (one writer; rebuild as nested presentation tables, inline every style to literal token values, add VML bulletproof button, `meta color-scheme`, alt text, and a matching plain-text part — markup/style only, no send/template-variable logic) → Verify (render across the matrix + dark mode + images-off; contrast + alt + link-text checks both schemes; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Layout is `<table role="presentation">` only (no flex/grid/float/position); every style inlined (renders correctly with `<head>` removed); content column ≤ ~600px; CTA is a bulletproof table-cell button working with images off (Outlook VML present).
- A real plain-text alternative ships; `lang` set; every meaningful `<img>` has descriptive alt and decorative ones `alt=""`; links are descriptive; body contrast ≥ 4.5:1 (≥3:1 large) in light AND dark renders.
- Classified and built as transactional (single primary action, no marketing cross-sell); colour values resolve to the brand tokens' literals (no off-palette hex); send/merge-field logic unchanged (diff check).
- **Gate:** hard oracles green (table-structure + inlined + bulletproof CTA + plain-text part + a11y/contrast both schemes + transactional taxonomy) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/transactional-email-design/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: responsive` for layout/width/stripping, `accessibility` for alt/contrast/lang/link-text — cite `1.1.1`/`1.4.3`/`3.1.1`/`2.4.4`, `content` for taxonomy/plain-text; `oracle: hard` for non-table layout, non-inlined styles, missing plain-text part, image-only CTA, missing alt, contrast fail in either scheme, marketing blocks in a transactional send; name the offending **client** as the `viewport`; `evidence` = the client render @ scheme/images-off + measured ratio / axe rule id), plus the verification block (per-client + dark-mode + images-off renders, hard-oracle results, rubric score).

## Guardrails
Per `shared/guardrails.md`: change template markup/inline style only — never the send pipeline, merge-field/template variables, tracking, or unsubscribe logic (preserve behaviour byte-for-byte). Reuse the brand token *values* and logo asset — inline the literal, never guess a hue. Read-only audit makes no edits; one writer for build; trust the actual client render (and the images-off + dark pass) over the diff, never a single-browser preview; delete temp render scripts after.
