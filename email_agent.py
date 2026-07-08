"""Send emails via Gmail API using shared OAuth credentials."""
import base64
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from googleapiclient.discovery import build

from parser_agent import _load_google_credentials


def _gmail_service():
    creds = _load_google_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def send_email(to: str, subject: str, html_body: str) -> str:
    """Send an HTML email from the authorized Gmail account. Returns message id."""
    if not to:
        raise ValueError("recipient email is required")

    message = MIMEMultipart("alternative")
    message["to"] = to
    message["subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service = _gmail_service()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"[email] sent to {to} subject={subject!r} id={result.get('id')}", file=sys.stderr)
    return result["id"]
