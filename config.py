"""Centralised non-secret application settings, loaded from config.yaml.

Secrets and per-deployment values (API keys, passwords, DB URI, Google IDs,
CORS origins, base URLs) stay in `.env` and are read with os.getenv where they
are used. All non-secret business configuration lives in `config.yaml`
(committed, diffable); this module loads it and exposes each value as a
module-level constant so callers keep using `config.VOICE_CALL_THRESHOLD` etc.
"""
import os

import yaml

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

with open(_CONFIG_PATH, "r") as _f:
    _CFG = yaml.safe_load(_f)

# --- Composite ranking weights (blend CV match + interview score) ---
RANK_CV_WEIGHT = _CFG["rank_cv_weight"]
RANK_INTERVIEW_WEIGHT = _CFG["rank_interview_weight"]

# --- Hiring recommendation score bands (composite_score -> label) ---
RECOMMEND_STRONG_YES = _CFG["recommend_strong_yes"]
RECOMMEND_YES = _CFG["recommend_yes"]
RECOMMEND_MAYBE = _CFG["recommend_maybe"]
RECOMMEND_REVIEW_MIN = _CFG["recommend_review_min"]

# --- Rule-based red-flag thresholds (below these -> flag raised) ---
RULE_MIN_EXPERIENCE_YEARS = _CFG["rule_min_experience_years"]
RULE_WEAK_CV = _CFG["rule_weak_cv"]
RULE_WEAK_INTERVIEW = _CFG["rule_weak_interview"]

# --- Voice screening ---
VOICE_CALL_THRESHOLD = _CFG["voice_call_threshold"]
SCORING_MODEL = _CFG["scoring_model"]
VAPI_DEFAULT_COUNTRY_CODE = _CFG["vapi_default_country_code"]

# --- Google Calendar (interview scheduling) ---
CALENDAR_TIMEZONE = _CFG["calendar_timezone"]
CALENDAR_BUSINESS_START_HOUR = _CFG["calendar_business_start_hour"]
CALENDAR_BUSINESS_END_HOUR = _CFG["calendar_business_end_hour"]
CALENDAR_MEETING_DURATION_MIN = _CFG["calendar_meeting_duration_min"]
CALENDAR_THRESHOLD = _CFG["calendar_threshold"]
CALENDAR_BUFFER_HOURS = _CFG["calendar_buffer_hours"]

# --- Candidate slot-picker booking window ---
BOOKING_DAYS_AHEAD = _CFG["booking_days_ahead"]
BOOKING_WEEKDAY_START_HOUR = _CFG["booking_weekday_start_hour"]
BOOKING_WEEKDAY_END_HOUR = _CFG["booking_weekday_end_hour"]
BOOKING_FRIDAY_START_HOUR = _CFG["booking_friday_start_hour"]
BOOKING_FRIDAY_END_HOUR = _CFG["booking_friday_end_hour"]
BOOKING_SLOT_DURATION_MIN = _CFG["booking_slot_duration_min"]
BOOKING_MAX_SLOTS_SHOWN = _CFG["booking_max_slots_shown"]
BOOKING_TOKEN_EXPIRES_HOURS = _CFG["booking_token_expires_hours"]

# --- Pre-interview reminder ---
REMINDER_HOURS_BEFORE = _CFG["reminder_hours_before"]

# --- Call recovery (retry declined calls) ---
MAX_RETRY_ATTEMPTS = _CFG["max_retry_attempts"]
RETRY_INTERVAL_MINUTES = _CFG["retry_interval_minutes"]

# --- Background loop intervals (seconds) ---
SHORTLIST_INTERVAL_SECONDS = _CFG["shortlist_interval_seconds"]
RETRY_LOOP_INTERVAL_SECONDS = _CFG["retry_loop_interval_seconds"]
REMINDER_LOOP_INTERVAL_SECONDS = _CFG["reminder_loop_interval_seconds"]
