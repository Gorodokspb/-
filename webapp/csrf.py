"""CSRF protection middleware using double-submit cookie + itsdangerous.

Stage 8.10.4 (F-1).
"""
from __future__ import annotations

import hmac
import secrets
from typing import Optional
from urllib.parse import parse_qs

from fastapi import Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

COOKIE_NAME = "csrf_token"
HEADER_NAME = "X-CSRF-Token"
FORM_FIELD = "csrf_token"
MAX_AGE_SECONDS = 2 * 60 * 60  # 2 hours

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
BYPASS_PATHS = {"/login"}


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt="csrf-v1")


def generate_csrf_token(secret_key: str) -> str:
    nonce = secrets.token_urlsafe(32)
    return _serializer(secret_key).dumps(nonce)


def verify_csrf_token(secret_key: str, supplied: Optional[str], cookie_value: Optional[str]) -> bool:
    if not supplied or not cookie_value:
        return False
    if not hmac.compare_digest(supplied, cookie_value):
        return False
    try:
        _serializer(secret_key).loads(cookie_value, max_age=MAX_AGE_SECONDS)
    except BadSignature:
        return False
    return True


def _extract_csrf_from_urlencoded(body: bytes, content_type: str) -> Optional[str]:
    """Extract csrf_token from application/x-www-form-urlencoded body."""
    if "application/x-www-form-urlencoded" not in content_type:
        return None
    try:
        parsed = parse_qs(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    values = parsed.get(FORM_FIELD)
    if not values:
        return None
    return values[0]


class CSRFMiddleware(BaseHTTPMiddleware):
    """Generate CSRF cookie on every request; verify on unsafe methods.

    For application/x-www-form-urlencoded: read body once, extract csrf_token,
    then re-inject the body so downstream handler sees it intact.

    For multipart/form-data: rely on X-CSRF-Token header (set by JS).
    This is safe because cross-site form submissions cannot set custom
    headers without CORS preflight, and CSRF attackers cannot read the
    cookie (httpOnly) to copy it into a header.
    """

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request: Request, call_next) -> Response:
        cookie_value = request.cookies.get(COOKIE_NAME)
        if not cookie_value:
            cookie_value = generate_csrf_token(self.secret_key)

        request.state.csrf_token = cookie_value

        if request.method in UNSAFE_METHODS and request.url.path not in BYPASS_PATHS:
            content_type = request.headers.get("content-type", "")
            supplied = None

            if "multipart/form-data" in content_type:
                supplied = request.headers.get(HEADER_NAME)
            else:
                body = await request.body()
                supplied = _extract_csrf_from_urlencoded(body, content_type)
                if not supplied:
                    supplied = request.headers.get(HEADER_NAME)

                async def receive():
                    return {"type": "http.request", "body": body, "more_body": False}
                request._receive = receive

            if not verify_csrf_token(self.secret_key, supplied, cookie_value):
                return JSONResponse(
                    {"detail": "CSRF token missing or invalid"},
                    status_code=403,
                )

        response = await call_next(request)
        response.set_cookie(
            key=COOKIE_NAME,
            value=cookie_value,
            max_age=MAX_AGE_SECONDS,
            httponly=True,
            samesite="lax",
            secure=True,
        )
        return response
