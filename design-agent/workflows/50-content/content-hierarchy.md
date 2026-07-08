# content-hierarchy

**Group:** 50-content
**Runs as:** inline
**Mode:** build (writer + verify loop) · audit (scannability scan)   ·   **Default model:** sonnet

## Purpose
Own how copy is structured and ordered on the page — front-load the conclusion, make the takeaway extractable by scanning, keep the prose plain — so a skimming user gets the point first.

## Inputs & preconditions
- From `project-design-config.md`: type scale + token source (for heading/body weights), component library (SectionHeader, Card), dev-server URL/port + creds, breakpoints.
- Target: the screen's body copy, headings, summaries, list-vs-paragraph blocks; the relevant guidance (NN/g writing-for-the-web).
- Preconditions: dev server reachable; existing headings/SectionHeader components read; copy reachable to screenshot at the project's viewports.

## Oracle (source of truth)
NN/g writing-for-the-web — inverted pyramid, concise + scannable + objective (≈ +124% measured usability), plain language.
- **hard:** the page's key takeaway is extractable from headings + first sentences alone (front-loaded, not buried in paragraph tails); reading level ≈ Grade 8 (plain language, no needless jargon).
- **soft:** scannability — meaningful headings, short paragraphs, lists where they fit, bolded key terms; objective non-promotional tone.

## Standards & techniques
- **Inverted pyramid:** conclusion first, then detail, then background — the most important sentence leads each block.
- **Concise + scannable + objective:** cut filler, break walls of text into headings/lists, drop marketing puffery — the combination is what measured ~124% better task usability.
- **Plain language ~Grade 8:** short sentences, common words, expand or avoid jargon; a reading-grade check is part of the gate.
- **Takeaway by scanning:** headings + first lines + bolded terms must carry the meaning without reading the body.

## Step sequence
- **audit:** Extract headings + first sentences and check the takeaway survives → run a reading-grade check → flag buried conclusions, walls of text, jargon → emit findings (read-only).
- **build:** Explore (≥2 restructures, read-only) → Judge (inverted-pyramid + scannability + grade-level rubric, order-swapped) → Implement (one writer; reorder/rewrite copy + heading markup only, reuse SectionHeader) → Verify (screenshot @ breakpoints; axe + zero console errors; reading-grade recheck; evaluator re-scores) → loop ≤15 or pass.

## Assertions & exit gate
- Takeaway extractable from headings + first sentences alone; conclusion front-loaded in each block.
- Reading level ≈ Grade 8; no unexplained jargon; paragraphs/lists scannable.
- **Gate:** hard oracles green (front-loaded takeaway + Grade-8 plain language) AND (build) rubric mean ≥ 0.8.

## Output
Write `artifacts/content-hierarchy/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type: content`, `heuristic: NN/g writing-for-the-web`; `oracle: hard` for buried takeaway and above-grade reading level), plus the verification block for build mode.

## Guardrails
Per `shared/guardrails.md`: reorder and rewrite copy + heading markup only — never logic or data. Reuse SectionHeader/Card and the type scale before inventing structure. Read-only audit makes no edits; one writer for build; trust the rendered screenshot over the diff.
