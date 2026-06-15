"""Standalone test: trigger the slot-picker booking flow end-to-end.

Skips voice call + scoring. Inserts a temporary job (with primary HR email),
a synthetic candidate, then calls create_slot_picker_booking with score=85.

Expected result:
  1. Email arrives at HR_EMAIL with subject "You're Shortlisted..."
  2. Email contains a "Pick Your Slot" link to http://localhost:8000/book/{token}
  3. Clicking a slot creates a real Google Calendar event + Meet link
  4. Confirmation page shown, calendar invite emailed via sendUpdates="all"

Run: python test_booking_flow.py
"""
import os
import sys
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

HR_EMAIL = "filzanoornaeem@gmail.com"
CANDIDATE_EMAIL = "filzanoor2025@gmail.com"
TEAM_MEMBER_EMAIL = "filza.n@tekhqs.com"
TEST_JOB_ID = f"test-job-{uuid.uuid4().hex[:8]}"
TEST_CAND_ID = f"test-cand-{uuid.uuid4().hex[:8]}"


def _db():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    name = os.getenv("MONGODB_DB", "recruitment-module")
    return MongoClient(uri)[name]


def main():
    db = _db()

    db["job_descriptions"].insert_one({
        "_id": TEST_JOB_ID,
        "role_title": "Test Role - Booking Flow",
        "primary_hr_email": HR_EMAIL,
        "team_members": [{"email": TEAM_MEMBER_EMAIL, "role": "Interviewer"}],
        "created_at": datetime.now(timezone.utc),
    })
    print(f"[setup] inserted test job: {TEST_JOB_ID}")
    print(f"[setup] primary HR: {HR_EMAIL}")
    print(f"[setup] team member: {TEAM_MEMBER_EMAIL}")

    candidate_doc = {
        "_id": TEST_CAND_ID,
        "name": "Test Candidate",
        "email": CANDIDATE_EMAIL,
        "phone_e164": "+923219499451",
        "phone": "+923219499451",
        "jd_id": TEST_JOB_ID,
    }
    print(f"[setup] using candidate: {TEST_CAND_ID}")

    from booking_agent import create_slot_picker_booking
    token = create_slot_picker_booking(candidate_doc, score=85)

    if not token:
        print("\n[FAIL] No booking created. Possible reasons:")
        print("  - No available slots in HR calendar")
        print("  - Gmail send permission missing (re-run: python parser_agent.py auth)")
        print("  - HR calendar not accessible via OAuth")
        sys.exit(1)

    base_url = os.getenv("BOOKING_BASE_URL", "http://localhost:8000")
    print(f"\n[OK] Booking created!")
    print(f"     Token: {token}")
    print(f"     URL  : {base_url}/book/{token}")
    print(f"\nNext steps:")
    print(f"  1. Check candidate inbox: {CANDIDATE_EMAIL}")
    print(f"  2. Email subject: 'You're Shortlisted - Choose Your Interview Slot'")
    print(f"  3. Click 'Pick Your Slot' (or open URL above)")
    print(f"  4. Pick any slot -> calendar event + Meet link created")
    print(f"  5. Calendar invite emailed to:")
    print(f"     - HR: {HR_EMAIL}")
    print(f"     - Team: {TEAM_MEMBER_EMAIL}")
    print(f"     - Candidate: {CANDIDATE_EMAIL}")
    print(f"\nCleanup (after testing):")
    print(f"  db.job_descriptions.deleteOne({{_id: '{TEST_JOB_ID}'}})")
    print(f"  db.pending_bookings.deleteOne({{_id: '{token}'}})")


if __name__ == "__main__":
    main()
