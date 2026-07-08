"""Extract structured insights from a voice-screening transcript using gpt-4o-mini."""
import json
import logging
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent / ".env")


SCHEMA_KEYS = [
    "candidate_name", "current_role", "current_company", "years_experience",
    "education", "tech_stack", "current_salary", "expected_salary",
    "notice_period_weeks", "work_mode_preference", "reason_for_change",
    "interest_level", "communication_quality",
    "red_flags", "key_strengths", "extraction_notes",
]
ARRAY_KEYS = ["tech_stack", "red_flags", "key_strengths"]


def _build_prompt(transcript: str) -> str:
    return f"""Extract structured info from this recruitment interview transcript.
Return ONLY valid JSON. Use null if a field is not mentioned. Do not infer.

TRANSCRIPT:
{transcript}

Required JSON schema:
{{
  "candidate_name": "string or null",
  "current_role": "string or null",
  "current_company": "string or null",
  "years_experience": "number or null",
  "education": {{"degree": "string or null", "institution": "string or null"}},
  "tech_stack": ["array of skill strings"],
  "current_salary": {{"value": "number or null", "currency": "string or null", "period": "monthly|yearly|null", "raw_text": "string"}},
  "expected_salary": {{"value": "number or null", "currency": "string or null", "period": "monthly|yearly|null", "raw_text": "string"}},
  "notice_period_weeks": "number or null",
  "work_mode_preference": "remote|onsite|hybrid|flexible|null",
  "reason_for_change": "string or null",
  "interest_level": "high|medium|low|null",
  "communication_quality": "clear|unclear|mixed",
  "red_flags": ["array of concern strings, [] if none"],
  "key_strengths": ["array of strength strings, [] if none"],
  "extraction_notes": "string with any caveats"
}}

Rules:
- Salary "200" likely means 200000 PKR if context supports; keep raw_text always.
- Tech stack: normalize (e.g., "py" -> "Python"). Skip generic words.
- Be conservative; null beats wrong info.
"""


def _validate(data: dict) -> dict:
    """Ensure schema compliance and normalize values."""
    for key in SCHEMA_KEYS:
        data.setdefault(key, None)
    for arr_key in ARRAY_KEYS:
        if not isinstance(data.get(arr_key), list):
            data[arr_key] = []
    wm = data.get("work_mode_preference")
    if isinstance(wm, str):
        wm_low = wm.lower()
        if "remote" in wm_low:
            data["work_mode_preference"] = "remote"
        elif "onsite" in wm_low or "office" in wm_low or "in-person" in wm_low:
            data["work_mode_preference"] = "onsite"
        elif "hybrid" in wm_low:
            data["work_mode_preference"] = "hybrid"
    return data


def extract_interview_insights(transcript: str) -> dict:
    """Main entry: returns structured dict extracted from transcript."""
    if not transcript or not transcript.strip():
        return {"extraction_failed": True, "error": "empty transcript"}

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    try:
        response = llm.invoke(_build_prompt(transcript))
        raw = (response.content or "").strip()
        # Strip code fences if model returns them
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        return _validate(data)
    except json.JSONDecodeError as e:
        logger.error(f"[transcript_analyzer] JSON parse failed: {e}")
        return {"extraction_failed": True, "error": f"json_decode: {e}", "raw_response": raw[:500]}
    except Exception as e:
        logger.error(f"[transcript_analyzer] extraction failed: {e}")
        return {"extraction_failed": True, "error": str(e)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sample = sys.stdin.read() if not sys.stdin.isatty() else "AI: tell me about yourself.\nUser: I am Ali, 3 years experience, AI Engineer."
    result = extract_interview_insights(sample)
    logger.info(json.dumps(result, indent=2, ensure_ascii=False))
