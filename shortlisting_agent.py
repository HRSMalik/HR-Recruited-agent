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


_MAX_CV_CHARS = 3000


def _format_candidate(candidate: dict) -> str:
    """Render candidate as clean, structured text for the LLM (avoid raw dict)."""
    cv_text = (candidate.get("raw_cv_text") or "").strip()[:_MAX_CV_CHARS]
    return f"""Name: {candidate.get('name') or 'Unknown'}

Experience:
  - Professional: {candidate.get('experience_years', 0)} years
  - Freelance: {candidate.get('freelance_experience_years', 0)} years

Education:
  - Degree: {candidate.get('last_education_degree') or 'N/A'}
  - Institution: {candidate.get('last_education_institution') or 'N/A'}

Resume Content:
{cv_text or '(empty)'}"""


def _score_candidate_against_jd(candidate: dict, jd_text: str) -> int:
    """LLM scores 0-100 how well the candidate's CV matches THIS specific JD."""
    candidate_block = _format_candidate(candidate)

    prompt = f"""
You are a senior recruiter scoring how well a candidate's CV matches a specific job.

=========== JOB DESCRIPTION ===========
{jd_text}
=======================================

=========== CANDIDATE ===========
{candidate_block}
=================================

WEIGHTED CRITERIA:
  1. Technical skill match (35%): JD's required tools/tech vs candidate's CV.
     Direct matches AND equivalent alternatives both count strongly.
  2. Experience relevance (30%): Years + project quality aligned with the role.
  3. Education alignment (20%): Degree level + field match (see hierarchy).
  4. Project specificity (10%): Concrete examples, quantifiable impact in CV.
  5. Domain / industry match (5%): Same sector experience (bonus only).

5-TIER RUBRIC:
  85-100  Exceptional fit. All required skills present, strong relevant
          experience, education aligned or exceeds requirement.
  70-84   Strong candidate. Most key skills covered (direct or equivalent),
          relevant experience, appropriate education.
  60-74   Decent fit. Partial skill overlap, transferable experience, some
          relevant background.
  40-59   Weak match. Limited skill overlap, tangential experience.
  0-39    Poor fit. No skill alignment, major mismatch.

EQUIVALENT SKILLS — treat as essentially matching, credit the same:
  - Data manipulation: Pandas ≈ Polars ≈ Dask ≈ PySpark
  - Deep learning:     PyTorch ≈ TensorFlow ≈ JAX ≈ Keras
  - Classical ML:      scikit-learn ≈ XGBoost ≈ LightGBM ≈ CatBoost
  - Web backend:       FastAPI ≈ Flask ≈ Django REST ≈ Express ≈ NestJS
  - Web frontend:      React ≈ Vue ≈ Svelte ≈ Angular ≈ SolidJS
  - SSR / meta:        Next.js ≈ Nuxt ≈ Remix ≈ SvelteKit
  - Styling:           Tailwind ≈ Bootstrap ≈ Material UI ≈ Chakra
  - SQL DBs:           PostgreSQL ≈ MySQL ≈ MariaDB ≈ SQL Server
  - NoSQL DBs:         MongoDB ≈ DynamoDB ≈ Firestore ≈ CosmosDB
  - Caches/queues:     Redis ≈ Memcached ; Kafka ≈ RabbitMQ ≈ SQS
  - Containers:        Docker ≈ Podman ; Kubernetes ≈ Docker Swarm ≈ Nomad
  - Cloud:             AWS ≈ GCP ≈ Azure (cross-cloud is fine)
  - LLM frameworks:    LangChain ≈ LlamaIndex ≈ Haystack ≈ Semantic Kernel
  - ETL/orchestration: Airflow ≈ Prefect ≈ Dagster ≈ Luigi
  - Vector stores:     Pinecone ≈ Weaviate ≈ Qdrant ≈ Milvus ≈ pgvector
  - CI/CD:             GitHub Actions ≈ GitLab CI ≈ CircleCI ≈ Jenkins

GENERAL EQUIVALENCE RULE: If a tool the candidate has serves the SAME PURPOSE
as a tool the JD requires, credit it as a match. Do NOT penalize for using a
different tool in the same family.

MODERN ALTERNATIVE BONUS: Newer/better alternatives (e.g., Polars instead of
Pandas, FastAPI instead of Flask, Rust instead of C) are a STRONG positive
signal — they indicate up-to-date skills, not a gap.

EDUCATION HIERARCHY:
  Level credit:   PhD > MPhil/MS > Bachelor's > Diploma
  Field alignment:
    - Exact field match: full credit
    - Adjacent field (CS ≈ Software Eng ≈ IT): full credit
    - Related field (Data Science ≈ Statistics ≈ Math for ML role): ~80%
    - Unrelated field: ~30%
  Rules:
    - A higher degree in a RELATED field is an UPGRADE, not a mismatch
      (e.g., MPhil in AI for an AI Engineer role asking for Bachelor's = strong).
    - Don't penalize "wrong degree name" if the field genuinely aligns.

DOMAIN MATCH BONUS (+5 to +10):
  If the JD names a domain (healthcare, fintech, e-commerce, edtech, gaming,
  etc.) and the candidate's CV shows experience in that same domain:
    - Direct domain match: +10
    - Adjacent domain:     +5
    - No domain mention:   no bonus, no penalty

CALIBRATION EXAMPLES (assume JD: AI Engineer, Python + FastAPI + ML):

  Score 90:
    "5 years Python at fintech, built FastAPI services backing a PyTorch
     recommendation system, deployed on AWS, led 4-person ML team."
    → Direct skills + experience + leadership + domain.

  Score 78:
    "MPhil in AI from a top university, built 3 production ML models using
     PyTorch, deployed with Flask on GCP, 1 year hands-on work."
    → Strong education (MPhil > Bachelor's) + equivalents (Flask≈FastAPI,
       GCP≈AWS) + concrete projects.

  Score 62:
    "3 years Python developer, built REST APIs with Flask, some ML through
     online courses, no production ML deployment."
    → Python yes, backend equivalent, but ML lacks depth.

  Score 38:
    "5 years JavaScript + PHP web developer, no Python or ML background."
    → Major gap in required skills.

Return ONLY a single integer 0-100. No explanation. No other text.
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
