"""Voice screening agent — LiveKit-based browser interview.

Flow:
  1. `_start_livekit_interview()` creates a LiveKit room with JD/candidate
     metadata, generates a JWT for the candidate, and emails them a link to
     /interview/{room_name}.
  2. The candidate opens the link in a browser; the LiveKit agent worker
     (livekit_agent.py, running locally) auto-dispatches and joins the room.
  3. After the interview the agent POSTs the transcript to
     /voice/livekit-complete, which resumes the pipeline.
  4. `score_and_persist_call()` scores and persists — unchanged from before.

Local dev setup:
    livekit-server --dev          # terminal 1
    python livekit_agent.py dev   # terminal 2
    uvicorn app:app --reload      # terminal 3
"""
import asyncio
import logging
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

from langchain.chat_models import init_chat_model
from utils.schemas import InterviewEvaluation
from dotenv import load_dotenv

import config
logger = logging.getLogger(__name__)

load_dotenv()

DEFAULT_COUNTRY_CODE = config.VAPI_DEFAULT_COUNTRY_CODE
_LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
_LIVEKIT_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
_LIVEKIT_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")




def _get_db():
    from services.db import get_db
    return get_db()


def _candidates():
    return _get_db()["candidates_info"]


def _screened():
    return _get_db()["screened_candidates"]


def _insights_collection():
    return _get_db()["interview_insights"]


def _meetings_collection():
    return _get_db()["meetings"]


def _jobs_collection():
    return _get_db()["job_descriptions"]


def list_screened_candidates(
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    min_score: Optional[int] = None,
) -> dict:
    """List screened candidates with optional filters, enriched with insights + meeting.

    Filters:
      - status: "calling" | "completed" (omitted = all)
      - min_score: only return rows where interview_score >= min_score
    Returns: {"items": [...], "total": N, "skip": S, "limit": L}
    """
    query: dict = {}
    if status:
        query["status"] = status
    if min_score is not None:
        query["interview_score"] = {"$gte": min_score}

    coll = _screened()
    total = coll.count_documents(query)
    docs = list(coll.find(query).sort("called_at", -1).skip(skip).limit(limit))
    if not docs:
        return {"items": [], "total": total, "skip": skip, "limit": limit}

    ids = [d["_id"] for d in docs]
    insights_map = {i["_id"]: i for i in _insights_collection().find({"_id": {"$in": ids}})}
    meetings_map = {m["_id"]: m for m in _meetings_collection().find({"_id": {"$in": ids}})}

    for d in docs:
        d["_id"] = str(d["_id"])
        cid = d["_id"]
        ins = insights_map.get(cid)
        if ins:
            ins["_id"] = str(ins["_id"])
        mtg = meetings_map.get(cid)
        if mtg:
            mtg["_id"] = str(mtg["_id"])
        d["insights"] = ins
        d["meeting"] = mtg

    return {"items": docs, "total": total, "skip": skip, "limit": limit}


def _collect_hr_attendees(job: Optional[dict]) -> list[str]:
    """Job se primary HR + team member emails collect karo.

    Order: primary HR first (used for freebusy lookup), then team members.
    Duplicates removed, order preserved.
    Raises ValueError if job has no primary_hr_email (required field).
    """
    if not job or not job.get("primary_hr_email"):
        raise ValueError("Job has no primary_hr_email; cannot schedule meeting.")
    emails: list[str] = [job["primary_hr_email"]]
    for m in job.get("team_members") or []:
        email = (m or {}).get("email")
        if email:
            emails.append(email)
    seen: set[str] = set()
    return [e for e in emails if not (e in seen or seen.add(e))]


def _normalize_phone(raw) -> Optional[str]:
    """Normalize CV phone strings into E.164, defaulting to the configured region.

    The app is Pakistan-centric, so VAPI_DEFAULT_COUNTRY_CODE defaults to +92 and
    the common local formats are handled (a bare leading 0 is the national trunk
    prefix, NOT part of an E.164 number):

      03001234567    -> strip trunk 0  -> +92 3001234567
      3001234567     -> bare national  -> +92 3001234567
      923001234567   -> already has CC -> +923001234567
      00923001234567 -> 00 intl prefix -> +923001234567
      +923001234567  -> already E.164   -> +923001234567

    Returns None if the result isn't a plausible E.164 number (11-15 digits).
    """
    if not raw:
        return None
    s = str(raw).strip()

    # Already E.164 — only validate the digit count.
    if s.startswith("+"):
        digits = re.sub(r"\D", "", s[1:])
        return f"+{digits}" if 11 <= len(digits) <= 15 else None

    digits = re.sub(r"\D", "", s)
    if not digits:
        return None

    cc = re.sub(r"\D", "", DEFAULT_COUNTRY_CODE)  # e.g. "92"
    if digits.startswith("00"):
        digits = digits[2:]                       # 00 = international access prefix
    elif digits.startswith("0"):
        digits = cc + digits[1:]                  # national trunk 0 -> country code
    elif digits.startswith(cc) and len(digits) >= 11:
        pass                                      # already carries the country code
    else:
        digits = cc + digits                      # bare national number

    return f"+{digits}" if 11 <= len(digits) <= 15 else None


def _livekit_http_url() -> str:
    """Convert ws:// LiveKit URL to http:// for REST API calls."""
    return _LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://")


def _gen_candidate_token(room_name: str, identity: str) -> str:
    """Generate a signed JWT for a candidate to join a LiveKit room."""
    from livekit.api import AccessToken, VideoGrants
    token = (
        AccessToken(api_key=_LIVEKIT_KEY, api_secret=_LIVEKIT_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
    )
    return token.to_jwt()


async def _create_livekit_room(room_name: str, metadata: str) -> None:
    """Create a LiveKit room with candidate/JD metadata."""
    from livekit import api as lk_api
    http_url = _livekit_http_url()
    lk = lk_api.LiveKitAPI(url=http_url, api_key=_LIVEKIT_KEY, api_secret=_LIVEKIT_SECRET)
    try:
        await lk.room.create_room(
            lk_api.CreateRoomRequest(
                name=room_name,
                metadata=metadata,
                empty_timeout=900,
                max_participants=5,
            )
        )
    finally:
        await lk.aclose()


def _start_livekit_interview(state: dict, pipeline_config: Optional[dict] = None) -> Optional[str]:
    """Create a LiveKit room, email the candidate the interview link.

    Returns room_name (stored as call_id in screened_candidates), or None on failure.
    Pipeline nodes run in threads (via asyncio.to_thread), so asyncio.run() is safe here.
    """
    cv_id: str = state["cv_id"]
    jd_id: str = state.get("jd_id", "")
    candidate_name: str = state.get("name") or "Candidate"
    email: Optional[str] = state.get("email")

    jd_doc = _jobs_collection().find_one({"_id": jd_id})
    jd_text: str = (jd_doc or {}).get("job_description", "")

    room_name = f"interview-{uuid.uuid4().hex[:12]}"
    meta = json.dumps({
        "cv_id": cv_id, "jd_id": jd_id,
        "jd_text": jd_text[:2000],
        "candidate_name": candidate_name,
    })

    try:
        asyncio.run(_create_livekit_room(room_name, meta))
    except Exception as e:
        logger.error(f"[livekit] room creation failed: {e!r}")
        return None

    token = _gen_candidate_token(room_name, candidate_name)
    thread_id = ((pipeline_config or {}).get("configurable") or {}).get("thread_id")

    _screened().insert_one({
        "_id": cv_id,
        "name": candidate_name,
        "phone": state.get("phone"),
        "email": email,
        "fit_percent": state.get("fit_percent"),
        "jd_id": jd_id,
        "experience_years": state.get("experience_years"),
        "last_education_degree": state.get("last_education_degree"),
        "call_id": room_name,
        "room_name": room_name,
        "thread_id": thread_id,
        "status": "interview_ready",
        "called_at": datetime.now(timezone.utc),
    })

    if email:
        base_url = os.getenv("BOOKING_BASE_URL", "http://localhost:8000")
        url = f"{base_url}/interview/{room_name}?token={token}"
        try:
            from services.email_agent import send_email
            send_email(
                to=email,
                subject="Your Technical Interview Is Ready — Join Now",
                html_body=_interview_invite_html(candidate_name, url),
            )
        except Exception as e:
            logger.error(f"[livekit] email failed for {email}: {e!r}")

    logger.warning(f"[livekit] room={room_name} created for cv_id={cv_id}")
    return room_name


def _interview_invite_html(name: str, url: str) -> str:
    import html as _html
    name = _html.escape(str(name))
    url = _html.escape(str(url))
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;max-width:560px;margin:auto;">
      <h2 style="color:#1a73e8;">You're Invited to Your Technical Interview</h2>
      <p>Hi {name},</p>
      <p>You've been selected to proceed to the technical screening interview.</p>
      <p style="margin:24px 0;">
        <a href="{url}" style="background:#1a73e8;color:#fff;padding:12px 24px;
           text-decoration:none;border-radius:4px;font-weight:bold;">
          Join Interview
        </a>
      </p>
      <p style="color:#666;font-size:13px;">
        The interview will be conducted by an AI assistant in your browser.<br/>
        Make sure you have a working microphone and camera.
      </p>
      <p>Best regards,<br/>HR Team</p>
    </body></html>
    """


_MAX_JD_CHARS = 2000



def _calculate_interview_score(evaluation: InterviewEvaluation) -> int:
    """Assemble final 0-100 interview score from Pydantic evaluation."""
    skills      = (evaluation.skill_match / 2.0) * 55
    experience  = evaluation.experience_fit * 25
    comm        = evaluation.communication_clarity * 5
    engagement  = evaluation.engagement_motivation * 15
    return max(0, min(100, round(skills + experience + comm + engagement)))


def _score_interview(transcript: str, summary: str, job_description: Optional[str] = None) -> dict:
    """Classify interview against JD via structured output; assemble score manually.

    Returns: {"score": int 0-100, "red_flags": list[str]}
    """
    jd_block = (job_description or "").strip()[:_MAX_JD_CHARS]
    jd_section = (
        f"=== JOB DESCRIPTION ===\n{jd_block}"
        if jd_block
        else "=== JOB DESCRIPTION ===\n(not available — score on general fit)"
    )

    prompt = f"""You are a senior recruiter scoring a phone-screen interview against a job.
Classify each criterion on its defined scale. Cite evidence from the transcript.

{jd_section}

=== INTERVIEW ===
Summary: {summary or "(no summary)"}
Transcript: {transcript or "(no transcript)"}

ASR ERRORS — this transcript is from automated speech recognition over a phone call.
Correct phonetic corruptions before scoring: "Langkain"→LangChain, "Fortress"→Postgres,
"Mango"→MongoDB, "Fast AP"→FastAPI, "pie torch"→PyTorch, "cuber netes"→Kubernetes.
Only correct when context is clearly about tools/skills. Do NOT penalize ASR errors.

EQUIVALENT SKILLS (treat as matching — do not penalise same-family tools):
  Pandas ≈ Polars ≈ Dask ≈ PySpark | PyTorch ≈ TensorFlow ≈ JAX ≈ Keras
  scikit-learn ≈ XGBoost ≈ LightGBM | FastAPI ≈ Flask ≈ Django REST ≈ Express
  React ≈ Vue ≈ Svelte ≈ Angular | PostgreSQL ≈ MySQL ≈ MariaDB
  MongoDB ≈ DynamoDB ≈ Firestore | AWS ≈ GCP ≈ Azure
  LangChain ≈ LlamaIndex ≈ Haystack | Docker/Podman; Kubernetes ≈ Docker Swarm
  GitHub Actions ≈ GitLab CI ≈ CircleCI | Airflow ≈ Prefect ≈ Dagster

GUIDELINES:
- Phone screens are SHORT (2-5 min). Judge quality, not length.
- A candidate naming required tech with one concrete example is a strong fit.
- Only list red_flags grounded in the transcript. Empty list if none."""

    llm = init_chat_model(config.SCORING_MODEL, temperature=0)
    evaluation: InterviewEvaluation = llm.with_structured_output(InterviewEvaluation).invoke(prompt)

    score = _calculate_interview_score(evaluation)
    logger.info(f"Skill:       {evaluation.skill_match}/2  | {evaluation.skill_evidence}")
    logger.info(f"Experience:  {evaluation.experience_fit}/1  | {evaluation.experience_evidence}")
    logger.info(f"Clarity:     {evaluation.communication_clarity}/1")
    logger.info(f"Engagement:  {evaluation.engagement_motivation}/1")
    logger.info(f"Red flags:   {evaluation.red_flags}")
    logger.info(f"Score: {score}/100")
    return {"score": score, "red_flags": evaluation.red_flags}


def score_and_persist_call(
    doc: dict,
    transcript: str,
    summary: str,
    end_reason: str = "unknown",
    duration: int = 0,
    tone: Optional[str] = None,
    live_red_flags: Optional[list] = None,
) -> dict:
    """Shared scoring + persistence for a finished LiveKit interview (single source of truth).

    Used by BOTH the legacy webhook (record_call_result, e.g. /test-interview) and
    the pipeline (score_interview node) so the two paths can never drift: categorize
    the interview, log the attempt (schedules a fresh invite for no_show/incomplete),
    score completed interviews, compute composite + recommendation + hybrid red
    flags, and persist everything to screened_candidates + interview_insights.

    `tone`/`live_red_flags` come from the realtime agent's own live assessment tool
    call (native audio perception — tone, pacing, confidence — a text-only post-call
    analysis of the transcript could never capture this).

    `doc` is the screened_candidates row (provides _id, jd_id, fit_percent,
    experience_years, name, email, phone_e164, call_id, triggered_by).
    Returns {category, reason_label, interview_score, red_flags, composite_score,
    recommendation, call_log_status} for the caller to route on.
    """
    from services.call_logs import categorize_call, log_call_attempt
    from services.ranking_agent import compute_composite, detect_rule_flags, recommend

    cv_id = doc["_id"]
    call_id = doc.get("call_id")
    transcript = transcript or ""
    summary = summary or ""
    live_red_flags = live_red_flags or []
    category, reason_label = categorize_call(end_reason)

    interview_score: Optional[int] = None
    interview_flags: list = []
    composite_score: Optional[float] = None
    recommendation: Optional[str] = None
    red_flags: list = list(live_red_flags)
    if category == "completed":
        job = _jobs_collection().find_one({"_id": doc.get("jd_id")})
        scored = _score_interview(transcript, summary, (job or {}).get("job_description"))
        interview_score = scored["score"]
        interview_flags = scored["red_flags"]
        rule_flags = detect_rule_flags({
            "fit_percent": doc.get("fit_percent"),
            "interview_score": interview_score,
            "experience_years": doc.get("experience_years"),
        })
        red_flags = interview_flags + rule_flags + live_red_flags
        composite_score = compute_composite(doc.get("fit_percent") or 0, interview_score)["composite_score"]
        recommendation = recommend(composite_score, red_flags)

    log_entry = log_call_attempt(
        candidate_id=cv_id, jd_id=doc.get("jd_id"), call_id=call_id,
        category=category, reason=reason_label, end_reason=end_reason,
        transcript=transcript, duration=duration, score=interview_score,
        triggered_by=doc.get("triggered_by", "auto"),
    )

    _screened().update_one(
        {"_id": cv_id},
        {"$set": {
            "transcript": transcript,
            "summary": summary,
            "interview_score": interview_score,
            "interview_red_flags": interview_flags,
            "red_flags": red_flags,
            "interview_tone": tone,
            "composite_score": composite_score,
            "recommendation": recommendation,
            "status": category,
            "category_reason": reason_label,
            "end_reason": end_reason,
            "duration_seconds": duration,
            "completed_at": datetime.now(timezone.utc),
        }},
    )

    if category == "completed":
        try:
            from services.transcript_analyzer import extract_interview_insights
            insights = extract_interview_insights(transcript)
            insights.update({
                "_id": cv_id, "call_id": call_id,
                "candidate_name_from_form": doc.get("name"),
                "candidate_email": doc.get("email"),
                "candidate_phone": doc.get("phone_e164"),
                "jd_id": doc.get("jd_id"),
                "interview_score": interview_score,
                "extracted_at": datetime.now(timezone.utc),
            })
            _insights_collection().replace_one({"_id": cv_id}, insights, upsert=True)
        except Exception as e:  # noqa: BLE001
            logger.error(f"[insights] extraction failed for call_id={call_id}: {e!r}")

    return {
        "category": category, "reason_label": reason_label,
        "interview_score": interview_score, "red_flags": red_flags,
        "composite_score": composite_score, "recommendation": recommendation,
        "call_log_status": log_entry.get("status"),
    }


def record_call_result(
    call_id: str,
    transcript: str,
    summary: str,
    end_reason: str = "unknown",
    duration: int = 0,
    tone: Optional[str] = None,
    live_red_flags: Optional[list] = None,
) -> None:
    """Legacy Vapi webhook handler (non-pipeline calls, e.g. /test-call).

    Delegates the scoring + persistence to the shared `score_and_persist_call`
    helper (same logic the pipeline uses), then fires the legacy fire-and-forget
    booking email and persists the ranked record for completed interviews.
    """
    doc = _screened().find_one({"call_id": call_id})
    if not doc:
        logger.warning(f"[vapi] webhook for unknown call_id={call_id}")
        return

    result = score_and_persist_call(doc, transcript, summary, end_reason, duration, tone, live_red_flags)

    if result["category"] != "completed":
        logger.info(
            f"[vapi] call {call_id} categorized as {result['category']} "
            f"({result['reason_label']}). Skipping booking + ranking."
        )
        return

    interview_score = result["interview_score"]
    threshold = config.CALENDAR_THRESHOLD
    if interview_score >= threshold and doc.get("email"):
        try:
            from services.booking_agent import create_slot_picker_booking
            token = create_slot_picker_booking(doc, interview_score)
            logger.warning(f"[booking] slot picker {'emailed' if token else 'NOT created'} for {doc.get('name')}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[booking] slot picker failed for call_id={call_id}: {e!r}")
    else:
        reason = "low_score" if interview_score < threshold else "missing_email"
        logger.warning(f"[booking] skipped for {doc.get('name')}: score={interview_score} reason={reason}")

    # Persist the ranked record so legacy candidates also land in ranked_candidates
    # (parity with the pipeline's rank node — previously missing here).
    try:
        from services.ranking_agent import rank_candidate
        rank_candidate(doc["_id"])
    except Exception as e:  # noqa: BLE001
        logger.error(f"[rank] failed for cv_id={doc['_id']}: {e!r}")


if __name__ == "__main__":
    logger.warning("voice_agent: use livekit_agent.py for interview agent")