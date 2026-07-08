import os
import re
from typing import List
from langchain.chat_models import init_chat_model
from pymongo import MongoClient
from dotenv import load_dotenv

from utils.schemas import CriteriaScoringResult, ProfessionalScoringResult

load_dotenv()

_DB = None
_IMPORTANCE_WEIGHTS = {
    "must_have": 4,
    "very_important": 3,
    "important": 2,
    "good_to_have": 1,
}
_MAX_CV_CHARS = 3000


def _get_db():
    global _DB
    if _DB is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _DB = MongoClient(uri)[db_name]
    return _DB


def _candidates():
    return _get_db()["candidates_info"]


def _job_descriptions():
    return _get_db()["job_descriptions"]


def _job_criteria():
    return _get_db()["job_criteria"]


def _format_candidate(candidate: dict) -> str:
    cv_text = (candidate.get("raw_cv_text") or "").strip()[:_MAX_CV_CHARS]
    return f"""Name: {candidate.get('name') or 'Unknown'}
Email: {candidate.get('email') or 'N/A'}
Experience: {candidate.get('experience_years', 0)} yrs professional, {candidate.get('freelance_experience_years', 0)} yrs freelance
Education: {candidate.get('last_education_degree') or 'N/A'} — {candidate.get('last_education_institution') or 'N/A'}

Resume:
{cv_text or '(empty)'}"""


def _extract_required_years(jd_text: str) -> float:
    """Extract minimum required experience years from JD text via regex. Returns 0 if not found."""
    patterns = [
        r'(\d+)\+\s*years?\s+(?:of\s+)?(?:professional\s+)?experience',
        r'minimum\s+(?:of\s+)?(\d+)\s*\+?\s*years?',
        r'at\s+least\s+(\d+)\s*\+?\s*years?',
        r'(\d+)\s*[-–]\s*\d+\s*years?\s+(?:of\s+)?experience',
        r'(\d+)\s*years?\s+(?:of\s+)?(?:relevant\s+)?(?:professional\s+)?experience',
    ]
    for pat in patterns:
        m = re.search(pat, jd_text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return 0.0


_SENIOR_KEYWORDS = (
    "senior", "sr.", "lead", "principal", "staff", "manager",
    "head of", "director", "architect", "chief",
)


def _is_senior_role(jd_text: str) -> bool:
    """Does the JD's title (always the first line) signal a senior/leadership
    role? Managerial-experience scoring only makes sense there — junior/mid
    candidates shouldn't be penalized for lacking team-lead experience."""
    title_line = jd_text.strip().splitlines()[0].lower() if jd_text.strip() else ""
    return any(kw in title_line for kw in _SENIOR_KEYWORDS)


def _calc_experience_score(candidate_years: float, required_years: float) -> float:
    """Return experience contribution 0–10 based on gap rules."""
    if required_years <= 0:
        return 8.3  # no stated requirement — near-full credit (~83%)

    gap = required_years - candidate_years

    if gap <= 0:
        credits = 85 if (candidate_years - required_years) >= 3 else 100
    elif gap < 0.5:
        credits = 95
    elif gap < 1.0:
        credits = 82
    elif gap < 2.0:
        credits = 60
    else:
        credits = 32

    return round((credits / 100) * 10, 1)


def _score_technical_criteria(cv_text: str, criteria: List[dict]) -> CriteriaScoringResult:
    criteria_block = "\n".join(
        f"{i+1}. [{c['importance'].upper()}] {c['criteria']}: {c['description']}"
        for i, c in enumerate(criteria)
    )
    prompt = f"""Score this candidate's CV against each technical criterion. Score 1-10 per criterion.

Scale: 1=no evidence, 3=weak/tangential, 5=partial/related, 7=good match, 10=strong direct proof with depth.

For each criterion:
- Cite specific evidence from the CV.
- If score < 8, state explicitly what is missing.
- Return one score per criterion in the same order listed.

=== CRITERIA ===
{criteria_block}

=== CV ===
{cv_text}"""

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    return llm.with_structured_output(CriteriaScoringResult).invoke(prompt)


def _score_professional(candidate: dict) -> ProfessionalScoringResult:
    cv_text = (candidate.get("raw_cv_text") or "").strip()[:_MAX_CV_CHARS]
    email = candidate.get("email", "")
    prompt = f"""Evaluate this CV on the following dimensions. Score each 1-10.

Document Professionalism:
- attention_to_detail (formatting consistency, typos, correct dates, clean layout)
- clarity_completion (all expected sections present, dates complete, no ambiguous info)

Professional Profile:
- strategic_focus (coherent career direction; roles align toward a clear goal)
- intellectual_ability (complexity of work tackled, advanced problem-solving, publications)
- managerial_experience (led teams or people; score 1 if no evidence at all)
- recognized_accomplishments (awards, certifications, notable publications or mentions)
- critical_thinking (quantified results, problem/solution framing, impact-oriented language)

Red Flags:
- timeline_tenure: true if employment gaps > 3 months or avg tenure < 1 yr
- experience_misrepresentation: true if claims seem inflated, vague, or inconsistent with dates
- unprofessional_email: true if email looks informal (e.g. cooldude123@, random digits)

Candidate email: {email}

=== CV ===
{cv_text}"""

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    return llm.with_structured_output(ProfessionalScoringResult).invoke(prompt)


def _calc_cv_score(
    tech: CriteriaScoringResult,
    criteria: List[dict],
    prof: ProfessionalScoringResult,
    experience_score: float,
    is_senior: bool,
) -> int:
    # Technical: 70%
    name_to_weight = {c["criteria"]: _IMPORTANCE_WEIGHTS.get(c["importance"], 1) for c in criteria}
    weighted_sum = sum(cs.score * name_to_weight.get(cs.criterion_name, 1) for cs in tech.scores)
    total_weight = sum(name_to_weight.get(cs.criterion_name, 1) for cs in tech.scores)
    technical_raw = weighted_sum / total_weight if total_weight else 5
    technical_contribution = (technical_raw / 10) * 70

    # Professional: 20%. managerial_experience only counts for senior/lead
    # roles — junior/mid candidates aren't expected to have led teams.
    dp = prof.document_professionalism
    pp = prof.professional_profile
    prof_scores = [
        dp.attention_to_detail, dp.clarity_completion,
        pp.strategic_focus, pp.intellectual_ability,
        pp.recognized_accomplishments, pp.critical_thinking,
    ]
    if is_senior:
        prof_scores.append(pp.managerial_experience)
    professional_contribution = (sum(prof_scores) / len(prof_scores) / 10) * 20

    # Experience: 10% (already on 0–10 scale)
    return max(0, min(100, round(technical_contribution + professional_contribution + experience_score)))


def _print_breakdown(
    tech: CriteriaScoringResult,
    prof: ProfessionalScoringResult,
    experience_score: float,
    required_years: float,
    candidate_years: float,
    total: int,
    is_senior: bool,
):
    print("=== Technical Criteria (70%) ===")
    for cs in tech.scores:
        print(f"  {cs.criterion_name}: {cs.score}/10 | {cs.evidence}")

    dp = prof.document_professionalism
    pp = prof.professional_profile
    rf = prof.red_flags

    print("=== Document Professionalism (20%) ===")
    print(f"  Attention to Detail:  {dp.attention_to_detail}/10 | {dp.attention_evidence}")
    print(f"  Clarity & Completion: {dp.clarity_completion}/10 | {dp.clarity_evidence}")

    print("=== Professional Profile ===")
    print(f"  Strategic Focus:          {pp.strategic_focus}/10 | {pp.strategic_evidence}")
    print(f"  Intellectual Ability:     {pp.intellectual_ability}/10 | {pp.intellectual_evidence}")
    counted_note = "" if is_senior else " (not counted — non-senior role)"
    print(f"  Managerial Experience:    {pp.managerial_experience}/10{counted_note} | {pp.managerial_evidence}")
    print(f"  Recognized Achievements:  {pp.recognized_accomplishments}/10 | {pp.accomplishments_evidence}")
    print(f"  Critical Thinking:        {pp.critical_thinking}/10 | {pp.critical_thinking_evidence}")

    print("=== Experience (10%) ===")
    print(f"  Candidate: {candidate_years} yrs | Required: {required_years} yrs | Score: {experience_score}/10")

    print("=== Red Flags ===")
    print(f"  Timeline/Tenure:             {rf.timeline_tenure} | {rf.timeline_evidence}")
    print(f"  Experience Misrepresentation:{rf.experience_misrepresentation} | {rf.representation_evidence}")
    print(f"  Unprofessional Email:        {rf.unprofessional_email}")

    print(f"=== Final Score: {total}/100 ===")


def _build_score_payload(
    tech: CriteriaScoringResult,
    prof: ProfessionalScoringResult,
    experience_score: float,
    required_years: float,
    total: int,
    is_senior: bool,
) -> dict:
    return {
        "fit_percent": total,
        "criteria_scores": [cs.model_dump() for cs in tech.scores],
        "document_professionalism": prof.document_professionalism.model_dump(),
        "professional_profile": prof.professional_profile.model_dump(),
        "red_flags": prof.red_flags.model_dump(),
        "experience_score": experience_score,
        "experience_required_years": required_years,
        "managerial_experience_counted": is_senior,
    }


def _score_candidate(candidate: dict, criteria: List[dict], jd_text: str = "") -> dict:
    cv_text = _format_candidate(candidate)
    tech = _score_technical_criteria(cv_text, criteria)
    prof = _score_professional(candidate)

    required_years = _extract_required_years(jd_text)
    candidate_years = (
        float(candidate.get("experience_years") or 0)
        + float(candidate.get("freelance_experience_years") or 0)
    )
    experience_score = _calc_experience_score(candidate_years, required_years)
    is_senior = _is_senior_role(jd_text)

    total = _calc_cv_score(tech, criteria, prof, experience_score, is_senior)
    _print_breakdown(tech, prof, experience_score, required_years, candidate_years, total, is_senior)
    return _build_score_payload(tech, prof, experience_score, required_years, total, is_senior)


def shortlist_for_jd(jd_id: str) -> List[dict]:
    jd_doc = _job_descriptions().find_one({"_id": jd_id})
    if not jd_doc:
        raise ValueError(f"No job_description found for jd_id={jd_id!r}.")
    jd_text = jd_doc.get("job_description", "")

    criteria_doc = _job_criteria().find_one({"_id": jd_id})
    if not criteria_doc or criteria_doc.get("status") != "confirmed":
        raise ValueError(f"No confirmed criteria for jd_id={jd_id!r}. Confirm criteria before scoring.")
    criteria = criteria_doc.get("criteria", [])
    if not criteria:
        raise ValueError(f"Criteria list is empty for jd_id={jd_id!r}.")

    candidates = list(_candidates().find({"jd_id": jd_id, "fit_percent": {"$exists": False}}))
    if not candidates:
        return []

    results = []
    for candidate in candidates:
        cv_id = candidate.get("_id")
        _candidates().update_one({"_id": cv_id}, {"$set": {"processing": True}})
        payload = _score_candidate(candidate, criteria, jd_text)
        payload["processing"] = False
        _candidates().update_one({"_id": cv_id}, {"$set": payload})
        results.append({"_id": cv_id, "jd_id": jd_id, "fit_percent": payload["fit_percent"]})

    results.sort(key=lambda d: d["fit_percent"], reverse=True)
    return results


def shortlist_all_jobs() -> dict:
    summary: dict = {}
    for jd in _job_descriptions().find({}, {"_id": 1}):
        jd_id = jd["_id"]
        try:
            results = shortlist_for_jd(jd_id)
            summary[jd_id] = {"scored": len(results)}
        except Exception as e:
            summary[jd_id] = {"error": repr(e)}
    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python shortlisting_agent.py <jd_id>")
        sys.exit(1)
    for r in shortlist_for_jd(sys.argv[1]):
        print(f"{r['fit_percent']:3d}%  cv_id={r['_id']}")
