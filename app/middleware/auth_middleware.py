"""
Authentication middleware module.

Provides a FastAPI HTTP middleware that validates incoming Bearer tokens
against Supabase Auth. On success, attaches a minimal auth context to
request.state.auth. On failure, returns a 401 Unauthorized response.

No RBAC, no application table queries, no business logic.
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.database.supabase import get_anon_client

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT authentication middleware.

    Extracts and validates the Bearer token on every request using
    Supabase Auth. Attaches ``request.state.auth`` on success.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        authorization: str | None = request.headers.get("Authorization")

        if not authorization:
            logger.warning("Authentication failed: missing Authorization header.")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header is missing."},
            )

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Authentication failed: malformed Authorization header.")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header is malformed."},
            )

        token: str = parts[1]

        try:
            client = get_anon_client()
            response = client.auth.get_user(token)
            user = response.user

            if user is None:
                raise ValueError("No user returned from token validation.")

        except Exception:
            logger.warning("Authentication failed: JWT validation unsuccessful.")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token."},
            )

        request.state.auth = {
            "user_id": user.id,
            "email": user.email,
        }

        logger.info("Authentication successful for user_id=%s.", user.id)

        return await call_next(request)
