"""
Session request and response schemas.

Defines Pydantic v2 models for the /sessions endpoints.
These models represent the API contract only — no business logic.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateSessionRequest(BaseModel):
    """Request body for POST /sessions."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    title: str = Field(..., description="A short, descriptive title for the proposal session.")
    raw_input: str = Field(..., description="The raw user input text to be processed by the pipeline.")


class CreateSessionResponse(BaseModel):
    """Response body for POST /sessions."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    session_id: str = Field(..., description="UUID of the newly created session.")
    status: str = Field(..., description="Initial status of the session.")


class SessionResponse(BaseModel):
    """Response body for a single session entry in GET /sessions."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    session_id: str = Field(..., description="UUID of the session.")
    title: str = Field(..., description="Title of the proposal session.")
    status: str = Field(..., description="Current status of the session.")
    slides_url: str | None = Field(None, description="Shareable Google Slides URL, populated once generation succeeds.")
    created_at: datetime = Field(..., description="Timestamp when the session was created.")


class GenerateResponse(BaseModel):
    """Response body for POST /sessions/{id}/generate."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    session_id: str = Field(..., description="UUID of the session that was processed.")
    status: str = Field(..., description="Final status of the session after pipeline execution.")
    slides_url: str | None = Field(None, description="Shareable Google Slides URL if generation succeeded.")
    final_response: str = Field(..., description="Final review output or failure reason from the pipeline.")
