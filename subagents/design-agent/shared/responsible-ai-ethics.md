# Responsible-AI & Fairness — the Ethics Lens for AI-Touched Screens

Binding on every design flow that touches an AI-driven surface (ranking, scoring, match %, auto-screen, suggested replies, summaries). The agent designs *how AI behaves and is presented to the user* — not just whether it looks good. A screen that surfaces an automated decision and can't honor this doc downgrades scope and says so. This is an HR/recruitment product: fairness is a hard oracle, not a nicety.

## 1. Microsoft HAX — the 18 Human-AI Interaction guidelines (Amershi et al., CHI 2019)
Every AI surface is audited against the relevant guidelines for its phase. Source: https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/

- **Initially** — **G1** make clear what the system can do · **G2** make clear how well it can do it (show capability + accuracy/limits up front; never imply certainty the model doesn't have).
- **During interaction** — **G3** time services based on context · **G4** show contextually relevant info · **G5** match relevant social norms · **G6** mitigate social biases.
- **When wrong** — **G7** support efficient invocation · **G8** support efficient dismissal · **G9** support efficient correction · **G10** scope services when in doubt · **G11** make clear why the system did what it did (explainability).
- **Over time** — **G12** remember recent interactions · **G13** learn from user behavior · **G14** update and adapt cautiously · **G15** encourage granular feedback · **G16** convey the consequences of user actions · **G17** provide global controls · **G18** notify users about changes.

## 2. Google PAIR — the four canon moves
Source: https://pair.withgoogle.com/guidebook/ . Each screen with AI output earns its design against these.

- **Set expectations (PAIR "Mental Models")** — the UI states what the AI does, what it doesn't, and that it adapts. No anthropomorphizing certainty; a match score is a suggestion, not a verdict.
- **Explain (PAIR "Explainability + Trust")** — every automated output carries a reason the user can see ("ranked on skills + years", not a black box). Partial explanations are fine; opaque ones are not.
- **Calibrate trust** — show confidence only where it aids the decision (High/Med/Low buckets or n-best over false-precision percentages). Design must not invite *over*-trust of a fallible model.
- **Graceful AI failure (PAIR "Errors + Graceful Failure")** — design the empty/low-confidence/wrong-output states explicitly; every failure returns control to the human with a path forward (edit, override, re-run, give feedback). An AI surface with no designed failure state fails the gate.

## 3. AI-use disclosure
- Any screen where AI ranks, scores, screens, drafts, or summarizes must **label it as AI-assisted** at the point of use — not buried in a footer or ToS.
- Disclose **what data feeds the decision** in plain language, and that a human can override it (closes HAX G11 + G16).
- Auto-generated text shown to a candidate or recruiter is marked as generated, with an obvious edit affordance before it's sent or acted on.

## 4. Bias / Fairness checklist — RECRUITMENT surfaces (hard oracle)
Recruitment AI can amplify discrimination at scale. Every candidate-facing or candidate-ranking screen is audited against this list; any failure is a `critical` ethics finding that blocks.

- **No protected-class signals surfaced or implied** — the UI never displays, sorts, filters, or visually emphasizes age, gender, race, ethnicity, national origin, religion, disability, pregnancy/marital status, or proxies (photo prominence, name-origin, graduation year, address/zip, "culture fit" tags). Flag any field that leaks one.
- **Audit ranking/score presentation for bias amplification** — a model score is presented as *one input*, not destiny: no auto-reject styling, no red/green moralizing of low scores, no hiding lower-ranked candidates by default. Verify sort/score visuals don't entrench a single signal.
- **Equal prominence for candidates** — identical card/row treatment, photo size, badge density, and CTA weight across all candidates; rank position must not change a candidate's *visual dignity* (same affordances top-to-bottom of the list).
- **Explainability of automated decisions** — any rank, score, or auto-screen exposes its top contributing factors in plain language so a recruiter can sanity-check for bias (HAX G11 + PAIR explainability).
- **Human-in-the-loop for consequential actions** — reject, advance, auto-disqualify, and any candidate-facing send require a human confirm step; no irreversible automated decision fires without a designed override (HAX G9, G16, G17). A consequential AI action with no human gate is a `critical` finding.
- **Symmetric error handling** — false-positive and false-negative paths are both designed; a candidate wrongly screened out has a visible, reachable path back into the pipeline.

## 5. Finding type — `ethics`
Ethics issues are first-class findings, logged with the schema in `finding-schema.md`.

- Add **`ethics`** to the finding `type` enum (alongside `accessibility | visual | interaction | token | heuristic | content | responsive`).
- `id` short-code **`ETH`** → `UX-ETH-001`, `UX-ETH-002`, …
- `oracle`: bias/fairness, missing human-in-the-loop, missing AI disclosure, and missing failure-state are **`hard`** (blocking on recruitment surfaces); softer calibration/explainability craft notes are `soft` above the rubric threshold.
- Cite the standard in a `ref`-style note: the **HAX guideline (`G1`–`G18`)** and/or the **PAIR chapter** the finding maps to — same way accessibility findings cite a WCAG SC and heuristic findings cite a Nielsen number.
- `evidence` is mandatory: the screenshot (with viewport) of the offending surface or the exact field/markup that surfaces a protected signal. No evidence → it's a note, not a finding.
