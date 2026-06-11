import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Header, File, UploadFile, status, Form, Query, Depends
from fastapi.responses import Response, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from schemas import JobPostAgentRequest, HumanFeedback, JobPostAgentResult, CandidateListResponse, JobListResponse
import uuid

from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from job_post import create_workflow_agent, _get_job_descriptions_collection
from parser_agent import _get_candidates_collection, ingest_new_applicants
from shortlisting_agent import shortlist_all_jobs
from voice_agent import call_top_candidates, record_call_result, list_screened_candidates, _initiate_vapi_call, _screened, _candidates, _normalize_phone
from call_logs import (
    list_call_logs as cl_list,
    call_stats as cl_stats,
    manual_retry as cl_manual_retry,
    close_log as cl_close,
    process_retries as cl_process_retries,
)
from typing import Optional
from datetime import datetime, timezone
import uuid


async def _shortlist_loop(interval_seconds: int):
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            print(f"[ingest] tick: running ingest_new_applicants", file=sys.stderr)
            ingest_summary = await asyncio.to_thread(ingest_new_applicants)
            print(f"[ingest] done: {ingest_summary}", file=sys.stderr)

            print(f"[shortlist] tick: running shortlist_all_jobs", file=sys.stderr)
            shortlist_summary = await asyncio.to_thread(shortlist_all_jobs)
            print(f"[shortlist] done: {shortlist_summary}", file=sys.stderr)

            print(f"[voice] tick: running call_top_candidates", file=sys.stderr)
            voice_summary = await asyncio.to_thread(call_top_candidates)
            print(f"[voice] done: {voice_summary}", file=sys.stderr)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            print(f"[scheduler] error: {e!r}", file=sys.stderr)


async def _retry_loop(interval_seconds: int = 60):
    """Dedicated background loop that fires pending retries from call_logs."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            result = await asyncio.to_thread(
                cl_process_retries,
                _initiate_vapi_call,
                _candidates(),
                _screened(),
                _normalize_phone,
            )
            if result["retried"] or result["errors"]:
                print(f"[retry] tick: {result}", file=sys.stderr)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            print(f"[retry] error: {e!r}", file=sys.stderr)


@asynccontextmanager
async def lifespan(app: FastAPI):
    interval = int(os.getenv("SHORTLIST_INTERVAL_SECONDS", "3600"))
    retry_interval = int(os.getenv("RETRY_LOOP_INTERVAL_SECONDS", "60"))
    shortlist_task = asyncio.create_task(_shortlist_loop(interval))
    retry_task = asyncio.create_task(_retry_loop(retry_interval))
    print(f"[shortlist] scheduler started; interval={interval}s", file=sys.stderr)
    print(f"[retry] scheduler started; interval={retry_interval}s", file=sys.stderr)
    try:
        yield
    finally:
        shortlist_task.cancel()
        retry_task.cancel()
        for t in (shortlist_task, retry_task):
            try:
                await t
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Recruitment Module API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        collection.find(query, {"name": 1, "fit_percent": 1, "jd_id": 1})
        .sort("fit_percent", -1)
        .skip(skip)
        .limit(limit)
    )
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


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


TEST_CALL_PHONE = "+923219499451"
TEST_CALL_EMAIL = "filzanoornaeem@gmail.com"
TEST_CALL_NAME = "Test Candidate"


@app.post("/test-call", tags=["Test"])
async def trigger_test_call():
    """Manual trigger: call the configured test phone using the latest HR-equipped job.
    Runs the full automatic flow after the call ends (score, insights, meeting)."""
    job = _get_job_descriptions_collection().find_one(
        {"primary_hr_email": {"$exists": True, "$ne": None}},
        sort=[("_id", -1)],
    )
    if not job:
        raise HTTPException(400, "No job with primary_hr_email found. Create a job first.")

    call_id = _initiate_vapi_call(TEST_CALL_PHONE)
    if not call_id:
        raise HTTPException(500, "Vapi did not return a call_id.")

    test_id = str(uuid.uuid4())
    _screened().insert_one({
        "_id": test_id,
        "name": TEST_CALL_NAME,
        "phone": TEST_CALL_PHONE,
        "phone_e164": TEST_CALL_PHONE,
        "email": TEST_CALL_EMAIL,
        "fit_percent": 100,
        "jd_id": job["_id"],
        "call_id": call_id,
        "status": "calling",
        "called_at": datetime.now(timezone.utc),
        "triggered_by": "test",
    })

    return {
        "success": True,
        "call_id": call_id,
        "phone": TEST_CALL_PHONE,
        "email": TEST_CALL_EMAIL,
        "test_id": test_id,
        "job_id": job["_id"],
    }


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

    await asyncio.to_thread(
        record_call_result, call_id, transcript, summary, end_reason, duration
    )
    return {"received": True}


@app.get("/call-logs", tags=["Call Logs"])
async def list_call_logs_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Filter: completed | cancelled | declined"),
    status: Optional[str] = Query(None, description="Filter: pending_retry | retried | exhausted | closed"),
):
    """List call_logs entries with optional category and status filters."""
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


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}