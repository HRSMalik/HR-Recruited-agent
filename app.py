import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Header, File, UploadFile, status, Form, Query, Depends, Body
from fastapi.responses import Response, JSONResponse, HTMLResponse
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
from booking_agent import get_booking, select_slot
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
            f'<button class="slot" data-slot="{iso}">{label}</button>'
            for iso, label in items
        )
        slot_panels += f'''
          <div class="slot-panel{active}" data-day="{key}">
            <div class="panel-head">{meta["full"]}</div>
            <div class="slot-grid">{buttons}</div>
          </div>'''

    token = booking["_id"]
    name = booking.get("candidate_name", "Candidate")
    score = booking.get("interview_score", "")
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
    meet = booking.get("meet_link") or ""
    slot_iso = booking.get("selected_slot") or ""
    name = booking.get("candidate_name", "")
    try:
        from datetime import datetime as _dt
        dt = _dt.fromisoformat(slot_iso)
        when_day = dt.strftime("%A, %B %d, %Y")
        when_time = dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        when_day = slot_iso
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
    result = await asyncio.to_thread(select_slot, token, slot)
    return result


@app.get("/book/{token}/confirmed", tags=["Booking"], response_class=HTMLResponse)
async def show_confirmed_page(token: str):
    booking = get_booking(token)
    if not booking or booking["status"] != "booked":
        return HTMLResponse("<h2>No confirmed booking found.</h2>", status_code=404)
    return HTMLResponse(_render_confirmed_page(booking))


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}