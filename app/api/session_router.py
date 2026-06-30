"""
Session router.

Thin FastAPI router for /sessions endpoints.
Contains no business logic — delegates entirely to session_service.
"""

from fastapi import APIRouter, HTTPException, Request

from app.schemas.session import (
    CreateSessionRequest,
    CreateSessionResponse,
    GenerateResponse,
    SessionResponse,
)
from app.services.session_service import create_session, generate_session, list_sessions

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/", response_model=CreateSessionResponse, status_code=201)
async def create_session_endpoint(
    request: Request,
    body: CreateSessionRequest,
) -> CreateSessionResponse:
    """
    Create a new proposal session.

    Delegates fully to session_service.create_session().
    """
    try:
        return create_session(request=body, auth=request.state.auth)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/", response_model=list[SessionResponse], status_code=200)
async def list_sessions_endpoint(request: Request) -> list[SessionResponse]:
    """
    List all sessions accessible to the authenticated user.

    Delegates fully to session_service.list_sessions().
    """
    try:
        return list_sessions(auth=request.state.auth)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{session_id}/generate", response_model=GenerateResponse, status_code=200)
async def generate_session_endpoint(
    request: Request,
    session_id: str,
) -> GenerateResponse:
    """
    Trigger the LangGraph proposal generation pipeline for a session.

    Delegates fully to session_service.generate_session().
    """
    try:
        return generate_session(session_id=session_id, auth=request.state.auth)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
