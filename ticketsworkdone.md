# Tickets Work Done — EP-RANK (Composite Ranking)

> Epic: **EP-RANK** | Sprint: **Sprint 1**
> Goal: Har candidate ka ek combined score (CV + interview) jo recruiter ko unified ranked shortlist de.

---

## ✅ EP-RANK-BE-001 — Composite Score (pure function)

**Ticket:** Pure fn `compute_composite(fit_percent, interview_score)` returning `{composite_score, score_breakdown}`. Weights env se (`RANK_CV_WEIGHT`=0.4, `RANK_INTERVIEW_WEIGHT`=0.6), normalised to 1.0. Clamp 0-100. Interview None → CV-only. No DB, no side effects.

**Status:** ✅ Done | ETA 2h

**Implemented:**
- New file `ranking_agent.py` with pure `compute_composite()`.
- Weights read **only from `.env`** (no hardcoded defaults) — missing/invalid env raises a clear error.
- Normalises weights to sum 1.0; clamps result 0-100.
- Interview `None` → CV-only scoring (weights `cv:1.0, interview:0.0`) so half-scored candidates can't outrank interviewed ones.
- Added to `.env`: `RANK_CV_WEIGHT=0.4`, `RANK_INTERVIEW_WEIGHT=0.6`.

**Verified:** `(80,67)→72.2`, `(90,None)→90`, `(120,-5)→40` (clamp).

---

## ✅ EP-RANK-BE-002 — Recommendation label + Hybrid red flags

**Ticket:** Pure fn `recommend(composite_score, red_flags)` → strong_yes (>=80) / yes (>=65) / maybe (>=50) / no. Red flags non-empty → downgrade: "review" if score>=70 else "no". Guard on empty input.

**Status:** ✅ Done | ETA 1h

**Implemented:**
- `recommend()` pure function with 4-tier bands + red-flag downgrade + None guard (returns "no").
- **Hybrid red flags** (extra scope, agreed): two sources combined —
  - `voice_agent.py` `_score_interview()` now returns `{"score", "red_flags"}` — LLM lists interview behaviour flags (evasive, skill mismatch vs CV, no concrete example). Added `_parse_score_payload()` for safe JSON parsing.
  - `ranking_agent.py` `detect_rule_flags(candidate)` — deterministic rule flags from env thresholds (`RULE_MIN_EXPERIENCE_YEARS`, `RULE_WEAK_CV`, `RULE_WEAK_INTERVIEW`).
- `record_call_result()` combines both flag sources, computes composite + recommendation, and stores `interview_red_flags`, `red_flags`, `composite_score`, `recommendation` on `screened_candidates`.
- Added to `.env`: `RULE_MIN_EXPERIENCE_YEARS=0`, `RULE_WEAK_CV=40`, `RULE_WEAK_INTERVIEW=40`.

**Verified (real LLM):** strong candidate → strong_yes; weak → no (LLM + rule flags); decent-but-evasive → no (LLM caught the gap). Test in `test_ranking_flow.py`.

---

## ✅ EP-RANK-BE-003 — Module self-test block

**Ticket:** Add `if __name__ == "__main__"` block exercising compute_composite happy path, None-interview CV-only path, and recommend across strong_yes / review (with flag) / no. Per repo convention. No DB required.

**Status:** ✅ Done | ETA 0.5h

**Implemented:**
- Self-test block in `ranking_agent.py` with **assertions** (not just prints) so a broken function fails loudly.
- Covers: composite happy path, composite CV-only path, recommend strong_yes / review (flagged) / no.
- Runs DB-free via `python ranking_agent.py`.

**Verified:** All self-tests passed.

---

## ✅ EP-RANK-BE-004 — Persist ranked shortlist (rank_candidate)

**Ticket:** Collection helpers (`_get_db/_candidates/_screened/_insights/_ranked`) matching shortlisting_agent lazy-singleton. `rank_candidate(cv_id)`: read fit_percent (candidates_info) + interview_score (screened_candidates) + red_flags/key_strengths (interview_insights); compute composite + recommendation; upsert `ranked_candidates` doc {_id, jd_id, name/email/phone, composite_score, score_breakdown, recommendation, red_flags, key_strengths, interview_status, ranked_at}; mirror composite_score+recommendation onto candidates_info. Guard-clause None on unknown cv_id. Idempotent.

**Status:** ✅ Done | ETA 3h

**Implemented:**
- Lazy-singleton DB helpers added to `ranking_agent.py`: `_get_db`, `_candidates`, `_screened`, `_insights`, `_ranked` (matches shortlisting_agent pattern).
- `rank_candidate(cv_id)`:
  - Guard clause: unknown cv_id → `None`.
  - Reads fit_percent (candidates_info), interview_score + combined red_flags (screened_candidates), key_strengths (interview_insights).
  - **red_flags = Option C:** reuses the LLM+rule combined `red_flags` stored on `screened_candidates` by BE-002; falls back to `detect_rule_flags()` when never interviewed.
  - `interview_status` = screened.status, else `"not_interviewed"`.
  - Upserts the `ranked_candidates` doc (replace_one upsert → idempotent).
  - Mirrors composite_score + recommendation onto candidates_info.
- New collection: `ranked_candidates` (recruiter pulls the per-job ranked shortlist from here).

**Verified (DB-backed test, `test_rank_candidate.py`):** unknown id → None; interviewed → composite 72.2 / recommendation "review" (flag) / persisted + mirrored; idempotent (no duplicate on re-run); not-interviewed → CV-only 30.0 + rule-flag fallback. All passed.

---

## ✅ EP-RANK-BE-005 — Ranked shortlist query (rank_for_jd)

**Ticket:** Implement `rank_for_jd(jd_id, top_n=None)` returning ranked_candidates for the job sorted by composite_score descending, each annotated with a 1-based `rank` field; top_n caps the list, omitting returns the full list.

**Status:** ✅ Done | ETA 2h

**Implemented:**
- `rank_for_jd(jd_id, top_n=None)` in `ranking_agent.py` (Approach A — DB-side sort):
  - `_ranked().find({jd_id}).sort("composite_score", -1)` — MongoDB does the sort (efficient + cloud-friendly: less data transferred).
  - `top_n` applied via `.limit()` at the DB level when `> 0`; omitted → full list.
  - Each doc annotated with 1-based `rank` (1 = highest composite); `_id` stringified for API/JSON readiness.
  - Unknown/empty job → `[]`.

**Verified (DB-backed test, `test_rank_for_jd.py`):** empty job → []; full list sorted desc with ranks [1,2,3] and stringified _id; top_n=2 caps correctly. All passed.

---

## ✅ EP-RANK-BE-006 — Ranked-candidates API endpoint

**Ticket:** Add GET /ranked-candidates to app.py (query params jd_id, optional top_n, skip/limit pagination consistent with /shortlisted-candidates). Add a RankedListResponse Pydantic model to schemas.py. Return ranked records highest-composite-first.

**Status:** ✅ Done | ETA 3h

**Implemented:**
- `RankedListResponse` (items/total/skip/limit) added to `schemas.py`, consistent with CandidateListResponse/JobListResponse.
- `GET /ranked-candidates` added to `app.py`:
  - Params: `jd_id` (required), `top_n` (optional, ≥1), `skip` (≥0), `limit` (1-100) — matches /shortlisted-candidates conventions.
  - Reuses `rank_for_jd(jd_id, top_n)` (BE-005), then paginates the result with `skip`/`limit`.
  - `top_n` caps the ranked pool; pagination applies within it; the 1-based `rank` is global across the pool (stays correct across pages).
  - `total` = full ranked pool size.

**Verified (FastAPI TestClient, `test_ranked_endpoint.py`, lifespan/background loops disabled):** empty job → 200 empty; sorted desc with ranks [1,2,3]; pagination skip=1/limit=1 → Sara with global rank 2; top_n=2 caps; missing jd_id → 422. All passed.

---

## ✅ EP-RANK-BE-007 — On-demand re-rank endpoint

**Ticket:** Add POST /jobs/{jd_id}/rerank to app.py that recomputes every ranked_candidates record for the JD using the current env weights; optionally accept {cv_weight, interview_weight} in the request body to override for that run. Returns the refreshed ranked shortlist.

**Status:** ✅ Done | ETA 2h

**Implemented:**
- Weight override threaded cleanly (Approach A — no env mutation):
  - `_read_weights(cv_override, interview_override)` uses explicit weights when both given, else env.
  - `compute_composite(..., cv_weight=None, interview_weight=None)` and `rank_candidate(cv_id, cv_weight=None, interview_weight=None)` pass overrides through.
- `rerank_jd(jd_id, cv_weight=None, interview_weight=None)` in `ranking_agent.py`: re-runs `rank_candidate` for every already-ranked candidate of the JD (CV + interview scores reused, only the blend changes), returns refreshed `rank_for_jd` list.
- `RerankRequest` (optional cv_weight/interview_weight, ge=0) added to `schemas.py`.
- `POST /jobs/{jd_id}/rerank` added to `app.py`: optional body overrides weights for that run only (.env untouched); returns RankedListResponse.

**Verified (`test_rerank.py`, TestClient, no lifespan):** weight override changes composite (env 72.0 vs 0.8/0.2 → 84.0); rerank interview-heavy → interview-strong candidate tops; rerank CV-heavy → CV-strong tops; POST endpoint with body re-ranks correctly; POST with no body uses env weights (200). Regression: self-test + BE-004/005 still pass.

**🎉 EP-RANK epic complete (BE-001 → BE-007).**

---

# EP-PIPE — Cohesive LangGraph Pipeline (Sprint 2)

## ✅ EP-PIPE-BE-001 — Define shared pipeline state

**Ticket:** New module pipeline.py. Define PipelineState TypedDict: cv_id, jd_id, profile fields (name/email/phone/experience/education/raw_cv_text), fit_percent, call_id/transcript/summary/interview_score/call_category, booking_token/selected_slot/meet_link, composite_score/recommendation, stage/status. Must be JSON-serialisable so the checkpointer can persist it.

**Status:** ✅ Done | ETA 3h

**Implemented:**
- New `pipeline.py` with `PipelineState(TypedDict, total=False)` — all ticket fields grouped by stage (identity, profile, matching, interview, booking, ranking, tracking).
- All values JSON-simple (str/int/float/list/None) so the checkpointer can persist/resume across interview & booking interrupts.
- Stage/status string constants (STAGE_*, STATUS_*) so nodes don't hardcode strings.
- `new_state(cv_id, jd_id)` helper to create a fresh active state.

**Verified (`python pipeline.py`):** state round-trips through `json.dumps`/`loads` (serialisable), fields present, stage default correct. Self-test passed.

---

## ✅ EP-PIPE-BE-002 — Checkpointer + graph factory

**Ticket:** Add create_pipeline_agent() that compiles an (initially empty) StateGraph over PipelineState with a SQLite checkpointer, falling back to InMemorySaver on failure — reuse the pattern from job_post.py:_build_checkpointer (separate sqlite file, e.g. pipeline_checkpoints.sqlite).

**Status:** ✅ Done | ETA 2h

**Implemented:**
- `_build_checkpointer()` in `pipeline.py` — mirrors `job_post.py` pattern: `SqliteSaver` on `pipeline_checkpoints.sqlite` (separate from job_post's file), falls back to `InMemorySaver` on any failure. Module-level `_checkpointer` built once.
- `create_pipeline_agent()` — compiles a `StateGraph(PipelineState)` with the checkpointer. Since LangGraph can't compile a truly empty graph, it holds a single `_passthrough` placeholder node (entry → END) that real nodes (parse→match→interview→book→rank) will replace from BE-003 onward.

**Verified (`python pipeline.py`):** agent compiles with `SqliteSaver` attached; `invoke(new_state(...))` round-trips state through the checkpointer (cv_id/stage preserved). Self-test passed.

---

## ✅ EP-PIPE-BE-003 — Parse CV node

**Ticket:** Add parse_cv node wrapping parser_agent.process_cv(pdf_path, jd_id); populate the profile fields of PipelineState from the returned candidate dict. Node runs in the first invoke before any interrupt, so the temp PDF path is valid. Set entry point to parse_cv.

**Status:** ✅ Done | ETA 3h

**Implemented:**
- Added `pdf_path` input field to `PipelineState` (set at launch, consumed by parse_cv).
- `parse_cv(state)` node: thin wrapper over `parser_agent.process_cv(pdf_path, jd_id)`; maps the returned `{id, data}` into state — cv_id, name, email, phone, experience_years, last_education_degree, raw_cv_text — and advances `stage` to `match`.
- `create_pipeline_agent()` now uses `parse_cv` as the entry point (placeholder removed); `parse_cv → END` for now (match node wired in BE-004).
- Decision: candidates_info sync deferred to BE-004 (match node) per ticket scope.

**Verified (`python pipeline.py`, process_cv monkeypatched — no real PDF/LLM):** invoking the graph runs parse_cv, populates profile fields + cv_id, and advances stage to `match`. Self-test passed.

---

## ✅ EP-PIPE-BE-004 — Match node

**Ticket:** Add match node wrapping shortlisting_agent._score_candidate_against_jd(candidate, jd_text) (load jd_text from job_descriptions by jd_id); write fit_percent into both PipelineState and candidates_info to keep the existing dashboards in sync.

**Status:** ✅ Done | ETA 2h

**Implemented:**
- `match(state)` node: loads jd_text from `job_descriptions` by jd_id, builds a candidate dict from state, calls `_score_candidate_against_jd` → fit_percent.
- Writes fit_percent into the pipeline state **and** upserts it (with the profile: jd_id, name, email, phone, experience, education) onto `candidates_info` so existing dashboards stay in sync.
- Wired into the graph: `parse_cv → match → END` (CV-fit router added in BE-005).

**Verified (`python pipeline.py`, scorer + DB helpers monkeypatched):** graph runs parse_cv → match; fit_percent lands in state (75) and the candidates_info update is captured with the correct _id + fit_percent. Self-test passed.

---

## ✅ EP-PIPE-BE-005 — CV-threshold router + reject node

**Ticket:** Add conditional edge route_after_match: fit_percent >= VOICE_CALL_THRESHOLD (env) routes to start_interview, otherwise to a terminal reject node that records status="rejected_cv" and ends. Read the threshold from env, no hardcode.

**Status:** ✅ Done | ETA 2h

**Implemented:**
- `route_after_match(state)` — reads `VOICE_CALL_THRESHOLD` from env (no hardcode); returns `"start_interview"` if fit_percent ≥ threshold else `"reject"`.
- `reject(state)` terminal node → sets `status="rejected_cv"` → END.
- Placeholder `start_interview(state)` node (sets stage=interview) so the graph compiles; replaced by the real Vapi interview node in BE-006.
- Wired via `add_conditional_edges("match", route_after_match, {...})`; both targets edge to END for now.

**Verified (`python pipeline.py`):** high fit (75 ≥ 70) routes to start_interview (stage=interview, not rejected); low fit (40 < 70) routes to reject (status=rejected_cv). Self-test passed.

---

## ✅ EP-PIPE-BE-006 — Interview node + interrupt (highest-risk)

**Ticket:** Add start_interview node: call _initiate_vapi_call(phone_e164), insert the screened_candidates row (status="calling") exactly as call_top_candidates does today, then interrupt() to suspend the graph until the Vapi webhook arrives.

**Status:** ✅ Done | ETA 4h

**Implemented:**
- Real `start_interview(state)` node (replaced the BE-005 placeholder): normalises phone (`_normalize_phone`), starts the call (`_initiate_vapi_call`), inserts the `screened_candidates` row (status="calling", call_id, cv_id, profile) with the same shape as `call_top_candidates`, then `interrupt()` suspends the graph until the webhook resumes (BE-007).
- **Re-call guard:** LangGraph re-runs a node from the top on resume, so the call + insert are guarded by an existing-row check (`_screened().find_one`) — the candidate is never called twice.
- Phone-invalid / no call_id → `status="rejected_cv"` (no interrupt).
- On resume the interrupt payload (transcript/summary/end_reason) is written into state for the scoring node (BE-008).

**Verified (`python pipeline.py`, voice_agent monkeypatched — no real Vapi/Mongo):** high fit runs parse→match→start_interview, initiates the Vapi call, inserts the calling row, and the graph **suspends** at the interrupt (`get_state().next == ('start_interview',)`); low fit still routes to reject. Self-test passed.

---

## ✅ EP-PIPE-BE-007 — Webhook resume wiring

**Ticket:** Modify POST /voice/webhook in app.py to resolve cv_id via screened_candidates.call_id and resume the graph thread with Command(resume={transcript, summary, end_reason, duration}) instead of calling record_call_result directly. Guard unknown/duplicate call_id (no crash). No regression to the status="calling" insert.

**Status:** ✅ Done | ETA 4h

**Implemented:**
- `start_interview` now stores the graph's `thread_id` (from node `config`) on the screened_candidates row, so the webhook can map call_id → thread.
- `/voice/webhook` (app.py): after parsing the Vapi report, looks up the screened row by call_id and resumes the graph via `Command(resume={transcript, summary, end_reason, duration})` on that thread (lazy global pipeline agent `_get_pipeline_agent()`).
- Guards: unknown call_id → `{error: "unknown call_id"}` (no crash); duplicate webhook → `get_state().next` empty → `{duplicate: true}` (no double-resume); rows without thread_id (legacy/test-call) → fall back to `record_call_result` (no regression).

**Verified (`test_pipeline_webhook.py`, TestClient, mocks for Vapi/scorer/DB):** unknown call_id guarded; launching a candidate pauses at interview with thread_id on the screened row; posting the end-of-call webhook resumes the graph past the interrupt (transcript lands in state); duplicate webhook guarded. All passed.

---

## ✅ EP-PIPE-BE-008 — Interview scoring node

**Ticket:** Add score_interview node (resume target): categorize_call, then _score_interview(transcript, summary, job_desc) and extract_interview_insights; persist interview_score, call_category and insights with parity to the current record_call_result behaviour.

**Status:** ✅ Done | ETA 3h

**Implemented:**
- Added `end_reason` + `duration` fields to PipelineState; `start_interview` now stores them from the resume payload (so the scorer can categorise).
- `score_interview(state)` node (runs right after resume): `categorize_call` → call_category; if completed, `_score_interview` (+ `detect_rule_flags` for the hybrid red flags) and `extract_interview_insights`; persists transcript/summary/interview_score/red_flags/status/category_reason to `screened_candidates` and the insights doc to `interview_insights`. Writes interview_score + call_category back to state.
- Booking/ranking intentionally left to separate nodes (BE-010/012); the post-interview router is BE-009.
- Wired: `start_interview → score_interview → END`.

**Verified (`python pipeline.py`, all externals mocked):** resuming the paused graph runs score_interview — call_category=completed, interview_score=82 land in state, and the score + insights are persisted to the (fake) collections. Self-test passed.

---

## ✅ EP-PIPE-BE-009 — Interview-threshold router

**Ticket:** Add route_after_interview: completed AND interview_score >= CALENDAR_THRESHOLD -> book; completed AND below -> rank; not-completed -> reject (keep the call_logs retry path compatible). All three branches reachable.

**Status:** ✅ Done | ETA 2h

**Implemented:**
- `route_after_interview(state)` — reads `CALENDAR_THRESHOLD` from env (no hardcode): not-completed → `reject`; completed & score ≥ threshold → `book`; completed & below → `rank`.
- `reject` node made shared/smart: sets `rejected_interview` when a call_category is present (interview stage), else `rejected_cv` (CV gate).
- Placeholder `book` and `rank` nodes (set stage) so the graph compiles; replaced by the booking-interrupt node (BE-010) and rank_candidate terminal (BE-012).
- Wired `add_conditional_edges("score_interview", route_after_interview, {book, rank, reject})`; legacy call_logs retry loop is untouched (operates on screened_candidates outside the graph).

**Verified (`python pipeline.py`, all 3 branches):** completed+82≥60 → book; completed+40<60 → rank; declined → reject (status=rejected_interview); CV gate low-fit still → rejected_cv. Self-test passed.

---

## ✅ EP-PIPE-BE-010 — Booking node + interrupt

**Ticket:** Add book node: call create_slot_picker_booking(candidate_doc, score) to email the picker link, then interrupt() to suspend until the candidate selects a slot.

**Status:** ✅ Done | ETA 4h

**Implemented:**
- Real `book(state)` node (replaced BE-009 placeholder): builds candidate_doc from state, calls `create_slot_picker_booking(doc, interview_score)` to email the picker link, then `interrupt()` suspends until the slot-select endpoint resumes (BE-011) with selected_slot + meet_link.
- **Re-email guard:** existing pending-booking check (`_bookings().find_one({candidate_id, status: pending})`) prevents a second email when LangGraph re-runs the node on resume.
- **No-hang guard:** if no token (no slots / no email), returns without interrupting so the graph falls through (to ranking) instead of waiting forever.
- On resume, writes booking_token / selected_slot / meet_link into state.

**Verified (`python pipeline.py`, booking_agent mocked):** high-score path emails the picker (token captured) and suspends at `book` (`get_state().next == ('book',)`); resuming with a chosen slot lands booking_token + meet_link in state. Self-test passed.

---

## ✅ EP-PIPE-BE-011 — Slot-select resume + event node

**Ticket:** Modify POST /api/booking/{token}/select to resolve cv_id via the booking token and resume the thread with Command(resume={selected_slot, meet_link}); add create_event node that records meet_link/selected_slot into state (preserve existing select_slot calendar-event behaviour).

**Status:** ✅ Done | ETA 4h

**Implemented:**
- `/api/booking/{token}/select` (app.py): keeps `select_slot(token, slot)` first — the **real Google Calendar event + Meet link creation is preserved**. Then, if `ok`, resolves the pipeline thread: token → `get_booking().candidate_id` → `_screened().thread_id` and resumes with `Command(resume={selected_slot, meet_link})`.
- **No double-resume guard:** only resumes when `get_state().next` is non-empty (still paused at `book`); a duplicate slot-select is a no-op for the graph.
- **No-regression guard:** if the booking has no `thread_id` (legacy booking, not launched via the pipeline), the endpoint skips the resume and returns the result as before.
- New `create_event(state)` node: records `selected_slot` / `meet_link` into state (the real event was already created by `select_slot`). Wiring: `book → create_event → rank` (rank still placeholder until BE-012).

**Verified (`python test_pipeline_booking.py`, TestClient end-to-end):** launch → pause at interview; webhook resume → score 82 → pause at `book`; POST slot-select → `select_slot` mock returns event → graph resumes past `book` → `create_event` records slot + meet link (in state) → reaches `rank`; duplicate slot-select guarded (no re-pause). `pipeline.py` self-test still green.

---

## ✅ EP-PIPE-BE-012 — Ranking terminal node

**Ticket:** Replace the rank placeholder with a terminal node that calls ranking_agent.rank_candidate(cv_id) then END; both the booking path and the below-threshold interview path converge here.

**Status:** ✅ Done | ETA 2h

**Implemented:**
- Real `rank(state)` node (replaced BE-009/010 placeholder): calls `ranking_agent.rank_candidate(state["cv_id"])` (EP-RANK-BE-004) which reads CV match + interview score + combined red flags and upserts the unified `ranked_candidates` doc.
- Mirrors the returned `composite_score` + `recommendation` back into pipeline state and sets `status="completed"`.
- **None-safe:** unknown cv_id → `rank_candidate` returns None → node uses `or {}` so composite/recommendation stay None and the graph still reaches END cleanly (no crash, no hang).
- Default env weights (no override) — the live pipeline uses configured RANK_* weights; the rerank endpoint handles overrides separately.
- Both exits converge at `rank → END`: booked candidates (`book → create_event → rank`) and interviewed-but-below-threshold ones (`route_after_interview → rank`).

**Verified (`python pipeline.py`, rank_candidate mocked):** booking path resumes → `book → create_event → rank` writes composite_score=78.5 + recommendation=yes + status=completed and reaches END; low-score path (40 < threshold) → `rank` → completed. `test_pipeline_booking.py` re-run green (rank_candidate mocked there too). All self-tests passed.

---

## ✅ EP-PIPE-BE-013 — Scheduler launches pipeline

**Ticket:** Refactor _shortlist_loop (app.py) to only detect new applicants (dedup via processed_applications) and launch one graph per candidate; stop calling shortlist_all_jobs / call_top_candidates directly.

**Status:** ✅ Done | ETA 4h

**Conflict fixed:** the old `ingest_new_applicants` itself parsed each CV (`process_cv`) and downloaded into a `TemporaryDirectory` that was deleted immediately — but the pipeline's `parse_cv` node also parses. Running both would parse twice and the temp PDF would already be gone. So ingest was split.

**Implemented:**
- `parser_agent.detect_new_applicants(dest_dir)`: reads the applicants sheet, dedups against `processed_applications`, downloads each NEW CV into `dest_dir` — **no parse, no record**. Returns `[{file_id, jd_id, pdf_path}]`.
- `parser_agent.mark_processed(file_id, jd_id, cv_id)`: records a processed applicant so later ticks skip it.
- `parser_agent.ingest_new_applicants()`: now a backward-compat wrapper (detect → `process_cv` → mark) for the CLI / manual runs.
- `app._launch_pipeline_for_applicant(applicant)`: launches one pipeline graph with a fresh `thread_id` (`pipe-<uuid>`); the first invoke runs `parse_cv` synchronously (temp PDF still alive) up to the interview interrupt; returns the parsed `cv_id`. Resume (webhook / slot-select) is handled by the existing endpoints via the thread_id on the screened row.
- `app._shortlist_loop`: rewritten — each tick `detect_new_applicants` → launch the graph per applicant → `mark_processed` (only on a returned cv_id, so a failed launch retries next tick). **No longer calls** `shortlist_all_jobs` or `call_top_candidates` (the graph does match + interview internally). `_retry_loop` left untouched.

**Verified (`python test_pipeline_scheduler.py`, downstream mocked):** launcher runs parse→match→interview (pauses) and returns cv_id; one loop body (detect → launch → mark) marks exactly once with the cv_id; a failed launch (no cv_id) is NOT marked (retried). `pipeline.py` + `test_pipeline_booking.py` re-run green (no regression).

---

## ✅ EP-PIPE-BE-014 — End-to-end validation harness

**Ticket:** Extend a test_booking_flow.py-style harness: drive one fixture candidate parse→ranked_candidates, simulate the Vapi webhook + slot-pick resumes, and assert existing endpoints are unchanged.

**Status:** ✅ Done | ETA 4h — **EP-PIPE COMPLETE** 🎉

**Implemented:**
- `test_pipeline_e2e.py`: drives ONE fixture candidate through the **whole** graph using the real endpoints (`/voice/webhook`, `/api/booking/{token}/select`, `/ranked-candidates`, `/health`) and the real compiled pipeline — only the external edges are mocked (Drive/Sheets, Vapi, LLM, Mongo via stateful `FakeColl`, Google Calendar).
- 5 stages asserted in order:
  1. **Launch (BE-013 path)** `_launch_pipeline_for_applicant` → parse (cv_id) + match (fit 88) → interview call placed, screened row `status=calling` with thread_id, graph paused.
  2. **Vapi webhook resume (BE-007)** → categorise + score (84) persisted → graph paused at `book`.
  3. **Slot-pick resume (BE-011)** `/api/booking/{token}/select` → `create_event` → `rank` → `status=completed`, meet_link + composite_score in state.
  4. **ranked_candidates persisted (BE-012)** — final shortlist doc written (recommendation `strong_yes`).
  5. **Existing endpoints unchanged** — `/ranked-candidates` returns the candidate (rank=1, total=1); `/health` 200.

**Verified (`python test_pipeline_e2e.py`):** all 5 stages pass — the candidate flows parse→match→interview→book→rank end-to-end with both async resumes, lands in ranked_candidates, and the pre-existing endpoints still behave.

---

## ✅ EP-PIPE-BE-015 — Call-logs + retry parity (gap-fix)

**Context:** An audit of the old `record_call_result` (the pre-pipeline Vapi webhook handler) vs the pipeline's `score_interview` node revealed the pipeline never called `log_call_attempt`. So pipeline candidates produced no `call_logs` entries (breaking `/call-logs`, `/call-stats`, retry endpoints) and **declined calls were never retried** — the graph just rejected them. (Not part of the original sprint backlog; added after the gap was found.)

**Behaviour rules preserved (from `categorize_call`):** completed → no retry; **cancelled** (candidate intentionally hung up / HR cancelled) → no retry; **declined** (no-answer, busy, voicemail, network/system error, accidental cut) → retry up to `MAX_RETRY_ATTEMPTS`.

**Implemented:**
- `score_interview` now calls `log_call_attempt(...)` (audit log + retry scheduling), reading `call_id`/`triggered_by` from the screened row, and returns the resulting `call_log_status` (added `call_log_status` to `PipelineState`). Also writes `vapi_end_reason` + `duration_seconds` to the screened row (metadata parity).
- New `wait_retry` node: a declined call that still has attempts left pauses here via `interrupt()`. The background `_retry_loop → process_retries` re-calls the candidate and updates the screened row's `call_id`; the new call's webhook hits `/voice/webhook`, which resolves the thread and resumes `wait_retry`, looping back to `score_interview` to re-categorise/re-log.
- `route_after_interview` updated: completed → book/rank; declined + `pending_retry` → `wait_retry`; cancelled / exhausted → reject. Graph wiring: `score_interview → wait_retry → score_interview` (loop).

**Verified (`python pipeline.py`):** declined + retriable pauses at `wait_retry`; resuming with another declined exhausts attempts → reject (rejected_interview); cancelled goes straight to reject with no `wait_retry` (no re-call). All 5 pipeline tests green (webhook/booking/e2e tests updated to mock `log_call_attempt`).

---

## ✅ EP-PIPE-BE-016 — Double-booking guard + screened consistency (bug-fix)

Two correctness bugs found by review:

**Issue 1 — Double-booking (booking_agent.select_slot):** the atomic lock was per-token (per-candidate) only; it stopped a candidate double-processing their own booking but did NOT stop two different candidates picking the same HR slot, and `create_calendar_event` inserts the event with no conflict check. Free/busy was checked only when slots were *generated*, not at selection.
- **Fix:** new `calendar_agent.is_slot_free(primary_hr_email, slot_start)` re-queries the HR free/busy for the chosen window. `select_slot` calls it after locking the booking and before creating the event; if the slot is now busy (another candidate or a manual HR event), it releases the booking back to `pending` and returns `{"ok": False, "error": "slot_taken"}` so the candidate can re-pick. This catches both concurrent candidates and external calendar changes.

**Issue 2 — Inconsistent data (pipeline.score_interview):** the node wrote `interview_score`/`red_flags` to `screened_candidates` but not `composite_score`/`recommendation` (those only landed in `ranked_candidates`), so dashboards reading `screened_candidates` showed blanks.
- **Fix:** `score_interview` now also computes `compute_composite` + `recommend` for completed calls and writes `composite_score` + `recommendation` onto the screened row (parity with the old `record_call_result`). The rank node still recomputes the same values when it persists the final shortlist.

**Verified (`python test_booking_double_booking.py`):** slot-free → booked + event created; slot-taken → `slot_taken` returned, booking released to pending, no meeting created. `pipeline.py` self-test asserts the screened row now carries `composite_score` + `recommendation` after scoring. All 6 tests green.

---

## ✅ EP-PIPE-BE-017 — Pakistani phone normalization (bug-fix)

**Issue:** `voice_agent._normalize_phone` produced invalid E.164 for the local PK formats real candidates use. `03001234567` (11 digits, leading national trunk 0) fell into the `11<=len<=15 → "+"+digits` branch and returned `+03001234567` — invalid (an E.164 country code never starts with 0), so Vapi silently rejected the call. The leading trunk `0` was never stripped, and the code default country code was `+1` (US) for a Pakistan-centric app. Masked in tests because every test mocked `_normalize_phone`.

**Implemented (region-aware rules, env-driven, no new dependency):**
- `DEFAULT_COUNTRY_CODE` default changed `+1` → `+92` (still `VAPI_DEFAULT_COUNTRY_CODE`, which the .env already set to +92).
- Rewrote `_normalize_phone`: `+` prefix → validate as-is; `00` → international access prefix stripped; leading `0` → national trunk stripped and country code prepended; bare 10-digit national → country code prepended; a number already carrying the country code (e.g. `92…`, ≥11 digits) → passthrough. Result validated to 11–15 digits else None.
- New `test_normalize_phone.py`: 12 real inputs (PK local/dashes/spaces, intl, 00-prefix, +E.164, too-short/empty/None/non-numeric) asserted directly against the real function (no mock).

**Verified (`python test_normalize_phone.py`):** all of `03001234567`, `3001234567`, `923001234567`, `00923001234567`, `+923001234567`, and spaced/dashed variants → `+923001234567`; junk → None. All 7 project tests green.

---

## ✅ EP-PIPE-BE-018 — Booking resume double-email guard (bug-fix)

**Issue:** the `book` node guards against re-emailing on resume with `_bookings().find_one({"candidate_id": cv_id, "status": "pending"})`. But LangGraph re-runs the node from the top on resume, and by then the slot-select endpoint has already called `select_slot`, flipping the booking `pending → booked` *before* it resumes the graph. So the `"pending"`-only guard found nothing → `create_slot_picker_booking` ran a second time → the candidate got a second slot-picker email and an orphan `pending` booking was created.

**Implemented:**
- Guard now matches any active booking: `{"candidate_id": cv_id, "status": {"$in": ["pending", "processing", "booked"]}}`. On resume it finds the now-`booked` booking, reuses its token, and skips creation — no second email, no orphan.

**Test hardening:** `test_pipeline_booking.py` previously mocked `_bookings().find_one` to always return `None` and `create_slot_picker_booking` as a no-op, which masked the bug. Rewrote with a stateful fake booking store: `create_slot_picker_booking` inserts a `pending` booking and increments a call counter; the `select_slot` mock flips it to `booked` before resume. The test now asserts `create` is called exactly once across the whole flow (would be 2 under the old guard).

**Verified (`python test_pipeline_booking.py`):** book pauses with one email; after slot-select resume the book re-run finds the booked booking and does NOT re-create (`book_calls == 1`); graph completes through create_event → rank. All 7 project tests green.

---

## ✅ EP-RANK-BE-008 — recommend() thresholds → env (config-fix)

**Issue:** `ranking_agent.recommend()` hardcoded the score bands (80/65/50 for strong_yes/yes/maybe and 70 for the red-flag review cutoff), violating CLAUDE.md ("Add all the thresholds in the env") and inconsistent with `detect_rule_flags()` in the same file, which already reads its thresholds from env via `_env_float_or`.

**Implemented:**
- `recommend()` now reads `RECOMMEND_STRONG_YES` (80), `RECOMMEND_YES` (65), `RECOMMEND_MAYBE` (50), `RECOMMEND_REVIEW_MIN` (70) via the existing `_env_float_or` helper (defaults preserve current behaviour).
- Added the four vars to `.env`.

**Verified (`python ranking_agent.py`):** recommend self-tests (strong_yes / review-flagged / no) pass unchanged with defaults. All 8 project tests green.

---

## ✅ EP-PIPE-BE-019 — Interview rubric overlapping bands (prompt-fix)

**Issue:** the `_score_interview` 5-tier scoring rubric (LLM prompt in `voice_agent.py`) had two overlapping bands — `70-84 Strong` and `60-74 Decent` both covered 70-74. A candidate scoring ~72 fits both tiers, giving the LLM an ambiguous signal and producing inconsistent scores for the same interview.

**Implemented:**
- Changed the Decent band `60-74` → `60-69` so the tiers are contiguous and non-overlapping: `0-39` Poor / `40-59` Weak / `60-69` Decent / `70-84` Strong / `85-100` Exceptional.

**Verified:** `voice_agent` imports clean; `test_pipeline_e2e.py` green (prompt-text-only change, no logic affected).

---

## ✅ EP-PIPE-BE-020 — Consolidate scoring/persist (drift fix)

**Issue:** the downstream call-handling logic existed in two parallel implementations — `pipeline.score_interview` (+ book/rank nodes) and the legacy `voice_agent.record_call_result`. They're mutually exclusive at runtime (the `/voice/webhook` handler routes by `thread_id`: present → pipeline resume, absent → record_call_result), so no double-fire — but the duplicated orchestration had already drifted three times (retry/log_call_attempt missing in pipeline → BE-015; composite/recommendation on screened missing → BE-016; and `record_call_result` never called `rank_candidate`, so legacy candidates never reached `ranked_candidates`). Every fix risked being applied to one path and forgotten on the other.

**Implemented:**
- Extracted `voice_agent.score_and_persist_call(doc, transcript, summary, end_reason, duration)` as the single source of truth for the identical portion: categorize → `log_call_attempt` (audit + retry scheduling) → `_score_interview` → hybrid red flags → `compute_composite` + `recommend` → persist to `screened_candidates` (incl. composite/recommendation/interview_red_flags/completed_at) + `interview_insights` (full metadata). Returns `{category, reason_label, interview_score, red_flags, composite_score, recommendation, call_log_status}`.
- `pipeline.score_interview` is now a thin wrapper: builds the doc from the screened row (falling back to state) and calls the helper; returns `interview_score` / `call_category` / `call_log_status` for routing. The retry/wait_retry routing and book/rank nodes are unchanged.
- `record_call_result` is now a thin wrapper: delegates to the helper, then does its legacy fire-and-forget booking email and — newly — calls `rank_candidate(cv_id)` so legacy candidates also land in `ranked_candidates` (last divergence removed).
- Control-flow that genuinely differs (pipeline pauses at the booking interrupt; legacy fires the email and returns) stays per-path; only the identical scoring+persist is shared.

**Verified (`python pipeline.py` + full suite):** pipeline self-test (completed/declined-retry/cancelled branches) and all 8 project tests green — both paths now run the same persistence logic.

---

## ✅ EP-PIPE-BE-021 — ASR-error robustness in scoring prompt (prompt-fix)

**Issue:** interview scores were coming out poor even with a transcript present, because the Vapi automated speech-to-text mishears words on phone calls — especially technical terms ("LangChain" → "Langkang", "Postgres" → "Fortress", "FastAPI" → "Fast AP"). The scoring LLM was judging a garbled transcript, so real skills weren't credited.

**Implemented:**
- Added an `ASR TRANSCRIPTION ERRORS — CRITICAL` block to the `_score_interview` prompt instructing the model to correct common phonetic corruptions before scoring, treat dropped-audio sentences as partial answers (not silence), ignore fillers/stutters, and not penalize ASR errors.
- Included a guardrail against over-correction: only map a word to a technology when the context is clearly about tools/skills; do NOT invent a tech from a common English word ("react to", "tensor", "go") or fabricate skills the candidate didn't mention.

**Note:** the root cause is upstream STT quality — the higher-leverage fix is in the Vapi assistant config (keyterm/keyword boosting for tech terms + a better transcriber model like Deepgram nova-2), which is dashboard-side and owned by the user. This prompt change is the code-side safety net.

**Verified:** `voice_agent` imports clean; `test_pipeline_e2e.py` green (prompt-text-only change).

---

## ✅ EP-PIPE-BE-022 — Scoring model env-driven, upgraded to gpt-4o (config-fix)

**Issue:** the interview-scoring LLM was hardcoded to `gpt-4o-mini` in `_score_interview`. A stronger model reasons better over noisy ASR transcripts (pairs with BE-021), and hardcoding violated CLAUDE.md ("prefer configuration over hardcoding").

**Implemented:**
- `_score_interview` now uses `init_chat_model(os.getenv("SCORING_MODEL", "gpt-4o"), temperature=0)`.
- Added `SCORING_MODEL=gpt-4o` to `.env`.
- Confirmed the configured `OPENAI_API_KEY` can call `gpt-4o` (live test call returned "OK") — no separate subscription needed; the OpenAI API is pay-per-use and gpt-4o shares the same key as gpt-4o-mini.

**Verified:** live gpt-4o call succeeded; all pipeline tests green (the scoring LLM is mocked in tests, so the model string is not exercised there).

---

## ✅ EP-PIPE-BE-023 — Pre-interview reminder (8h before) (feature)

**Goal:** email both the candidate and the HR/team members ~8 hours before a scheduled Google Meet interview.

**Design decision:** this is NOT a pipeline graph node. The pipeline ends at `rank` shortly after booking, but the interview is days later, and the reminder is a wall-clock (time-based) trigger — LangGraph interrupts wait on events, not timers. So it's a separate background loop, mirroring the existing `_retry_loop`, driven by the `meetings` collection.

**Implemented:**
- `booking_agent.send_due_reminders()`: scans `meetings` for `status="scheduled"`, `reminder_sent != True`, and `meeting_time` within `now .. now + REMINDER_HOURS_BEFORE` (8h, env). Emails candidate + all `hr_attendees` (deduped) via `email_agent.send_email` with a reminder body (`_render_reminder`: time, timezone, Meet link), then sets `reminder_sent`/`reminder_sent_at` so each meeting is reminded exactly once.
- `app._reminder_loop`: new background task in the lifespan (every `REMINDER_LOOP_INTERVAL_SECONDS`=900), calls `send_due_reminders` off-thread — same shape as `_retry_loop`.
- `booking_agent.select_slot`: the meetings doc now initializes `reminder_sent: False`.
- `.env`: `REMINDER_HOURS_BEFORE=8`, `REMINDER_LOOP_INTERVAL_SECONDS=900`.

**Verified (`python test_reminder.py`):** of three meetings (due-in-3h / far-20h / already-sent), exactly the due one is reminded; the email goes to candidate + both HR/team members (deduped); `reminder_sent` is set so a second tick sends 0. All 8 project tests green.

---

## ✅ EP-PIPE-BE-024 — Skip non-PDF uploads (runtime fix)

**Issue:** during live testing a candidate (hamza.a@tekhqs.com) submitted a `.txt` file (92 bytes) instead of a PDF via the Google Form. `_download_drive_pdf` saved it as `.pdf`, then `process_cv` → fitz raised `FileDataError` on every scheduler tick — because a failed launch never calls `mark_processed`, so the bad file was re-detected and re-attempted forever (log spam). Not a regression from BE-013 — the old `ingest_new_applicants` would fail identically; it's a data/format problem.

**Implemented:**
- `parser_agent.detect_new_applicants` now fetches the Drive file `mimeType` (`files().get`) before downloading. If it isn't `application/pdf`, it logs the skip, calls `mark_processed(file_id, jd_id, status="skipped_not_pdf")`, and continues — so the junk file never enters the pipeline and is never retried.
- `parser_agent.mark_processed` gained a `status` param (`"processed"` | `"skipped_not_pdf"`) and a nullable `cv_id`.

**Verified:** `parser_agent` imports clean; scheduler/pipeline/e2e tests green. The previously-stuck `.txt` self-heals on the next tick (gets recorded as skipped, no more errors).

---

## ✅ EP-PIPE-BE-025 — Calendar invite leaked score/salary (privacy-fix)

**Issue:** `calendar_agent._build_description` wrote the interview into the calendar event description as "Voice screening complete. Score: 60/100" plus expected salary and notice period. Because the **candidate is an attendee** on that event (along with HR/team), the invite exposed internal evaluation data — the candidate could see their own screening score and the recruiter's notes on their salary.

**Implemented:**
- Removed score, expected_salary, and notice_period from the event description. It now reads "Technical interview." + neutral, candidate-safe context (current role / company / years of experience / tech stack) + "Please be prepared." The `score` arg is kept for backward compatibility but no longer rendered.
- HR still sees the score/recommendation in `screened_candidates` / `ranked_candidates` (dashboard), not in the shared invite.

**Note (related, not code):** the invite time showing "5am UTC" is correct — that's 10am Asia/Karachi (UTC+5); the Google account's calendar timezone is set to UTC, so set it to Asia/Karachi to display PKT. The event is created with the correct Asia/Karachi timezone.

**Verified:** `calendar_agent` imports clean; `_build_description(60, {...salary...})` no longer contains the score/salary/notice — only role + tech stack.

---

## 📁 Files Touched (so far)

| File | Change |
|------|--------|
| `ranking_agent.py` | New — compute_composite, recommend, detect_rule_flags, self-test, DB helpers, rank_candidate, rank_for_jd |
| `voice_agent.py` | _score_interview returns score+flags; record_call_result stores composite/recommendation/flags |
| `.env` | RANK_* weights + RULE_* thresholds + RECOMMEND_* score bands |
| `test_ranking_flow.py` | New — end-to-end hybrid flow test |
| `test_rank_candidate.py` | New — DB-backed rank_candidate test (guard, idempotent, mirror, not-interviewed) |
| `test_rank_for_jd.py` | New — DB-backed rank_for_jd test (sort order, rank field, top_n, empty) |
| `schemas.py` | Added RankedListResponse |
| `app.py` | Added GET /ranked-candidates + POST /jobs/{jd_id}/rerank endpoints |
| `test_ranked_endpoint.py` | New — TestClient test for /ranked-candidates (sort, pagination, top_n, 422) |
| `schemas.py` | Added RerankRequest |
| `test_rerank.py` | New — TestClient test for rerank (weight override, endpoint, env default) |
| `pipeline.py` | New — state (BE-001); checkpointer+factory (BE-002); parse_cv (BE-003); match (BE-004); router + reject (BE-005); start_interview + interrupt + thread_id (BE-006/007); score_interview (BE-008); route_after_interview (BE-009); book node + interrupt (BE-010); create_event node + book→create_event→rank wiring (BE-011); rank terminal node calls rank_candidate→END (BE-012); log_call_attempt + wait_retry node + retry routing loop (BE-015) |
| `app.py` | /voice/webhook resumes pipeline graph via Command(resume) + guards/fallback (BE-007); /api/booking/{token}/select resumes booking thread after select_slot (BE-011); _shortlist_loop rewritten to detect→launch pipeline→mark per applicant + _launch_pipeline_for_applicant helper (BE-013) |
| `parser_agent.py` | Split ingest: detect_new_applicants (download only) + mark_processed; ingest_new_applicants now a backward-compat wrapper (BE-013) |
| `test_pipeline_webhook.py` | New — TestClient end-to-end interrupt→resume test (BE-007) |
| `test_pipeline_booking.py` | New — TestClient end-to-end slot-select→resume test (BE-011) |
| `test_pipeline_scheduler.py` | New — scheduler detect→launch→mark test (BE-013) |
| `test_pipeline_e2e.py` | New — full end-to-end harness: one candidate parse→ranked_candidates + both resumes + endpoints unchanged (BE-014) |
| `calendar_agent.py` | Added is_slot_free (free/busy re-check at selection) (BE-016) |
| `booking_agent.py` | select_slot re-verifies is_slot_free before event; slot_taken → release + reject (BE-016) |
| `test_booking_double_booking.py` | New — double-booking prevention test (BE-016) |
| `voice_agent.py` | _normalize_phone rewritten region-aware (PK trunk-0/00/bare/CC); default +92 (BE-017); score_and_persist_call shared helper, record_call_result slimmed + rank_candidate (BE-020) |
| `test_normalize_phone.py` | New — 12 real-input phone cases, no mock (BE-017) |
| `booking_agent.py` | select_slot free/busy re-check (BE-016); reminder_sent init + send_due_reminders + _render_reminder (BE-023) |
| `app.py` | _reminder_loop background task + lifespan wiring (BE-023) |
| `parser_agent.py` | detect_new_applicants skips non-PDF uploads + mark_processed status (BE-024) |
| `calendar_agent.py` | is_slot_free free/busy re-check (BE-016); _build_description candidate-safe — no score/salary (BE-025) |
| `test_reminder.py` | New — pre-interview reminder window/dedup/recipients test (BE-023) |
