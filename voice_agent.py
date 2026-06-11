"""Voice screening agent backed by Vapi.

Flow:
  1. After each shortlist tick, `call_top_candidates()` finds candidates in
     `candidates_info` with `fit_percent >= threshold` who aren't already in
     `screened_candidates`.
  2. For each, normalizes the phone number to E.164 and POSTs to Vapi's
     `/call/phone` endpoint to start the call.
  3. Inserts a row into `screened_candidates` with status="calling" so we
     don't re-call.
  4. When Vapi POSTs back to `/voice/webhook` (in app.py) with the
     end-of-call report, `record_call_result()` saves transcript + summary
     and uses an LLM to compute an `interview_score`.
"""
import os
import re
import sys
from datetime import datetime, timezone
from typing import Optional

import requests
from langchain.chat_models import init_chat_model
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


VAPI_API_URL = "https://api.vapi.ai"
DEFAULT_COUNTRY_CODE = os.getenv("VAPI_DEFAULT_COUNTRY_CODE", "+1")


_DB = None


def _get_db():
    global _DB
    if _DB is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _DB = MongoClient(uri)[db_name]
    return _DB


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
    """Normalize CV phone strings into E.164.

    Strategy:
      - Strip everything except digits and a leading +.
      - If it starts with +, require 11-15 digits total (country code + subscriber).
      - If 10 digits and no +, prepend VAPI_DEFAULT_COUNTRY_CODE.
      - If 11-15 digits and no +, treat the leading digits as the country code.
    """
    if not raw:
        return None
    s = str(raw).strip()
    if s.startswith("+"):
        digits = re.sub(r"\D", "", s[1:])
        if not (11 <= len(digits) <= 15):
            return None
        return f"+{digits}"
    digits = re.sub(r"\D", "", s)
    if len(digits) == 10:
        return f"{DEFAULT_COUNTRY_CODE}{digits}"
    if 11 <= len(digits) <= 15:
        return f"+{digits}"
    return None


def _initiate_vapi_call(phone_e164: str) -> Optional[str]:
    """POST to Vapi to start a phone call. Returns call_id, or None on failure."""
    api_key = os.getenv("VAPI_API_KEY")
    assistant_id = os.getenv("VAPI_ASSISTANT_ID")
    phone_number_id = os.getenv("VAPI_PHONE_NUMBER_ID")

    if not api_key or not assistant_id or not phone_number_id:
        raise RuntimeError(
            "VAPI_API_KEY, VAPI_ASSISTANT_ID, and VAPI_PHONE_NUMBER_ID must all be set."
        )

    resp = requests.post(
        f"{VAPI_API_URL}/call/phone",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "phoneNumberId": phone_number_id,
            "customer": {"number": phone_e164},
            "assistantId": assistant_id,
        },
        timeout=30,
    )
    if resp.status_code >= 400:
        print(f"[vapi] call failed for {phone_e164}: {resp.status_code} {resp.text}", file=sys.stderr)
        return None
    return resp.json().get("id")


def call_top_candidates(threshold: int = 80) -> dict:
    """Initiate Vapi calls for shortlisted candidates not yet screened.

    Returns: {"called": N, "skipped": N, "errors": [...]}.
    """
    missing = [
        name for name in ("VAPI_API_KEY", "VAPI_ASSISTANT_ID", "VAPI_PHONE_NUMBER_ID")
        if not os.getenv(name)
    ]
    if missing:
        return {"called": 0, "skipped": 0, "errors": [f"skipping voice agent; missing env vars: {missing}"]}

    candidates = list(_candidates().find({"fit_percent": {"$gte": threshold}}))
    called = 0
    skipped = 0
    errors: list[str] = []

    for c in candidates:
        cv_id = c.get("_id")
        if _screened().find_one({"_id": cv_id}):
            skipped += 1
            continue

        phone_e164 = _normalize_phone(c.get("phone"))
        if not phone_e164:
            skipped += 1
            errors.append(f"cv_id={cv_id}: unusable phone {c.get('phone')!r}")
            continue

        try:
            call_id = _initiate_vapi_call(phone_e164)
            if not call_id:
                errors.append(f"cv_id={cv_id}: Vapi did not return a call_id")
                continue

            _screened().insert_one({
                "_id": cv_id,
                "name": c.get("name"),
                "phone": c.get("phone"),
                "phone_e164": phone_e164,
                "email": c.get("email"),
                "fit_percent": c.get("fit_percent"),
                "jd_id": c.get("jd_id"),
                "experience_years": c.get("experience_years"),
                "last_education_degree": c.get("last_education_degree"),
                "call_id": call_id,
                "status": "calling",
                "called_at": datetime.now(timezone.utc),
            })
            called += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"cv_id={cv_id}: {e!r}")

    return {"called": called, "skipped": skipped, "errors": errors}


def _score_interview(transcript: str, summary: str) -> int:
    """LLM rates the candidate 0-100 from the interview content."""
    prompt = f"""
    You are evaluating a phone-screen interview. Score the candidate 0-100 based on:
    - Clarity and confidence of communication
    - Demonstrated relevant experience
    - Engagement and interest in the role
    - Red flags (vague answers, evasiveness, contradictions)

    INTERVIEW SUMMARY:
    {summary}

    FULL TRANSCRIPT:
    {transcript}

    Return ONLY a single integer between 0 and 100. No explanation, no other text.
    """
    llm = init_chat_model("gpt-4o-mini", temperature=0)
    response = llm.invoke(prompt)
    raw = (response.content or "").strip()
    m = re.search(r"\d{1,3}", raw)
    if not m:
        return 0
    return max(0, min(100, int(m.group(0))))


def record_call_result(
    call_id: str,
    transcript: str,
    summary: str,
    end_reason: str = "unknown",
    duration: int = 0,
) -> None:
    """Called from the Vapi webhook handler.

    Categorizes the call (completed/cancelled/declined), logs to call_logs,
    and runs the full downstream flow (score, insights, meeting) only for
    completed calls. Declined calls get scheduled for retry.
    """
    doc = _screened().find_one({"call_id": call_id})
    if not doc:
        print(f"[vapi] webhook for unknown call_id={call_id}", file=sys.stderr)
        return

    from call_logs import categorize_call, log_call_attempt
    category, reason_label = categorize_call(end_reason, transcript or "", duration)

    interview_score: Optional[int] = None
    if category == "completed":
        interview_score = _score_interview(transcript or "", summary or "")

    log_call_attempt(
        candidate_id=doc["_id"],
        jd_id=doc.get("jd_id"),
        call_id=call_id,
        category=category,
        reason=reason_label,
        vapi_end_reason=end_reason,
        transcript=transcript or "",
        duration=duration,
        score=interview_score,
        triggered_by=doc.get("triggered_by", "auto"),
    )

    _screened().update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "transcript": transcript,
            "summary": summary,
            "interview_score": interview_score,
            "status": category,
            "category_reason": reason_label,
            "vapi_end_reason": end_reason,
            "duration_seconds": duration,
            "completed_at": datetime.now(timezone.utc),
        }},
    )

    if category != "completed":
        print(
            f"[vapi] call {call_id} categorized as {category} ({reason_label}). "
            f"Skipping insights + meeting.",
            file=sys.stderr,
        )
        return

    insights = None
    try:
        from transcript_analyzer import extract_interview_insights
        insights = extract_interview_insights(transcript or "")
        insights["_id"] = doc["_id"]
        insights["call_id"] = call_id
        insights["candidate_name_from_form"] = doc.get("name")
        insights["candidate_email"] = doc.get("email")
        insights["candidate_phone"] = doc.get("phone_e164")
        insights["jd_id"] = doc.get("jd_id")
        insights["interview_score"] = interview_score
        insights["extracted_at"] = datetime.now(timezone.utc)
        _insights_collection().replace_one(
            {"_id": doc["_id"]}, insights, upsert=True
        )
        print(f"[insights] saved for {doc.get('name')}", file=sys.stderr)
    except Exception as e:
        print(f"[insights] extraction failed for call_id={call_id}: {e!r}", file=sys.stderr)

    threshold = int(os.getenv("CALENDAR_THRESHOLD", "60"))
    if interview_score >= threshold and doc.get("email"):
        try:
            job = _jobs_collection().find_one({"_id": doc.get("jd_id")})
            hr_attendees = _collect_hr_attendees(job)
            from calendar_agent import schedule_interview
            meeting = schedule_interview(doc, interview_score,
                                          hr_attendees=hr_attendees,
                                          insights=insights)
            meeting["_id"] = doc["_id"]
            meeting["call_id"] = call_id
            _meetings_collection().replace_one(
                {"_id": doc["_id"]}, meeting, upsert=True
            )
            print(f"[calendar] meeting scheduled for {doc.get('name')} at {meeting['meeting_time']}", file=sys.stderr)
        except Exception as e:
            print(f"[calendar] scheduling failed for call_id={call_id}: {e!r}", file=sys.stderr)
    else:
        reason = "low_score" if interview_score < threshold else "missing_email"
        print(f"[calendar] skipped for {doc.get('name')}: score={interview_score} threshold={threshold} reason={reason}", file=sys.stderr)


if __name__ == "__main__":
    print(call_top_candidates(), file=sys.stderr)