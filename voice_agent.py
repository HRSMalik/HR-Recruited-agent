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


def record_call_result(call_id: str, transcript: str, summary: str) -> None:
    """Called from the Vapi webhook handler. Updates the screened_candidates doc."""
    doc = _screened().find_one({"call_id": call_id})
    if not doc:
        print(f"[vapi] webhook for unknown call_id={call_id}", file=sys.stderr)
        return

    interview_score = _score_interview(transcript or "", summary or "")

    _screened().update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "transcript": transcript,
            "summary": summary,
            "interview_score": interview_score,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc),
        }},
    )


if __name__ == "__main__":
    print(call_top_candidates(), file=sys.stderr)