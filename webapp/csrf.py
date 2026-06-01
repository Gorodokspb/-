"""CSRF protection middleware using double-submit cookie + itsdangerous.

Stage 8.10.4 (F-1).
"""
from __future__ import annotations

import hmac
import secrets
from typing import Optional

from fastapi import Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

COOKIE_NAME = "csrf_token"
HEADER_NAME = "X-CSRF-Token"
FORM_FIELD = "csrf_token"
MAX_AGE_SECONDS = 2 * 60 * 60  # 2 hours

# Methods that may change server state and require CSRF validation.
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Endpoints that bypass CSRF (must be reachable before authentication).
BYPASS_PATHS = {"/login"}


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt="csrf-v1")


def generate_csrf_token(secret_key: str) -> str:
    """Generate a fresh CSRF token: random nonce signed with secret_key."""
    nonce = secrets.token_urlsafe(32)
    return _serializer(secret_key).dumps(nonce)


def verify_csrf_token(secret_key: str, supplied: Optional[str], cookie_value: Optional[str]) -> bool:
    """Verify the supplied token against the signed cookie value.

    Returns True if both tokens are equal (constant-time compare) AND
    the cookie value is a valid signed token.
    """
    if not supplied or not cookie_value:
        return False
    if not hmac.compare_digest(supplied, cookie_value):
        return False
    try:
        _serializer(secret_key).loads(cookie_value, max_age=MAX_AGE_SECONDS)
    except BadSignature:
        return False
    return True


class CSRFMiddleware(BaseHTTPMiddleware):
    """Generate CSRF cookie on every request; verify on unsafe methods."""

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key

    async def dispatch(self, request: Request, call_next) -> Response:
        cookie_value = request.cookies.get(COOKIE_NAME)
        if not cookie_value:
            cookie_value = generate_csrf_token(self.secret_key)

        request.state.csrf_token = cookie_value

        if request.method in UNSAFE_METHODS and request.url.path not in BYPASS_PATHS:
            supplied = request.headers.get(HEADER_NAME)
            if not supplied:
                try:
                    form = await request.form()
                    supplied = form.get(FORM_FIELD)
                except Exception:
                    supplied = None
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
