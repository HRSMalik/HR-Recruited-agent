import asyncio
import html
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Header, File, UploadFile, status, Form, Query, Depends, Body
from fastapi.responses import Response, JSONResponse, HTMLResponse
from auth import require_api_key
from pymongo.errors import PyMongoError
import config
from schemas import JobPostAgentRequest, HumanFeedback, JobPostAgentResult, CandidateListResponse, JobListResponse, RankedListResponse, RerankRequest, CriteriaUpdateRequest
from criteria_agent import generate_criteria, get_criteria, update_criteria, confirm_criteria
import uuid

from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from job_post import create_workflow_agent, _get_job_descriptions_collection, publish_job_to_linkedin
from parser_agent import _get_candidates_collection, detect_new_applicants, mark_processed
from voice_agent import record_call_result, list_screened_candidates, _screened
from call_logs import (
    list_call_logs as cl_list,
    call_stats as cl_stats,
    manual_retry as cl_manual_retry,
    close_log as cl_close,
)
from booking_agent import get_booking, select_slot
from typing import Optional
from datetime import datetime, timezone
import uuid


def _launch_pipeline_for_applicant(applicant: dict) -> Optional[str]:
    """Run one new applicant through the pipeline graph (parse -> match -> ...).

    The first invoke runs synchronously up to the first interrupt (the interview),
    so parse_cv consumes pdf_path while the temp file is still alive. Resuming
    (webhook / slot-select) is handled by the existing endpoints via the thread_id
    stored on the screened row. Returns the cv_id once parsed, else None.
    """
    agent = _get_pipeline_agent()
    cfg = {"configurable": {"thread_id": f"pipe-{uuid.uuid4()}"}}
    agent.invoke(
        {"pdf_path": applicant["pdf_path"], "jd_id": applicant["jd_id"],
         "stage": "parse", "status": "active"},
        cfg,
    )
    return agent.get_state(cfg).values.get("cv_id")


async def _shortlist_loop(interval_seconds: int):
    """Detect new applicants and launch one pipeline graph per candidate.

    Replaces the old ingest -> shortlist_all_jobs -> call_top_candidates steps:
    the graph now handles parse/match/interview/book/rank internally.
    """
    import tempfile

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            with tempfile.TemporaryDirectory() as tmp_dir:
                new_applicants = await asyncio.to_thread(detect_new_applicants, tmp_dir)
                print(f"[pipeline] tick: {len(new_applicants)} new applicant(s)", file=sys.stderr)
                for applicant in new_applicants:
                    try:
                        cv_id = await asyncio.to_thread(_launch_pipeline_for_applicant, applicant)
                        if cv_id:
                            await asyncio.to_thread(
                                mark_processed, applicant["file_id"], applicant["jd_id"], cv_id
                            )
                            print(f"[pipeline] launched cv_id={cv_id} jd={applicant['jd_id']}", file=sys.stderr)
                    except Exception as e:  # noqa: BLE001
                        print(f"[pipeline] launch error file_id={applicant['file_id']}: {e!r}", file=sys.stderr)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            print(f"[scheduler] error: {e!r}", file=sys.stderr)


def _retry_start_interview(cand: dict):
    """Adapt a screened_candidates doc into the state shape _start_livekit_interview
    expects, for candidates whose initial_screening_logs retry is due."""
    from voice_agent import _start_livekit_interview
    state = {
        "cv_id": cand["_id"],
        "jd_id": cand.get("jd_id", ""),
        "name": cand.get("name"),
        "email": cand.get("email"),
    }
    return _start_livekit_interview(state)


async def _retry_loop(interval_seconds: int = 60):
    """Send a fresh LiveKit interview invite (new room + new email) to candidates
    whose no_show/incomplete attempt is due for retry."""
    from call_logs import process_retries

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            result = await asyncio.to_thread(process_retries, _retry_start_interview, _screened())
            if result["retried"] or result["errors"]:
                print(f"[retry] tick: {result}", file=sys.stderr)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            print(f"[retry] error: {e!r}", file=sys.stderr)


async def _reminder_loop(interval_seconds: int):
    """Background loop that emails a pre-interview reminder to candidate + HR/team.

    Time-based (not part of the pipeline graph): periodically scans scheduled
    meetings starting within REMINDER_HOURS_BEFORE and sends a one-time reminder.
    """
    from booking_agent import send_due_reminders

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            result = await asyncio.to_thread(send_due_reminders)
            if result["sent"] or result["errors"]:
                print(f"[reminder] tick: {result}", file=sys.stderr)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            print(f"[reminder] error: {e!r}", file=sys.stderr)


@asynccontextmanager
async def lifespan(app: FastAPI):
    interval = config.SHORTLIST_INTERVAL_SECONDS
    retry_interval = config.RETRY_LOOP_INTERVAL_SECONDS
    reminder_interval = config.REMINDER_LOOP_INTERVAL_SECONDS
    # Auto-retry re-invites (new room + new email) every no_show/incomplete candidate.
    # OFF by default: during testing it floods the worker with phantom rooms and emails
    # real candidates. Set ENABLE_AUTO_RETRY=true only in production.
    auto_retry = os.getenv("ENABLE_AUTO_RETRY", "false").lower() == "true"
    shortlist_task = asyncio.create_task(_shortlist_loop(interval))
    retry_task = asyncio.create_task(_retry_loop(retry_interval)) if auto_retry else None
    reminder_task = asyncio.create_task(_reminder_loop(reminder_interval))
    print(f"[shortlist] scheduler started; interval={interval}s", file=sys.stderr)
    print(f"[retry] scheduler {'started; interval=' + str(retry_interval) + 's' if auto_retry else 'DISABLED (ENABLE_AUTO_RETRY=false)'}", file=sys.stderr)
    print(f"[reminder] scheduler started; interval={reminder_interval}s", file=sys.stderr)
    try:
        yield
    finally:
        shortlist_task.cancel()
        if retry_task:
            retry_task.cancel()
        reminder_task.cancel()
        for t in (shortlist_task, retry_task, reminder_task):
            if t is None:
                continue
            try:
                await t
            except asyncio.CancelledError:
                pass


# Interactive docs (and the public /openapi.json schema dump) are off by default
# so the API surface isn't exposed; set ENABLE_API_DOCS=true in dev to turn on.
_docs_on = os.getenv("ENABLE_API_DOCS", "false").lower() == "true"
app = FastAPI(
    title="Recruitment Module API",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
    docs_url="/docs" if _docs_on else None,
    redoc_url="/redoc" if _docs_on else None,
    openapi_url="/openapi.json" if _docs_on else None,
)

# Explicit origin allowlist (QA-02): "*" + allow_credentials is unsafe — it lets
# any site call the API with credentials. Origins come from the env so production
# just sets CORS_ALLOWED_ORIGINS without a code change; default is local Streamlit.
_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8501").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Content-Security-Policy is intentionally permissive on inline script/style:
# the booking HTML pages use inline <script>/<style> + Google Fonts. It still
# restricts framing, external scripts, and other origins (defense-in-depth,
# QA-14). Tightening to nonce-based CSP would require externalising those assets.
_CSP = (
    "default-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "connect-src 'self' ws://localhost:7880 wss://localhost:7880 ws: wss: https://api.deepgram.com; "
    "media-src 'self' blob:; "
    "img-src 'self' data:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)


@app.middleware("http")
async def _security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
    )
    response.headers.setdefault("Content-Security-Policy", _CSP)
    return response


@app.exception_handler(PyMongoError)
async def _mongo_unavailable_handler(request, exc):
    # Any unhandled MongoDB failure (e.g. server unreachable) -> a clean,
    # actionable 503 instead of an opaque 500. No internal detail is leaked.
    print(f"[db] {request.url.path} -> {type(exc).__name__}: {exc}", file=sys.stderr)
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})

# Compile once per process so InMemorySaver can keep thread state.
job_post_agent = create_workflow_agent()



@app.post(
    "/job-posts",
    tags=["Job Posts"],
    status_code=status.HTTP_201_CREATED,
    response_model=JobPostAgentResult,
)
async def create_job_post(job_post: JobPostAgentRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "form_data": job_post.model_dump(),
        "generated_post": None,
        "human_feedback": None,
        "approved": False,
        "linkedin_posted": False,
    }

    try:
        response = job_post_agent.invoke(initial_state, config=config)
    except GraphInterrupt as e:
        interrupts = e.args[0] if e.args else []
        interrupt_value = interrupts[0].value if interrupts else {}
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "needs_review",
                "thread_id": thread_id,
                "generated_post": interrupt_value.get("generated_post", ""),
                "linkedin_posted": False,
                "message": interrupt_value.get("message"),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Fallback for LangGraph versions that surface interrupts in the response.
    if isinstance(response, dict) and "__interrupt__" in response:
        interrupts = response["__interrupt__"]
        interrupt_value = interrupts[0].value if interrupts else {}
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "needs_review",
                "thread_id": thread_id,
                "generated_post": interrupt_value.get("generated_post", ""),
                "linkedin_posted": False,
                "message": interrupt_value.get("message"),
            },
        )

    return {
        "status": "approved",
        "thread_id": thread_id,
        "generated_post": response.get("generated_post", "") if isinstance(response, dict) else "",
        "linkedin_posted": response.get("linkedin_posted", False) if isinstance(response, dict) else False,
        "message": None,
    }


@app.post(
    "/job-posts/{thread_id}/review",
    tags=["Job Posts"],
    response_model=JobPostAgentResult,
)
async def review_job_post(thread_id: str, human_feedback: HumanFeedback):
    config = {"configurable": {"thread_id": thread_id}}

    feedback_payload = human_feedback.model_dump(exclude_none=True)
    if feedback_payload.get("action") == "edit" and not feedback_payload.get("edited_post"):
        raise HTTPException(status_code=400, detail="edited_post is required when action=edit")
    if feedback_payload.get("action") == "regenerate" and not feedback_payload.get("feedback"):
        raise HTTPException(status_code=400, detail="feedback is required when action=regenerate")

    try:
        response = job_post_agent.invoke(Command(resume=feedback_payload), config=config)
    except GraphInterrupt as e:
        interrupts = e.args[0] if e.args else []
        interrupt_value = interrupts[0].value if interrupts else {}
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "needs_review",
                "thread_id": thread_id,
                "generated_post": interrupt_value.get("generated_post", ""),
                "linkedin_posted": False,
                "message": interrupt_value.get("message"),
            },
        )
    except ValueError as e:
        msg = str(e)
        # Some ValueErrors are user/config errors (e.g., missing GOOGLE_FORM_URL), not missing threads.
        # Treat "missing state/thread" issues as 404, everything else as 400.
        lowered = msg.lower()
        is_missing_thread = (
            "start a new thread" in lowered
            or ("thread" in lowered and "missing" in lowered and "workflow" in lowered)
            or "unknown or expired thread" in lowered
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if is_missing_thread else status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown or expired thread_id (missing state key: {e}). Create a new thread via POST /job-posts.",
        )

    if isinstance(response, dict) and "__interrupt__" in response:
        interrupts = response["__interrupt__"]
        interrupt_value = interrupts[0].value if interrupts else {}
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "status": "needs_review",
                "thread_id": thread_id,
                "generated_post": interrupt_value.get("generated_post", ""),
                "linkedin_posted": False,
                "message": interrupt_value.get("message"),
            },
        )

    return {
        "status": "approved",
        "thread_id": thread_id,
        "generated_post": response.get("generated_post", "") if isinstance(response, dict) else "",
        "linkedin_posted": response.get("linkedin_posted", False) if isinstance(response, dict) else False,
        "message": None,
    }





@app.get("/candidates", tags=["Candidates"], response_model=CandidateListResponse)
async def list_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    collection = _get_candidates_collection()
    query = {"fit_percent": {"$exists": False}}
    total = collection.count_documents(query)
    docs = list(collection.find(query).skip(skip).limit(limit))
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


@app.get("/shortlisted-candidates", tags=["Candidates"], response_model=CandidateListResponse)
async def list_shortlisted_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    collection = _get_candidates_collection()
    query = {"fit_percent": {"$exists": True}}
    total = collection.count_documents(query)
    docs = list(
        collection.find(query, {
            "name": 1, "email": 1, "phone": 1,
            "experience_years": 1, "freelance_experience_years": 1,
            "last_education_degree": 1, "last_education_institution": 1,
            "fit_percent": 1, "jd_id": 1,
            "criteria_scores": 1, "document_professionalism": 1,
            "professional_profile": 1, "red_flags": 1,
            "experience_score": 1, "experience_required_years": 1,
        })
        .sort("fit_percent", -1)
        .skip(skip)
        .limit(limit)
    )
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


@app.get("/ranked-candidates", tags=["Candidates"], response_model=RankedListResponse)
async def list_ranked_candidates(
    jd_id: str = Query(..., description="Job ID to rank candidates for"),
    top_n: Optional[int] = Query(None, ge=1, description="Cap the ranked pool to the top N before paginating"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Ranked shortlist for a job, highest composite score first.

    `top_n` caps the ranked pool; `skip`/`limit` paginate within it. The 1-based
    `rank` on each item is global across the ranked pool, not per-page.
    """
    from ranking_agent import rank_for_jd
    ranked = rank_for_jd(jd_id, top_n=top_n)
    return {
        "items": ranked[skip: skip + limit],
        "total": len(ranked),
        "skip": skip,
        "limit": limit,
    }


@app.post("/jobs/{jd_id}/rerank", tags=["Candidates"], response_model=RankedListResponse)
async def rerank_job(jd_id: str, body: Optional[RerankRequest] = None):
    """Recompute every ranked candidate for a job and return the refreshed shortlist.

    Reuses each candidate's existing CV and interview scores; only the weight
    blend changes. Optional body {cv_weight, interview_weight} overrides the env
    weights for this run only (the .env is not modified). Both must be supplied
    together to take effect.
    """
    from ranking_agent import rerank_jd
    # Fail loud on an unknown jd_id: a rerank is an explicit action, so a typo
    # should 404, not silently "succeed" with an empty list.
    if not _get_job_descriptions_collection().find_one({"_id": jd_id}):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Job not found: {jd_id}")
    cv_weight = body.cv_weight if body else None
    interview_weight = body.interview_weight if body else None
    ranked = rerank_jd(jd_id, cv_weight=cv_weight, interview_weight=interview_weight)
    return {"items": ranked, "total": len(ranked), "skip": 0, "limit": len(ranked)}


@app.get("/screened_candidates", tags=["Candidates"], response_model=CandidateListResponse)
async def list_screened(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter: 'calling' or 'completed'"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Only return rows with interview_score >= this"),
):
    """List candidates whose phone screening has been initiated, enriched with insights and meeting info."""
    return list_screened_candidates(skip=skip, limit=limit, status=status, min_score=min_score)


@app.get("/job-posts", tags=["Job Posts"], response_model=JobListResponse)
async def list_job_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    collection = _get_job_descriptions_collection()
    total = collection.count_documents({})
    docs = list(collection.find().skip(skip).limit(limit))
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


@app.post("/test-interview", tags=["Test"])
async def trigger_test_interview():
    """Create a LiveKit interview room for manual testing and return the join link."""
    from voice_agent import _start_livekit_interview, _gen_candidate_token
    job = _get_job_descriptions_collection().find_one({}, sort=[("_id", -1)])
    if not job:
        raise HTTPException(400, "No jobs found. Create a job first.")

    test_id = str(uuid.uuid4())
    state = {
        "cv_id": test_id,
        "jd_id": job["_id"],
        "name": "Test Candidate",
        "email": None,
        "fit_percent": 100,
        "experience_years": 3,
        "last_education_degree": "BS CS",
    }
    room_name = await asyncio.to_thread(_start_livekit_interview, state)
    if not room_name:
        raise HTTPException(500, "Failed to create LiveKit interview room.")

    token = _gen_candidate_token(room_name, "Test Candidate")
    base_url = os.getenv("BOOKING_BASE_URL", "http://localhost:8000")
    return {
        "room_name": room_name,
        "interview_url": f"{base_url}/interview/{room_name}?token={token}",
        "test_id": test_id,
        "job_id": job["_id"],
    }


_pipeline_agent = None


def _get_pipeline_agent():
    """Compile the pipeline graph once and reuse it (carries the checkpointer)."""
    global _pipeline_agent
    if _pipeline_agent is None:
        from pipeline import create_pipeline_agent
        _pipeline_agent = create_pipeline_agent()
    return _pipeline_agent


@app.post("/voice/webhook", tags=["Voice"])
async def voice_webhook(payload: dict):
    """Receive end-of-call reports from Vapi. Categorizes the call (completed/
    cancelled/declined), persists to call_logs, and runs the downstream flow
    (score, insights, meeting) only for completed calls."""
    msg = payload.get("message") or {}
    if msg.get("type") != "end-of-call-report":
        return {"received": True, "ignored": True}

    call = msg.get("call") or {}
    call_id = call.get("id")
    if not call_id:
        return {"received": True, "error": "missing call_id"}

    transcript_raw = (msg.get("artifact") or {}).get("transcript") or msg.get("transcript") or ""
    if isinstance(transcript_raw, list):
        transcript = "\n".join(
            f"{(m.get('role') or 'AI').title()}: {m.get('message', '')}"
            for m in transcript_raw
        )
    else:
        transcript = transcript_raw

    summary = (
        (msg.get("analysis") or {}).get("summary")
        or msg.get("summary")
        or ""
    )

    end_reason = msg.get("endedReason") or call.get("endedReason") or "unknown"
    duration = int(
        call.get("duration")
        or msg.get("durationSeconds")
        or msg.get("duration")
        or 0
    )

    # Resolve the candidate/thread from the call_id and resume the paused graph.
    row = _screened().find_one({"call_id": call_id})
    if not row:
        return {"received": True, "error": "unknown call_id"}

    thread_id = row.get("thread_id")
    if not thread_id:
        # Legacy / test-call path (not launched via the pipeline) — no regression.
        await asyncio.to_thread(
            record_call_result, call_id, transcript, summary, end_reason, duration
        )
        return {"received": True, "via": "legacy"}

    agent = _get_pipeline_agent()
    cfg = {"configurable": {"thread_id": thread_id}}
    snap = await asyncio.to_thread(agent.get_state, cfg)
    if not getattr(snap, "next", None):
        # Already resumed (duplicate webhook) — don't double-resume.
        return {"received": True, "duplicate": True}

    await asyncio.to_thread(
        agent.invoke,
        Command(resume={
            "transcript": transcript, "summary": summary,
            "end_reason": end_reason, "duration": duration,
        }),
        cfg,
    )
    return {"received": True, "resumed": True}


@app.post("/voice/livekit-complete", tags=["Voice"])
async def livekit_interview_complete(payload: dict = Body(...)):
    """Receive transcript from livekit_agent.py when an interview ends.

    Looks up the screened_candidates row by room_name (stored as call_id),
    then resumes the paused pipeline thread — same mechanism as the old Vapi webhook.
    """
    cv_id = payload.get("cv_id")
    room_name = payload.get("room_name")
    transcript = payload.get("transcript", "")
    end_reason = payload.get("end_reason", "completed")
    duration = int(payload.get("duration") or 0)
    tone = payload.get("tone")
    live_red_flags = payload.get("live_red_flags") or []

    if not cv_id and not room_name:
        return {"received": True, "error": "cv_id or room_name required"}

    row = _screened().find_one({"_id": cv_id} if cv_id else {"room_name": room_name})
    if not row:
        return {"received": True, "error": "unknown interview"}

    thread_id = row.get("thread_id")
    if not thread_id:
        await asyncio.to_thread(
            record_call_result, room_name or cv_id, transcript, "", end_reason, duration,
            tone, live_red_flags,
        )
        return {"received": True, "via": "legacy"}

    agent = _get_pipeline_agent()
    cfg = {"configurable": {"thread_id": thread_id}}
    snap = await asyncio.to_thread(agent.get_state, cfg)
    if not getattr(snap, "next", None):
        return {"received": True, "duplicate": True}

    await asyncio.to_thread(
        agent.invoke,
        Command(resume={
            "transcript": transcript, "summary": "",
            "end_reason": end_reason, "duration": duration,
            "tone": tone, "live_red_flags": live_red_flags,
        }),
        cfg,
    )
    return {"received": True, "resumed": True}


@app.get("/interview/{room_name}", tags=["Interview"], response_class=HTMLResponse)
async def interview_room_page(room_name: str, token: str = Query(...)):
    """Serve the browser-based interview room page for a candidate."""
    livekit_url = os.getenv("LIVEKIT_URL_PUBLIC", os.getenv("LIVEKIT_URL", "ws://localhost:7880"))
    return HTMLResponse(_render_interview_page(room_name, token, livekit_url))


def _render_interview_page(room_name: str, token: str, livekit_url: str) -> str:
    room_safe = html.escape(room_name)
    token_safe = html.escape(token)
    lk_url_safe = html.escape(livekit_url)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Technical Interview — HR Recruited</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
     background:#0a0e1a;color:#e8eaf0;min-height:100vh;display:flex;flex-direction:column;}}

/* ── Header ── */
.header{{display:flex;align-items:center;justify-content:space-between;
         padding:16px 24px;background:#0f1422;border-bottom:1px solid #1e2540;}}
.logo{{display:flex;align-items:center;gap:10px;}}
.logo-dot{{width:10px;height:10px;background:#4f8ef7;border-radius:50%;
           box-shadow:0 0 8px #4f8ef7;}}
.logo-text{{font-size:16px;font-weight:600;letter-spacing:.3px;}}
.header-meta{{font-size:13px;color:#6b7499;}}
#timer{{font-variant-numeric:tabular-nums;color:#4f8ef7;font-weight:600;}}

/* ── Main layout ── */
.main{{flex:1;display:grid;grid-template-columns:1fr 320px;gap:0;overflow:hidden;}}

/* ── Video area ── */
.video-area{{position:relative;background:#060910;display:flex;
             align-items:center;justify-content:center;min-height:0;}}
#local-video{{width:100%;height:100%;object-fit:cover;border-radius:0;transform:scaleX(-1);}}
.video-placeholder{{display:flex;flex-direction:column;align-items:center;gap:12px;
                    color:#3a4060;font-size:15px;}}
.video-placeholder svg{{opacity:.3;}}
.cam-badge{{position:absolute;bottom:16px;left:16px;background:rgba(10,14,26,.75);
           backdrop-filter:blur(8px);border:1px solid #1e2540;
           padding:6px 12px;border-radius:20px;font-size:12px;color:#8b9cc8;}}

/* ── Sidebar ── */
.sidebar{{background:#0f1422;border-left:1px solid #1e2540;
          display:flex;flex-direction:column;padding:20px;gap:20px;overflow-y:auto;}}

.agent-card{{background:#141929;border:1px solid #1e2540;border-radius:12px;
             padding:20px;text-align:center;}}
.agent-avatar{{width:56px;height:56px;background:linear-gradient(135deg,#1e3a8a,#4f8ef7);
               border-radius:50%;margin:0 auto 12px;display:flex;align-items:center;
               justify-content:center;font-size:22px;position:relative;}}
.agent-avatar::after{{content:'';position:absolute;inset:-3px;border-radius:50%;
                      border:2px solid transparent;transition:border-color .3s;}}
.agent-avatar.speaking::after{{border-color:#4f8ef7;
                               animation:pulse-ring 1s ease-in-out infinite;}}
@keyframes pulse-ring{{0%,100%{{opacity:1;transform:scale(1);}}
                        50%{{opacity:.5;transform:scale(1.08);}}}}
.agent-name{{font-size:14px;font-weight:600;margin-bottom:4px;}}
.agent-status{{font-size:12px;color:#6b7499;}}
#agent-speaking-text{{font-size:11px;color:#4f8ef7;min-height:16px;margin-top:6px;}}

/* ── Wave bars ── */
.wave{{display:flex;align-items:center;justify-content:center;gap:3px;height:28px;margin:10px 0;}}
.wave-bar{{width:3px;height:4px;background:#4f8ef7;border-radius:2px;
           transition:height .1s ease;opacity:.4;}}
.wave-bar.active{{animation:wave-anim .8s ease-in-out infinite;opacity:1;}}
.wave-bar:nth-child(2){{animation-delay:.1s;}}
.wave-bar:nth-child(3){{animation-delay:.2s;}}
.wave-bar:nth-child(4){{animation-delay:.15s;}}
.wave-bar:nth-child(5){{animation-delay:.05s;}}
@keyframes wave-anim{{0%,100%{{height:4px;}}50%{{height:18px;}}}}

/* ── Status bar ── */
.status-bar{{display:flex;align-items:center;gap:8px;padding:10px 16px;
             background:#080c18;border-top:1px solid #1e2540;font-size:12px;}}
.status-dot{{width:8px;height:8px;border-radius:50%;background:#6b7499;flex-shrink:0;}}
.status-dot.connecting{{background:#f59e0b;animation:blink 1s infinite;}}
.status-dot.connected{{background:#34d399;}}
.status-dot.ended{{background:#ef4444;}}
@keyframes blink{{0%,100%{{opacity:1;}}50%{{opacity:.3;}}}}
#status-text{{color:#6b7499;}}

/* ── Controls ── */
.controls{{display:flex;align-items:center;justify-content:center;gap:12px;
           padding:16px 24px;background:#0f1422;border-top:1px solid #1e2540;}}
.ctrl-btn{{width:48px;height:48px;border-radius:50%;border:none;cursor:pointer;
           display:flex;align-items:center;justify-content:center;
           transition:all .2s;font-size:18px;}}
.ctrl-btn.mic{{background:#1e2540;color:#e8eaf0;}}
.ctrl-btn.mic:hover{{background:#273060;}}
.ctrl-btn.mic.muted{{background:#ef4444;color:#fff;}}
.ctrl-btn.cam{{background:#1e2540;color:#e8eaf0;}}
.ctrl-btn.cam:hover{{background:#273060;}}
.ctrl-btn.cam.off{{background:#374151;color:#9ca3af;}}
.ctrl-btn.end{{background:#ef4444;color:#fff;width:56px;height:56px;}}
.ctrl-btn.end:hover{{background:#dc2626;}}

/* ── Overlay messages ── */
.overlay{{position:fixed;inset:0;background:rgba(6,9,16,.95);display:flex;
          flex-direction:column;align-items:center;justify-content:center;
          gap:16px;z-index:100;}}
.overlay.hidden{{display:none;}}
.overlay h2{{font-size:22px;font-weight:600;}}
.overlay p{{color:#6b7499;font-size:14px;text-align:center;max-width:340px;}}
.spinner{{width:40px;height:40px;border:3px solid #1e2540;
          border-top-color:#4f8ef7;border-radius:50%;animation:spin .8s linear infinite;}}
@keyframes spin{{to{{transform:rotate(360deg);}}}}
.end-card{{background:#141929;border:1px solid #1e2540;border-radius:16px;
           padding:32px 40px;text-align:center;max-width:380px;}}
.end-card .checkmark{{font-size:48px;margin-bottom:12px;}}

@media(max-width:700px){{
  .main{{grid-template-columns:1fr;grid-template-rows:1fr auto;}}
  .sidebar{{border-left:none;border-top:1px solid #1e2540;max-height:220px;}}
}}
</style>
</head>
<body>

<!-- Connecting overlay -->
<div class="overlay" id="overlay-connecting">
  <div class="spinner"></div>
  <h2>Connecting…</h2>
  <p>Setting up your interview room. Please allow microphone and camera access.</p>
</div>

<!-- Waiting-for-interviewer overlay (agent worker joining/spinning up) -->
<div class="overlay hidden" id="overlay-waiting-agent">
  <div class="spinner"></div>
  <h2>Connecting you to your interviewer…</h2>
  <p id="waiting-agent-text">This usually takes just a few seconds. Please stay on this page.</p>
</div>

<!-- Audio unlock overlay (browser autoplay policy) -->
<div class="overlay hidden" id="overlay-audio" style="background:rgba(10,14,26,.92);z-index:200;">
  <div class="end-card">
    <div class="checkmark">🎧</div>
    <h2>Enable Audio</h2>
    <p style="margin-bottom:20px;">Click below to start the AI interviewer's audio.</p>
    <button id="btn-enable-audio"
      style="padding:14px 32px;background:#2563eb;color:#fff;border:none;border-radius:8px;
             font-size:16px;font-weight:600;cursor:pointer;">
      Start Interview Audio
    </button>
  </div>
</div>

<!-- End overlay -->
<div class="overlay hidden" id="overlay-ended">
  <div class="end-card">
    <div class="checkmark">✅</div>
    <h2>Interview Complete</h2>
    <p>Thank you for your time. We'll review your responses and be in touch within 2–3 business days.</p>
  </div>
</div>

<div class="header">
  <div class="logo">
    <div class="logo-dot"></div>
    <div class="logo-text">HR Recruited — Technical Screening</div>
  </div>
  <div class="header-meta">Room: {room_safe} &nbsp;|&nbsp; <span id="timer">00:00</span></div>
</div>

<div class="main">
  <div class="video-area">
    <div class="video-placeholder" id="video-placeholder">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17 10.5V7a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3.5l4 4v-11l-4 4z"/>
      </svg>
      Camera off
    </div>
    <video id="local-video" autoplay muted playsinline style="display:none;"></video>
    <div class="cam-badge" id="cam-badge">📷 You</div>
  </div>

  <div class="sidebar">
    <div class="agent-card">
      <div class="agent-avatar" id="agent-avatar">🤖</div>
      <div class="agent-name">AI Interviewer</div>
      <div class="agent-status" id="agent-status">Waiting to connect…</div>
      <div class="wave" id="wave">
        <div class="wave-bar"></div>
        <div class="wave-bar"></div>
        <div class="wave-bar"></div>
        <div class="wave-bar"></div>
        <div class="wave-bar"></div>
      </div>
      <div id="agent-speaking-text"></div>
    </div>

  </div>
</div>

<div class="status-bar">
  <div class="status-dot connecting" id="status-dot"></div>
  <span id="status-text">Connecting to interview room…</span>
  <span id="mic-status" style="margin-left:auto;font-size:11px;color:#6b7499;">Mic: —</span>
</div>

<div class="controls">
  <button class="ctrl-btn mic" id="btn-mic" title="Toggle microphone">🎙️</button>
  <button class="ctrl-btn end" id="btn-end" title="End interview">📵</button>
  <button class="ctrl-btn cam" id="btn-cam" title="Toggle camera">📷</button>
</div>

<script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.min.js"></script>
<script>
const LIVEKIT_URL = "{lk_url_safe}";
const TOKEN = "{token_safe}";

const {{ Room, RoomEvent, Track, createLocalVideoTrack }} = LivekitClient;

const room = new Room({{
  adaptiveStream: true,
  dynacast: true,
  audioCaptureDefaults: {{ echoCancellation: true, noiseSuppression: true, autoGainControl: true }},
}});

// ── DOM refs ──
const overlayConn    = document.getElementById("overlay-connecting");
const overlayWaitingAgent = document.getElementById("overlay-waiting-agent");
const waitingAgentText    = document.getElementById("waiting-agent-text");
const overlayEnded   = document.getElementById("overlay-ended");
const localVideo     = document.getElementById("local-video");
const videoPlaceholder = document.getElementById("video-placeholder");
const statusDot      = document.getElementById("status-dot");
const statusText     = document.getElementById("status-text");
const timerEl        = document.getElementById("timer");
const agentAvatar    = document.getElementById("agent-avatar");
const agentStatus    = document.getElementById("agent-status");
const agentSpeakText = document.getElementById("agent-speaking-text");
const waveBars       = document.querySelectorAll(".wave-bar");
const btnMic         = document.getElementById("btn-mic");
const btnCam         = document.getElementById("btn-cam");
const btnEnd         = document.getElementById("btn-end");

let micMuted = false;
let camOff   = false;
let startTime = null;
let timerInterval = null;
let localVideoTrack = null;
let micStatusEl = document.getElementById("mic-status");

function updateMicStatus(active, err) {{
  if (err) {{
    micStatusEl.textContent = "Mic: DENIED ⚠️";
    micStatusEl.style.color = "#ef4444";
    statusText.textContent = "⚠️ Microphone access denied — interviewer cannot hear you. Allow mic in browser and reload.";
  }} else if (active) {{
    micStatusEl.textContent = "Mic: Active 🟢";
    micStatusEl.style.color = "#34d399";
  }} else {{
    micStatusEl.textContent = "Mic: Muted 🔴";
    micStatusEl.style.color = "#ef4444";
  }}
}}

// ── Timer ──
function startTimer() {{
  startTime = Date.now();
  timerInterval = setInterval(() => {{
    const s = Math.floor((Date.now() - startTime) / 1000);
    const m = String(Math.floor(s / 60)).padStart(2, "0");
    const sec = String(s % 60).padStart(2, "0");
    timerEl.textContent = m + ":" + sec;
  }}, 1000);
}}

// ── Agent speaking state ──
function setAgentSpeaking(speaking) {{
  agentAvatar.classList.toggle("speaking", speaking);
  waveBars.forEach(b => b.classList.toggle("active", speaking));
  agentSpeakText.textContent = speaking ? "Speaking…" : "";
  if (speaking) agentStatus.textContent = "Speaking";
  else if (room.state === "connected") agentStatus.textContent = "Listening";
}}

// ── Waiting-for-interviewer overlay ──
let agentJoined = false;
let waitingAgentTimeout = null;

function hasAgentAlreadyJoined() {{
  for (const p of room.remoteParticipants.values()) {{
    if (p.identity && p.identity.startsWith("agent")) return true;
  }}
  return false;
}}

function showWaitingForAgent() {{
  if (agentJoined || hasAgentAlreadyJoined()) {{ agentJoined = true; return; }}
  overlayWaitingAgent.classList.remove("hidden");
  waitingAgentTimeout = setTimeout(() => {{
    if (!agentJoined) {{
      waitingAgentText.textContent =
        "This is taking longer than usual. Please hold on — if nothing happens " +
        "in another minute, try refreshing the page.";
    }}
  }}, 30000);
}}

function hideWaitingForAgent() {{
  agentJoined = true;
  overlayWaitingAgent.classList.add("hidden");
  if (waitingAgentTimeout) {{ clearTimeout(waitingAgentTimeout); waitingAgentTimeout = null; }}
}}

// ── Room events ──
const overlayAudio = document.getElementById("overlay-audio");
const btnEnableAudio = document.getElementById("btn-enable-audio");

// Browser autoplay policy: unlock audio on first user gesture
room.on(RoomEvent.AudioPlaybackStatusChanged, () => {{
  if (!room.canPlaybackAudio) {{
    overlayAudio.classList.remove("hidden");
  }} else {{
    overlayAudio.classList.add("hidden");
  }}
}});

btnEnableAudio.addEventListener("click", async () => {{
  await room.startAudio();
  overlayAudio.classList.add("hidden");
}});

room.on(RoomEvent.Connected, async () => {{
  overlayConn.classList.add("hidden");
  statusDot.className = "status-dot connected";
  statusText.textContent = "Connected — interview in progress";
  startTimer();
  showWaitingForAgent();
  // Attempt audio unlock immediately — works if browser allows autoplay
  try {{ await room.startAudio(); }} catch(e) {{}}

  // Enable microphone via LiveKit participant API
  try {{
    await room.localParticipant.setMicrophoneEnabled(true);
    updateMicStatus(true);
  }} catch(e) {{
    console.error("mic error", e);
    updateMicStatus(false, e.message);
  }}

  try {{
    localVideoTrack = await createLocalVideoTrack({{ resolution: {{ width: 1280, height: 720 }} }});
    const el = localVideoTrack.attach();
    localVideo.srcObject = el.srcObject || null;
    // Attach directly for local preview
    localVideo.style.display = "block";
    videoPlaceholder.style.display = "none";
    localVideoTrack.on("started", () => {{
      const videoEl = localVideoTrack.attach();
      localVideo.srcObject = videoEl.srcObject;
    }});
    await room.localParticipant.publishTrack(localVideoTrack);
  }} catch(e) {{ console.warn("camera error", e); }}
}});

room.on(RoomEvent.ParticipantConnected, (p) => {{
  if (p.identity && p.identity.startsWith("agent")) {{
    agentStatus.textContent = "Connected";
    statusText.textContent = "AI interviewer has joined";
    hideWaitingForAgent();
  }}
}});

room.on(RoomEvent.ParticipantDisconnected, (p) => {{
  if (p.identity && p.identity.startsWith("agent")) {{
    agentStatus.textContent = "Disconnected";
    setAgentSpeaking(false);
  }}
}});

room.on(RoomEvent.TrackSubscribed, (track, pub, participant) => {{
  if (track.kind === Track.Kind.Audio) {{
    const el = track.attach();
    document.body.appendChild(el);
  }}
}});

room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {{
  const agentSpeaking = speakers.some(s => s.identity && s.identity.startsWith("agent"));
  const meSpeaking    = speakers.some(s => s.identity === room.localParticipant.identity);
  setAgentSpeaking(agentSpeaking);
  if (meSpeaking && !agentSpeaking) statusText.textContent = "You are speaking…";
  else if (agentSpeaking) statusText.textContent = "AI interviewer is speaking…";
  else if (room.state === "connected") statusText.textContent = "Connected — interview in progress";

}});

// Auto-recover mic if the track gets unpublished unexpectedly
room.on(RoomEvent.LocalTrackUnpublished, (pub) => {{
  if (pub.kind === Track.Kind.Audio && !micMuted) {{
    setTimeout(async () => {{
      try {{
        await room.localParticipant.setMicrophoneEnabled(true);
        updateMicStatus(true);
      }} catch(e) {{ console.warn("mic recovery failed", e); }}
    }}, 1000);
  }}
}});

room.on(RoomEvent.Disconnected, () => {{
  clearInterval(timerInterval);
  statusDot.className = "status-dot ended";
  statusText.textContent = "Interview ended";
  overlayEnded.classList.remove("hidden");
}});

// ── Controls ──
btnMic.addEventListener("click", async () => {{
  micMuted = !micMuted;
  try {{
    await room.localParticipant.setMicrophoneEnabled(!micMuted);
    updateMicStatus(!micMuted);
  }} catch(e) {{ console.error("mic toggle error", e); }}
  btnMic.classList.toggle("muted", micMuted);
  btnMic.textContent = micMuted ? "🔇" : "🎙️";
}});

btnCam.addEventListener("click", async () => {{
  if (!localVideoTrack) return;
  camOff = !camOff;
  localVideoTrack.mute(camOff);
  btnCam.classList.toggle("off", camOff);
  btnCam.textContent = camOff ? "📵" : "📷";
  localVideo.style.display = camOff ? "none" : "block";
  videoPlaceholder.style.display = camOff ? "flex" : "none";
}});

btnEnd.addEventListener("click", async () => {{
  if (confirm("End the interview?")) {{
    await room.disconnect();
  }}
}});

// ── Connect ──
(async () => {{
  try {{
    await room.connect(LIVEKIT_URL, TOKEN);
  }} catch(err) {{
    overlayConn.innerHTML = `
      <div style="color:#ef4444;font-size:32px;">⚠️</div>
      <h2>Connection Failed</h2>
      <p>${{err.message || "Could not connect to the interview room. Please check your link and try again."}}</p>`;
  }}
}})();
</script>
</body>
</html>"""


@app.get("/call-logs", tags=["Call Logs"])
async def list_call_logs_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter: completed | no_show | incomplete"),
    status: Optional[str] = Query(None, description="Filter: pending_retry | retried | exhausted | closed"),
):
    """List initial_screening_logs entries with optional category and status filters."""
    return cl_list(skip=skip, limit=limit, category=category, status=status)


@app.get("/call-stats", tags=["Call Logs"])
async def call_stats_endpoint():
    """Aggregated counts for dashboard metrics."""
    return cl_stats()


@app.post("/call-logs/{log_id}/retry-now", tags=["Call Logs"])
async def manual_retry_endpoint(log_id: str):
    """Force the log's next_retry_at to NOW so the retry scheduler picks it up."""
    ok = cl_manual_retry(log_id)
    if not ok:
        raise HTTPException(404, "Log not found or not retriable")
    return {"success": True, "message": "Will retry on next scheduler tick"}


@app.post("/call-logs/{log_id}/close", tags=["Call Logs"])
async def close_log_endpoint(log_id: str):
    """Mark a call_log as closed (terminal state, no more retries)."""
    ok = cl_close(log_id)
    if not ok:
        raise HTTPException(404, "Log not found")
    return {"success": True}


def _render_picker_page(booking: dict) -> str:
    from collections import defaultdict
    from datetime import datetime as _dt

    grouped = defaultdict(list)
    day_meta = {}
    for iso in booking.get("available_slots") or []:
        dt = _dt.fromisoformat(iso)
        key = dt.strftime("%Y-%m-%d")
        if key not in day_meta:
            day_meta[key] = {
                "weekday": dt.strftime("%a").upper(),
                "day_num": dt.strftime("%d"),
                "month": dt.strftime("%b %Y"),
                "full": dt.strftime("%A, %B %d, %Y"),
            }
        grouped[key].append((iso, dt.strftime("%I:%M %p").lstrip("0")))

    day_tabs = ""
    slot_panels = ""
    for idx, (key, items) in enumerate(grouped.items()):
        meta = day_meta[key]
        active = " active" if idx == 0 else ""
        day_tabs += f'''
          <button class="day-tab{active}" data-day="{key}">
            <span class="dt-weekday">{meta["weekday"]}</span>
            <span class="dt-num">{meta["day_num"]}</span>
            <span class="dt-month">{meta["month"].split()[0]}</span>
          </button>'''
        buttons = "".join(
            f'<button class="slot" data-slot="{html.escape(iso)}">{html.escape(label)}</button>'
            for iso, label in items
        )
        slot_panels += f'''
          <div class="slot-panel{active}" data-day="{key}">
            <div class="panel-head">{meta["full"]}</div>
            <div class="slot-grid">{buttons}</div>
          </div>'''

    token = booking["_id"]
    # candidate_name comes from the CV (untrusted); escape it and every other
    # interpolated field to prevent stored XSS on this public-by-token page.
    name = html.escape(str(booking.get("candidate_name", "Candidate")))
    score = html.escape(str(booking.get("interview_score", "")))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Schedule Interview</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Google Sans','Roboto',-apple-system,BlinkMacSystemFont,sans-serif;
       background:#f0f4f9;color:#202124;min-height:100vh;padding:32px 16px;}}
  .container{{max-width:920px;margin:0 auto;background:#fff;border-radius:16px;
              box-shadow:0 1px 3px rgba(60,64,67,.08),0 4px 16px rgba(60,64,67,.12);
              overflow:hidden;}}
  header{{padding:28px 32px;border-bottom:1px solid #e8eaed;
         background:linear-gradient(135deg,#1a73e8 0%,#4285f4 100%);color:#fff;}}
  header h1{{font-size:22px;font-weight:500;letter-spacing:.2px;margin-bottom:6px;}}
  header p{{font-size:14px;opacity:.92;}}
  .badge{{display:inline-block;background:rgba(255,255,255,.22);padding:3px 10px;
         border-radius:12px;font-size:12px;font-weight:500;margin-left:8px;}}
  .body{{display:grid;grid-template-columns:200px 1fr;gap:0;min-height:420px;}}
  .day-list{{border-right:1px solid #e8eaed;padding:16px 0;background:#fafbfc;
            overflow-y:auto;max-height:540px;}}
  .day-tab{{display:flex;flex-direction:column;align-items:center;width:100%;padding:12px 8px;
          background:transparent;border:none;border-left:3px solid transparent;cursor:pointer;
          font-family:inherit;color:#5f6368;transition:all .15s;}}
  .day-tab:hover{{background:#f1f3f4;}}
  .day-tab.active{{background:#e8f0fe;border-left-color:#1a73e8;color:#1a73e8;}}
  .dt-weekday{{font-size:11px;font-weight:500;letter-spacing:1px;opacity:.7;}}
  .dt-num{{font-size:24px;font-weight:500;line-height:1.1;margin:2px 0;}}
  .dt-month{{font-size:11px;opacity:.7;}}
  .panel-wrap{{padding:24px 28px;}}
  .slot-panel{{display:none;}}
  .slot-panel.active{{display:block;}}
  .panel-head{{font-size:15px;font-weight:500;color:#202124;margin-bottom:18px;
              padding-bottom:12px;border-bottom:1px solid #e8eaed;}}
  .slot-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:10px;}}
  .slot{{padding:14px 8px;border:1px solid #dadce0;background:#fff;color:#1a73e8;
        border-radius:8px;cursor:pointer;font-family:inherit;font-size:14px;font-weight:500;
        transition:all .15s;}}
  .slot:hover{{background:#e8f0fe;border-color:#1a73e8;box-shadow:0 1px 3px rgba(26,115,232,.2);}}
  .slot:disabled{{opacity:.4;cursor:wait;}}
  .footer{{padding:14px 32px;background:#fafbfc;border-top:1px solid #e8eaed;
          font-size:12px;color:#5f6368;display:flex;justify-content:space-between;align-items:center;}}
  #status{{font-weight:500;color:#1a73e8;}}
  #status.error{{color:#d93025;}}
  @media (max-width:680px){{
    .body{{grid-template-columns:1fr;}}
    .day-list{{display:flex;overflow-x:auto;border-right:none;border-bottom:1px solid #e8eaed;max-height:none;padding:8px;}}
    .day-tab{{min-width:72px;border-left:none;border-bottom:3px solid transparent;}}
    .day-tab.active{{border-left:none;border-bottom-color:#1a73e8;}}
  }}
</style></head>
<body>
  <div class="container">
    <header>
      <h1>Schedule Your Interview <span class="badge">Score {score}/100</span></h1>
      <p>Hi {name} — pick a time that works for you (Asia/Karachi)</p>
    </header>
    <div class="body">
      <div class="day-list">{day_tabs}</div>
      <div class="panel-wrap">{slot_panels}</div>
    </div>
    <div class="footer">
      <span>Duration: 30 minutes &middot; Google Meet</span>
      <span id="status"></span>
    </div>
  </div>
<script>
const TOKEN="{token}";
document.querySelectorAll(".day-tab").forEach(t=>t.addEventListener("click",()=>{{
  const d=t.dataset.day;
  document.querySelectorAll(".day-tab").forEach(x=>x.classList.toggle("active",x===t));
  document.querySelectorAll(".slot-panel").forEach(p=>p.classList.toggle("active",p.dataset.day===d));
}}));
document.querySelectorAll(".slot").forEach(b=>b.addEventListener("click",async()=>{{
  const slot=b.dataset.slot;
  const status=document.getElementById("status");
  document.querySelectorAll(".slot").forEach(x=>x.disabled=true);
  status.classList.remove("error");
  status.textContent="Booking your slot...";
  try{{
    const r=await fetch(`/api/booking/${{TOKEN}}/select`,{{
      method:"POST",headers:{{"Content-Type":"application/json"}},
      body:JSON.stringify({{slot}})
    }});
    const j=await r.json();
    if(j.ok){{window.location.href=`/book/${{TOKEN}}/confirmed`;}}
    else{{status.classList.add("error");status.textContent="Error: "+(j.error||"unknown");
         document.querySelectorAll(".slot").forEach(x=>x.disabled=false);}}
  }}catch(e){{status.classList.add("error");status.textContent="Network error.";
       document.querySelectorAll(".slot").forEach(x=>x.disabled=false);}}
}}));
</script></body></html>"""


def _render_confirmed_page(booking: dict) -> str:
    meet = html.escape(booking.get("meet_link") or "")
    slot_iso = booking.get("selected_slot") or ""
    name = html.escape(str(booking.get("candidate_name", "")))
    try:
        from datetime import datetime as _dt
        dt = _dt.fromisoformat(slot_iso)
        when_day = dt.strftime("%A, %B %d, %Y")
        when_time = dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        when_day = html.escape(slot_iso)
        when_time = ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Interview Confirmed</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Google Sans','Roboto',-apple-system,sans-serif;background:#f0f4f9;
       color:#202124;min-height:100vh;display:flex;align-items:center;justify-content:center;
       padding:24px;}}
  .card{{max-width:520px;width:100%;background:#fff;border-radius:16px;
        box-shadow:0 1px 3px rgba(60,64,67,.08),0 4px 16px rgba(60,64,67,.12);overflow:hidden;}}
  .check{{padding:36px 24px 16px;text-align:center;
         background:linear-gradient(135deg,#0f9d58 0%,#34a853 100%);color:#fff;}}
  .check svg{{width:56px;height:56px;background:rgba(255,255,255,.22);border-radius:50%;
             padding:14px;margin-bottom:12px;}}
  .check h1{{font-size:22px;font-weight:500;}}
  .check p{{font-size:14px;opacity:.92;margin-top:4px;}}
  .body{{padding:24px 28px;}}
  .row{{display:flex;align-items:flex-start;gap:14px;padding:14px 0;border-bottom:1px solid #f1f3f4;}}
  .row:last-child{{border-bottom:none;}}
  .icon{{width:36px;height:36px;background:#e8f0fe;color:#1a73e8;border-radius:50%;
        display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:18px;}}
  .row .label{{font-size:12px;color:#5f6368;text-transform:uppercase;letter-spacing:.5px;
              font-weight:500;margin-bottom:2px;}}
  .row .value{{font-size:15px;color:#202124;font-weight:500;}}
  .row .value a{{color:#1a73e8;text-decoration:none;word-break:break-all;}}
  .row .value a:hover{{text-decoration:underline;}}
  .footer{{padding:14px 28px;background:#fafbfc;border-top:1px solid #e8eaed;
          font-size:12px;color:#5f6368;text-align:center;}}
</style></head>
<body>
  <div class="card">
    <div class="check">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5z"/></svg>
      <h1>Interview Confirmed</h1>
      <p>A calendar invite has been emailed to you</p>
    </div>
    <div class="body">
      <div class="row">
        <div class="icon">&#128197;</div>
        <div><div class="label">Date</div><div class="value">{when_day}</div></div>
      </div>
      <div class="row">
        <div class="icon">&#128338;</div>
        <div><div class="label">Time</div><div class="value">{when_time} (Asia/Karachi)</div></div>
      </div>
      <div class="row">
        <div class="icon">&#127909;</div>
        <div><div class="label">Google Meet</div><div class="value"><a href="{meet}">{meet}</a></div></div>
      </div>
      <div class="row">
        <div class="icon">&#128100;</div>
        <div><div class="label">Candidate</div><div class="value">{name}</div></div>
      </div>
    </div>
    <div class="footer">Need to reschedule? Reply to the calendar invite email.</div>
  </div>
</body></html>"""


@app.get("/book/{token}", tags=["Booking"], response_class=HTMLResponse)
async def show_booking_page(token: str):
    booking = get_booking(token)
    if not booking:
        return HTMLResponse("<h2>Invalid booking link.</h2>", status_code=404)
    if booking["status"] == "booked":
        return HTMLResponse(_render_confirmed_page(booking))
    expires = booking["expires_at"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        return HTMLResponse("<h2>This link has expired. Please contact HR.</h2>", status_code=410)
    return HTMLResponse(_render_picker_page(booking))


@app.post("/api/booking/{token}/select", tags=["Booking"])
async def api_select_slot(token: str, payload: dict = Body(...)):
    slot = payload.get("slot")
    if not slot:
        raise HTTPException(400, "slot is required")

    # Create the calendar event + Meet link (existing behaviour, preserved).
    result = await asyncio.to_thread(select_slot, token, slot)

    # If this booking belongs to a paused pipeline thread, resume it with the
    # chosen slot + Meet link. Thread is resolved token -> candidate_id -> screened.
    if result.get("ok"):
        booking = get_booking(token)
        screened = _screened().find_one({"_id": (booking or {}).get("candidate_id")})
        thread_id = (screened or {}).get("thread_id")
        if thread_id:
            agent = _get_pipeline_agent()
            cfg = {"configurable": {"thread_id": thread_id}}
            snap = await asyncio.to_thread(agent.get_state, cfg)
            if getattr(snap, "next", None):  # still paused at book -> resume
                await asyncio.to_thread(
                    agent.invoke,
                    Command(resume={
                        "selected_slot": slot, "meet_link": result.get("meet_link"),
                    }),
                    cfg,
                )
    return result


@app.get("/book/{token}/confirmed", tags=["Booking"], response_class=HTMLResponse)
async def show_confirmed_page(token: str):
    booking = get_booking(token)
    if not booking or booking["status"] != "booked":
        return HTMLResponse("<h2>No confirmed booking found.</h2>", status_code=404)
    return HTMLResponse(_render_confirmed_page(booking))


@app.post("/jobs/{jd_id}/criteria/generate", tags=["Criteria"])
async def generate_job_criteria(jd_id: str):
    """Generate evaluation criteria from the JD text and save as draft."""
    jd = _get_job_descriptions_collection().find_one({"_id": jd_id})
    if not jd:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Job not found: {jd_id}")
    jd_text = jd.get("job_description", "")
    if not jd_text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Job description is empty")
    doc = await asyncio.to_thread(generate_criteria, jd_id, jd_text)
    doc["_id"] = str(doc["_id"])
    return doc


@app.get("/jobs/{jd_id}/criteria", tags=["Criteria"])
async def get_job_criteria(jd_id: str):
    """Fetch current criteria (draft or confirmed) for a job."""
    doc = await asyncio.to_thread(get_criteria, jd_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No criteria found for job: {jd_id}")
    doc["_id"] = str(doc["_id"])
    return doc


@app.put("/jobs/{jd_id}/criteria", tags=["Criteria"])
async def update_job_criteria(jd_id: str, body: CriteriaUpdateRequest):
    """Replace the full criteria list (keeps draft status)."""
    try:
        doc = await asyncio.to_thread(update_criteria, jd_id, body.criteria)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    doc["_id"] = str(doc["_id"])
    return doc


@app.post("/jobs/{jd_id}/criteria/confirm", tags=["Criteria"])
async def confirm_job_criteria(jd_id: str):
    """Lock criteria as confirmed, then publish the job to LinkedIn — the
    listing only goes live once scoring criteria exist for it, never before."""
    try:
        doc = await asyncio.to_thread(confirm_criteria, jd_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    doc["_id"] = str(doc["_id"])

    try:
        await asyncio.to_thread(publish_job_to_linkedin, jd_id)
        doc["linkedin_posted"] = True
    except Exception as e:  # noqa: BLE001
        doc["linkedin_posted"] = False
        doc["linkedin_error"] = str(e)
        print(f"[linkedin] publish failed for jd_id={jd_id}: {e!r}", file=sys.stderr)

    return doc


@app.get("/health", tags=["Health Check"])
async def health_check():
    # Liveness only: is the process up? Does NOT check dependencies.
    return {"status": "ok"}


_ready_client = None


def _readiness_db_client():
    # Dedicated short-timeout client so a down DB fails the probe fast (not 30s).
    global _ready_client
    if _ready_client is None:
        from pymongo import MongoClient
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _ready_client = MongoClient(uri, serverSelectionTimeoutMS=2000)
    return _ready_client


@app.get("/ready", tags=["Health Check"])
async def readiness_check():
    # Readiness: can we actually serve traffic (is MongoDB reachable)?
    try:
        await asyncio.to_thread(_readiness_db_client().admin.command, "ping")
        return {"status": "ready"}
    except Exception:  # noqa: BLE001
        return JSONResponse(
            status_code=503, content={"status": "not ready", "reason": "database unavailable"}
        )