"""
Main application entry point.

Instantiates the FastAPI application, registers middleware, routers,
and defines public health endpoints. No business logic.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth_router import router as auth_router
from app.api.session_router import router as session_router
from app.middleware.auth_middleware import AuthMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public paths that bypass authentication
# ---------------------------------------------------------------------------
_PUBLIC_PATHS: set[str] = {
    "/",
    "/health",
    "/api/auth/signup",
    "/api/auth/login",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Secure Multi-Agent AI Proposal Workspace",
    description="Production-grade backend for an AI proposal generation system built with FastAPI, LangGraph, and Google Slides API.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth middleware — registered after CORS so CORS headers are always applied.
# Skips public paths to allow unauthenticated access to signup/login/health.
# ---------------------------------------------------------------------------
# Instantiated once at startup — not per request. Recreating BaseHTTPMiddleware
# on every call re-registers it into Starlette's stack and causes RuntimeErrors.
_auth_middleware = AuthMiddleware(app)

@app.middleware("http")
async def conditional_auth(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)
    return await _auth_middleware.dispatch(request, call_next)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix="/api")
app.include_router(session_router, prefix="/api")

# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    """Public root endpoint — no authentication required."""
    return JSONResponse({
        "status": "running",
        "service": "Secure Multi-Agent AI Proposal Workspace",
        "version": "0.1.0",
    })


@app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    """Lightweight health check — no authentication required."""
    return JSONResponse({"status": "healthy"})
