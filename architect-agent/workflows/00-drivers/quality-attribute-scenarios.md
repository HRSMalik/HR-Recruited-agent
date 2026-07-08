# quality-attribute-scenarios

**Group:** 00-drivers
**Runs as:** subagent: ../.claude/agents/requirements-analyst.md
**Mode:** audit (review an existing system's stated qualities) · design (build the utility tree for a new design)   ·   **Default model:** sonnet

## Purpose
Turn vague "-ilities" into a **prioritized, measurable oracle** — the utility tree. Every architecture decision downstream is judged against this; without it there is no hard oracle and no way to say a design is "good." Answers: *which quality attributes matter, made concrete as scenarios with response measures, ranked by business value × technical risk?*

## Inputs & preconditions
- From `project-architecture-config.md`: the architectural-drivers seed, the stated NFRs (from the BRD/PRD — never invent numbers), the compliance regime, the scale/SLO targets, the constraints.
- The functional scope (what the system does) and the stakeholders (who cares about which quality).
- Preconditions: the source-of-truth docs (`docs/`, `project-understanding.md`) read; if a quality target (RTO, availability, peak load) is **not stated**, surface it as an open driver question — do not assume a number.

## Oracle (source of truth)
The stakeholders' stated business goals + the documented NFRs, expressed as the SEI **6-part quality-attribute scenario** ending in a **response measure** (`evaluation-method.md`). The utility tree itself becomes the hard-oracle target set for every later flow.
- **hard:** every architecturally-significant quality has at least one scenario; every scenario is 6-part (*source · stimulus · artifact · environment · response · response-measure*) and ends in a **measurable** response (a number, a percentile, a time bound) — not an adjective; every scenario is prioritized on **(business value, technical risk)** ∈ {H,M,L}²; every response measure traces to a stated business goal or documented NFR (no invented numbers).
- **soft:** the tree is balanced (no attribute that matters is missing — performance, reliability, security, modifiability, cost, compliance, operability), the scenarios are realistic (drawn from real stimuli/environments), and the prioritization is defensible.

## Standards & techniques
- **ISO/IEC 25010** quality characteristics as the attribute taxonomy (so nothing material is forgotten): functional suitability, performance efficiency, compatibility, usability, reliability, security, maintainability, portability — plus cost as a first-class driver.
- **The 6-part scenario** — *source* (who/what triggers), *stimulus* (the event), *artifact* (the part stimulated), *environment* (normal / peak / degraded / under-attack), *response* (what the system does), *response-measure* (the number it's held to).
- **Utility-tree prioritization** — the `(business value, technical risk)` pair per leaf; the `(H,H)` leaves are where the architecture lives or dies and get the most evaluation effort; `(L,L)` is noise.
- **Quality-attribute taxonomy of stimuli** per attribute (the SEI tactics catalogs) — e.g. availability stimuli = fault/crash/timeout/omission; performance stimuli = event arrival (periodic/stochastic/sporadic) — use them so scenarios cover the real stimulus space, not just the happy case.

## Step sequence
- **audit:** read the existing NFRs/SLOs → restate each as a 6-part scenario → flag every "-ility" with **no response measure** as a gap → check coverage against ISO 25010 (which attributes have no scenario?) → emit findings (missing measures, unbalanced tree, untraceable numbers). Read-only, authors nothing.
- **design:** Frame the stakeholders + business goals → draft scenarios per attribute from the ISO-25010 taxonomy + the stimulus catalogs → attach a response measure to each (traced to a goal/NFR; surface unknowns as open questions, don't invent) → prioritize each on (value, risk) → assemble the **utility tree** and write it to `architecture/<slug>/quality-attributes.md`. (This is the only `00-drivers` flow that authors an artifact — it produces the oracle every other flow consumes.)

## Assertions & exit gate
- Every architecturally-significant quality has ≥1 scenario; every scenario is 6-part and ends in a measurable response.
- Every response measure traces to a stated business goal or documented NFR (no invented numbers); unknowns are listed as open driver questions, not guessed.
- Every leaf is prioritized on (business value, technical risk); the `(H,*)` leaves are identified as the evaluation focus.
- **Gate:** hard oracles green (6-part + measurable + traced + prioritized) AND (design) the tree covers the ISO-25010 attributes that matter for this system with a defensible prioritization (rubric mean ≥ 0.8).

## Output
Write `artifacts/quality-attribute-scenarios/report.json` per `shared/report-format.md` — findings per `finding-schema.md` (`type:"driver"`; `oracle:"hard"` for a quality with no measurable scenario or an untraceable number), the `drivers[]` block (the prioritized scenarios), and for design mode the path to the authored `architecture/<slug>/quality-attributes.md` (the utility tree). Open driver questions (unstated RTO/availability/scale) are listed explicitly for the controller to resolve — never silently assumed.

## Guardrails
Per `shared/guardrails.md`: ground every scenario in a stated goal/NFR — **never invent a response measure**; if it's unstated, it's an open question, not a guess. Read-only audit authors nothing. The utility tree is the foundation of every later flow's oracle — get the numbers right or mark them open. Propose & document — never implement.
