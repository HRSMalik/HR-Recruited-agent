"""Call categorization + audit log + retry helpers.

Categorizes each Vapi call into completed/cancelled/declined using:
  - endedReason (primary signal, Layer 1)
  - transcript + duration (only for ambiguous customer-ended-call, Layer 2)

Persists every attempt to `call_logs` and schedules retries for declined calls.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
RETRY_INTERVAL_MINUTES = int(os.getenv("RETRY_INTERVAL_MINUTES", "5"))


_DB = None


def _get_db():
    global _DB
    if _DB is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _DB = MongoClient(uri)[db_name]
    return _DB


def _call_logs_collection():
    return _get_db()["call_logs"]


# Vapi end reasons that map directly without checking transcript/duration.
# These are 100% trusted from Vapi — no false positives possible.
COMPLETED_REASONS = {"assistant-ended-call", "assistant-said-end-call-phrase"}

NETWORK_DECLINE_REASONS = {
    "phone-call-provider-closed-websocket": "network_drop",
    "silence-timed-out": "weak_signal_or_silence",
    "pipeline-error": "system_error",
    "transport-error": "network_transport",
    "customer-busy": "busy_line",
    "customer-did-not-answer": "no_answer",
    "voicemail": "voicemail",
    "worker-shutdown": "vapi_worker_shutdown",
}

ADMIN_CANCEL_REASONS = {"manually-canceled", "manual-call-canceled"}

# Threshold for ambiguous customer-ended-call classification
MIN_WORDS_FOR_INTENTIONAL = 30
MIN_DURATION_FOR_INTENTIONAL = 15


def count_user_words(transcript: str) -> int:
    """Count words spoken by the candidate (User lines only, ignore AI)."""
    if not transcript:
        return 0
    user_lines = [
        line for line in transcript.split("\n")
        if line.strip().startswith("User:")
    ]
    return sum(len(line.split(":", 1)[1].split()) for line in user_lines if ":" in line)


def categorize_call(
    end_reason: str,
    transcript: str,
    duration: int,
) -> Tuple[str, str]:
    """Decide if call was completed, cancelled, or declined.

    Layer 1: Trust Vapi's endedReason when it's a sure signal.
    Layer 2: Only for ambiguous customer-ended-call, use transcript + duration.

    Returns: (category, reason_label)
    """
    end_reason = end_reason or "unknown"
    transcript = transcript or ""
    duration = duration or 0

    # Layer 1: Sure cases — direct mapping, transcript/duration ignored
    if end_reason in COMPLETED_REASONS:
        return "completed", "interview_finished"

    if end_reason in ADMIN_CANCEL_REASONS:
        return "cancelled", "hr_admin_cancelled"

    if end_reason in NETWORK_DECLINE_REASONS:
        return "declined", NETWORK_DECLINE_REASONS[end_reason]

    # Pipeline-* and vapi-* error families
    if end_reason.startswith("pipeline-error") or end_reason.startswith("call.start.error"):
        return "declined", "system_error"

    # Layer 2: Ambiguous case — customer-ended-call
    if end_reason == "customer-ended-call":
        user_words = count_user_words(transcript)

        if user_words >= MIN_WORDS_FOR_INTENTIONAL:
            return "cancelled", "intentional_after_conversation"
        if user_words >= 5 and duration >= MIN_DURATION_FOR_INTENTIONAL:
            return "cancelled", "intentional_early"
        if duration < MIN_DURATION_FOR_INTENTIONAL:
            return "declined", "abrupt_cut_likely_accidental"
        return "declined", "no_speech_then_cut"

    # Unknown / future reasons — default to declined (safe path, retry once)
    return "declined", f"unknown:{end_reason}"


def log_call_attempt(
    candidate_id: str,
    jd_id: Optional[str],
    call_id: str,
    category: str,
    reason: str,
    vapi_end_reason: str,
    transcript: str,
    duration: int,
    score: Optional[int] = None,
    triggered_by: str = "auto",
) -> dict:
    """Insert a new call_logs entry. Schedules retry if declined and attempts < max."""
    prev_attempts = _call_logs_collection().count_documents({
        "candidate_id": candidate_id,
    })
    attempt_number = prev_attempts + 1

    now = datetime.now(timezone.utc)

    entry = {
        "_id": str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "jd_id": jd_id,
        "call_id": call_id,
        "category": category,
        "category_reason": reason,
        "attempt_number": attempt_number,
        "vapi_end_reason": vapi_end_reason,
        "transcript": transcript,
        "duration_seconds": duration,
        "interview_score": score,
        "triggered_by": triggered_by,
        "created_at": now,
    }

    if category == "declined" and attempt_number < MAX_RETRY_ATTEMPTS:
        entry["status"] = "pending_retry"
        entry["next_retry_at"] = now + timedelta(minutes=RETRY_INTERVAL_MINUTES)
    elif category == "declined":
        entry["status"] = "exhausted"
    else:
        entry["status"] = "closed"

    _call_logs_collection().insert_one(entry)
    return entry


def process_retries(initiate_call_fn, candidates_collection, screened_collection, normalize_phone_fn) -> dict:
    """Re-trigger Vapi calls for logs whose next_retry_at has arrived.

    Called by the background retry scheduler every 60 seconds.
    Dependencies passed in to avoid circular imports.
    """
    now = datetime.now(timezone.utc)
    pending = list(_call_logs_collection().find({
        "status": "pending_retry",
        "next_retry_at": {"$lte": now},
        "attempt_number": {"$lt": MAX_RETRY_ATTEMPTS},
    }))

    retried = 0
    errors: list[str] = []

    for log in pending:
        cand = candidates_collection.find_one({"_id": log["candidate_id"]})
        if not cand:
            errors.append(f"candidate {log['candidate_id']} not found")
            _call_logs_collection().update_one(
                {"_id": log["_id"]},
                {"$set": {"status": "exhausted", "exhausted_reason": "candidate_missing"}},
            )
            continue

        phone_e164 = normalize_phone_fn(cand.get("phone"))
        if not phone_e164:
            errors.append(f"candidate {log['candidate_id']} has invalid phone")
            continue

        try:
            new_call_id = initiate_call_fn(phone_e164)
            if not new_call_id:
                errors.append(f"vapi did not return call_id for {log['candidate_id']}")
                continue

            screened_collection.update_one(
                {"_id": log["candidate_id"]},
                {"$set": {
                    "call_id": new_call_id,
                    "status": "calling",
                    "called_at": now,
                }},
            )

            _call_logs_collection().update_one(
                {"_id": log["_id"]},
                {"$set": {"status": "retried", "retried_at": now, "next_call_id": new_call_id}},
            )

            retried += 1
            print(f"[retry] re-called {cand.get('name')} (attempt {log['attempt_number'] + 1}/{MAX_RETRY_ATTEMPTS})", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{log['candidate_id']}: {e!r}")

    return {"retried": retried, "errors": errors, "checked": len(pending)}


def list_call_logs(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """List call_logs with optional filters."""
    query: dict = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status

    coll = _call_logs_collection()
    total = coll.count_documents(query)
    docs = list(coll.find(query).sort("created_at", -1).skip(skip).limit(limit))
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


def call_stats() -> dict:
    """Aggregated counts for dashboard metrics."""
    coll = _call_logs_collection()
    return {
        "completed": coll.count_documents({"category": "completed"}),
        "cancelled": coll.count_documents({"category": "cancelled"}),
        "declined": coll.count_documents({"category": "declined"}),
        "pending_retry": coll.count_documents({"status": "pending_retry"}),
        "exhausted": coll.count_documents({"status": "exhausted"}),
        "closed": coll.count_documents({"status": "closed"}),
        "total": coll.count_documents({}),
    }


def manual_retry(log_id: str) -> bool:
    """Force the log's next_retry_at to NOW so the scheduler picks it up next tick."""
    result = _call_logs_collection().update_one(
        {"_id": log_id, "status": {"$in": ["pending_retry", "exhausted"]}},
        {"$set": {
            "status": "pending_retry",
            "next_retry_at": datetime.now(timezone.utc),
        }},
    )
    return result.modified_count > 0


def close_log(log_id: str) -> bool:
    """Mark log as closed (terminal state — no more retries)."""
    result = _call_logs_collection().update_one(
        {"_id": log_id},
        {"$set": {
            "status": "closed",
            "closed_at": datetime.now(timezone.utc),
        }},
    )
    return result.modified_count > 0
