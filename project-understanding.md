# Project Understanding — HR Recruited

**Project-specific context.** The general developer style guide is NOT duplicated here — it lives only in `claude-stuff/CLAUDE.md` (canonical). This file captures what is specific to HR Recruited.

**Last Updated:** 2026-07-08

---

## What it is

Autonomous AI recruitment **backend**. Candidates apply themselves (inbound only — there is **no sourcing agent**), and the system parses their CV, scores fit against the JD, screens them by voice interview, books an HR meeting, and ranks them into a shortlist. The Streamlit UI is **test-only**, not a deliverable — frontend findings are deprioritized.

## Architecture

FastAPI + a per-candidate **LangGraph** pipeline with durable suspend/resume across interrupts, MongoDB persistence, and external integrations.

**Pipeline:** `parse_cv → match → [CV-fit gate] → start_interview → score_interview → [interview gate] → book (candidate self-picks a slot) → create_event → rank → END`, with `reject` and `wait_retry` terminals. Persisted via a SQLite checkpointer; resumes on two interrupts (voice webhook, slot-pick).

**The 5 agents:** job-post (`job_post.py`), parser (`parser_agent.py`, GPT-Vision), matching (`shortlisting_agent.py` + `criteria_agent.py`), interview (voice — see stack below), ranking (`ranking_agent.py`, composite CV 40 / interview 60).

**Voice stack (in flux):** the canonical branch replaced the original Vapi voice with **LiveKit + Gemini realtime** (`livekit_agent.py`). The old Vapi `/voice/webhook` still exists as dead-but-reachable legacy; the new ingress is `/voice/livekit-complete`.

**Key files:** `app.py` (API + background loops), `pipeline.py` (graph), `config.py` (non-secret config), `schemas.py`, `booking_agent.py`, `calendar_agent.py`, `call_logs.py`, `transcript_analyzer.py`, `email_agent.py`, `auth.py`, `mcp_server.py` (LinkedIn publish via Playwright).

**Integrations:** OpenAI (GPT-4o / 4o-mini), LiveKit + Gemini realtime, Google Calendar/Drive/Sheets/Gmail, (legacy) Vapi.

## Repos & branches (dual-repo)

- **Personal — `HRSMalik/HR-Recruited-agent`** (this repo): full codebase + planning/audit docs (`DEEP_AUDIT_2026-06.md`, PRD, sprint sheets, `backlog.md`, `workdone.md`). My control/planning workspace.
- **Org — `MalikHarris-tekh/hr-recruited`**: clean canonical code. Branches: `main` (canonical), `hrfilza` (Filza), `hrhamza` (Hamza), `flowmingo`, **`hrmalik`** (my control branch, off `main`).
- **`main` is currently the merged `hrhamza` LiveKit rework** (Hamza self-merged PR #1 on 2026-07-08, no review — flagged; `main` should get branch protection).
- **Branch divergence:** the LinkedIn publish fix (`a5fe051`) lives only on `hrfilza` and is **missing from `main`/`hrhamza`** — needs cherry-picking.

## Team

Malik (control/planning), Filza (`FilzaNoor123`), Hamza (`HamzaAhmad536`). GitHub accounts: `HRSMalik` personal, `MalikHarris-tekh` org — always return to `HRSMalik` after org operations.

## Hard constraints

- All QA/audit is **non-destructive, read-only** against a **LOCAL** sandbox (`recruitment-module-qa` on localhost) — **never** touch Atlas prod (`hr-rec.qtct5dr.mongodb.net`, db `recruitment-module`).
- Planning-only engagement: I plan & assign; the associate dev implements. I don't write product code unless asked.
- Never commit secrets (`.env`, `.trello_creds` are gitignored). Never add a Co-Authored-By-Claude line.

## Status (2026-07-08)

Deep audit complete (5 parts) against the canonical code. **Not launch-ready:** all 10 criticals open, both legal blockers open (name-in-scoring, no human-in-loop), 7 new LiveKit vulnerabilities. The scoring rework did close the fragile-parser + silent-0 holes (real progress). Full inventory in `DEEP_AUDIT_2026-06.md`; actionable items in `backlog.md`.
