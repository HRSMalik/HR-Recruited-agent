from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
import fitz  # PyMuPDF
from pathlib import Path
import base64
import csv
import json
import os
import re
import shutil
import uuid
from datetime import date
from io import StringIO
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()


_MONGO_COLLECTION = None


def _get_candidates_collection():
    """Lazily build and cache the MongoDB `candidates_info` collection handle."""
    global _MONGO_COLLECTION
    if _MONGO_COLLECTION is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _MONGO_COLLECTION = MongoClient(uri)[db_name]["candidates_info"]
    return _MONGO_COLLECTION


class ParserAgentState(TypedDict, total=False):
    pdf_path: str
    pages_root: str
    cv_id: str
    work_dir: str
    image_paths: List[str]
    cv_text: str
    extracted_data: Dict[str, Any]
    form_experience_str: str
    llm_experience_years: float
    saved: bool


def pdf_to_images(pdf_path: str, output_dir: str) -> str:
    """Render each PDF page to PNG inside output_dir."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            pix.save(str(output_dir / f"page_{page_num + 1}.png"))
    finally:
        doc.close()

    return str(output_dir)


def init_node(state: ParserAgentState) -> ParserAgentState:
    if not state.get("pdf_path"):
        raise ValueError("Missing 'pdf_path' in parser state.")
    pages_root = state.get("pages_root") or "pdf_pages"
    cv_id = str(uuid.uuid4())
    work_dir = str(Path(pages_root) / cv_id)
    return {**state, "cv_id": cv_id, "work_dir": work_dir}


def render_pages_node(state: ParserAgentState) -> ParserAgentState:
    folder = pdf_to_images(state["pdf_path"], state["work_dir"])
    image_paths = sorted(
        str(Path(folder) / f)
        for f in os.listdir(folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    )
    return {**state, "image_paths": image_paths}


def ocr_node(state: ParserAgentState) -> ParserAgentState:
    doc = fitz.open(state["pdf_path"])
    try:
        extracted_text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
    return {**state, "cv_text": extracted_text}


def _parse_role_date(s):
    if not s:
        return None
    s = str(s).strip().lower()
    if s in ("present", "current", "now", "ongoing", "today"):
        return date.today()
    m = re.match(r"^(\d{4})-(\d{1,2})", s)
    if m:
        year, month = int(m.group(1)), max(1, min(12, int(m.group(2))))
        return date(year, month, 1)
    m = re.match(r"^(\d{4})$", s)
    if m:
        return date(int(m.group(1)), 1, 1)
    return None


def _months_between(start, end):
    """Months in the half-open interval [start, end). Standard CV-duration semantics."""
    months = set()
    if not start or not end or start >= end:
        return months
    y, m = start.year, start.month
    while (y, m) < (end.year, end.month):
        months.add((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _compute_experience(roles):
    """Given LLM-extracted role list, return (professional_years, freelance_years) as exact decimals."""
    professional_months = set()
    freelance_months = set()

    if not isinstance(roles, list):
        return 0.0, 0.0

    for role in roles:
        if not isinstance(role, dict):
            continue
        kind = (role.get("kind") or "professional").strip().lower()
        start = _parse_role_date(role.get("start"))
        end = _parse_role_date(role.get("end")) or date.today()
        months = _months_between(start, end)
        if not months:
            continue
        if kind == "internship":
            continue
        if kind == "freelance":
            freelance_months |= months
        else:
            professional_months |= months

    return (
        round(len(professional_months) / 12, 2),
        round(len(freelance_months) / 12, 2),
    )


def extract_fields_node(state: ParserAgentState) -> ParserAgentState:
    cv_text = state["cv_text"]

    prompt = f"""
    Extract the following information from the CV text.

    Return ONLY valid JSON (no markdown, no commentary).

    Required fields:
    - name
    - phone
    - email
    - last_education_institution
    - last_education_degree (e.g., "Bachelor's in Computer Science")
    - experience_roles: a JSON ARRAY of work history records.

    For each role in the CV, add one object to experience_roles:
    {{
      "title": "<job title>",
      "company": "<employer>",
      "start": "<YYYY-MM>",
      "end": "<YYYY-MM or 'present'>",
      "kind": "professional" | "internship" | "freelance"
    }}

    Rules for experience_roles:
    - DO NOT compute or sum durations. Just extract dates.
    - Use YYYY-MM format when the month is explicit in the CV.
    - If ONLY the year is given (e.g., "2023 - Present"), return just the year ("2023"), NOT "2023-01".
    - If the role is currently ongoing, end = "present".
    - kind = "internship" only for unpaid or explicitly labeled intern roles.
    - kind = "freelance" only for Upwork/Fiverr/gig platforms.
    - All other roles (Projects-Based, Contract, Part-time, Full-time) are "professional".
    - ONLY include actual employment at a named company/organization.
      DO NOT include: personal projects, academic projects, university final-year projects,
      portfolio items, hackathon entries, side projects, or anything where the "employer"
      is just a project name. If you cannot identify a real employer/company for the role,
      DO NOT include it.

    Other rules:
    - If a non-experience field is missing, return an empty string.
    - Do not wrap JSON in markdown.

    CV TEXT:
    {cv_text}
    """

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    response = llm.invoke(prompt)

    try:
        data = json.loads(response.content)
    except Exception:
        data = {
            "name": "",
            "phone": "",
            "email": "",
            "last_education_institution": "",
            "last_education_degree": "",
            "experience_roles": [],
        }

    roles = data.get("experience_roles") or []
    prof_years, freelance_years = _compute_experience(roles)
    data["experience_years"] = prof_years
    data["freelance_experience_years"] = freelance_years

    data["raw_cv_text"] = cv_text
    return {**state, "extracted_data": data}


def fetch_form_response_node(state: ParserAgentState) -> ParserAgentState:
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    email = ((state.get("extracted_data") or {}).get("email") or "").strip().lower()
    if not sheet_id or not email:
        return {**state, "form_experience_str": ""}

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception:
        return {**state, "form_experience_str": ""}

    reader = csv.DictReader(StringIO(resp.text))
    for row in reader:
        if (row.get("Email") or "").strip().lower() == email:
            return {**state, "form_experience_str": (row.get("Experience") or "").strip()}

    return {**state, "form_experience_str": ""}


def relookup_experience_node(state: ParserAgentState) -> ParserAgentState:
    cv_text = state.get("cv_text") or ""
    if not cv_text.strip():
        return {**state, "llm_experience_years": 0.0}

    prompt = f"""
    Calculate the candidate's total years of professional work experience from the CV text below.

    Rules:
    - Sum the duration of each non-freelance, non-internship professional role.
    - For roles ending "present", today's date is {date.today()}.
    - Return ONLY a single decimal number (e.g. 2.5). No words, no units.

    CV TEXT:
    {cv_text}
    """

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    response = llm.invoke(prompt)

    match = re.search(r"-?\d+(?:\.\d+)?", response.content or "")
    value = float(match.group()) if match else 0.0
    return {**state, "llm_experience_years": value}


def _parse_form_experience(s: str):
    if not s:
        return None, False
    is_threshold = "+" in s
    match = re.search(r"-?\d+(?:\.\d+)?", s)
    return (float(match.group()), is_threshold) if match else (None, False)


def validate_experience_node(state: ParserAgentState) -> ParserAgentState:
    extracted = dict(state.get("extracted_data") or {})
    form_str = state.get("form_experience_str", "")
    llm_val = float(state.get("llm_experience_years") or 0.0)

    cv_raw = extracted.get("experience_years", "")
    try:
        cv_val = float(cv_raw) if cv_raw not in ("", None) else None
    except (TypeError, ValueError):
        cv_val = None

    n, is_threshold = _parse_form_experience(form_str)

    if cv_val is None or n is None:
        result = "No"
    elif is_threshold:
        result = "Yes" if (llm_val >= n and cv_val >= n) else "No"
    else:
        result = "Yes" if (abs(llm_val - n) <= 0.2 and abs(cv_val - n) <= 0.2) else "No"

    extracted["validate_experience"] = result
    return {**state, "extracted_data": extracted}


def persist_node(state: ParserAgentState) -> ParserAgentState:
    cv_id = state["cv_id"]
    data = state["extracted_data"]
    _get_candidates_collection().replace_one(
        {"_id": cv_id},
        {**data, "_id": cv_id},
        upsert=True,
    )
    return {**state, "saved": True}


def cleanup_node(state: ParserAgentState) -> ParserAgentState:
    work_dir = Path(state["work_dir"])
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    return state


def create_parser_agent():
    workflow = StateGraph(ParserAgentState)

    workflow.add_node("init", init_node)
    workflow.add_node("render_pages", render_pages_node)
    workflow.add_node("ocr", ocr_node)
    workflow.add_node("extract_fields", extract_fields_node)
    workflow.add_node("fetch_form", fetch_form_response_node)
    workflow.add_node("relookup_experience", relookup_experience_node)
    workflow.add_node("validate_experience", validate_experience_node)
    workflow.add_node("persist", persist_node)
    workflow.add_node("cleanup", cleanup_node)

    workflow.set_entry_point("init")
    workflow.add_edge("init", "render_pages")
    workflow.add_edge("render_pages", "ocr")
    workflow.add_edge("ocr", "extract_fields")
    workflow.add_edge("extract_fields", "fetch_form")
    workflow.add_edge("fetch_form", "relookup_experience")
    workflow.add_edge("relookup_experience", "validate_experience")
    workflow.add_edge("validate_experience", "persist")
    workflow.add_edge("persist", "cleanup")
    workflow.add_edge("cleanup", END)

    return workflow.compile()


parser_agent = create_parser_agent()


def process_cv(pdf_path: str, pages_root: str = "pdf_pages") -> dict:
    initial_state: ParserAgentState = {
        "pdf_path": pdf_path,
        "pages_root": pages_root,
    }
    work_dir_fallback = None
    try:
        final_state = parser_agent.invoke(initial_state)
        work_dir_fallback = final_state.get("work_dir")
        return {
            "id": final_state["cv_id"],
            "data": final_state["extracted_data"],
        }
    finally:
        if work_dir_fallback:
            p = Path(work_dir_fallback)
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)


if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "faiz.pdf"
    result = process_cv(pdf_path)
    print(result)
