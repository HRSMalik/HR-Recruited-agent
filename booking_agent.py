"""Candidate-driven slot picker booking flow.

After a candidate passes voice screening, instead of auto-scheduling a fixed
slot, we generate a list of available slots from the HR's calendar, save a
`pending_booking`, and email the candidate a link to pick their preferred time.
Once the candidate picks a slot, a real calendar event with Google Meet is
created (reusing `calendar_agent`) and the booking is marked `booked`.
"""
import html
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

import config

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


def _reservations():
    return _get_db()["slot_reservations"]


def _reserve_slots(attendee_emails: list, slot_iso: str, candidate_id: str) -> Optional[list]:
    """Atomically reserve `slot_iso` for every attendee. Returns the list of
    reserved _ids on success, or None if any attendee's slot is already taken.

    Each reservation _id is "email|slot_iso" — MongoDB's unique _id makes the
    insert atomic, so two candidates picking the same time can never both win
    (no Google-Calendar propagation lag, no check-then-act race). If a later
    attendee collides, the ones already inserted are rolled back so no slot is
    left blocked. A reservation already held by THIS candidate (e.g. a retry
    after a failed finalize) is treated as owned, not a collision.
    """
    from pymongo.errors import DuplicateKeyError

    reserved: list = []
    for email in dict.fromkeys(e for e in attendee_emails if e):  # dedup, drop empty
        rid = f"{email}|{slot_iso}"
        try:
            _reservations().insert_one({"_id": rid, "candidate_id": candidate_id,
                                        "created_at": datetime.now(timezone.utc)})
            reserved.append(rid)
        except DuplicateKeyError:
            existing = _reservations().find_one({"_id": rid})
            if existing and existing.get("candidate_id") == candidate_id:
                reserved.append(rid)  # already ours
                continue
            _release_slots(reserved)  # collision -> roll back this candidate's holds
            return None
    return reserved


def _release_slots(reserved_ids: list) -> None:
    """Delete reservation rows so the slot is bookable again (rollback / cancel)."""
    if reserved_ids:
        _reservations().delete_many({"_id": {"$in": reserved_ids}})


def _cfg() -> dict:
    return {
        "tz": ZoneInfo(config.CALENDAR_TIMEZONE),
        "days_ahead": config.BOOKING_DAYS_AHEAD,
        "weekday_start": config.BOOKING_WEEKDAY_START_HOUR,
        "weekday_end": config.BOOKING_WEEKDAY_END_HOUR,
        "friday_start": config.BOOKING_FRIDAY_START_HOUR,
        "friday_end": config.BOOKING_FRIDAY_END_HOUR,
        "slot_duration_min": config.BOOKING_SLOT_DURATION_MIN,
        "max_slots_shown": config.BOOKING_MAX_SLOTS_SHOWN,
        "token_expires_hours": config.BOOKING_TOKEN_EXPIRES_HOURS,
        "base_url": os.getenv("BOOKING_BASE_URL", "http://localhost:8000"),
        "buffer_hours": config.CALENDAR_BUFFER_HOURS,
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
    # name is candidate-supplied (from CV) -> escape to prevent stored XSS in email.
    name = html.escape(str(name))
    booking_url = html.escape(str(booking_url))
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color:#222; max-width:560px; margin:auto;">
        <h2 style="color:#2e7d32;">Congratulations {name}!</h2>
        <p>You've successfully cleared the voice screening.</p>
        <p>Please choose your interview slot below:</p>
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
        # Mongo may return a tz-NAIVE expires_at; `now` is tz-aware. Comparing
        # them raises TypeError -> 500. Normalize to UTC-aware first (mirrors the
        # GET /book/{token} handler).
        expires = existing["expires_at"]
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= now:
            return {"ok": False, "error": "expired"}
        return {"ok": False, "error": "slot_unavailable"}

    reserved: list = []
    try:
        slot_dt = datetime.fromisoformat(slot_iso)
        if slot_dt.tzinfo is None:
            slot_dt = slot_dt.replace(tzinfo=cfg["tz"])
        hr_attendees = [booking["primary_hr_email"]]
        for m in booking.get("team_members") or []:
            if (m or {}).get("email"):
                hr_attendees.append(m["email"])

        from calendar_agent import create_calendar_event, is_slot_free

        # Layer 1 (authoritative): atomically reserve the slot for EVERY attendee
        # in MongoDB before doing anything else. This closes the check-then-act
        # race — two candidates picking the same time can never both win, and a
        # shared team member can't be double-booked across two candidates.
        acquired = _reserve_slots(hr_attendees, slot_iso, booking["candidate_id"])
        if acquired is None:
            _bookings().update_one(
                {"_id": token},
                {"$set": {"status": "pending", "selected_slot": None}},
            )
            return {"ok": False, "error": "slot_taken"}
        reserved[:] = acquired

        # Layer 2 (safety net): the slot was free at generation, but a manual HR
        # event may have appeared since. Release our reservation + the booking so
        # the candidate can re-pick.
        if not is_slot_free(booking["primary_hr_email"], slot_dt):
            _release_slots(reserved)
            _bookings().update_one(
                {"_id": token},
                {"$set": {"status": "pending", "selected_slot": None}},
            )
            return {"ok": False, "error": "slot_taken"}

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
                "reminder_sent": False,
            },
            upsert=True,
        )

        return {"ok": True, "meet_link": event["meet_link"], "meeting_time": event["start_time"].isoformat()}
    except Exception as e:  # noqa: BLE001
        # Release the slot we reserved so it isn't blocked forever, and reopen
        # the booking for a re-pick.
        _release_slots(reserved)
        _bookings().update_one(
            {"_id": token},
            {"$set": {"status": "pending", "selected_slot": None}},
        )
        print(f"[booking] failed to finalize {token}: {e!r}", file=sys.stderr)
        return {"ok": False, "error": "internal_error"}


def _render_reminder(meeting: dict, hours: int) -> str:
    """HTML body for the pre-interview reminder email."""
    mt = meeting.get("meeting_time")
    when = mt.strftime("%a %d %b %Y, %I:%M %p") if hasattr(mt, "strftime") else str(mt)
    # Escape every interpolated field (candidate_name from CV is untrusted).
    when = html.escape(when)
    tz = html.escape(str(meeting.get("timezone", "")))
    meet = html.escape(str(meeting.get("meet_link", "")))
    name = html.escape(str(meeting.get("candidate_name", "Candidate")))
    return f"""<div style="font-family:sans-serif">
      <h2>Interview Reminder</h2>
      <p>This is a reminder that the interview with <b>{name}</b> is in about
      <b>{hours} hours</b>.</p>
      <p><b>When:</b> {when} {tz}</p>
      <p><b>Google Meet:</b> <a href="{meet}">{meet}</a></p>
      <p>Please be available a few minutes early.</p>
    </div>"""


def send_due_reminders() -> dict:
    """Send a one-time pre-interview reminder to candidate + HR/team members.

    Scans `meetings` for scheduled interviews starting within REMINDER_HOURS_BEFORE
    hours that haven't been reminded yet, emails everyone on the meeting, and sets
    `reminder_sent` so each meeting is reminded exactly once. Driven by the
    background _reminder_loop in app.py (time-based, not part of the graph).
    """
    from email_agent import send_email

    hours = config.REMINDER_HOURS_BEFORE
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=hours)

    due = list(_meetings().find({
        "status": "scheduled",
        "reminder_sent": {"$ne": True},
        "meeting_time": {"$gt": now, "$lte": window_end},
    }))

    sent = 0
    errors: list[str] = []
    for m in due:
        recipients = [m.get("candidate_email"), *(m.get("hr_attendees") or [])]
        recipients = [r for r in dict.fromkeys(recipients) if r]  # dedup, drop empty
        subject = f"Reminder: Interview in ~{hours}h — {m.get('candidate_name', 'Candidate')}"
        html = _render_reminder(m, hours)
        try:
            for r in recipients:
                send_email(r, subject, html)
            _meetings().update_one(
                {"_id": m["_id"]},
                {"$set": {"reminder_sent": True, "reminder_sent_at": now}},
            )
            sent += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"{m.get('_id')}: {e!r}")

    return {"sent": sent, "errors": errors}
