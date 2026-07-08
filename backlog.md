# Backlog — HR Recruited

**Project:** Autonomous AI recruitment backend (FastAPI + LangGraph + MongoDB + LiveKit/Gemini voice)
**Last Updated:** 2026-07-08

> Seeded from `DEEP_AUDIT_2026-06.md` (Parts 1-5). Full finding inventory (16 criticals/majors, 7 logic, 9 design, 24 features) lives in the audit; this backlog carries the actionable, prioritized subset. Never delete rows — move Open → Completed with a date.

---

## Summary

| Total | Complete | Open |
| --- | --- | --- |
| 31 | 1 | 30 |

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
| BL-FE-02 | SVG `Icon` set (no emoji) + the standard component library: `Button`, `Card`/`CardHeader`/`CardBody`/`CardFooter`, `PageBanner`, `SectionHeader`, `Input`/`TextArea`, `Select`, `Table`, `Badge`, `AlertBanner`, `Modal` | HIGH |
| BL-FE-03 | API layer: central `apiFetch()` + TS types + Zod schemas for backend responses (candidates, ranked, job-posts, criteria, call-logs, meetings); Zustand stores | HIGH |
| BL-FE-04 | App shell: sidebar nav (Overview/Job posts/Shortlist/Candidates/Interviews/Meetings) + top bar + React Router routes + theme toggle + API-key/auth handling | HIGH |
| BL-FE-05 | Overview screen — stat cards, recruitment funnel, screening-call donut (Recharts), "Needs your attention" block; wire to `/call-stats` + pipeline | HIGH |
| BL-FE-06 | Job posts + criteria editor — list, create (JD generate/review), criteria editor (generate → edit importance → confirm/lock); wire to `/job-posts` + `/jobs/{id}/criteria/*` | HIGH |
| BL-FE-07 | Shortlist — ranked table (composite, recommendation, red flags), filters, re-rank weights; wire to `/ranked-candidates` + `/rerank` | HIGH |
| BL-FE-08 | Candidate detail — fit by criterion, interview insights + transcript, CV summary, decision actions (advance/hold/reject, logged); wire to candidate data | MEDIUM |
| BL-FE-09 | Interviews (call ops) — stat tiles, call-log table, outcomes donut, retry queue; wire to `/call-logs` + `/call-stats` + retry/close | MEDIUM |
| BL-FE-10 | Meetings — day-grouped scheduled interviews, status, Join → room, reschedule; wire to bookings/meetings | MEDIUM |
| BL-FE-11 | Interview room — `livekit-client` integration (AI-audio tile + candidate camera + live transcript + mic/cam/captions/leave + question progress); wire to `/interview/{room}` + LiveKit token | HIGH |
| BL-FE-12 | Polish + states + a11y + responsive — loading/empty/error states, `:focus-visible`, WCAG AA, breakpoints, dark theme; design-agent verify pass | MEDIUM |
| BL-FE-13 | FE Dockerfile + build/deploy (Vite build) + CI | LOW |

---

## Completed

| ID | Description | Priority | Status |
|---|---|---|---|
| BL-FE-01 | Scaffold `frontend/` (Vite + React + TS) + design tokens (slate + growth-green, light/dark) + folder structure | HIGH | COMPLETE 2026-07-08 — build + live render verified |
