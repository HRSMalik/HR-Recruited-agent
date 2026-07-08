import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from pymongo import MongoClient
from dotenv import load_dotenv

from schemas import Criterion, CriterionImportance

load_dotenv()

_DB = None


def _get_db():
    global _DB
    if _DB is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _DB = MongoClient(uri)[db_name]
    return _DB


def _collection():
    return _get_db()["job_criteria"]


class _CriterionDraft(BaseModel):
    criteria: str = Field(description="Technical competency area from the JD (e.g. the domain or skill cluster). Never a soft skill, never education.")
    description: str = Field(max_length=1000, description="Concrete technical indicators to look for. No mention of attitude, communication, or education.")
    importance: CriterionImportance
    applies_to_cv: bool
    applies_to_interview: bool


class _CriteriaList(BaseModel):
    criteria: List[_CriterionDraft] = Field(description="6-10 technical criteria extracted from the JD. No soft skills.")


def generate_criteria(jd_id: str, jd_text: str) -> dict:
    """LLM generates criteria from JD text, saves as draft, returns the doc."""
    prompt = f"""Extract 6-10 technical evaluation criteria from this job description.

RULES:
- Each criterion must be a technical skill, domain, or methodology explicitly mentioned in the JD.
- Name each criterion as a technical competency area (e.g. the domain or skill cluster, not a task).
- DO NOT generate criteria for: education, degree, communication, teamwork, collaboration, passion, attitude, or any soft skill.
- Description: state what a strong candidate should demonstrate — tools, depth, scope. Be concrete.

Importance levels:
- must_have: explicitly required; candidate cannot do the job without it
- very_important: strongly preferred or repeated in JD
- important: mentioned as a requirement
- good_to_have: listed as a plus/nice-to-have

applies_to_cv: assessable from resume
applies_to_interview: should be probed via technical questions

=== JOB DESCRIPTION ===
{jd_text}"""

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    result: _CriteriaList = llm.with_structured_output(_CriteriaList).invoke(prompt)

    criteria = [
        Criterion(
            id=str(uuid.uuid4()),
            criteria=c.criteria,
            description=c.description,
            importance=c.importance,
            applies_to_cv=c.applies_to_cv,
            applies_to_interview=c.applies_to_interview,
        )
        for c in result.criteria
    ]

    doc = {
        "_id": jd_id,
        "jd_id": jd_id,
        "status": "draft",
        "criteria": [c.model_dump() for c in criteria],
        "generated_at": datetime.now(timezone.utc),
        "confirmed_at": None,
    }
    _collection().replace_one({"_id": jd_id}, doc, upsert=True)
    return doc


def get_criteria(jd_id: str) -> Optional[dict]:
    return _collection().find_one({"_id": jd_id})


def update_criteria(jd_id: str, criteria: List[Criterion]) -> dict:
    """Replace the criteria list; keeps draft status."""
    if not _collection().find_one({"_id": jd_id}):
        raise ValueError(f"No criteria found for jd_id={jd_id!r}")
    _collection().update_one(
        {"_id": jd_id},
        {"$set": {"criteria": [c.model_dump() for c in criteria]}},
    )
    return _collection().find_one({"_id": jd_id})


def confirm_criteria(jd_id: str) -> dict:
    """Lock criteria for scoring."""
    doc = _collection().find_one({"_id": jd_id})
    if not doc:
        raise ValueError(f"No criteria found for jd_id={jd_id!r}")
    if not doc.get("criteria"):
        raise ValueError("Cannot confirm an empty criteria list")
    _collection().update_one(
        {"_id": jd_id},
        {"$set": {"status": "confirmed", "confirmed_at": datetime.now(timezone.utc)}},
    )
    return _collection().find_one({"_id": jd_id})
