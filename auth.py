"""API-key authentication for the Recruitment Module API.

Wired as an app-level dependency so EVERY route is protected by default. A small
allowlist stays public: health checks, the candidate self-service booking pages
(the booking token in the URL is itself the credential), and the Vapi voice
webhook (an external machine caller that cannot carry our key).

Clients authenticate with `Authorization: Bearer <API_KEY>` where API_KEY comes
from the environment (never hardcoded).
"""
import os

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_bearer = HTTPBearer(auto_error=False)

_PUBLIC_EXACT = {"/health", "/ready"}
_PUBLIC_PREFIXES = ("/book/", "/api/booking/", "/voice/webhook", "/interview/", "/voice/livekit-complete")


def _is_public(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    return any(path == p.rstrip("/") or path.startswith(p) for p in _PUBLIC_PREFIXES)


def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    """Reject any request to a protected route without a valid bearer API key."""
    if request.method == "OPTIONS" or _is_public(request.url.path):
        return
    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Server auth not configured: API_KEY is unset",
        )
    if credentials is None or credentials.credentials != expected:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key"
        )
