# Work Completion Workflow

> **Permanent project file — do not remove.**
> **⚠️ MANDATORY for ANY task, no exceptions** — a **Trello card**, a **`backlog.md` item**, a
> bug fix, a one-off change, a refactor — anything that changes the product runs this same gated
> flow. "It looks small/trivial" is never a reason to skip the gates. Same loop, same discipline.

Never start building, scaffold, create files, or mark anything complete without being explicitly
told to **at each step**. **Every step must explain itself** — state what the step is, do it,
report what it found, then **ask permission** before the next step. Each step is its own gate;
never batch steps or batch decisions.

> **Engagement note (HR Recruited):** this is a **backend-only, inbound-only, planning-only**
> project. **Claude audits / proposes / verifies — it never writes product code or memory.** The
> **associate (Filza/Hamza) or Malik writes the product code** on the control branch `hrmalik`.
> Source of truth = `PRD.md` + `DEEP_AUDIT_2026-06.md`. Ticket surfaces = the Trello board
> (`TeJrES78`) + `backlog.md`. There is no frontend deliverable, so the UI/UX gates are omitted
> (add them only if a Streamlit test-UI item ever arises).

## The gated sequence

1. **Explain the item** (trigger: user moves a Trello card to In Progress / flips a backlog item
   `[ ] → [~]` / "start X") — what it changes, which modules/pipeline-nodes/endpoints/collections
   it affects, key decisions. Nothing else. Wait.
2. **PRD + audit scan** — read the relevant `PRD.md` sections and the cited `DEEP_AUDIT_2026-06.md`
   finding **word by word**. Verify claims against the PRD/code directly — do not trust a prior
   audit's reading. For new scope with no PRD backing, state "no PRD backing — new scope" and do a
   first-principles review instead. Report → ask permission.
3. **Code scan** — read the existing codebase for everything affected (pipeline nodes, agents,
   `config.py`, `schemas.py`, DB access, patterns to reuse). AFTER the PRD scan. Report → ask.
4. **Dev best-practices web scan** — best practices, current library versions, security/state
   patterns (LangGraph durable execution, LiveKit/Gemini, MongoDB, OpenAI). Report → ask.
5. **Audit** — Claude (or a specialized agent: security-scanner, exploratory-tester,
   qa-orchestrator) audits the surface and reports a prioritized findings list. Report → ask.
6. User says **"create the backlog"** (exact phrase) → create `BL-XXX` items in `backlog.md`; each
   traces to a PRD section / audit finding ID (AUD-C0x / L# / F#) or "new scope".
7. User says **"start BL-XX"** / bare **"start"** → flip the item `[ ] → [~]` In Progress, **first
   explain the item**, then build only that item. **The associate / Malik writes the product code**
   (on `hrmalik`); Claude only audits / proposes / verifies — never writes product code or memory.
8. **Commit locally after EVERY item with code changes** — message references the `BL-*` ID. Never
   go 2–3 items without a commit. No `Co-Authored-By`.
9. User says **"next"** → next item. (Never auto-advance after a close — "Up Next" is reference,
   not permission.)
10. **Verify + smoke** — Claude drives the flow / runs hard oracles against the **LOCAL sandbox**
    (`recruitment-module-qa` on localhost) — **never Atlas prod**. A green build/`py_compile` is NOT
    a smoke test. Run it MYSELF first; assert on unique detail, not generic labels. Log observations;
    fix any ❌.
11. **UAT** — present a short **user-acceptance checklist** (what to run, what to expect) and **wait
    for the user to test + accept**. The item stays `[~]` In Progress until they confirm; fix
    anything flagged, then re-offer. **Never self-close** — UAT is a separate gate after my own smoke.
12. **10 test cases (after UAT passes)** — the item's smoke test must contain **exactly 10 test
    cases** (each acceptance criterion's happy path + edge / negative / boundary / role cases + a
    regression of prior behaviour), as runnable assertions. Re-establishing the deleted suite is
    backlog **BL-18**. Mandatory gate — nothing closes without its 10 cases.
13. On acceptance → **close**: flip `[~] → [x]` Done with a one-line **close note** (what delivered
    + how verified/UAT'd + the 10 cases), log `workdone.md` on full item/epic close, update counts.
14. **Close comment** — move the mapped Trello card to Done; the backlog close note is the local
    analog of the card comment (plain English, no PRD refs, no markdown).

Order is fixed: **explain → PRD/audit → code scan → dev web scan → audit → backlog →
build/commit/next → verify+smoke → UAT → 10 test cases → close → close-comment.** Each is a separate
report-and-permission gate. Do NOT skip to step 6 just because something is "In Progress."

## Two surfaces, one workflow

- **Trello board `TeJrES78`** — cards move To Do / Sprint → In Progress → Review → Done.
- **`backlog.md` items** — the checkbox IS the status: `- [ ]` To Do → `- [~]` In Progress (exactly
  one at a time) → `- [x]` Done; the close note is the local analog of the card comment.
- When a backlog item maps to a Trello card, move both in lockstep. **Never delete items** (permanent
  history) — move to Completed with a date.

## PRD / audit compliance — non-negotiable

Every field, value, validation rule, conditional behaviour, and label must match `PRD.md` **word for
word**, scanned word-by-word and cross-cutting. Every backlog item cites its PRD section / audit
finding ID. Unbuilt sections still get their schema/state shape defined.
