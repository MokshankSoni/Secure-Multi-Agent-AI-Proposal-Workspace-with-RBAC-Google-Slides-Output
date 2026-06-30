"""
Authentication request and response schemas.

Defines Pydantic v2 models for the /auth endpoints.
These models represent the API contract only — no business logic.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    """Request body for POST /signup."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    email: EmailStr = Field(..., description="User's email address.")
    password: str = Field(..., min_length=8, description="User's password. Minimum 8 characters.")
    organization_id: str = Field(..., description="UUID of the organization the user belongs to.")
    role: Literal["admin", "member"] = Field(..., description="Role assigned to the user within the organization.")


class SignupResponse(BaseModel):
    """Response body for POST /signup."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    message: str = Field(..., description="Confirmation message on successful signup.")


class LoginRequest(BaseModel):
    """Request body for POST /login."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    email: EmailStr = Field(..., description="User's email address.")
    password: str = Field(..., description="User's password.")


class LoginResponse(BaseModel):
    """Response body for POST /login."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    access_token: str = Field(..., description="JWT access token issued by Supabase Auth.")
    refresh_token: str = Field(..., description="Refresh token issued by Supabase Auth.")
    token_type: str = Field(..., description="Token type, typically 'bearer'.")
    expires_in: int = Field(..., description="Seconds until the access token expires.")
    user_id: str = Field(..., description="Supabase Auth user UUID.")
