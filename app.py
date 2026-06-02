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
from voice_agent import call_top_candidates, record_call_result


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    interval = int(os.getenv("SHORTLIST_INTERVAL_SECONDS", "3600"))
    task = asyncio.create_task(_shortlist_loop(interval))
    print(f"[shortlist] scheduler started; interval={interval}s", file=sys.stderr)
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
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


@app.post("/voice/webhook", tags=["Voice"])
async def voice_webhook(payload: dict):
    """Receive end-of-call reports from Vapi. Persists transcript + summary
    and scores the interview into `screened_candidates`."""
    msg = payload.get("message") or {}
    if msg.get("type") != "end-of-call-report":
        return {"received": True, "ignored": True}

    call = msg.get("call") or {}
    call_id = call.get("id")
    if not call_id:
        return {"received": True, "error": "missing call_id"}

    transcript = (
        (msg.get("artifact") or {}).get("transcript")
        or msg.get("transcript")
        or ""
    )
    summary = (
        (msg.get("analysis") or {}).get("summary")
        or msg.get("summary")
        or ""
    )

    await asyncio.to_thread(record_call_result, call_id, transcript, summary)
    return {"received": True}


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}