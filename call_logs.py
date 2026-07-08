"""Initial screening interview categorization + audit log + retry helpers.

Categorizes each LiveKit interview attempt into completed/no_show/incomplete based
on the end_reason livekit_agent.py reports (a candidate either joined and finished,
never joined, or joined but didn't finish — no phone-call retry semantics apply).

Persists every attempt to `initial_screening_logs` and schedules a fresh interview
invite (new room + new email) for no_show/incomplete candidates.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from dotenv import load_dotenv
from pymongo import MongoClient

import config

load_dotenv()


MAX_RETRY_ATTEMPTS = config.MAX_RETRY_ATTEMPTS
RETRY_INTERVAL_MINUTES = config.RETRY_INTERVAL_MINUTES


_DB = None


def _get_db():
    global _DB
    if _DB is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _DB = MongoClient(uri)[db_name]
    return _DB


def _screening_logs_collection():
    return _get_db()["initial_screening_logs"]


# end_reason codes livekit_agent.py reports, mapped to a category + human reason.
_REASON_MAP: dict[str, Tuple[str, str]] = {
    "completed": ("completed", "interview_finished"),
    "no_show": ("no_show", "candidate_never_joined"),
    "unresponsive": ("incomplete", "candidate_unresponsive"),
    "participant_disconnected": ("incomplete", "candidate_left_early"),
    "timeout": ("incomplete", "max_duration_reached"),
}


def categorize_call(end_reason: str) -> Tuple[str, str]:
    """Decide if an interview was completed, a no-show, or incomplete.

    livekit_agent.py reports a specific, unambiguous end_reason for every outcome,
    so this is a direct lookup — no transcript/duration heuristics needed.

    Returns: (category, reason_label)
    """
    end_reason = end_reason or "unknown"
    return _REASON_MAP.get(end_reason, ("incomplete", f"unknown:{end_reason}"))


def log_call_attempt(
    candidate_id: str,
    jd_id: Optional[str],
    call_id: str,
    category: str,
    reason: str,
    end_reason: str,
    transcript: str,
    duration: int,
    score: Optional[int] = None,
    triggered_by: str = "auto",
) -> dict:
    """Insert a new initial_screening_logs entry. Schedules a retry for no_show/incomplete
    candidates (a fresh interview invite), unless attempts are exhausted."""
    prev_attempts = _screening_logs_collection().count_documents({
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
        "end_reason": end_reason,
        "transcript": transcript,
        "duration_seconds": duration,
        "interview_score": score,
        "triggered_by": triggered_by,
        "created_at": now,
    }

    if category in ("no_show", "incomplete") and attempt_number < MAX_RETRY_ATTEMPTS:
        entry["status"] = "pending_retry"
        entry["next_retry_at"] = now + timedelta(minutes=RETRY_INTERVAL_MINUTES)
    elif category in ("no_show", "incomplete"):
        entry["status"] = "exhausted"
    else:
        entry["status"] = "closed"

    _screening_logs_collection().insert_one(entry)
    return entry


def process_retries(start_interview_fn, screened_collection) -> dict:
    """Send a fresh interview invite for logs whose next_retry_at has arrived.

    Called by the background retry scheduler every 60 seconds. `start_interview_fn`
    creates a new LiveKit room + emails the candidate (voice_agent._start_livekit_interview),
    returning the new room_name or None on failure. Dependency injected to avoid
    circular imports.
    """
    now = datetime.now(timezone.utc)
    pending = list(_screening_logs_collection().find({
        "status": "pending_retry",
        "next_retry_at": {"$lte": now},
        "attempt_number": {"$lt": MAX_RETRY_ATTEMPTS},
    }))

    retried = 0
    errors: list[str] = []

    for log in pending:
        cand = screened_collection.find_one({"_id": log["candidate_id"]})
        if not cand:
            errors.append(f"candidate {log['candidate_id']} not found")
            _screening_logs_collection().update_one(
                {"_id": log["_id"]},
                {"$set": {"status": "exhausted", "exhausted_reason": "candidate_missing"}},
            )
            continue

        try:
            new_room_name = start_interview_fn(cand)
            if not new_room_name:
                errors.append(f"could not create LiveKit room for {log['candidate_id']}")
                continue

            screened_collection.update_one(
                {"_id": log["candidate_id"]},
                {"$set": {
                    "call_id": new_room_name,
                    "room_name": new_room_name,
                    "status": "interview_ready",
                    "called_at": now,
                }},
            )

            _screening_logs_collection().update_one(
                {"_id": log["_id"]},
                {"$set": {"status": "retried", "retried_at": now, "next_call_id": new_room_name}},
            )

            retried += 1
            print(
                f"[retry] new interview invite sent to {cand.get('name')} "
                f"(attempt {log['attempt_number'] + 1}/{MAX_RETRY_ATTEMPTS})",
                file=sys.stderr,
            )
        except Exception as e:  # noqa: BLE001
            errors.append(f"{log['candidate_id']}: {e!r}")

    return {"retried": retried, "errors": errors, "checked": len(pending)}


def list_call_logs(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """List initial_screening_logs with optional filters."""
    query: dict = {}
    if category:
        query["category"] = category
    if status:
        query["status"] = status

    coll = _screening_logs_collection()
    total = coll.count_documents(query)
    docs = list(coll.find(query).sort("created_at", -1).skip(skip).limit(limit))
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"items": docs, "total": total, "skip": skip, "limit": limit}


def call_stats() -> dict:
    """Aggregated counts for dashboard metrics."""
    coll = _screening_logs_collection()
    return {
        "completed": coll.count_documents({"category": "completed"}),
        "no_show": coll.count_documents({"category": "no_show"}),
        "incomplete": coll.count_documents({"category": "incomplete"}),
        "pending_retry": coll.count_documents({"status": "pending_retry"}),
        "exhausted": coll.count_documents({"status": "exhausted"}),
        "closed": coll.count_documents({"status": "closed"}),
        "total": coll.count_documents({}),
    }


def manual_retry(log_id: str) -> bool:
    """Force the log's next_retry_at to NOW so the scheduler picks it up next tick."""
    result = _screening_logs_collection().update_one(
        {"_id": log_id, "status": {"$in": ["pending_retry", "exhausted"]}},
        {"$set": {
            "status": "pending_retry",
            "next_retry_at": datetime.now(timezone.utc),
        }},
    )
    return result.modified_count > 0


def close_log(log_id: str) -> bool:
    """Mark log as closed (terminal state — no more retries)."""
    result = _screening_logs_collection().update_one(
        {"_id": log_id},
        {"$set": {
            "status": "closed",
            "closed_at": datetime.now(timezone.utc),
        }},
    )
    return result.modified_count > 0
