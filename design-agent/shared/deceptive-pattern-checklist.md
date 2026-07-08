# Deceptive-Pattern Checklist — the Fair-Pattern Bar

A reviewer-run checklist for deceptive design ("dark patterns"). This is now a **legal-risk axis** (GDPR Art. 5/7/25, DSA Art. 25), not soft ethics — a confirmed pattern is a `heuristic` finding at **major+**, never cosmetic. The oracle is the EDPB taxonomy below + the live screen; for each category the **fair-pattern alternative** is the required fix. Wired into `60-evaluation/heuristic-audit.md` as a second rule set alongside Nielsen's 10.

## The taxonomy (EDPB 6 categories + 4 classic types)

| # | Pattern | What it looks like on the screen | Fair-pattern fix (the required `fix`) |
|---|---------|----------------------------------|---------------------------------------|
| **D-01** | **Overloading** | Flooding the user with requests, options, or consent toggles to wear them down (privacy maze, too many choices). | One clear decision; sensible grouped defaults; no per-vendor toggle wall. |
| **D-02** | **Skipping** | Designing the flow so users overlook a data/privacy decision (deceptive snugness, look-over-there). | Surface the decision in the primary path; don't bury it past the CTA. |
| **D-03** | **Stirring** | Steering via emotion — **confirmshaming** ("No, I like paying full price") or **visual interference** (the Reject button styled to disappear). | No guilt copy; **symmetric Accept/Reject** — same size, weight, colour, contrast. |
| **D-04** | **Hindering / Obstruction** | Making an action artificially hard — **roach-motel / hard-to-cancel** (easy in, maze out), dead-end, longer-than-necessary cancel flow. | **Easy cancel = easy signup** — symmetric exit, same number of steps/clicks. |
| **D-05** | **Fickle** | Inconsistent, unstable interface that hides info (the choice moves, language shifts, controls disappear between states). | Stable, predictable layout; controls stay where the user left them. |
| **D-06** | **Left in the dark** | Hiding information or interface elements, or leaving intent ambiguous (hidden costs, unclear who sees the data). | State cost, recipient, and consequence up front, in plain language. |
| **D-07** | **Sneaking** | Slipping in items/charges the user didn't ask for — hidden costs, **sneak-into-basket**, hidden subscription, drip pricing. | Show full price + every line item before the commit step; no auto-adds. |
| **D-08** | **Forced action** | A wanted action gated behind an unwanted one — **forced continuity**, forced account creation, privacy-zuckering, gated consent. | Make the gate genuinely optional; offer a guest/skip path; granular consent. |
| **D-09** | **Nagging** | Repeated interruption that nags toward the designer's preferred choice (persistent re-prompts after a "No"). | Honour the first answer; cap re-prompts; "don't ask again" actually sticks. |
| **D-10** | **Preselection** | A consequential option **pre-ticked** in the provider's favour (opt-out marketing, pre-checked consent — invalid under GDPR). | **Honest defaults** — non-essential options default OFF; consent is opt-in, unticked. |

## Checklist a reviewer runs (per screen, at every breakpoint)

Drive the live flow — especially **consent, signup, checkout, and cancel/delete** paths. Tick each; any unticked box is a finding.

- [ ] **Symmetric choice** — Accept and Reject/Decline have equal visual weight (size, colour, contrast, position). No styled-to-disappear Reject. (→ D-03)
- [ ] **No confirmshaming** — decline copy is neutral; no guilt/shame wording on the opt-out. (→ D-03)
- [ ] **No roach motel** — cancel/unsubscribe/delete is reachable in the same effort as signup; count the clicks both ways. (→ D-04)
- [ ] **Honest defaults** — every non-essential toggle/checkbox defaults OFF; nothing consequential is pre-ticked. (→ D-10)
- [ ] **No sneaking** — full price and every added item shown before the commit; no auto-added extras, no hidden recurring charge. (→ D-07)
- [ ] **No forced action** — the wanted task isn't gated behind unnecessary account creation or bundled consent; granular + optional. (→ D-08)
- [ ] **No nagging** — a declined prompt isn't repeated; "no" and "don't ask again" persist. (→ D-09)
- [ ] **Not left in the dark** — cost, data recipient, and consequence stated up front in plain language. (→ D-06)
- [ ] **Stable & not overloaded** — controls don't move/relabel between states; the decision isn't buried under option overload or skipped past the CTA. (→ D-01/D-02/D-05)

## Output

Per `finding-schema.md`: `type: heuristic`, `heuristic: "EDPB D-0N <name>"`, `wcag_ref: null`, `oracle: soft` (advisory above threshold; a confirmed consent/cancel pattern defaults to **major** per `quality-rubric.md`). Every finding carries a screenshot + viewport and a `fix` stated as the fair-pattern alternative above. Read-only — route the fix to the owning build flow (content/interaction); never edit here.

## Sources

- Deceptive Design — Types of deceptive patterns: https://www.deceptive.design/types
- EDPB Guidelines 03/2022 on deceptive design patterns in social media platform interfaces (categories: overloading, skipping, stirring, hindering, fickle, left in the dark): https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-032022-deceptive-design-patterns-social-media_en
