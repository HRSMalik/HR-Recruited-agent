"""Google Calendar agent: find a free slot, create an interview event with Meet link."""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from googleapiclient.discovery import build

from services.parser_agent import _load_google_credentials

import config

load_dotenv(Path(__file__).resolve().parent / ".env")


def _cfg():
    return {
        "tz": ZoneInfo(config.CALENDAR_TIMEZONE),
        "start_hour": config.CALENDAR_BUSINESS_START_HOUR,
        "end_hour": config.CALENDAR_BUSINESS_END_HOUR,
        "duration_min": config.CALENDAR_MEETING_DURATION_MIN,
        "buffer_hours": config.CALENDAR_BUFFER_HOURS,
        "search_days_ahead": 14,
    }


def _service():
    creds = _load_google_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _candidate_slots(cfg: dict):
    """Yield potential start times (Mon-Fri, within business hours, after buffer)."""
    tz = cfg["tz"]
    now = datetime.now(tz)
    earliest = now + timedelta(hours=cfg["buffer_hours"])
    step = timedelta(minutes=cfg["duration_min"])

    for day_offset in range(cfg["search_days_ahead"]):
        day = (earliest + timedelta(days=day_offset)).date()
        weekday = day.weekday()
        if weekday >= 5:
            continue
        slot = datetime(day.year, day.month, day.day, cfg["start_hour"], 0, tzinfo=tz)
        end_of_day = datetime(day.year, day.month, day.day, cfg["end_hour"], 0, tzinfo=tz)
        while slot + step <= end_of_day:
            if slot >= earliest:
                yield slot
            slot += step


def find_next_available_slot(primary_hr_email: str) -> datetime:
    """Query primary HR's calendar busy times, return first free slot start datetime."""
    cfg = _cfg()
    service = _service()

    now = datetime.now(cfg["tz"])
    window_end = now + timedelta(days=cfg["search_days_ahead"] + 1)

    body = {
        "timeMin": now.isoformat(),
        "timeMax": window_end.isoformat(),
        "items": [{"id": primary_hr_email}],
    }
    fb = service.freebusy().query(body=body).execute()
    busy = fb.get("calendars", {}).get(primary_hr_email, {}).get("busy", [])

    busy_ranges = []
    for b in busy:
        s = datetime.fromisoformat(b["start"].replace("Z", "+00:00")).astimezone(cfg["tz"])
        e = datetime.fromisoformat(b["end"].replace("Z", "+00:00")).astimezone(cfg["tz"])
        busy_ranges.append((s, e))

    step = timedelta(minutes=cfg["duration_min"])
    for slot in _candidate_slots(cfg):
        slot_end = slot + step
        if not any(s < slot_end and slot < e for s, e in busy_ranges):
            return slot
    raise RuntimeError("No free slot found in the next 14 days within business hours.")


def is_slot_free(primary_hr_email: str, slot_start: datetime) -> bool:
    """Re-verify the chosen slot is still free on the primary HR's calendar.

    Used at selection time to prevent double-booking: between slot generation and
    a candidate's pick, the HR calendar may have changed (another candidate booked
    it, or a manual event was added). Returns True only if the [slot, slot+duration)
    window has no busy overlap.
    """
    cfg = _cfg()
    if slot_start.tzinfo is None:
        slot_start = slot_start.replace(tzinfo=cfg["tz"])
    slot_end = slot_start + timedelta(minutes=cfg["duration_min"])

    body = {
        "timeMin": slot_start.isoformat(),
        "timeMax": slot_end.isoformat(),
        "items": [{"id": primary_hr_email}],
    }
    fb = _service().freebusy().query(body=body).execute()
    busy = fb.get("calendars", {}).get(primary_hr_email, {}).get("busy", [])

    for b in busy:
        s = datetime.fromisoformat(b["start"].replace("Z", "+00:00"))
        e = datetime.fromisoformat(b["end"].replace("Z", "+00:00"))
        if s < slot_end and slot_start < e:  # overlap
            return False
    return True


def _build_description(score: int, insights: dict | None) -> str:
    """Calendar event description. The CANDIDATE is an attendee on this event, so
    it must NOT expose internal evaluation data — screening score, expected salary
    and notice period are deliberately omitted. Only neutral professional context
    (the candidate's own role/company/experience/stack) is kept for the interviewer.
    `score` is accepted for backward compatibility but intentionally not shown.
    """
    lines = ["Technical interview.", ""]
    if insights:
        if insights.get("current_role"):
            lines.append(f"Current role: {insights['current_role']}")
        if insights.get("current_company"):
            lines.append(f"Company: {insights['current_company']}")
        if insights.get("years_experience") is not None:
            lines.append(f"Experience: {insights['years_experience']} years")
        tech = insights.get("tech_stack") or []
        if tech:
            lines.append(f"Tech stack: {', '.join(tech)}")
    lines.append("")
    lines.append("Please be prepared for a technical interview.")
    return "\n".join(lines)


def create_calendar_event(candidate_name: str, candidate_email: str,
                          slot_start: datetime, score: int,
                          hr_attendees: list[str],
                          insights: dict | None = None) -> dict:
    """Create the Calendar event with Google Meet link. Returns event metadata."""
    if not hr_attendees:
        raise ValueError("hr_attendees is required and must contain at least one email.")
    cfg = _cfg()
    service = _service()
    primary_hr = hr_attendees[0]

    slot_end = slot_start + timedelta(minutes=cfg["duration_min"])
    attendees = [{"email": e} for e in hr_attendees]
    if candidate_email:
        attendees.append({"email": candidate_email})

    event_body = {
        "summary": f"Interview: {candidate_name}",
        "description": _build_description(score, insights),
        "start": {"dateTime": slot_start.isoformat(), "timeZone": str(cfg["tz"])},
        "end": {"dateTime": slot_end.isoformat(), "timeZone": str(cfg["tz"])},
        "attendees": attendees,
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        "reminders": {"useDefault": True},
    }

    created = service.events().insert(
        calendarId="primary",
        body=event_body,
        conferenceDataVersion=1,
        sendUpdates="all",
    ).execute()

    meet_link = None
    for ep in (created.get("conferenceData") or {}).get("entryPoints", []):
        if ep.get("entryPointType") == "video":
            meet_link = ep.get("uri")
            break

    return {
        "event_id": created["id"],
        "meet_link": meet_link or created.get("hangoutLink"),
        "start_time": slot_start,
        "end_time": slot_end,
        "duration_min": cfg["duration_min"],
        "hr_attendees": hr_attendees,
        "primary_hr_email": primary_hr,
        "timezone": str(cfg["tz"]),
    }


def schedule_interview(candidate_doc: dict, score: int,
                       hr_attendees: list[str],
                       insights: dict | None = None) -> dict:
    """Top-level: find slot + create event. Returns full meeting dict for MongoDB."""
    if not hr_attendees:
        raise ValueError("hr_attendees is required and must contain at least one email.")
    primary_hr = hr_attendees[0]

    name = candidate_doc.get("name") or "Candidate"
    email = candidate_doc.get("email")
    slot = find_next_available_slot(primary_hr_email=primary_hr)
    event = create_calendar_event(name, email, slot, score,
                                   hr_attendees=hr_attendees,
                                   insights=insights)
    return {
        "candidate_name": name,
        "candidate_email": email,
        "candidate_phone": candidate_doc.get("phone_e164") or candidate_doc.get("phone"),
        "jd_id": candidate_doc.get("jd_id"),
        "interview_score": score,
        "meeting_time": event["start_time"],
        "meeting_end_time": event["end_time"],
        "meeting_duration_min": event["duration_min"],
        "meet_link": event["meet_link"],
        "calendar_event_id": event["event_id"],
        "attendees": [*hr_attendees, email] if email else list(hr_attendees),
        "hr_attendees": hr_attendees,
        "primary_hr_email": primary_hr,
        "status": "scheduled",
        "created_at": datetime.now(timezone.utc),
        "timezone": event["timezone"],
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    test_hr = sys.argv[1] if len(sys.argv) > 1 else "filzanoornaeem@gmail.com"
    print(f"Next available slot for {test_hr}:", find_next_available_slot(test_hr))
