from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict, Optional, List, Dict, Any
import fitz  # PyMuPDF
from pathlib import Path
import base64
import io
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from datetime import date, datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()


_MONGO_COLLECTION = None
_PROCESSED_COLLECTION = None


def _get_candidates_collection():
    """Lazily build and cache the MongoDB `candidates_info` collection handle."""
    global _MONGO_COLLECTION
    if _MONGO_COLLECTION is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _MONGO_COLLECTION = MongoClient(uri)[db_name]["candidates_info"]
    return _MONGO_COLLECTION


def _get_processed_collection():
    """Tracks already-ingested Drive file IDs so re-runs don't re-parse the same CV."""
    global _PROCESSED_COLLECTION
    if _PROCESSED_COLLECTION is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _PROCESSED_COLLECTION = MongoClient(uri)[db_name]["processed_applications"]
    return _PROCESSED_COLLECTION


_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
]
_GOOGLE_CREDS_PATH = ".credentials/credentials.json"
_GOOGLE_TOKEN_PATH = ".credentials/google_token.json"
_FILE_ID_RE = re.compile(r"[?&]id=([a-zA-Z0-9_-]+)|/d/([a-zA-Z0-9_-]+)")


def _authorize_or_raise(reason: str):
    """Run the OAuth flow if we have a TTY; otherwise raise a clear error."""
    if sys.stdin.isatty():
        print(f"{reason}; launching authorization flow...", file=sys.stderr)
        authorize()
    else:
        raise RuntimeError(
            f"{reason}. Run `python parser_agent.py auth` in a terminal to authorize, "
            f"then restart the server."
        )


def _load_google_credentials() -> Credentials:
    if not os.path.exists(_GOOGLE_TOKEN_PATH):
        _authorize_or_raise(reason=f"No token at {_GOOGLE_TOKEN_PATH}")

    creds = Credentials.from_authorized_user_file(_GOOGLE_TOKEN_PATH, _GOOGLE_SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(_GOOGLE_TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
            except RefreshError as e:
                try:
                    os.remove(_GOOGLE_TOKEN_PATH)
                except OSError:
                    pass
                _authorize_or_raise(
                    reason=f"Refresh token at {_GOOGLE_TOKEN_PATH} was revoked ({e})"
                )
                creds = Credentials.from_authorized_user_file(_GOOGLE_TOKEN_PATH, _GOOGLE_SCOPES)
        else:
            _authorize_or_raise(reason=f"Token at {_GOOGLE_TOKEN_PATH} is invalid and cannot be refreshed")
            creds = Credentials.from_authorized_user_file(_GOOGLE_TOKEN_PATH, _GOOGLE_SCOPES)
    return creds


def authorize():
    """Run the OAuth flow once and save a token with Drive + Sheets scopes.

    Idempotent: re-running with a valid token of the right scopes is a no-op.
    If the existing token has different scopes, it's deleted and re-created
    so the user re-consents to the new scope set.
    """
    if not os.path.exists(_GOOGLE_CREDS_PATH):
        raise FileNotFoundError(
            f"Missing {_GOOGLE_CREDS_PATH}. Download an OAuth client JSON from "
            f"Google Cloud Console > APIs & Services > Credentials and place it there."
        )

    if os.path.exists(_GOOGLE_TOKEN_PATH):
        existing = Credentials.from_authorized_user_file(_GOOGLE_TOKEN_PATH, _GOOGLE_SCOPES)
        if set(existing.scopes or []) != set(_GOOGLE_SCOPES):
            print("Existing token has different scopes; re-authorizing...")
            os.remove(_GOOGLE_TOKEN_PATH)
        else:
            print(f"Token already at {_GOOGLE_TOKEN_PATH} with correct scopes. Nothing to do.")
            return

    flow = InstalledAppFlow.from_client_secrets_file(_GOOGLE_CREDS_PATH, _GOOGLE_SCOPES)
    creds = flow.run_local_server(
        port=0,
        login_hint=os.getenv("HR_EMAIL", "filzanoornaeem@gmail.com"),
        prompt="consent",
    )
    os.makedirs(os.path.dirname(_GOOGLE_TOKEN_PATH), exist_ok=True)
    with open(_GOOGLE_TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    print(f"Saved token to {_GOOGLE_TOKEN_PATH}")


def _read_sheet_rows(sheets_service, spreadsheet_id: str, sheet_name: str) -> List[dict]:
    """Read the sheet and return rows as dicts keyed by column header."""
    rng = f"{sheet_name}!A1:ZZ"
    resp = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=rng
    ).execute()
    values = resp.get("values", [])
    if not values:
        return []
    headers = values[0]
    rows = []
    for raw in values[1:]:
        padded = raw + [""] * (len(headers) - len(raw))
        rows.append(dict(zip(headers, padded)))
    return rows


def _extract_drive_file_id(cell_value: str) -> Optional[str]:
    """Extract the first Drive file ID from a Google Form file-upload cell."""
    if not cell_value:
        return None
    m = _FILE_ID_RE.search(cell_value)
    if not m:
        return None
    return m.group(1) or m.group(2)


def _download_drive_pdf(drive_service, file_id: str, dest_path: str) -> None:
    request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    with open(dest_path, "wb") as f:
        f.write(fh.read())

class ParserAgentState(TypedDict):
    pass




def pdf_to_images(pdf_path, output_dir):
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



def extract_text_from_pdf(pdf_path: str, work_dir: str) -> str:
    """Render PDF pages into work_dir and OCR them with the OpenAI vision model."""
    folder_path = pdf_to_images(pdf_path, work_dir)
    try:
        image_paths = sorted(
            f for f in os.listdir(folder_path) if f.endswith((".png", ".jpg", ".jpeg"))
        )
        extracted_text = ""

        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        for image_path in image_paths:
            with open(os.path.join(folder_path, image_path), "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

                ext = os.path.splitext(image_path)[-1].lower()
                mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
                mime_type = mime_map.get(ext, "image/png")

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{mime_type};base64,{image_data}"}
                                },
                                {
                                    "type": "text",
                                    "text": "Extract and return all the text visible in this image. Return only the extracted text, nothing else."
                                }
                            ]
                        }
                    ],
                    max_tokens=2000
                )
                extracted_text += response.choices[0].message.content.strip() + "\n"
        return extracted_text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""
    

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


def extract_cv_details(cv_text: str, cv_id: str, jd_id: Optional[str] = None) -> dict:
    prompt = f"""
    Extract the following information from the CV text.

    Return ONLY valid JSON with these fields:
    - name (string)
    - phone (string)
    - email (string)
    - last_education_institution (string)
    - last_education_degree (string, e.g. "Bachelor's in Computer Science")
    - roles (array): work history. Each entry must be an object with:
        - kind: one of "professional", "freelance", "internship"
        - start: "YYYY-MM" (or "YYYY" if only the year is given)
        - end: "YYYY-MM", or "present" if the role is ongoing
        - title: job title (string, optional)
        - company: company name (string, optional)

    Classification rules for `kind`:
    - "freelance" if the work was via Upwork, Fiverr, Toptal, Freelancer.com,
      or the role is explicitly self-employed / contract / freelance.
    - "internship" for internships, co-ops, apprenticeships, trainee programs.
    - "professional" for everything else (full-time, part-time employment).

    Output rules:
    - If a string field is missing, return "".
    - If no work history can be extracted, return roles: [].
    - Do not include explanations.
    - Do not wrap the JSON in markdown.

    CV TEXT:
    {cv_text}
    """

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    response = llm.invoke(prompt)

    try:
        json_response = json.loads(response.content)
    except Exception:
        json_response = {
            "name": "",
            "phone": "",
            "email": "",
            "last_education_institution": "",
            "last_education_degree": "",
            "roles": [],
        }

    prof_years, freelance_years = _compute_experience(json_response.get("roles") or [])
    json_response["experience_years"] = prof_years
    json_response["freelance_experience_years"] = freelance_years
    json_response["raw_cv_text"] = cv_text

    _get_candidates_collection().replace_one(
        {"_id": cv_id},
        {**json_response, "_id": cv_id, "jd_id": jd_id},
        upsert=True,
    )

    return json_response


def process_cv(pdf_path: str, jd_id: Optional[str] = None, pages_root: str = "pdf_pages", extracted_root: str = "extracted_data",) -> dict:

    cv_id = str(uuid.uuid4())
    work_dir = Path(pages_root) / cv_id
    try:
        cv_text = extract_text_from_pdf(pdf_path, str(work_dir))
        data = extract_cv_details(cv_text, cv_id, jd_id)
        return {"id": cv_id, "data": data}
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def ingest_new_applicants() -> dict:
    """Pull unprocessed rows from the `initial_applicants` sheet, download each CV
    from Drive, run it through `process_cv`, and record the file_id in
    `processed_applications` so re-runs skip it.

    Required env vars:
      GOOGLE_SHEETS_ID              Spreadsheet ID (from the sheet URL).
      GOOGLE_SHEET_NAME             Tab name. Default: "Form Responses 1".
      GOOGLE_SHEET_JOB_ID_COLUMN    Header text. Default: "Job ID".
      GOOGLE_SHEET_CV_COLUMN        Header text. Default: "Upload your CV".
    """
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SHEETS_ID env var not set.")

    sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Form Responses 1")
    job_id_col = os.getenv("GOOGLE_SHEET_JOB_ID_COLUMN", "Job ID")
    cv_col = os.getenv("GOOGLE_SHEET_CV_COLUMN", "Upload your CV")

    creds = _load_google_credentials()
    sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

    rows = _read_sheet_rows(sheets_service, spreadsheet_id, sheet_name)
    processed = _get_processed_collection()

    ingested = 0
    skipped = 0
    errors: list[str] = []

    for row in rows:
        jd_id = (row.get(job_id_col) or "").strip()
        cv_cell = row.get(cv_col) or ""
        file_id = _extract_drive_file_id(cv_cell)

        if not jd_id or not file_id:
            skipped += 1
            continue

        if processed.find_one({"_id": file_id}):
            skipped += 1
            continue

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                pdf_path = os.path.join(tmp_dir, f"{file_id}.pdf")
                _download_drive_pdf(drive_service, file_id, pdf_path)
                result = process_cv(pdf_path, jd_id=jd_id)

            processed.insert_one({
                "_id": file_id,
                "processed_at": datetime.now(timezone.utc),
                "jd_id": jd_id,
                "cv_id": result["id"],
            })
            ingested += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"file_id={file_id}: {e!r}")

    return {"ingested": ingested, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    import sys as _sys
    cmd = _sys.argv[1] if len(_sys.argv) > 1 else ""
    if cmd == "auth":
        authorize()
    elif cmd == "ingest":
        print(ingest_new_applicants(), file=_sys.stderr)
    else:
        result = process_cv("syedali.pdf")
        print(result)