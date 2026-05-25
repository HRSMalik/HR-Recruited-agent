"""Pulls new form submissions, downloads CVs from Drive, runs parser, stores in Mongo."""

import csv
import io
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from pymongo import MongoClient

from parser_agent import process_cv, _get_candidates_collection

load_dotenv()


_PROCESSED_COLLECTION = None
_DRIVE_SERVICE = None
_DRIVE_FILE_ID_RE = re.compile(r"[?&/]id=([A-Za-z0-9_-]+)|/file/d/([A-Za-z0-9_-]+)")


def _get_processed_collection():
    global _PROCESSED_COLLECTION
    if _PROCESSED_COLLECTION is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _PROCESSED_COLLECTION = MongoClient(uri)[db_name]["processed_submissions"]
    return _PROCESSED_COLLECTION


def _get_drive_service():
    global _DRIVE_SERVICE
    if _DRIVE_SERVICE is None:
        key_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
        creds = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        _DRIVE_SERVICE = build("drive", "v3", credentials=creds)
    return _DRIVE_SERVICE


def _extract_file_id(resume_link: str) -> Optional[str]:
    if not resume_link:
        return None
    m = _DRIVE_FILE_ID_RE.search(resume_link)
    if not m:
        return None
    return m.group(1) or m.group(2)


_EXPECTED_HEADERS = ["Timestamp", "Name", "Email", "Experience", "Resume", "Job Reference Code", "Extra"]


def _fetch_sheet_rows() -> list[dict]:
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("Missing GOOGLE_SHEET_ID in .env")
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    reader = csv.reader(io.StringIO(resp.text))
    rows = list(reader)
    if not rows:
        return []

    raw_headers = rows[0]
    # If headers are generic "Column N", remap by position to canonical names.
    if all(h.lower().startswith("column ") for h in raw_headers if h):
        headers = _EXPECTED_HEADERS[: len(raw_headers)]
    else:
        headers = raw_headers

    return [dict(zip(headers, r + [""] * (len(headers) - len(r)))) for r in rows[1:]]


def _submission_key(row: dict) -> str:
    return f"{(row.get('Email') or '').strip().lower()}|{(row.get('Timestamp') or '').strip()}"


def _download_pdf(file_id: str, dest: Path) -> None:
    request = _get_drive_service().files().get_media(fileId=file_id)
    with open(dest, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def sync_once(temp_dir: str = "sync_temp") -> dict:
    rows = _fetch_sheet_rows()
    processed = _get_processed_collection()

    work_dir = Path(temp_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    stats = {"total": len(rows), "new": 0, "ok": 0, "errors": 0, "skipped": 0}

    for row in rows:
        key = _submission_key(row)
        if not row.get("Email") or processed.find_one({"submission_key": key}):
            stats["skipped"] += 1
            continue

        stats["new"] += 1
        email = row["Email"].strip()
        file_id = _extract_file_id(row.get("Resume") or "")

        if not file_id:
            print(f"  [skip] {email}: no resume link", file=sys.stderr)
            stats["errors"] += 1
            continue

        local_pdf = work_dir / f"{file_id}.pdf"
        try:
            _download_pdf(file_id, local_pdf)
            print(f"  downloaded: {local_pdf.name}", file=sys.stderr)
        except HttpError as e:
            print(f"  [error] {email}: drive download failed - {e}", file=sys.stderr)
            stats["errors"] += 1
            continue

        try:
            result = process_cv(str(local_pdf))
            cv_id = result["id"]
            sheet_thread_id = (row.get("Job Reference Code") or "").strip()
            if sheet_thread_id and result["data"].get("job_thread_id") != sheet_thread_id:
                _get_candidates_collection().update_one(
                    {"_id": cv_id},
                    {"$set": {"job_thread_id": sheet_thread_id, "form_email": email}},
                )
            tid = sheet_thread_id or result["data"].get("job_thread_id", "")
            print(f"  parsed: {email} -> cv_id={cv_id}, job_thread_id={tid!r}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"  [error] {email}: parser failed - {e}", file=sys.stderr)
            stats["errors"] += 1
            continue
        finally:
            if local_pdf.exists():
                local_pdf.unlink()

        processed.insert_one(
            {
                "submission_key": key,
                "email": email,
                "form_timestamp": row.get("Timestamp"),
                "cv_id": cv_id,
                "job_thread_id": tid,
            }
        )
        stats["ok"] += 1

    return stats


if __name__ == "__main__":
    stats = sync_once()
    print(
        f"\n[sync_forms] total={stats['total']} new={stats['new']} "
        f"ok={stats['ok']} errors={stats['errors']} skipped={stats['skipped']}"
    )
