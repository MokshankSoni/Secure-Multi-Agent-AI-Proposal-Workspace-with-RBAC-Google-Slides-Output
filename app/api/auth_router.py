"""
Authentication router.

Thin FastAPI router for /auth endpoints.
Contains no business logic — delegates entirely to AuthService.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.auth import LoginRequest, LoginResponse, SignupRequest, SignupResponse
from app.services.auth_service import login, signup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup_endpoint(request: SignupRequest) -> SignupResponse:
    """
    Register a new user and create their organization profile.

    Delegates fully to auth_service.signup().
    """
    try:
        result = signup(
            email=request.email,
            password=request.password,
            organization_id=request.organization_id,
            role=request.role,
        )
        return SignupResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/login", response_model=LoginResponse, status_code=200)
async def login_endpoint(request: LoginRequest) -> LoginResponse:
    """
    Authenticate a user and return JWT tokens.

    Delegates fully to auth_service.login().
    """
    try:
        result = login(
            email=request.email,
            password=request.password,
        )
        return LoginResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
