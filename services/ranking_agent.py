"""Blend CV-match and interview scores into one composite score.

`compute_composite`, `recommend`, and `detect_rule_flags` are pure (no DB).
`rank_candidate` is the persistence layer: it reads from candidates_info /
screened_candidates / interview_insights and writes a unified ranked_candidates
document.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional, TypedDict
from dotenv import load_dotenv

import config
logger = logging.getLogger(__name__)

load_dotenv()




def _get_db():
    from services.db import get_db
    return get_db()


def _candidates():
    return _get_db()["candidates_info"]


def _screened():
    return _get_db()["screened_candidates"]


def _insights():
    return _get_db()["interview_insights"]


def _ranked():
    return _get_db()["ranked_candidates"]


class ScoreBreakdown(TypedDict):
    cv_match: float
    interview: Optional[float]
    weights: dict


class CompositeResult(TypedDict):
    composite_score: float
    score_breakdown: ScoreBreakdown


def _read_weights(
    cv_override: Optional[float] = None,
    interview_override: Optional[float] = None,
) -> tuple[float, float]:
    """Resolve CV/interview weights, normalised to sum 1.0.

    Uses the explicit overrides when both are given (e.g. a re-rank run with
    custom weights); otherwise falls back to the env values.
    """
    if cv_override is not None and interview_override is not None:
        cv, interview = float(cv_override), float(interview_override)
    else:
        cv = config.RANK_CV_WEIGHT
        interview = config.RANK_INTERVIEW_WEIGHT
    total = cv + interview
    if total <= 0:
        raise ValueError("CV + interview weights must sum to > 0.")
    return cv / total, interview / total


def _clamp(score: float) -> float:
    return max(0.0, min(100.0, score))


def compute_composite(
    fit_percent: float,
    interview_score: Optional[float],
    cv_weight: Optional[float] = None,
    interview_weight: Optional[float] = None,
) -> CompositeResult:
    """Blend CV match and interview performance into one 0-100 score.

    When `interview_score` is None the candidate was never interviewed, so the
    composite is CV-only. This keeps half-scored candidates from outranking
    fully-interviewed ones (an interviewed weak candidate isn't beaten by an
    un-interviewed strong CV unless the CV genuinely scores higher).

    `cv_weight`/`interview_weight` override the env weights for this call (used
    by the on-demand re-rank flow); both must be given or both omitted.
    """
    cv = _clamp(float(fit_percent))
    cv_weight, interview_weight = _read_weights(cv_weight, interview_weight)

    if interview_score is None:
        return {
            "composite_score": round(cv, 2),
            "score_breakdown": {
                "cv_match": cv,
                "interview": None,
                "weights": {"cv": 1.0, "interview": 0.0},
            },
        }

    interview = _clamp(float(interview_score))
    composite = _clamp(cv * cv_weight + interview * interview_weight)
    return {
        "composite_score": round(composite, 2),
        "score_breakdown": {
            "cv_match": cv,
            "interview": interview,
            "weights": {"cv": round(cv_weight, 4), "interview": round(interview_weight, 4)},
        },
    }


def recommend(composite_score: Optional[float], red_flags: Optional[list]) -> str:
    """Map a composite score to a hiring recommendation label.

    Clean candidates use the score bands directly. Any red flag forces a
    conservative downgrade: a high score becomes "review" (human must look)
    and anything else becomes "no" — a flagged candidate is never auto-advanced.
    """
    if composite_score is None:
        return "no"

    score = _clamp(float(composite_score))

    strong_yes = config.RECOMMEND_STRONG_YES
    yes = config.RECOMMEND_YES
    maybe = config.RECOMMEND_MAYBE
    review_min = config.RECOMMEND_REVIEW_MIN

    if red_flags:
        return "review" if score >= review_min else "no"

    if score >= strong_yes:
        return "strong_yes"
    if score >= yes:
        return "yes"
    if score >= maybe:
        return "maybe"
    return "no"


def detect_rule_flags(candidate: dict) -> list:
    """Hard, deterministic red flags from candidate fields + config thresholds.

    Complements the LLM-detected interview flags with rules the model can't be
    trusted to apply consistently. Only checks fields that actually exist on the
    candidate document; missing fields are skipped, not flagged.
    """
    if not candidate:
        return []

    flags: list = []
    fit = candidate.get("fit_percent")
    interview = candidate.get("interview_score")
    exp = candidate.get("experience_years")

    min_exp = config.RULE_MIN_EXPERIENCE_YEARS
    weak_cv = config.RULE_WEAK_CV
    weak_interview = config.RULE_WEAK_INTERVIEW

    if exp is not None and float(exp) < min_exp:
        flags.append(f"insufficient experience (<{min_exp:g} yrs)")
    if fit is not None and float(fit) < weak_cv:
        flags.append(f"low CV match (<{weak_cv:g})")
    if interview is not None and float(interview) < weak_interview:
        flags.append(f"weak interview (<{weak_interview:g})")

    return flags


def rank_candidate(
    cv_id,
    cv_weight: Optional[float] = None,
    interview_weight: Optional[float] = None,
) -> Optional[dict]:
    """Persist a unified ranked record for one candidate.

    Reads CV match (candidates_info), interview score + combined red flags
    (screened_candidates, set by voice_agent), and key strengths
    (interview_insights). Computes composite + recommendation and upserts a
    ranked_candidates doc; also mirrors composite_score + recommendation back
    onto candidates_info for quick lookup.

    Idempotent — re-running for the same cv_id overwrites the same doc.
    Returns the ranked doc, or None if the cv_id is unknown.
    """
    cand = _candidates().find_one({"_id": cv_id})
    if not cand:
        return None

    screened = _screened().find_one({"_id": cv_id}) or {}
    insights = _insights().find_one({"_id": cv_id}) or {}

    fit_percent = cand.get("fit_percent") or 0
    interview_score = screened.get("interview_score")

    # Red flags: prefer the combined (LLM + rule) flags voice_agent already
    # stored on screened_candidates. If the candidate was never interviewed,
    # fall back to rule-based flags derived from the CV match.
    if screened.get("red_flags") is not None:
        red_flags = screened.get("red_flags") or []
    else:
        red_flags = detect_rule_flags({
            "fit_percent": fit_percent,
            "interview_score": interview_score,
            "experience_years": cand.get("experience_years"),
        })

    key_strengths = insights.get("key_strengths") or []
    interview_status = screened.get("status") or "not_interviewed"

    composite = compute_composite(fit_percent, interview_score, cv_weight, interview_weight)
    composite_score = composite["composite_score"]
    recommendation = recommend(composite_score, red_flags)

    doc = {
        "_id": cv_id,
        "jd_id": cand.get("jd_id"),
        "name": cand.get("name"),
        "email": cand.get("email"),
        "phone": cand.get("phone"),
        "composite_score": composite_score,
        "score_breakdown": composite["score_breakdown"],
        "recommendation": recommendation,
        "red_flags": red_flags,
        "key_strengths": key_strengths,
        "interview_status": interview_status,
        "ranked_at": datetime.now(timezone.utc),
    }
    _ranked().replace_one({"_id": cv_id}, doc, upsert=True)

    _candidates().update_one(
        {"_id": cv_id},
        {"$set": {
            "composite_score": composite_score,
            "recommendation": recommendation,
        }},
    )
    return doc


def rank_for_jd(jd_id, top_n: Optional[int] = None) -> list:
    """Return a job's ranked_candidates, highest composite first.

    MongoDB does the sort (composite_score descending); each doc is annotated
    with a 1-based `rank`. `top_n` caps the list at the DB level; omitting it
    returns the full ranked list. Unknown/empty job → [].
    """
    cursor = _ranked().find({"jd_id": jd_id}).sort("composite_score", -1)
    if top_n and top_n > 0:
        cursor = cursor.limit(top_n)

    results = []
    for i, doc in enumerate(cursor):
        doc["_id"] = str(doc["_id"])
        doc["rank"] = i + 1
        results.append(doc)
    return results


def rerank_jd(
    jd_id,
    cv_weight: Optional[float] = None,
    interview_weight: Optional[float] = None,
) -> list:
    """Recompute every ranked_candidates record for a job, then return the
    refreshed ranked shortlist.

    Re-runs `rank_candidate` for each already-ranked candidate using the given
    weight overrides (or the current env weights when omitted) — the CV and
    interview scores are reused, only the blend changes.
    """
    cv_ids = [d["_id"] for d in _ranked().find({"jd_id": jd_id}, {"_id": 1})]
    for cv_id in cv_ids:
        rank_candidate(cv_id, cv_weight, interview_weight)
    return rank_for_jd(jd_id)


if __name__ == "__main__":
    # Self-test (no DB required): runs with `python ranking_agent.py`.

    # compute_composite — happy path: blends CV + interview by env weights.
    blended = compute_composite(80, 67)
    assert blended["composite_score"] == 72.2, blended
    assert blended["score_breakdown"]["interview"] == 67.0
    logger.info(f"[ok] composite happy path     -> {blended['composite_score']}")

    # compute_composite — CV-only when never interviewed.
    cv_only = compute_composite(90, None)
    assert cv_only["composite_score"] == 90.0, cv_only
    assert cv_only["score_breakdown"]["interview"] is None
    assert cv_only["score_breakdown"]["weights"] == {"cv": 1.0, "interview": 0.0}
    logger.info(f"[ok] composite CV-only path   -> {cv_only['composite_score']}")

    # recommend — strong_yes (clean, high score).
    assert recommend(85, []) == "strong_yes"
    logger.info("[ok] recommend strong_yes")

    # recommend — review (high score but a red flag forces human review).
    assert recommend(85, ["fake degree"]) == "review"
    logger.info("[ok] recommend review (flagged)")

    # recommend — no (flag + sub-threshold score).
    assert recommend(60, ["unexplained gap"]) == "no"
    logger.info("[ok] recommend no")

    logger.info("All self-tests passed.")
