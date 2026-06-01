import os
import re
from typing import List, Optional
from langchain.chat_models import init_chat_model
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


_DB = None


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


def _score_candidate_against_jd(candidate: dict, jd_text: str) -> int:
    """Ask the LLM to score 0-100 how well the candidate fits the JD."""
    candidate_summary = {
        "name": candidate.get("name"),
        "experience_years": candidate.get("experience_years"),
        "freelance_experience_years": candidate.get("freelance_experience_years"),
        "last_education_degree": candidate.get("last_education_degree"),
        "last_education_institution": candidate.get("last_education_institution"),
        "raw_cv_text": candidate.get("raw_cv_text", ""),
    }

    prompt = f"""
    You are evaluating whether a candidate is a fit for a job.

    JOB DESCRIPTION:
    {jd_text}

    CANDIDATE:
    {candidate_summary}

    Compare the candidate's skills and experience against the job description.
    Return ONLY a single integer between 0 and 100 representing the fit percentage.
    No explanation, no other text, just the number.
    """

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    response = llm.invoke(prompt)
    raw = (response.content or "").strip()

    match = re.search(r"\d{1,3}", raw)
    if not match:
        return 0
    score = int(match.group(0))
    return max(0, min(100, score))


def shortlist_for_jd(jd_id: str) -> List[dict]:
    """Score every unscored candidate linked to `jd_id` against the JD.

    Writes the score back to `candidates_info.fit_percent`. Returns the list
    of newly-scored candidates sorted by fit_percent descending.
    """
    jd_doc = _job_descriptions().find_one({"_id": jd_id})
    if not jd_doc:
        raise ValueError(f"No job_description found for jd_id={jd_id!r}.")
    jd_text = jd_doc.get("job_description", "")
    if not jd_text.strip():
        raise ValueError(f"job_description for jd_id={jd_id!r} is empty.")

    candidates = list(_candidates().find(
        {"jd_id": jd_id, "fit_percent": {"$exists": False}}
    ))
    if not candidates:
        return []

    results = []
    for candidate in candidates:
        cv_id = candidate.get("_id")
        score = _score_candidate_against_jd(candidate, jd_text)
        _candidates().update_one(
            {"_id": cv_id},
            {"$set": {"fit_percent": score}},
        )
        results.append({"_id": cv_id, "jd_id": jd_id, "fit_percent": score})

    results.sort(key=lambda d: d["fit_percent"], reverse=True)
    return results


def shortlist_all_jobs() -> dict:
    """Run shortlisting across every job in `job_descriptions`.

    Returns a summary keyed by jd_id. Failures on one job don't block the others.
    """
    summary: dict = {}
    for jd in _job_descriptions().find({}, {"_id": 1}):
        jd_id = jd["_id"]
        try:
            results = shortlist_for_jd(jd_id)
            summary[jd_id] = {"scored": len(results)}
        except Exception as e:  # noqa: BLE001
            summary[jd_id] = {"error": repr(e)}
    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python shortlisting_agent.py <jd_id>")
        sys.exit(1)
    for r in shortlist_for_jd(sys.argv[1]):
        print(f"{r['fit_percent']:3d}%  cv_id={r['_id']}")
