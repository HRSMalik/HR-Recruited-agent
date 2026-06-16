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


def call_top_candidates(threshold: Optional[int] = None) -> dict:
    """Initiate Vapi calls for shortlisted candidates not yet screened.

    Eligibility: `fit_percent >= threshold`. The threshold is taken from
    `VOICE_CALL_THRESHOLD` env var so it can be tuned without code changes.

    Returns: {"called": N, "skipped": N, "errors": [...]}.
    """
    if threshold is None:
        threshold = int(os.getenv("VOICE_CALL_THRESHOLD", "70"))

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


_MAX_JD_CHARS = 2000


def _score_interview(transcript: str, summary: str, job_description: Optional[str] = None) -> int:
    """LLM rates the candidate 0-100 against the JD.

    Scoring is job-aware: the candidate is judged on how well their interview
    answers match THIS specific job's requirements (role, skills, experience).
    If `job_description` is missing (e.g. test cases), falls back to a generic
    rubric so the function never crashes.
    """
    jd_block = (job_description or "").strip()[:_MAX_JD_CHARS]

    jd_section = (
        f"=========== JOB DESCRIPTION ===========\n{jd_block}\n=======================================\n"
        if jd_block
        else "=========== JOB DESCRIPTION ===========\n(not available — score on general fit)\n=======================================\n"
    )

    prompt = f"""
You are a senior recruiter scoring a phone-screen interview against a specific job.

{jd_section}

=========== INTERVIEW ===========
Summary: {summary or "(no summary)"}

Transcript:
{transcript or "(no transcript)"}
=================================

HOW TO SCORE (0-100):
Compare the candidate's interview answers AGAINST the JOB DESCRIPTION above. The
score must reflect role-fit, not generic conversation quality.

Weighted criteria:
  1. Skill match (40%): Did the candidate mention the technologies, tools, or
     domains listed in the JD's requirements? BOTH direct matches AND
     equivalent alternatives count strongly (see EQUIVALENT SKILLS below).
  2. Experience fit (25%): Does their stated experience (years, projects,
     responsibilities) align with what the JD asks for?
  3. Communication clarity (20%): Are answers specific, structured, confident?
  4. Engagement & motivation (15%): Did they show interest in THIS role?

EQUIVALENT SKILLS — treat as essentially matching, credit the same:
  - Data manipulation: Pandas ≈ Polars ≈ Dask ≈ PySpark
  - Deep learning:     PyTorch ≈ TensorFlow ≈ JAX ≈ Keras
  - Classical ML:      scikit-learn ≈ XGBoost ≈ LightGBM ≈ CatBoost
  - Web backend:       FastAPI ≈ Flask ≈ Django REST ≈ Express ≈ NestJS
  - Web frontend:      React ≈ Vue ≈ Svelte ≈ Angular ≈ SolidJS
  - SSR / meta:        Next.js ≈ Nuxt ≈ Remix ≈ SvelteKit
  - Styling:           Tailwind ≈ Bootstrap ≈ Material UI ≈ Chakra
  - SQL DBs:           PostgreSQL ≈ MySQL ≈ MariaDB ≈ SQL Server
  - NoSQL DBs:         MongoDB ≈ DynamoDB ≈ Firestore ≈ CosmosDB
  - Caches/queues:     Redis ≈ Memcached ; Kafka ≈ RabbitMQ ≈ SQS
  - Containers:        Docker ≈ Podman ; Kubernetes ≈ Docker Swarm ≈ Nomad
  - Cloud:             AWS ≈ GCP ≈ Azure (cross-cloud experience is fine)
  - LLM frameworks:    LangChain ≈ LlamaIndex ≈ Haystack ≈ Semantic Kernel
  - ETL/orchestration: Airflow ≈ Prefect ≈ Dagster ≈ Luigi
  - Vector stores:     Pinecone ≈ Weaviate ≈ Qdrant ≈ Milvus ≈ pgvector
  - CI/CD:             GitHub Actions ≈ GitLab CI ≈ CircleCI ≈ Jenkins

GENERAL EQUIVALENCE RULE: If a tool the candidate mentioned serves the SAME
PURPOSE as a tool the JD requires, treat it as a match. Do NOT penalize the
candidate just because they happen to use a different tool in the same family.

MODERN ALTERNATIVE BONUS: If the candidate uses a NEWER/BETTER alternative
(e.g., Polars instead of Pandas, Rust instead of C, FastAPI instead of Flask),
treat it as a STRONG match — it signals up-to-date skills, not a gap.

5-TIER RUBRIC:
  85-100  Exceptional fit. Most/all required skills mentioned with specific
          examples. Experience clearly aligns. Strong, structured answers.
  70-84   Strong candidate. Most key skills covered. Relevant experience.
          Clear communication.
  60-74   Decent fit. Partial skill overlap. Basic competence shown.
          Average communication.
  40-59   Weak match. Few required skills mentioned. Vague or generic answers.
  0-39    Poor fit. No skill alignment, off-topic, or clear red flags
          (evasiveness, contradictions, no domain knowledge).

IMPORTANT GUIDELINES:
- Phone screens are SHORT (2-5 min). Do NOT penalize brevity. Focus on the
  QUALITY of what was said, not the length.
- A candidate who clearly names required tech and gives one concrete example is
  a STRONG fit even in 3 minutes.
- Reserve scores below 50 ONLY when the candidate has no skill overlap with the
  JD or shows clear red flags. Don't default to "low score because short call".
- If the JD section says "(not available)", judge general communication, clarity,
  and engagement.

CALIBRATION EXAMPLES (assuming JD asks for Python + FastAPI + ML + Pandas):
  Score 85: "I have 3 years building FastAPI APIs for ML pipelines at a fintech.
            Currently leading a recommendation service using Python and PyTorch."
            → Specific tech, role, context, direct match.
  Score 82: "I use Python with Flask and Polars for data processing, and
            TensorFlow for ML — recently migrated a pipeline from Pandas to
            Polars for 10x speedup."
            → JD said FastAPI/Pandas/PyTorch; candidate uses Flask/Polars/
            TensorFlow — all equivalents, strong real example. STILL HIGH.
  Score 65: "Yes, I know Python and have used FastAPI in a couple of projects.
            Some ML exposure."
            → Skills named but no depth.
  Score 40: "I work with various technologies. Some Python here and there."
            → Generic, no specifics, weak match.
  Score 15: "I don't really use those tools. I mainly do other things."
            → No alignment with JD.

Return ONLY a single integer 0-100. No explanation. No other text.
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
        job = _jobs_collection().find_one({"_id": doc.get("jd_id")})
        job_desc = (job or {}).get("job_description")
        interview_score = _score_interview(transcript or "", summary or "", job_desc)

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
            from booking_agent import create_slot_picker_booking
            token = create_slot_picker_booking(doc, interview_score)
            if token:
                print(f"[booking] slot picker emailed to {doc.get('name')} token={token}", file=sys.stderr)
            else:
                print(f"[booking] slot picker NOT created for {doc.get('name')} (no slots or missing config)", file=sys.stderr)
        except Exception as e:
            print(f"[booking] slot picker failed for call_id={call_id}: {e!r}", file=sys.stderr)
    else:
        reason = "low_score" if interview_score < threshold else "missing_email"
        print(f"[booking] skipped for {doc.get('name')}: score={interview_score} threshold={threshold} reason={reason}", file=sys.stderr)


if __name__ == "__main__":
    print(call_top_candidates(), file=sys.stderr)