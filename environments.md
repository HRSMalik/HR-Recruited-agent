# HR Recruited — Environments

Single FastAPI backend (no frontend deliverable — the Streamlit app is test-only). LangGraph
per-candidate pipeline + MongoDB + LiveKit/Gemini voice + Google (Calendar/Drive/Sheets/Gmail) +
OpenAI. See `project-understanding.md` for architecture and `WORK_COMPLETION_WORKFLOW.md` for the flow.

**Working model:** backend-only, inbound-only, **planning-only** — Claude audits/verifies; the
associate/Malik implements on the `hrmalik` control branch. All QA/audit is **non-destructive** and
runs against the **LOCAL sandbox only**.

## Services

| Service | Env | Base URL | Health | Notes |
| ------- | --- | -------- | ------ | ----- |
| API | local | http://localhost:8000 | /health, /ready | FastAPI in `app.py` (`uvicorn app:app`); background loops (shortlist / retry / reminder) start on boot — mind the spend (see audit AUD-C04). |
| Interview (LiveKit) | local | LiveKit server (`LIVEKIT_URL`); candidate page `GET /interview/{room}?token=` | — | `livekit_agent.py` + Gemini realtime. ⚠️ defaults to `devkey`/`secret` if env unset — set real creds (audit). |
| Streamlit test UI | local | http://localhost:8501 | — | **test-only, not a deliverable.** |
| API | deployed | _TBD — not deployed_ | — | No Dockerfile / CI yet (audit F11/F12). |
| MongoDB | **local sandbox** | mongodb://localhost:27017 · db `recruitment-module-qa` | — | ✅ The **only** writable QA/audit target. |
| MongoDB | prod (Atlas) | `hr-rec.qtct5dr.mongodb.net` · db `recruitment-module` | — | ⛔ **NEVER touch** — no reads/writes during QA/audit. Assert NON-PROD before any DB op. |

**Config:** secrets in `.env` only (`OPENAI_API_KEY`, `MONGODB_URI`, `LIVEKIT_URL`/`LIVEKIT_API_KEY`/
`LIVEKIT_API_SECRET`, `GOOGLE_*`, `VAPI_*`, `API_KEY`); non-secret config in `config.py`;
`.env.example` documents the keys. Secrets never go in this file.

## Git Sync (personal ↔ org)

> **Model (atypical):** the **ORG repo is authoritative** — Filza/Hamza push to org branches and the
> canonical line is org `main`. The personal repo is a **planning workspace + full code mirror**.
> So `/gitpush` here means: **pull org `main` → refresh the personal code mirror** (code files only,
> never touch the planning docs); Malik's own code changes go **org-side** via the nested clone on
> **`hrmalik` → PR → `main`** (reviewed, no self-merge). Always confirm the org target before pushing.

| Field            | Value                                                        |
| ---------------- | ------------------------------------------------------------ |
| Personal account | HRSMalik                                                     |
| Personal dir     | /home/malik-harris/tekhqs/HR-Recruited agent                 |
| Personal repo    | HRSMalik/HR-Recruited-agent (branch `main`)                  |
| Org account      | MalikHarris-tekh                                             |
| Org dir          | /home/malik-harris/tekhqs/HR-Recruited agent/hr-recruited (nested clone) |
| Org repo         | MalikHarris-tekh/hr-recruited                                |
| Branch           | org canonical `main`; Malik control branch `hrmalik` → PR → `main`. Personal `main`. |

**Directory mappings** (org is the code source of truth):
| Personal subdir | Org subdir | Sync rule |
| --------------- | ---------- | --------- |
| repo root (code: `*.py`, `docs/`, `evaluation/`, `ragasev/`) | nested clone `hr-recruited/` root | code mirror — pull org→personal (additive + existing-only); **never `--delete`** the personal planning docs |

**Never sync to org (personal-only planning/audit layer):** `DEEP_AUDIT_2026-06.md`, `PRD.md`,
`[PRD] *.pdf`, `SPRINT_SHEET_SPEC.md`, `gen_sprint_sheet.py`, `generate_pdf.py`, `push_to_trello.py`,
`HRRecruited_Sprint_RANK_PIPE.xlsx`, `Work_Report_*.pdf`, `backlog.md`, `workdone.md`,
`project-understanding.md`, `WORK_COMPLETION_WORKFLOW.md`, `environments.md`, `CLAUDE.md`, `claude.md`,
`.claude/`, `.trello_creds`, `.env`.

**Org-only (source of truth for code — never overwrite from personal):** all backend `*.py`,
`agents.md`, `tickets.instructions.md`, `ticketsworkdone.md`, `docs/`, `evaluation/`, `ragasev/`,
`.env.example`. On genuine conflict, **org wins** (reconcile with Filza/Hamza first).

**rsync excludes:** `.git`, `.env`, `__pycache__`, `*.pyc`, `*.log`, `.venv`, `venv`, `data`,
`data.zip`, `*.zip`, `*.pkl`, `node_modules`, `dist`, **`hr-recruited`**, **`claude-stuff`** (the
nested-clone subdirs must be excluded so rsync never recurses into itself).
