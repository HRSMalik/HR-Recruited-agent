# Backlog — HR Recruited

**Project:** Autonomous AI recruitment backend (FastAPI + LangGraph + MongoDB + LiveKit/Gemini voice)
**Last Updated:** 2026-07-08

> Seeded from `DEEP_AUDIT_2026-06.md` (Parts 1-5). Full finding inventory (16 criticals/majors, 7 logic, 9 design, 24 features) lives in the audit; this backlog carries the actionable, prioritized subset. Never delete rows — move Open → Completed with a date.

---

## Summary

| Total | Complete | Open |
| --- | --- | --- |
| 31 | 13 | 18 |

_(18 backend audit items · 13 frontend build items)_

---

## Open

| ID | Description | Priority |
|---|---|---|
| BL-01 | Remove candidate name/email/school from the scoring LLM context — proxy discrimination (cites AUD-C01) | HIGH |
| BL-02 | Add human-in-the-loop review gate before advance/reject/call/book — GDPR Art.22 / EU AI Act Art.14 (cites AUD-C02) | HIGH |
| BL-03 | Authenticate + make idempotent the voice ingress `/voice/webhook` + `/voice/livekit-complete` (cites AUD-C03) | HIGH |
| BL-04 | Spend controls: page/applicant cap, scheduler kill-switch, rate-limit middleware, Gemini interview-duration cap (cites AUD-C04) | HIGH |
| BL-05 | Parser: strip markdown fences + flag parse-failure to stop blank-candidate persistence (cites AUD-C05) | HIGH |
| BL-06 | Poison-pill: `mark_processed` on launch failure with bounded attempts (cites AUD-C06) | HIGH |
| BL-07 | Booking: check and write the SAME calendar id (fix wrong-calendar / double-book) (cites AUD-C07) | HIGH |
| BL-08 | Bootstrap DB indexes at startup + TTL index on `slot_reservations` (cites AUD-C08) | HIGH |
| BL-09 | Ranking: cap CV-only composite or segregate interviewed/not lists (cites AUD-C09) | MEDIUM |
| BL-10 | Reaper for wedged pipeline threads + fix checkpointer concurrency (WAL/serialize) (cites AUD-C10) | HIGH |
| BL-11 | LiveKit: replace default `devkey`/`secret`, require env creds, set token TTL | HIGH |
| BL-12 | LiveKit: dispatch allowlist so the agent doesn't auto-join every room (budget burn) | HIGH |
| BL-13 | LiveKit: stop token-in-URL; stop plaintext PII transcripts on disk + add retention | HIGH |
| BL-14 | Cherry-pick the LinkedIn publish fix (F1 / `a5fe051`) onto `hrmalik`/`main` | HIGH |
| BL-15 | Fix inverted CV gate threshold (70 → PRD 60) (cites L1) | MEDIUM |
| BL-16 | Fix flagged 65-69 auto-reject band; make recommend bands monotonic (cites L2/L3) | MEDIUM |
| BL-17 | Reconcile `hrfilza`/`hrhamza` divergence + add branch protection on `main` | MEDIUM |
| BL-18 | Re-establish hermetic test suite + CI gate (tests were deleted `854396a`) | MEDIUM |

### Frontend build — recruiter dashboard (React + TS + Vite)

> Builds the approved refined design (`designs/recruiter-dashboard/` — growth-green, SVG icons, whitespace-first) against the FastAPI backend, in `frontend/`. Ordered foundation-first; each item is independently buildable + verifiable and traces to a design screen or a CLAUDE.md FE convention.

| ID | Description | Priority |
|---|---|---|

---

## Completed

| ID | Description | Priority | Status |
|---|---|---|---|
| BL-FE-01 | Scaffold `frontend/` (Vite + React + TS) + design tokens (slate + growth-green, light/dark) + folder structure | HIGH | COMPLETE 2026-07-08 — build + live render verified |
| BL-FE-02 | SVG `Icon` set + component library (Button, Card*, PageBanner, SectionHeader, Input/TextArea, Select, Table, Badge, AlertBanner, Modal) | HIGH | COMPLETE 2026-07-08 — build + gallery render verified |
| BL-FE-03 | API layer: `apiFetch()` + Zod schemas/types + typed endpoints + Zustand stores (session, jobs, shortlist, calls) | HIGH | COMPLETE 2026-07-08 — tsc strict verified |
| BL-FE-04 | App shell: sidebar nav + React Router routes + theme toggle (session store) + placeholder pages | HIGH | COMPLETE 2026-07-08 — build + live render (routing + active nav) verified |
| BL-FE-05 | Overview — stat cards, funnel, screening-call donut (Recharts), "Needs your attention"; calls store + sample fallback | HIGH | COMPLETE 2026-07-08 — typecheck + live render verified |
| BL-FE-06 | Job posts + criteria editor (editable rows, importance selects, draft→confirm/lock); jobs store + criteria endpoints | HIGH | COMPLETE 2026-07-08 — typecheck + live render verified |
| BL-FE-07 | Shortlist — ranked table (composite bars, recommendation badges, red-flag chips), filters, re-rank modal; shortlist store | HIGH | COMPLETE 2026-07-08 — typecheck + live render verified |
| BL-FE-08 | Candidate detail — fit by criterion, interview insights + transcript, CV summary, human decision actions (logged) | MEDIUM | COMPLETE 2026-07-08 — typecheck + live render verified |
| BL-FE-09 | Interviews (call ops) — stat tiles, call-log table w/ retry/close, outcomes donut, retry queue; calls store | MEDIUM | COMPLETE 2026-07-08 — typecheck + live render verified |
| BL-FE-10 | Meetings — day-grouped scheduled interviews, status pills, Join → /interview/:room, reschedule | MEDIUM | COMPLETE 2026-07-08 — typecheck + live render verified |
| BL-FE-11 | Interview room — Meet-style dark room + livekit-client (connect/track/controls) scaffold; preview when no server | HIGH | COMPLETE 2026-07-08 — typecheck + live render verified |
| BL-FE-12 | Polish — responsive breakpoints (sidebar collapse, grids stack, table scroll-containment), dark-theme verified, reduced-motion, a11y (focus-visible + aria-labels) | MEDIUM | COMPLETE 2026-07-08 — build + light/dark/narrow render verified |
| BL-FE-13 | FE Dockerfile (node build → nginx serve, SPA fallback) + .dockerignore + GitHub Actions CI (typecheck + build) | LOW | COMPLETE 2026-07-08 — CI yaml valid + build verified (docker daemon n/a to build image) |
