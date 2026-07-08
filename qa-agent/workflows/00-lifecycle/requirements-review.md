# requirements-review

**Category:** 00-lifecycle
**Runs as:** subagent: ../.claude/agents/qa-orchestrator.md (inline lifecycle flow)
**Default model:** sonnet   ·   **Mode:** read-only

## Purpose
Shift-left static review of the BRD / user stories / acceptance criteria. Answers: "Is each requirement testable, complete, and unambiguous before a single test or line of code is written?"

## Inputs & preconditions
- Required artifacts: BRD / PRD, user stories (As-a / I-want / So-that), acceptance criteria (Given/When/Then), any glossary.
- Target: the requirements document set (file paths or ticket IDs); no running SUT needed.
- Preconditions: requirement IDs exist and are stable; assert each story has at least an ID + title. If ACs are absent, that is itself a finding, not a blocker.

## Oracle (source of truth)
The requirement text itself plus external quality criteria: **INVEST** (Independent, Negotiable, Valuable, Estimable, Small, Testable) for stories, **IEEE 830 / ISO/IEC/IEEE 29148** requirement attributes (correct, unambiguous, complete, consistent, verifiable, traceable), and the **3 C's** (Card, Conversation, Confirmation). NEVER the developer's interpretation.

## Step sequence (Plan → Act → Verify)
1. **Plan** — enumerate every requirement/story ID in scope; bucket checks: testability, completeness (missing AC, missing NFRs, missing error paths), ambiguity (weasel words: "fast", "user-friendly", "etc.", "and/or", "support"), consistency (contradicting reqs), atomicity (one story doing two things).
2. **Act** — review one requirement at a time; run each through INVEST + 29148 verifiability; flag passive voice / unquantified adjectives via a weasel-word lexicon; skip-and-continue if a single story is malformed.
3. **Verify** — assert against the oracle: a requirement passes only if it is verifiable (an objective pass/fail test can be written), has explicit ACs, and contains no unresolved ambiguity. Capture the offending sentence as evidence.

## Assertions & exit gate
- Every story has ≥1 testable acceptance criterion expressed in measurable terms.
- No ambiguous quantifier remains unresolved (e.g. "responds quickly" → must state a numeric target).
- No requirement bundles two independent behaviors (INVEST-Small/Independent).
- **Gate:** `no_ambiguous_or_untestable_requirements` — passes when 0 critical/major findings (an untestable or missing-AC requirement is **major**; ambiguity that blocks test design is **critical**).

## Output
Write `artifacts/requirements-review/report.json` per `shared/report-format.md`:
`{ flow:"requirements-review", status, summary{total,passed,failed,skipped}, findings[], gate{name:"no_ambiguous_or_untestable_requirements",passed} }`.
Each finding (`QA-REQ-NNN`) names the requirement ID in `oracle`, quotes the ambiguous/missing text in `evidence`, and suggests the corrected, testable wording in `suggested_fix`.

## Guardrails
Read-only — `disallowedTools: Edit, Write` on the source docs. Never invent requirements or assume intent; flag the gap instead. No external calls. Cap `maxTurns`; secrets via env. Findings are recommendations only — a human owns requirement sign-off.
