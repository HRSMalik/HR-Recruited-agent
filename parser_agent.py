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
from google.auth.transport.requests import Request
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
]
_GOOGLE_CREDS_PATH = ".credentials/credentials.json"
_GOOGLE_TOKEN_PATH = ".credentials/google_token.json"
_FILE_ID_RE = re.compile(r"[?&]id=([a-zA-Z0-9_-]+)|/d/([a-zA-Z0-9_-]+)")


def _load_google_credentials() -> Credentials:
    if not os.path.exists(_GOOGLE_TOKEN_PATH):
        raise RuntimeError(
            f"Missing {_GOOGLE_TOKEN_PATH}. Run `python download_drive.py` once interactively "
            f"to authorize with Sheets + Drive scopes."
        )
    creds = Credentials.from_authorized_user_file(_GOOGLE_TOKEN_PATH, _GOOGLE_SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(_GOOGLE_TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                f"Stored token at {_GOOGLE_TOKEN_PATH} is invalid and cannot be refreshed. "
                f"Re-run `python download_drive.py` to re-authorize."
            )
    return creds


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
    

def extract_cv_details(cv_text: str, cv_id: str, jd_id: Optional[str] = None) -> dict:
    prompt = f"""
    Extract the following information from the CV text.

    Return ONLY valid JSON.

    Required fields:
    - name
    - phone
    - email
    - last_education_institution
    - last_education_degree (e.g., "Bachelor's in Computer Science", "Master's in Data Science", etc.)
    - experience_years (total years of relevant work experience)
    - freelance_experience_years (total years of freelance experience, if any)(optional)

    Rules:
    - If a field is missing, return an empty string
    - Do not include explanations
    - Do not wrap JSON in markdown
    - to get experience, count time from their jobs start date and end dates to get total number of year
    - get the experience in exact years, if experience starts from mar 2018 and ends in jan 2020, then experience is 1.8 years and so on, if it mentions jun 2018 to present then todays date is {date.today()} count the experience accordingly.
    - count freelance experience separately i.e. (upwork, fiverr, etc.)
    - do not add freelance experience in experience_years field, it should be only in freelance_experience_years field

    
    CV TEXT:
    {cv_text}
    """

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    response = llm.invoke(prompt)

    try:
        json_response = json.loads(response.content)
        json_response["raw_cv_text"] = cv_text
    except Exception:
        json_response = {
            "name": "",
            "phone": "",
            "email": "",
            "last_education_institution": "",
            "last_education_degree": "",
            "experience_years": "",
            "freelance_experience_years": "",
            "raw_cv_text": cv_text
        }


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
    if len(_sys.argv) > 1 and _sys.argv[1] == "ingest":
        print(ingest_new_applicants(), file=_sys.stderr)
    else:
        result = process_cv("faiz.pdf")
        print(result)