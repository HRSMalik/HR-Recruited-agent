# Tickets Status Tracker

> How to read status:
> - 🟢 **Fully Done** — implemented + verified, nothing pending.
> - 🟡 **Partially Done** — some part implemented, some part still pending.
> - 🔴 **Not Started** — not begun yet.
>
> Update the **Status** column as work progresses. Detailed implementation notes live in `ticketsworkdone.md`.

---

## ⚠️ WORKFLOW — Follow For EVERY Ticket (mandatory)

**Do NOT write any code until the user explicitly says "start".**

For each ticket, first present (text only, no code):

1. **Workflow** — what this ticket does end-to-end, where it fits in the system.
2. **Approaches** — possible ways to implement it, with pros/cons.
3. **Key Decisions** — choices that need confirming (collections, schema, trade-offs, open questions).
4. **Implementation Plan** — exact files to add/modify + what changes in each.

➡️ Then **WAIT**. Only when the user says **"start"** (or "ok do it" / "implement") → write the code.

After coding: run the self-test / verification, then update this tracker + `ticketsworkdone.md`.

---

## Epic: EP-RANK — Composite Ranking (Sprint 1)

| Ticket | Title | Status | ETA | Notes |
|--------|-------|--------|-----|-------|
| EP-RANK-BE-001 | compute_composite (pure fn) | 🟢 Fully Done | 2h | weights env-only, clamp, CV-only path |
| EP-RANK-BE-002 | recommend() + hybrid red flags | 🟢 Fully Done | 1h | voice LLM flags + rule flags, verified w/ real LLM |
| EP-RANK-BE-003 | __main__ self-test block | 🟢 Fully Done | 0.5h | assertions, DB-free, all pass |
| EP-RANK-BE-004 | rank_candidate (persist ranked shortlist) | 🟢 Fully Done | 3h | DB helpers + rank_candidate; red flags via screened (Option C) + rule fallback; idempotent, DB-tested |
| EP-RANK-BE-005 | rank_for_jd (ranked shortlist query) | 🟢 Fully Done | 2h | DB sort desc + 1-based rank + top_n limit; empty→[]; DB-tested |
| EP-RANK-BE-006 | GET /ranked-candidates API | 🟢 Fully Done | 3h | endpoint reuses rank_for_jd; jd_id/top_n/skip/limit; RankedListResponse; TestClient-tested |
| EP-RANK-BE-007 | POST /jobs/{jd_id}/rerank | 🟢 Fully Done | 2h | weight override threaded through compute_composite→rank_candidate; rerank_jd helper; env default; TestClient-tested. EP-RANK COMPLETE 🎉 |

---

## Epic: EP-PIPE — Cohesive LangGraph Pipeline (Sprint 2)

| Ticket | Title | Status | ETA | Notes |
|--------|-------|--------|-----|-------|
| EP-PIPE-BE-001 | Define shared pipeline state | 🟢 Fully Done | 3h | pipeline.py: PipelineState TypedDict (total=False), stage/status constants, new_state(); JSON-serialisable self-test |
| EP-PIPE-BE-002 | Checkpointer + graph factory | 🟢 Fully Done | 2h | _build_checkpointer (SQLite→InMemory fallback, pipeline_checkpoints.sqlite) + create_pipeline_agent (placeholder node compiles); self-tested |
| EP-PIPE-BE-003 | Parse CV node | 🟢 Fully Done | 3h | parse_cv wraps process_cv → populates profile + cv_id; pdf_path field added; entry point set; self-tested (mocked process_cv) |
| EP-PIPE-BE-004 | Match node | 🟢 Fully Done | 2h | match wraps _score_candidate_against_jd; loads jd_text by jd_id; writes fit_percent to state + candidates_info (upsert); self-tested (mocked) |
| EP-PIPE-BE-005 | CV-threshold router + reject | 🟢 Fully Done | 2h | route_after_match (VOICE_CALL_THRESHOLD env) → start_interview | reject(status=rejected_cv); placeholder start_interview; both branches self-tested |
| EP-PIPE-BE-006 | Interview node + interrupt | 🟢 Fully Done | 4h | start_interview: normalise phone + Vapi call + screened row(status=calling) + interrupt(); existing-row guard against re-call on resume; self-tested (graph suspends) |
| EP-PIPE-BE-007 | Webhook resume wiring | 🟢 Fully Done | 4h | /voice/webhook resolves call_id→thread (screened row) + Command(resume=...); start_interview stores thread_id; legacy fallback + unknown/duplicate guards; TestClient end-to-end resume verified |
| EP-PIPE-BE-008 | Interview scoring node | 🟢 Fully Done | 3h | score_interview (resume target): categorize_call + _score_interview + hybrid red flags + extract_interview_insights; persists score/category/flags/insights; end_reason+duration fields; self-tested via resume |
| EP-PIPE-BE-009 | Interview-threshold router | 🟢 Fully Done | 2h | route_after_interview (CALENDAR_THRESHOLD env): completed&≥→book, completed&<→rank, not-completed→reject; smart reject (rejected_interview vs rejected_cv); placeholders book/rank; 3 branches self-tested |
| EP-PIPE-BE-010 | Booking node + interrupt | 🟢 Fully Done | 4h | book wraps create_slot_picker_booking + interrupt() until slot picked; existing-pending guard; no-token→no hang; self-tested (suspend + resume) |
| EP-PIPE-BE-011 | Slot-select resume + event node | 🟢 Fully Done | 4h | POST /api/booking/{token}/select: select_slot (event creation preserved) then resolve token→candidate_id→screened.thread_id + Command(resume={selected_slot,meet_link}); create_event node records slot/link into state; book→create_event→rank wiring; not-paused guard (no double-resume); TestClient end-to-end verified |
| EP-PIPE-BE-012 | Ranking terminal node | 🟢 Fully Done | 2h | rank node now calls ranking_agent.rank_candidate(cv_id)→END (replaced placeholder); mirrors composite_score+recommendation into state, status=completed; None-safe on unknown cv_id; both exits (booked + low-score) converge; self-test extended (rank_candidate mocked) |
| EP-PIPE-BE-013 | Scheduler launches pipeline | 🟢 Fully Done | 4h | _shortlist_loop rewritten: detect_new_applicants (download only) → _launch_pipeline_for_applicant (one graph per candidate) → mark_processed; stopped calling shortlist_all_jobs/call_top_candidates; split ingest to fix double-parse + temp-file-lifetime conflict (ingest_new_applicants now a backward-compat wrapper); failed launch not marked (retries); tested |
| EP-PIPE-BE-014 | End-to-end validation harness | 🟢 Fully Done | 4h | test_pipeline_e2e.py: one fixture candidate driven parse→match→interview→book→rank via real endpoints+graph (externals mocked); both resumes (Vapi webhook + slot-pick) verified; ranked_candidates persisted; existing endpoints unchanged (/ranked-candidates reflects it, /health 200). EP-PIPE COMPLETE 🎉 |
| QA-14 | [MINOR] Missing security headers | 🟢 Fully Done | 0.3h | (security-fix, defense-in-depth) added a global `@app.middleware("http")` setting X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Referrer-Policy: no-referrer, HSTS, and a Content-Security-Policy on every response incl. public /book/* pages. CSP is pragmatic (allows 'unsafe-inline' script/style + Google Fonts so the booking pages keep working) but restricts framing/external scripts/origins — also blunts QA-03 XSS. Verified via Test_files/test_security_headers.py (local-only). NOTE: nonce-based strict CSP deferred (would need externalising the booking pages' inline script/style) |
| QA-13 | [MINOR] Opaque 500s + shallow health check | 🟢 Fully Done | 0.5h | (reliability-fix) (1) global `@app.exception_handler(PyMongoError)` → any Mongo failure returns clean 503 "database unavailable" (was opaque 500), logs type to stderr, no leak. (2) new `/ready` readiness probe pings Mongo with a dedicated 2s-timeout client → 200 "ready" / 503 "not ready"; `/health` stays liveness-only (always 200). `/ready` added to auth public allowlist. Verified via Test_files/test_reliability.py (local-only; 4 cases). |
| QA-12 (part 1) | BE-013 scheduler dead imports removed | 🟢 Fully Done | 0.1h | (cleanup) removed 3 dead imports left after the BE-013 refactor: `shortlist_all_jobs` (shortlisting_agent — whole import line gone), `call_top_candidates` + `ingest_new_applicants` (from voice_agent/parser_agent lines). All were import-only, unused (graph does detect→launch→mark itself). app imports clean. Part 2 (loop-wiring test) intentionally SKIPPED per user decision to keep tests out of the repo |
| REFACTOR-01 | Centralize config — secrets in .env, thresholds in config.py | 🟢 Fully Done | 2h | (refactor, user-requested) ~25 non-secret thresholds/tunables were scattered as os.getenv across 7 files. New `config.py` holds them as pure constants (ranking weights, recommend bands, rule flags, calendar/booking windows, voice/scoring, retry/reminder, loop intervals). Migrated ranking_agent/calendar_agent/booking_agent/voice_agent/pipeline/app/call_logs to `import config`; removed dead `_env_float_or` + dead os.environ in pipeline self-test. `.env`/`.env.example` now hold ONLY secrets + per-deploy (API keys, LinkedIn, Vapi, Google IDs, Mongo URI, BOOKING_BASE_URL, CORS, ENABLE_API_DOCS). Values preserved from current .env (no behaviour change). All modules import clean; ranking + pipeline self-tests green. NOTE: diverges from CLAUDE.md "all thresholds in env" per explicit user decision (config.py is still centralized configuration) |
| QA-07 | [MAJOR] booking slot-select 500 — naive vs aware datetime | 🟢 Fully Done | 0.3h | (bug-fix) select_slot compared Mongo's tz-NAIVE expires_at against tz-AWARE now → TypeError → 500 on real paths (slot no longer available, or token expired). GET /book/{token} already guarded this; select_slot didn't. Fix: normalize expires_at to UTC-aware before the `<= now` check (mirrors show_booking_page). Fails before any reservation/calendar write, so no corruption. New test_booking_expiry.py (naive-past→expired, naive-future→slot_unavailable, aware-past→expired; no 500). All 14 tests green |
| QA-06 | [MAJOR] rerank 500 on zero-sum weights | 🟢 Fully Done | 0.3h | (validation-fix) POST /jobs/{jd_id}/rerank with {"cv_weight":0,"interview_weight":0} passed Pydantic ge=0 but summed to 0 → ranking_agent raised uncaught ValueError → HTTP 500. Fix: cross-field `@model_validator(mode="after")` on RerankRequest — both given & sum ≤ 0 → 422 at the validation layer (single weight / no body still allowed, env default applies). New test_rerank_weights_validation.py (0+0→422, valid→200, none→200, single→200). All 13 tests green |
| QA-05 | [MEDIUM] rerank unknown jd -> 200-empty not 404 | 🟢 Fully Done | 0.3h | (correctness-fix) POST /jobs/{jd_id}/rerank returned 200 {items:[],total:0} for a non-existent jd_id → a typo silently "succeeded". Fix: existence check via _get_job_descriptions_collection().find_one({"_id": jd_id}) up front → 404 "Job not found" when absent; valid jd reranks as before. Listing GET endpoints deliberately left returning empty (empty result is normal for listings). New test_rerank_404.py. All 12 tests green |
| QA-04 | [MEDIUM] Ranking 500 if weights unset; ship .env.example | 🟢 Fully Done | 0.5h | (config-fix, = EP-RANK-BE-001) `_read_weights` used the RAISING `_env_float` for RANK_CV_WEIGHT/RANK_INTERVIEW_WEIGHT → unset env = ValueError = /ranked-candidates + /jobs/{jd}/rerank 500. Fix: switched to `_env_float_or` with defaults 0.4/0.6 (removed now-dead `_env_float`). Shipped `.env.example` (all vars, secrets as placeholders) + `.gitignore` `!.env.example` exception so it's committed while `.env` stays ignored. New test_ranking_weights.py (unset→defaults, no crash; env still honoured). All 11 tests green |
| QA-03 | [HIGH] Stored XSS — candidate name unescaped | 🟢 Fully Done | 1h | (security-fix) candidate_name (from CV, untrusted) was interpolated raw into HTML/email in 4 renderers → `<script>` in a name executed on the public booking pages + emails. Fix: `html.escape()` every interpolated field in `app._render_picker_page` (name, score, slot iso, label), `app._render_confirmed_page` (name, meet_link, date), `booking_agent._slot_picker_html` (name, booking_url), `booking_agent._render_reminder` (name, when, tz, meet_link). New test_xss.py proves `<script>` name → `&lt;script&gt;` in all 4. All 10 tests green |
| QA-02 | [MAJOR] CORS reflects any Origin w/ credentials | 🟢 Fully Done | 0.5h | (security-fix) app.py CORS had allow_origins=["*"] + allow_credentials=True → any site could call the API with credentials (echoed Origin + allow-credentials:true). Fix: explicit env-driven allowlist `CORS_ALLOWED_ORIGINS` (comma-separated; default http://localhost:8501,http://localhost:8000 for local Streamlit; production just adds its URL to the env, no code change). Dropped "*". New test_cors.py (allowlisted origin echoed, arbitrary origin NOT reflected, no "*"). All 9 tests green |
| QA-01 | [CRITICAL] No auth on any endpoint | 🟢 Fully Done | 2h | (security-fix) HTTPBearer was imported in app.py but never wired → every route 200 with no credentials, /openapi.json public; anyone could trigger POST /job-posts (LLM+LinkedIn spend), POST /test-call (real Vapi call), reads of all PII. Fix: new auth.py `require_api_key` (Authorization: Bearer <API_KEY> from env) added as an app-level dependency → ALL routes protected by default; public allowlist = /health + /book/* + /api/booking/* + /voice/webhook (token/external-caller are their own credential). Docs+/openapi.json gated behind ENABLE_API_DOCS (default off). streamlit_app.py routes every call through an authed requests.Session (loads API_KEY from .env). New test_auth.py (health public, protected 401 no-key/wrong-key, 200 with key, booking+webhook public). All 8 project tests green (test_pipeline_e2e patched to send the key). NOTE: /voice/webhook still public — should later add Vapi signature/secret verification |
| EP-PIPE-BE-027 | Atomic slot reservation (race-proof) | 🟢 Fully Done | 1.5h | (bug-fix) Two candidates could still double-book the same time: is_slot_free (BE-016) relied on Google free/busy which is eventually-consistent + a check-then-act (TOCTOU) race + only checked primary HR. Fix: new slot_reservations collection — select_slot now atomically insert_one({_id:"email\|slot"}) for EVERY attendee (primary HR + team) BEFORE creating the event; any DuplicateKeyError → roll back this candidate's holds + reopen booking + slot_taken (closes the race with no propagation lag; also covers shared team members). is_slot_free kept as Layer-2 safety net for manual HR events. Reservation released on event-creation failure. test_booking_double_booking.py extended (3 cases incl. concurrent same-slot rejected while Google still says free). All 7 project tests green. NOTE: reschedule/cancel flow (not yet built) must call _release_slots |
| EP-PIPE-BE-026 | Slot-picker email English + no score | 🟢 Fully Done | 0.1h | (copy-fix) candidate slot-picker email had Roman-Urdu lines ("Aapka voice screening clear ho gaya", "Apna interview slot khud choose karein") + showed the numeric Score. Converted to English and removed the score line (consistent with BE-025) |
| EP-PIPE-BE-025 | Calendar invite leaks score/salary | 🟢 Fully Done | 0.25h | (privacy-fix) calendar_agent._build_description put screening score + expected salary + notice period into the event description — visible to the CANDIDATE (an attendee) + team. Removed score/salary/notice; kept neutral context (role/company/experience/stack). HR sees score in dashboard, not the invite |
| EP-PIPE-BE-024 | Skip non-PDF uploads (runtime fix) | 🟢 Fully Done | 0.5h | (runtime-fix) a candidate uploaded a .txt instead of PDF → fitz FileDataError every scheduler tick (failed launch never marked processed → infinite retry). detect_new_applicants now checks Drive mimeType before download; non-PDF → log + mark_processed(status="skipped_not_pdf") + skip. mark_processed gained status param. Self-heals the stuck file on next tick |
| EP-PIPE-BE-023 | Pre-interview reminder (8h before) | 🟢 Fully Done | 2h | (feature) NOT a pipeline node — time-based background loop. New booking_agent.send_due_reminders (scans meetings for scheduled interviews starting within REMINDER_HOURS_BEFORE=8, emails candidate + HR/team via email_agent, sets reminder_sent once); new app._reminder_loop (every REMINDER_LOOP_INTERVAL_SECONDS=900, mirrors _retry_loop); meetings doc inits reminder_sent=False. test_reminder.py (window/dedup/recipients) green |
| EP-PIPE-BE-022 | Scoring model env-driven (gpt-4o) | 🟢 Fully Done | 0.25h | (config-fix) _score_interview model was hardcoded gpt-4o-mini; now os.getenv("SCORING_MODEL","gpt-4o") + .env SCORING_MODEL=gpt-4o. Verified gpt-4o works with the configured OPENAI_API_KEY (real test call returned OK). Better reasoning over noisy ASR transcripts. Tests green (LLM mocked) |
| EP-PIPE-BE-021 | ASR-error robustness in scoring prompt | 🟢 Fully Done | 0.5h | (prompt-fix) poor scores traced to garbled Vapi speech-to-text (tech terms misheard). Added an "ASR TRANSCRIPTION ERRORS" block to _score_interview prompt: correct phonetic corruptions before scoring (Langkang→LangChain, Fortress→Postgres, etc.), treat dropped audio as partial answers, ignore fillers, do NOT penalize ASR errors — with a guardrail to NOT fabricate tech from common English words. Root fix (Vapi STT keyterm boosting / nova-2) is dashboard-side. Imports clean, e2e green |
| EP-PIPE-BE-020 | Consolidate scoring/persist (drift fix) | 🟢 Fully Done | 2h | (refactor) pipeline.score_interview and voice_agent.record_call_result had duplicated scoring+persist orchestration (mutually exclusive via thread_id, but already drifted 3×). Extracted single source of truth voice_agent.score_and_persist_call (categorize+log+score+composite+recommendation+screened+insights); both paths now call it. Also added rank_candidate to record_call_result so legacy candidates also reach ranked_candidates (last divergence). All 8 tests green |
| EP-PIPE-BE-019 | Interview rubric overlapping bands | 🟢 Fully Done | 0.5h | (prompt-fix) _score_interview 5-tier rubric had "70-84 Strong" and "60-74 Decent" both covering 70-74 → ambiguous LLM signal, inconsistent scores. Changed Decent band 60-74 → 60-69 (now contiguous, non-overlapping: 0-39/40-59/60-69/70-84/85-100) |
| EP-RANK-BE-008 | recommend() thresholds → env | 🟢 Fully Done | 0.5h | (config-fix) recommend() hardcoded 80/65/50/70; now env-driven via _env_float_or (RECOMMEND_STRONG_YES=80, RECOMMEND_YES=65, RECOMMEND_MAYBE=50, RECOMMEND_REVIEW_MIN=70) — matches CLAUDE.md "all thresholds in env" + parity with detect_rule_flags. Defaults preserve behaviour; self-test green |
| EP-PIPE-BE-018 | Booking resume double-email guard | 🟢 Fully Done | 1h | (bug-fix) book node guard matched status="pending" only; select_slot flips booking pending→booked BEFORE the graph resumes, so on the book re-run the guard missed it → create_slot_picker_booking ran again (second email + orphan booking). Fix: match any active status {$in:[pending,processing,booked]}. test_pipeline_booking.py made stateful (counts create calls) to assert exactly one email across resume |
| EP-PIPE-BE-017 | Pakistani phone normalization | 🟢 Fully Done | 2h | (bug-fix) _normalize_phone gave invalid E.164 for PK local formats (03001234567 → +03001234567 → Vapi reject); leading trunk 0 wasn't stripped. Rewrote with region-aware rules (strip trunk 0 → +92; 00 intl prefix; bare 10-digit → +92; already-CC passthrough); default VAPI_DEFAULT_COUNTRY_CODE +92. New test_normalize_phone.py (12 real-input cases, no mock) all green |
| EP-PIPE-BE-016 | Double-booking guard + screened consistency | 🟢 Fully Done | 2h | (bug-fix) Issue 1: select_slot now re-verifies HR free/busy via new calendar_agent.is_slot_free before creating the event; slot taken → reject (slot_taken) + booking released for re-pick (prevents two candidates booking the same HR slot). Issue 2: score_interview now also writes composite_score + recommendation to screened_candidates (was only on ranked_candidates → dashboards showed blanks). Tested: test_booking_double_booking.py + pipeline self-test |
| EP-PIPE-BE-015 | Call-logs + retry parity | 🟢 Fully Done | 3h | (gap-fix, not in sprint xlsx) score_interview now calls log_call_attempt (audit to call_logs + retry scheduling) and returns call_log_status; new wait_retry node pauses on retriable declines until process_retries re-calls + webhook resumes (loops back to score_interview); cancelled/exhausted → reject (no re-call); added vapi_end_reason + duration_seconds to screened row. Restores parity with old record_call_result so /call-logs, /call-stats and declined-retry work in the pipeline. Self-test covers retry-loop + cancelled-direct-reject; all 5 pipeline tests green |

---

## Status Legend

| Symbol | Meaning | Criteria |
|--------|---------|----------|
| 🟢 Fully Done | Complete | Code implemented + tested/verified + no pending sub-tasks |
| 🟡 Partially Done | In progress | Core implemented but verification or a sub-part pending |
| 🔴 Not Started | Pending | No code written yet |

---

## Open Decisions / Clarifications

- **EP-RANK-BE-004 (resolved):** red_flags source = **Option C** — reuse the combined (LLM + rule) `red_flags` already stored on `screened_candidates` by BE-002; fall back to `detect_rule_flags()` when the candidate was never interviewed. Kept composite+recommendation on `screened_candidates` (interview-level) *and* `ranked_candidates` (final shortlist source).

---

_Last updated: 2026-06-18 — EP-PIPE COMPLETE (BE-001–014). Both epics done._
