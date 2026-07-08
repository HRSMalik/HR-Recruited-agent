"""Centralised, non-secret application settings (thresholds & tunables).

Secrets and per-deployment values (API keys, passwords, DB URI, Google IDs,
CORS origins, base URLs, feature toggles) stay in `.env` and are read with
os.getenv where they are used. Everything here is business configuration that
is the same across environments, kept in one place to avoid drift.
"""

# --- Composite ranking weights (blend CV match + interview score) ---
RANK_CV_WEIGHT = 0.4
RANK_INTERVIEW_WEIGHT = 0.6

# --- Hiring recommendation score bands (composite_score -> label) ---
RECOMMEND_STRONG_YES = 80
RECOMMEND_YES = 65
RECOMMEND_MAYBE = 50
RECOMMEND_REVIEW_MIN = 70

# --- Rule-based red-flag thresholds (below these -> flag raised) ---
RULE_MIN_EXPERIENCE_YEARS = 0
RULE_WEAK_CV = 40
RULE_WEAK_INTERVIEW = 40

# --- Voice screening ---
VOICE_CALL_THRESHOLD = 70          # fit_percent >= this -> candidate is called
SCORING_MODEL = "gpt-4o"           # LLM used to score interview transcripts
VAPI_DEFAULT_COUNTRY_CODE = "+92"  # default region for phone normalisation

# --- Google Calendar (interview scheduling) ---
CALENDAR_TIMEZONE = "Asia/Karachi"
CALENDAR_BUSINESS_START_HOUR = 14
CALENDAR_BUSINESS_END_HOUR = 17
CALENDAR_MEETING_DURATION_MIN = 30
CALENDAR_THRESHOLD = 60            # interview score >= this -> book a meeting
CALENDAR_BUFFER_HOURS = 24         # earliest bookable slot, from now

# --- Candidate slot-picker booking window ---
BOOKING_DAYS_AHEAD = 10
BOOKING_WEEKDAY_START_HOUR = 10
BOOKING_WEEKDAY_END_HOUR = 19
BOOKING_FRIDAY_START_HOUR = 10
BOOKING_FRIDAY_END_HOUR = 12
BOOKING_SLOT_DURATION_MIN = 60
BOOKING_MAX_SLOTS_SHOWN = 50
BOOKING_TOKEN_EXPIRES_HOURS = 48

# --- Pre-interview reminder ---
REMINDER_HOURS_BEFORE = 8

# --- Call recovery (retry declined calls) ---
MAX_RETRY_ATTEMPTS = 3
RETRY_INTERVAL_MINUTES = 5

# --- Background loop intervals (seconds) ---
SHORTLIST_INTERVAL_SECONDS = 30
RETRY_LOOP_INTERVAL_SECONDS = 60
REMINDER_LOOP_INTERVAL_SECONDS = 900
