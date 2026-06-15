"""Candidate-driven slot picker booking flow.

After a candidate passes voice screening, instead of auto-scheduling a fixed
slot, we generate a list of available slots from the HR's calendar, save a
`pending_booking`, and email the candidate a link to pick their preferred time.
Once the candidate picks a slot, a real calendar event with Google Meet is
created (reusing `calendar_agent`) and the booking is marked `booked`.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from googleapiclient.discovery import build
from pymongo import MongoClient

from parser_agent import _load_google_credentials

load_dotenv()


_DB = None


def _get_db():
    global _DB
    if _DB is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _DB = MongoClient(uri)[db_name]
    return _DB


def _bookings():
    return _get_db()["pending_bookings"]


def _jobs():
    return _get_db()["job_descriptions"]


def _meetings():
    return _get_db()["meetings"]


def _cfg() -> dict:
    return {
        "tz": ZoneInfo(os.getenv("CALENDAR_TIMEZONE", "Asia/Karachi")),
        "days_ahead": int(os.getenv("BOOKING_DAYS_AHEAD", "7")),
        "weekday_start": int(os.getenv("BOOKING_WEEKDAY_START_HOUR", "10")),
        "weekday_end": int(os.getenv("BOOKING_WEEKDAY_END_HOUR", "19")),
        "friday_start": int(os.getenv("BOOKING_FRIDAY_START_HOUR", "10")),
        "friday_end": int(os.getenv("BOOKING_FRIDAY_END_HOUR", "12")),
        "slot_duration_min": int(os.getenv("BOOKING_SLOT_DURATION_MIN", "60")),
        "max_slots_shown": int(os.getenv("BOOKING_MAX_SLOTS_SHOWN", "15")),
        "token_expires_hours": int(os.getenv("BOOKING_TOKEN_EXPIRES_HOURS", "48")),
        "base_url": os.getenv("BOOKING_BASE_URL", "http://localhost:8000"),
        "buffer_hours": int(os.getenv("CALENDAR_BUFFER_HOURS", "24")),
    }


def _calendar_service():
    creds = _load_google_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _get_busy_ranges(hr_email: str, cfg: dict) -> list:
    """Query HR calendar's busy slots for the booking window."""
    service = _calendar_service()
    now = datetime.now(cfg["tz"])
    window_end = now + timedelta(days=cfg["days_ahead"] + 1)
    body = {
        "timeMin": now.isoformat(),
        "timeMax": window_end.isoformat(),
        "items": [{"id": hr_email}],
    }
    fb = service.freebusy().query(body=body).execute()
    busy = fb.get("calendars", {}).get(hr_email, {}).get("busy", [])
    ranges = []
    for b in busy:
        s = datetime.fromisoformat(b["start"].replace("Z", "+00:00")).astimezone(cfg["tz"])
        e = datetime.fromisoformat(b["end"].replace("Z", "+00:00")).astimezone(cfg["tz"])
        ranges.append((s, e))
    return ranges


def _day_window(day, weekday: int, cfg: dict):
    """Return (start_hour, end_hour) for a given weekday based on booking rules."""
    if weekday >= 5:
        return None
    if weekday == 4:
        return cfg["friday_start"], cfg["friday_end"]
    return cfg["weekday_start"], cfg["weekday_end"]


def generate_available_slots(hr_email: str) -> list:
    """Build candidate-facing slot list, filtered by HR busy times.

    Rules:
      - Mon-Thu: BOOKING_WEEKDAY_START_HOUR..BOOKING_WEEKDAY_END_HOUR
      - Friday : BOOKING_FRIDAY_START_HOUR..BOOKING_FRIDAY_END_HOUR
      - Sat-Sun: skipped
      - Each slot is `slot_duration_min` long, on the hour, future-only (after buffer).
    """
    cfg = _cfg()
    now = datetime.now(cfg["tz"])
    earliest = now + timedelta(hours=cfg["buffer_hours"])
    busy = _get_busy_ranges(hr_email, cfg)
    step = timedelta(minutes=cfg["slot_duration_min"])

    slots: list[datetime] = []
    for offset in range(cfg["days_ahead"]):
        day = (now + timedelta(days=offset)).date()
        window = _day_window(day, day.weekday(), cfg)
        if not window:
            continue
        start_h, end_h = window
        slot = datetime(day.year, day.month, day.day, start_h, 0, tzinfo=cfg["tz"])
        end_of_day = datetime(day.year, day.month, day.day, end_h, 0, tzinfo=cfg["tz"])
        while slot + step <= end_of_day:
            if slot >= earliest and not any(s < slot + step and slot < e for s, e in busy):
                slots.append(slot)
            slot += step
        if len(slots) >= cfg["max_slots_shown"]:
            break
    return slots[: cfg["max_slots_shown"]]


def _slot_picker_html(name: str, score: int, booking_url: str, expires_hours: int) -> str:
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color:#222; max-width:560px; margin:auto;">
        <h2 style="color:#2e7d32;">Congratulations {name}!</h2>
        <p>Aapka voice screening clear ho gaya.</p>
        <p><b>Score:</b> {score}/100</p>
        <p>Apna interview slot khud choose karein:</p>
        <p style="margin:24px 0;">
          <a href="{booking_url}"
             style="background:#2e7d32; color:#fff; padding:12px 24px;
                    text-decoration:none; border-radius:4px; font-weight:bold;">
            Pick Your Slot
          </a>
        </p>
        <p style="color:#666; font-size:13px;">
          Link expires in {expires_hours} hours.<br/>
          Available: Mon-Thu 10AM-7PM, Friday 10AM-12PM (Asia/Karachi).
        </p>
        <p>Best regards,<br/>HR Team</p>
      </body>
    </html>
    """


def create_slot_picker_booking(candidate_doc: dict, score: int) -> Optional[str]:
    """Generate slots, persist a pending booking, and email the picker link.

    Returns the booking token, or None if no slots are available / email missing.
    """
    cfg = _cfg()
    email = candidate_doc.get("email")
    if not email:
        print(f"[booking] candidate {candidate_doc.get('_id')} has no email; skipping", file=sys.stderr)
        return None

    job = _jobs().find_one({"_id": candidate_doc.get("jd_id")})
    if not job or not job.get("primary_hr_email"):
        print(f"[booking] job {candidate_doc.get('jd_id')} missing primary_hr_email", file=sys.stderr)
        return None

    primary_hr = job["primary_hr_email"]
    slots = generate_available_slots(primary_hr)
    if not slots:
        print(f"[booking] no slots available for HR {primary_hr}", file=sys.stderr)
        return None

    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    booking = {
        "_id": token,
        "candidate_id": candidate_doc["_id"],
        "candidate_email": email,
        "candidate_name": candidate_doc.get("name") or "Candidate",
        "candidate_phone": candidate_doc.get("phone_e164") or candidate_doc.get("phone"),
        "jd_id": candidate_doc.get("jd_id"),
        "primary_hr_email": primary_hr,
        "team_members": job.get("team_members") or [],
        "available_slots": [s.isoformat() for s in slots],
        "interview_score": score,
        "status": "pending",
        "selected_slot": None,
        "meet_link": None,
        "calendar_event_id": None,
        "created_at": now,
        "expires_at": now + timedelta(hours=cfg["token_expires_hours"]),
        "booked_at": None,
    }
    _bookings().insert_one(booking)

    booking_url = f"{cfg['base_url']}/book/{token}"
    from email_agent import send_email
    send_email(
        to=email,
        subject="You're Shortlisted — Choose Your Interview Slot",
        html_body=_slot_picker_html(
            booking["candidate_name"], score, booking_url, cfg["token_expires_hours"]
        ),
    )
    return token


def get_booking(token: str) -> Optional[dict]:
    return _bookings().find_one({"_id": token})


def select_slot(token: str, slot_iso: str) -> dict:
    """Atomically lock the chosen slot, create the real calendar event, return result.

    Result shape:
      {"ok": True, "meet_link": "...", "meeting_time": "..."}
      {"ok": False, "error": "..."}
    """
    cfg = _cfg()
    now = datetime.now(timezone.utc)
    booking = _bookings().find_one_and_update(
        {
            "_id": token,
            "status": "pending",
            "expires_at": {"$gt": now},
            "available_slots": slot_iso,
        },
        {"$set": {"status": "processing", "selected_slot": slot_iso}},
    )
    if not booking:
        existing = _bookings().find_one({"_id": token})
        if not existing:
            return {"ok": False, "error": "invalid_token"}
        if existing["status"] == "booked":
            return {"ok": False, "error": "already_booked"}
        if existing["expires_at"] <= now:
            return {"ok": False, "error": "expired"}
        return {"ok": False, "error": "slot_unavailable"}

    try:
        slot_dt = datetime.fromisoformat(slot_iso)
        if slot_dt.tzinfo is None:
            slot_dt = slot_dt.replace(tzinfo=cfg["tz"])
        hr_attendees = [booking["primary_hr_email"]]
        for m in booking.get("team_members") or []:
            if (m or {}).get("email"):
                hr_attendees.append(m["email"])

        from calendar_agent import create_calendar_event
        event = create_calendar_event(
            candidate_name=booking["candidate_name"],
            candidate_email=booking["candidate_email"],
            slot_start=slot_dt,
            score=booking["interview_score"],
            hr_attendees=hr_attendees,
        )

        _bookings().update_one(
            {"_id": token},
            {"$set": {
                "status": "booked",
                "meet_link": event["meet_link"],
                "calendar_event_id": event["event_id"],
                "booked_at": datetime.now(timezone.utc),
            }},
        )

        _meetings().replace_one(
            {"_id": booking["candidate_id"]},
            {
                "_id": booking["candidate_id"],
                "candidate_name": booking["candidate_name"],
                "candidate_email": booking["candidate_email"],
                "candidate_phone": booking.get("candidate_phone"),
                "jd_id": booking.get("jd_id"),
                "interview_score": booking["interview_score"],
                "meeting_time": event["start_time"],
                "meeting_end_time": event["end_time"],
                "meeting_duration_min": event["duration_min"],
                "meet_link": event["meet_link"],
                "calendar_event_id": event["event_id"],
                "attendees": [*hr_attendees, booking["candidate_email"]],
                "hr_attendees": hr_attendees,
                "primary_hr_email": booking["primary_hr_email"],
                "status": "scheduled",
                "booked_via": "candidate_selection",
                "booking_token": token,
                "created_at": datetime.now(timezone.utc),
                "timezone": event["timezone"],
            },
            upsert=True,
        )

        return {"ok": True, "meet_link": event["meet_link"], "meeting_time": event["start_time"].isoformat()}
    except Exception as e:  # noqa: BLE001
        _bookings().update_one(
            {"_id": token},
            {"$set": {"status": "pending", "selected_slot": None}},
        )
        print(f"[booking] failed to finalize {token}: {e!r}", file=sys.stderr)
        return {"ok": False, "error": "internal_error"}
