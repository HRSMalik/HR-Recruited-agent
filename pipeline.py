"""Shared state for the end-to-end candidate pipeline (Agents 2-5).

`PipelineState` is the single object that flows through the LangGraph pipeline:
each node (parse -> match -> interview -> book -> rank) fills in its own fields.
All values are JSON-simple (str/int/float/list/dict/None) so the checkpointer can
persist and resume the graph across the async interview/booking interrupts.

This ticket only defines the state shape — nodes/graph come in later tickets.
"""
import os
import sqlite3
import sys

from typing import Optional, TypedDict

import config

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt


class PipelineState(TypedDict, total=False):
    # --- identity ---
    cv_id: str
    jd_id: str

    # --- input (set at launch; consumed by parse_cv) ---
    pdf_path: Optional[str]

    # --- profile (filled by parse_cv node) ---
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    experience_years: Optional[float]
    last_education_degree: Optional[str]
    raw_cv_text: Optional[str]

    # --- matching (filled by match node) ---
    fit_percent: Optional[int]

    # --- interview (filled by start_interview / score_interview nodes) ---
    call_id: Optional[str]
    transcript: Optional[str]
    summary: Optional[str]
    end_reason: Optional[str]
    duration: Optional[int]
    tone: Optional[str]  # live, from the realtime agent's own audio perception
    live_red_flags: Optional[list]  # live, from the realtime agent's own assessment
    interview_score: Optional[int]
    call_category: Optional[str]
    call_log_status: Optional[str]  # closed | pending_retry | exhausted (from log_call_attempt)

    # --- booking (filled by book / create_event nodes) ---
    booking_token: Optional[str]
    selected_slot: Optional[str]
    meet_link: Optional[str]

    # --- ranking (filled by rank terminal node) ---
    composite_score: Optional[float]
    recommendation: Optional[str]

    # --- tracking ---
    stage: str   # parse | match | interview | book | rank
    status: str  # active | rejected_cv | rejected_interview | completed


# Stage/status constants so nodes don't hardcode strings.
STAGE_PARSE = "parse"
STAGE_MATCH = "match"
STAGE_INTERVIEW = "interview"
STAGE_BOOK = "book"
STAGE_RANK = "rank"

STATUS_ACTIVE = "active"
STATUS_REJECTED_CV = "rejected_cv"
STATUS_REJECTED_INTERVIEW = "rejected_interview"
STATUS_COMPLETED = "completed"


def new_state(cv_id: str, jd_id: str) -> PipelineState:
    """Create a fresh state for a candidate entering the pipeline."""
    return {"cv_id": cv_id, "jd_id": jd_id, "stage": STAGE_PARSE, "status": STATUS_ACTIVE}


def _build_checkpointer():
    """SQLite checkpointer for pipeline state; falls back to in-memory on failure.

    Mirrors job_post.py:_build_checkpointer but uses a separate sqlite file so
    the two graphs don't share checkpoint storage.
    """
    db_path = os.path.join(os.path.dirname(__file__), "pipeline_checkpoints.sqlite")
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore

        conn = sqlite3.connect(db_path, check_same_thread=False)
        saver = SqliteSaver(conn)
        saver.setup()
        return saver
    except Exception as e:  # noqa: BLE001
        print(f"using in-memory saver. SqliteSaver unavailable: {e!r}", file=sys.stderr)
        return InMemorySaver()


_checkpointer = _build_checkpointer()


def parse_cv(state: PipelineState) -> PipelineState:
    """Parse the applicant's CV and populate the profile fields of the state.

    Thin wrapper over `parser_agent.process_cv`, which generates the cv_id and
    extracts the candidate dict. Runs in the first invoke (before any interrupt),
    so the temp PDF path in `state["pdf_path"]` is still valid.
    """
    from parser_agent import process_cv

    result = process_cv(state["pdf_path"], state.get("jd_id"))
    data = result.get("data", {})
    return {
        "cv_id": result["id"],
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "experience_years": data.get("experience_years"),
        "last_education_degree": data.get("last_education_degree"),
        "raw_cv_text": data.get("raw_cv_text"),
        "stage": STAGE_MATCH,
    }


def match(state: PipelineState) -> PipelineState:
    """Score the parsed CV against confirmed JD criteria and record fit_percent."""
    from shortlisting_agent import (
        _score_candidate, _job_criteria, _job_descriptions, _candidates,
    )

    jd_id = state.get("jd_id")
    criteria_doc = _job_criteria().find_one({"_id": jd_id})
    if not criteria_doc or criteria_doc.get("status") != "confirmed":
        raise ValueError(f"No confirmed criteria for jd_id={jd_id!r}. Confirm criteria before scoring.")
    criteria = criteria_doc.get("criteria", [])

    jd_doc = _job_descriptions().find_one({"_id": jd_id})
    jd_text = (jd_doc or {}).get("job_description", "")

    candidate = {
        "name": state.get("name"),
        "email": state.get("email"),
        "experience_years": state.get("experience_years"),
        "freelance_experience_years": state.get("freelance_experience_years"),
        "last_education_degree": state.get("last_education_degree"),
        "raw_cv_text": state.get("raw_cv_text"),
    }
    # Flag before the LLM scoring calls (which take several seconds) so the
    # Candidates page can show this one as actively being processed, not just queued.
    _candidates().update_one({"_id": state["cv_id"]}, {"$set": {"processing": True}}, upsert=True)
    payload = _score_candidate(candidate, criteria, jd_text)

    _candidates().update_one(
        {"_id": state["cv_id"]},
        {"$set": {
            "jd_id": jd_id,
            "name": state.get("name"),
            "email": state.get("email"),
            "phone": state.get("phone"),
            "experience_years": state.get("experience_years"),
            "last_education_degree": state.get("last_education_degree"),
            **payload,
            "processing": False,
        }},
        upsert=True,
    )
    return {"fit_percent": payload["fit_percent"]}


def route_after_match(state: PipelineState) -> str:
    """Route by CV fit: strong enough → interview, otherwise → reject.

    Threshold comes from config.VOICE_CALL_THRESHOLD, never hardcoded.
    """
    threshold = config.VOICE_CALL_THRESHOLD
    if (state.get("fit_percent") or 0) >= threshold:
        return "start_interview"
    return "reject"


def reject(state: PipelineState) -> PipelineState:
    """Terminal reject node, shared by the CV gate and the interview gate.

    A call_category present means the candidate reached the interview, so the
    rejection is interview-stage; otherwise it's the earlier CV-fit gate.
    """
    if state.get("call_category"):
        return {"status": STATUS_REJECTED_INTERVIEW}
    return {"status": STATUS_REJECTED_CV}


def route_after_interview(state: PipelineState) -> str:
    """Route by interview outcome.

    completed                  -> book (strong) or rank (weak), CALENDAR_THRESHOLD env.
    no_show / incomplete       -> wait_retry (pause for a fresh interview invite).
    retries exhausted          -> reject (no further invites).

    log_call_attempt schedules no_show/incomplete attempts as pending_retry until
    MAX_RETRY_ATTEMPTS, then marks them exhausted.
    """
    if state.get("call_category") == "completed":
        threshold = config.CALENDAR_THRESHOLD
        return "book" if (state.get("interview_score") or 0) >= threshold else "rank"
    if state.get("call_log_status") == "pending_retry":
        return "wait_retry"
    return "reject"


def book(state: PipelineState) -> PipelineState:
    """Email the slot-picker link, then suspend until the candidate picks a slot.

    Wraps booking_agent.create_slot_picker_booking, then `interrupt()` pauses the
    graph until the slot-select endpoint resumes the thread (BE-011) with the
    chosen slot + Meet link.

    Guarded by an existing-booking check because LangGraph re-runs the node from
    the top on resume — without it the candidate would be emailed twice. The guard
    matches any active booking (pending/processing/booked), NOT just "pending":
    by the time the slot-select endpoint resumes the graph it has already flipped
    the booking to "booked", so a "pending"-only check would miss it and re-create
    a second booking + email.
    """
    from booking_agent import create_slot_picker_booking, _bookings

    cv_id = state["cv_id"]
    existing = _bookings().find_one({
        "candidate_id": cv_id,
        "status": {"$in": ["pending", "processing", "booked"]},
    })
    token = existing["_id"] if existing else create_slot_picker_booking(
        {
            "_id": cv_id,
            "email": state.get("email"),
            "name": state.get("name"),
            "phone": state.get("phone"),
            "jd_id": state.get("jd_id"),
        },
        state.get("interview_score"),
    )
    if not token:
        return {"booking_token": None, "stage": STAGE_BOOK}

    payload = interrupt({"cv_id": cv_id, "awaiting": "slot_pick", "booking_token": token})
    payload = payload or {}
    return {
        "booking_token": token,
        "selected_slot": payload.get("selected_slot"),
        "meet_link": payload.get("meet_link"),
        "stage": STAGE_BOOK,
    }


def create_event(state: PipelineState) -> PipelineState:
    """Record the chosen slot + Meet link into state after the booking resumes.

    The real Google Calendar event + Meet link are created by
    booking_agent.select_slot (called from the slot-select endpoint) — that
    behaviour is preserved. This node only mirrors the resumed slot/link into the
    pipeline state so downstream (rank) and dashboards see a consistent record.
    """
    return {
        "selected_slot": state.get("selected_slot"),
        "meet_link": state.get("meet_link"),
        "stage": STAGE_BOOK,
    }


def rank(state: PipelineState) -> PipelineState:
    """Terminal node: persist the candidate's final ranked record, then END.

    Both pipeline exits converge here — booked candidates (book -> create_event)
    and interviewed-but-below-threshold ones (route_after_interview). Delegates to
    ranking_agent.rank_candidate (EP-RANK), which reads CV match + interview score
    + red flags and upserts the unified ranked_candidates doc. Mirrors the resulting
    composite_score + recommendation back into state and marks the run completed.

    None-safe: an unknown cv_id returns None, so the graph still completes cleanly.
    """
    from ranking_agent import rank_candidate

    doc = rank_candidate(state["cv_id"]) or {}
    return {
        "composite_score": doc.get("composite_score"),
        "recommendation": doc.get("recommendation"),
        "status": STATUS_COMPLETED,
        "stage": STAGE_RANK,
    }


def start_interview(state: PipelineState, config=None) -> PipelineState:
    """Create a LiveKit interview room and email the candidate a join link.

    Creates the room once (guarded against re-runs on LangGraph resume), then
    suspends until /voice/livekit-complete resumes the thread with the transcript.
    """
    from voice_agent import _start_livekit_interview, _screened

    cv_id = state["cv_id"]
    if not _screened().find_one({"_id": cv_id}):
        room_name = _start_livekit_interview(state, config)
        if not room_name:
            return {"status": STATUS_REJECTED_CV}

    # Suspend; /voice/livekit-complete resumes with transcript + end_reason + duration.
    payload = interrupt({"cv_id": cv_id, "awaiting": "livekit_interview"})
    payload = payload or {}
    return {
        "transcript": payload.get("transcript"),
        "summary": payload.get("summary", ""),
        "end_reason": payload.get("end_reason", "completed"),
        "duration": payload.get("duration", 0),
        "tone": payload.get("tone"),
        "live_red_flags": payload.get("live_red_flags") or [],
        "stage": STAGE_INTERVIEW,
    }


def score_interview(state: PipelineState) -> PipelineState:
    """Categorise + score + persist the interview via the shared helper.

    Resume target after the webhook (and after each retry). Delegates to
    voice_agent.score_and_persist_call — the single source of truth shared with
    the legacy webhook path — so the two never drift. The returned call_log_status
    drives route_after_interview (retriable declines -> wait_retry node). Booking
    and ranking are separate nodes (BE-010/012).
    """
    from voice_agent import score_and_persist_call, _screened

    cv_id = state["cv_id"]
    doc = _screened().find_one({"_id": cv_id}) or {
        "_id": cv_id,
        "jd_id": state.get("jd_id"),
        "fit_percent": state.get("fit_percent"),
        "experience_years": state.get("experience_years"),
        "name": state.get("name"),
        "email": state.get("email"),
    }
    result = score_and_persist_call(
        doc,
        transcript=state.get("transcript") or "",
        summary=state.get("summary") or "",
        end_reason=state.get("end_reason") or "unknown",
        duration=state.get("duration") or 0,
        tone=state.get("tone"),
        live_red_flags=state.get("live_red_flags") or [],
    )
    return {
        "interview_score": result["interview_score"],
        "call_category": result["category"],
        "call_log_status": result["call_log_status"],
    }


def wait_retry(state: PipelineState) -> PipelineState:
    """Pause the graph until the scheduled retry call's webhook resumes it.

    A declined call that still has attempts left lands here. The background retry
    scheduler (_retry_loop -> process_retries) re-calls the candidate and updates
    the screened row's call_id; when that new call's webhook arrives, /voice/webhook
    resolves the thread and resumes here with the fresh call result. Control then
    loops back to score_interview, which re-categorises and re-logs the attempt.
    """
    payload = interrupt({"cv_id": state["cv_id"], "awaiting": "retry_webhook"})
    payload = payload or {}
    return {
        "transcript": payload.get("transcript"),
        "summary": payload.get("summary"),
        "end_reason": payload.get("end_reason"),
        "duration": payload.get("duration"),
        "stage": STAGE_INTERVIEW,
    }


def create_pipeline_agent():
    """Compile the candidate pipeline graph over PipelineState.

    Flow: parse_cv -> match -> [route by CV fit] -> start_interview -> score_interview ->
    [route by interview] -> book -> create_event -> rank (or reject). The rank node persists
    the final ranked_candidates record (EP-RANK) before END. The compiled graph carries the
    SQLite checkpointer so it can resume across the interview (webhook) and booking (slot-pick)
    interrupts.
    """
    builder = StateGraph(PipelineState)
    builder.add_node("parse_cv", parse_cv)
    builder.add_node("match", match)
    builder.add_node("start_interview", start_interview)
    builder.add_node("score_interview", score_interview)
    builder.add_node("wait_retry", wait_retry)
    builder.add_node("book", book)
    builder.add_node("create_event", create_event)
    builder.add_node("rank", rank)
    builder.add_node("reject", reject)

    builder.set_entry_point("parse_cv")
    builder.add_edge("parse_cv", "match")
    builder.add_conditional_edges(
        "match", route_after_match,
        {"start_interview": "start_interview", "reject": "reject"},
    )
    builder.add_edge("start_interview", "score_interview")
    builder.add_conditional_edges(
        "score_interview", route_after_interview,
        {"book": "book", "rank": "rank", "reject": "reject", "wait_retry": "wait_retry"},
    )
    builder.add_edge("wait_retry", "score_interview")
    builder.add_edge("book", "create_event")
    builder.add_edge("create_event", "rank")
    builder.add_edge("rank", END)
    builder.add_edge("reject", END)
    return builder.compile(checkpointer=_checkpointer)


if __name__ == "__main__":
    import json

    # Self-test: state must be JSON-serialisable (required by the checkpointer).
    state = new_state("cv-123", "jd-456")
    state.update({
        "name": "Test User", "fit_percent": 80,
        "interview_score": 72, "meet_link": "https://meet.google.com/abc",
        "composite_score": 76.8, "recommendation": "yes",
    })

    dumped = json.dumps(state)              # raises if not serialisable
    restored = json.loads(dumped)
    assert restored["cv_id"] == "cv-123"
    assert restored["composite_score"] == 76.8
    assert restored["stage"] == STAGE_PARSE
    print("[ok] PipelineState is JSON-serialisable")
    print("[ok] fields:", sorted(state.keys()))

    # Graph factory: compiles with a checkpointer.
    agent = create_pipeline_agent()
    assert agent is not None
    assert agent.checkpointer is not None
    print(f"[ok] pipeline agent compiled (checkpointer={type(_checkpointer).__name__})")

    # parse_cv node: monkeypatch process_cv so no real PDF/LLM is needed.
    import parser_agent
    parser_agent.process_cv = lambda pdf_path, jd_id=None: {
        "id": "cv-parsed-1",
        "data": {
            "name": "Test User", "email": "t@example.com", "phone": "0300",
            "experience_years": 3.0, "last_education_degree": "BS CS",
            "raw_cv_text": "resume text",
        },
    }

    # match node: monkeypatch scorer + DB helpers (no real LLM / Mongo).
    import shortlisting_agent
    _mock_payload = {
        "fit_percent": 75,
        "criteria_scores": [],
        "document_professionalism": {},
        "professional_profile": {},
        "red_flags": {"timeline_tenure": False, "timeline_evidence": "", "experience_misrepresentation": False, "representation_evidence": "", "unprofessional_email": False},
        "experience_score": 8.3,
        "experience_required_years": 0.0,
    }
    shortlisting_agent._score_candidate = lambda candidate, criteria, jd_text="": _mock_payload
    shortlisting_agent._job_criteria = lambda: type(
        "C", (), {"find_one": lambda self, q: {"status": "confirmed", "criteria": [{"criteria": "Python", "importance": "must_have", "description": "Python dev"}]}}
    )()
    shortlisting_agent._job_descriptions = lambda: type(
        "C", (), {"find_one": lambda self, q: {"job_description": "AI Engineer JD"}}
    )()
    _captured = {}
    shortlisting_agent._candidates = lambda: type(
        "C", (), {"update_one": lambda self, q, u, upsert=False: _captured.update({"q": q, "u": u})}
    )()

    # start_interview + score_interview: monkeypatch voice_agent / call_logs /
    # transcript_analyzer / ranking_agent (no real Vapi / Mongo / LLM).
    import uuid
    import voice_agent, call_logs, transcript_analyzer
    from langgraph.types import Command

    class _FakeColl:
        def __init__(self): self.docs = []
        def find_one(self, q):
            return next((d for d in self.docs if all(d.get(k) == v for k, v in q.items())), None)
        def insert_one(self, doc): self.docs.append(dict(doc))
        def replace_one(self, q, doc, upsert=False):
            d = self.find_one(q)
            if d: d.clear(); d.update(doc)
            elif upsert: self.docs.append(dict(doc))
        def update_one(self, q, u, upsert=False):
            d = self.find_one(q)
            if d: d.update(u.get("$set", {}))
            elif upsert: self.docs.append({**q, **u.get("$set", {})})

    _screened_coll, _insights_coll = _FakeColl(), _FakeColl()
    _livekit_rooms = {}
    voice_agent._start_livekit_interview = lambda state, cfg=None: (
        _livekit_rooms.update({"cv_id": state["cv_id"]}) or f"interview-{state['cv_id'][:8]}"
    )
    voice_agent._screened = lambda: _screened_coll
    voice_agent._insights_collection = lambda: _insights_coll
    voice_agent._jobs_collection = lambda: type("C", (), {"find_one": lambda s, q: {"job_description": "JD"}})()
    voice_agent._score_interview = lambda t, s, jd=None: {"score": 82, "red_flags": ["vague on gap"]}
    call_logs.categorize_call = lambda end_reason: ("completed", "ok")
    transcript_analyzer.extract_interview_insights = lambda t: {"key_strengths": ["FastAPI"], "red_flags": []}

    # log_call_attempt: mirror real status logic (no_show/incomplete -> pending_retry
    # until MAX, then exhausted; completed -> closed) without touching Mongo.
    _FAKE_MAX_RETRY = 2
    _attempts: dict = {}

    def _fake_log_call_attempt(candidate_id, jd_id, call_id, category, reason,
                               end_reason, transcript, duration, score=None,
                               triggered_by="auto"):
        _attempts[candidate_id] = _attempts.get(candidate_id, 0) + 1
        if category in ("no_show", "incomplete") and _attempts[candidate_id] < _FAKE_MAX_RETRY:
            status = "pending_retry"
        elif category in ("no_show", "incomplete"):
            status = "exhausted"
        else:
            status = "closed"
        return {"status": status, "attempt_number": _attempts[candidate_id]}

    call_logs.log_call_attempt = _fake_log_call_attempt

    # book node: monkeypatch booking_agent (no real email / slots / Mongo).
    import booking_agent
    _booked = {}
    booking_agent.create_slot_picker_booking = lambda doc, score: (_booked.update({"cv_id": doc["_id"], "score": score}) or "tok-1")
    booking_agent._bookings = lambda: type("C", (), {"find_one": lambda s, q: None})()

    # rank terminal node: monkeypatch ranking_agent.rank_candidate (no real DB).
    import ranking_agent
    _ranked_calls = []
    ranking_agent.rank_candidate = lambda cv_id, cv_weight=None, interview_weight=None: (
        _ranked_calls.append(cv_id) or {"composite_score": 78.5, "recommendation": "yes"}
    )

    launch = {"pdf_path": "/tmp/fake.pdf", "jd_id": "jd-1",
              "stage": STAGE_PARSE, "status": STATUS_ACTIVE}

    # High fit (75 >= 70) -> parse -> match -> start_interview -> INTERRUPT (pause).
    cfg_high = {"configurable": {"thread_id": f"t-{uuid.uuid4()}"}}
    agent.invoke(launch, cfg_high)
    assert _captured["u"]["$set"]["fit_percent"] == 75
    print("[ok] parse_cv + match (fit=75) mirror fit_percent to candidates_info")
    assert _livekit_rooms.get("cv_id") == "cv-parsed-1", "LiveKit room should have been created"
    assert agent.get_state(cfg_high).next, "graph should be paused at the interview interrupt"
    print("[ok] start_interview creates LiveKit room and suspends at interrupt")

    resume_payload = Command(resume={
        "transcript": "I use Python and FastAPI", "summary": "strong",
        "end_reason": "completed", "duration": 120,
    })

    # Resume (webhook) -> score_interview categorises, scores, persists.
    final = agent.invoke(resume_payload, cfg_high)
    assert final["call_category"] == "completed"
    assert final["interview_score"] == 82
    _scr = _screened_coll.find_one({"_id": "cv-parsed-1"})
    assert _scr["interview_score"] == 82
    assert _scr["composite_score"] is not None and _scr["recommendation"] is not None
    assert _insights_coll.find_one({"_id": "cv-parsed-1"})["key_strengths"] == ["FastAPI"]
    print("[ok] score_interview: categorise + score + composite/recommendation + insights persisted")

    # route_after_interview branch 1: completed + score(82) >= 60 -> book -> INTERRUPT.
    assert _booked["cv_id"] == "cv-parsed-1" and _booked["score"] == 82
    assert agent.get_state(cfg_high).next == ("book",)
    print("[ok] route_after_interview: high score -> book emails picker + suspends at interrupt")

    # Resume booking (slot picked) -> book -> create_event -> rank -> END.
    booked = agent.invoke(Command(resume={
        "selected_slot": "2026-06-20T10:00:00", "meet_link": "https://meet.google.com/xyz",
    }), cfg_high)
    assert booked["booking_token"] == "tok-1"
    assert booked["meet_link"] == "https://meet.google.com/xyz"
    print("[ok] book resume: slot + meet link land in state")
    # rank terminal node ran: composite + recommendation in state, status completed.
    assert "cv-parsed-1" in _ranked_calls
    assert booked["composite_score"] == 78.5 and booked["recommendation"] == "yes"
    assert booked["status"] == STATUS_COMPLETED and booked["stage"] == STAGE_RANK
    assert not agent.get_state(cfg_high).next, "graph should have reached END"
    print("[ok] rank terminal: rank_candidate persisted, status=completed, reached END")

    def _run_to_interview(thread):
        cfg = {"configurable": {"thread_id": thread}}
        agent.invoke(launch, cfg)
        return cfg

    # Branch 2: completed + score(40) < 60 -> rank.
    voice_agent._score_interview = lambda t, s, jd=None: {"score": 40, "red_flags": []}
    cfg2 = _run_to_interview(f"t-{uuid.uuid4()}")
    r2 = agent.invoke(resume_payload, cfg2)
    assert r2["interview_score"] == 40 and r2["stage"] == STAGE_RANK
    assert r2["status"] == STATUS_COMPLETED and r2["recommendation"] == "yes"
    print("[ok] route_after_interview: completed + low score -> rank -> completed")

    # Branch 3: no_show + retriable -> wait_retry (PAUSE); retry resume -> no_show
    # again -> attempts exhausted -> reject (rejected_interview).
    # (Reset the shared attempt counter — every test thread reuses cv-parsed-1.)
    _attempts.clear()
    call_logs.categorize_call = lambda end_reason: ("no_show", "candidate_never_joined")
    cfg3 = _run_to_interview(f"t-{uuid.uuid4()}")
    r3 = agent.invoke(resume_payload, cfg3)          # attempt 1 -> pending_retry
    assert agent.get_state(cfg3).next == ("wait_retry",), agent.get_state(cfg3).next
    assert r3["call_log_status"] == "pending_retry"
    print("[ok] route_after_interview: no_show + retriable -> wait_retry (paused for a fresh invite)")

    r3b = agent.invoke(resume_payload, cfg3)         # retry webhook -> attempt 2 -> exhausted
    assert r3b["call_category"] == "no_show" and r3b["call_log_status"] == "exhausted"
    assert r3b["status"] == STATUS_REJECTED_INTERVIEW
    assert not agent.get_state(cfg3).next, "graph should reach END after retries exhausted"
    print("[ok] wait_retry resume -> no_show again -> exhausted -> reject (rejected_interview)")

    # restore completed categorisation for any later assertions
    call_logs.categorize_call = lambda end_reason: ("completed", "ok")

    # CV gate: low fit (40 < 70) -> reject -> status rejected_cv (no interview).
    shortlisting_agent._score_candidate = lambda candidate, criteria, jd_text="": {**_mock_payload, "fit_percent": 40}
    low = agent.invoke(launch, {"configurable": {"thread_id": f"t-{uuid.uuid4()}"}})
    assert low["fit_percent"] == 40 and low["status"] == STATUS_REJECTED_CV
    print("[ok] route_after_match: low fit -> reject (status=rejected_cv)")
    print("All pipeline self-tests passed.")
