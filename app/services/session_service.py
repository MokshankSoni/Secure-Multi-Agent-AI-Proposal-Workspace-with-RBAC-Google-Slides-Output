"""
Session service module.

Orchestrates the full proposal generation lifecycle:

    Supabase → LangGraph pipeline → Google Slides → Supabase persistence

This module contains ONLY business logic.
No FastAPI, no APIRouter, no Request objects, no HTTPException.
"""

import logging

from app.database.supabase import get_service_client
from app.graph.builder import build_graph
from app.schemas.session import (
    CreateSessionRequest,
    CreateSessionResponse,
    GenerateResponse,
    SessionResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level graph singleton.
# build_graph() compiles the StateGraph, which is expensive. Compiling once
# at import time and reusing the compiled graph on every request avoids that
# overhead and keeps LangGraph's internal checkpointer state stable.
# ---------------------------------------------------------------------------
GRAPH = build_graph()


# ---------------------------------------------------------------------------
# Public Methods
# ---------------------------------------------------------------------------

def create_session(
    request: CreateSessionRequest,
    auth: dict,
) -> CreateSessionResponse:
    """
    Insert a new session row into Supabase and return its ID and initial status.

    Args:
        request: Validated CreateSessionRequest containing title and raw_input.
        auth:    Auth context dict with user_id, organization_id, role.

    Returns:
        CreateSessionResponse with session_id and status.
    """
    # service_client is used throughout because session writes originate from
    # the server, not the end-user's JWT. Using the service role key bypasses
    # RLS and guarantees the insert succeeds regardless of policy constraints.
    service_client = get_service_client()

    try:
        result = service_client.table("sessions").insert({
            "organization_id": auth["organization_id"],
            "owner_id": auth["user_id"],
            "title": request.title,
            "raw_input": request.raw_input,
            "status": "pending",
        }).execute()

        row = result.data[0]
        logger.info(
            "Session created: id=%s owner=%s org=%s",
            row["id"], auth["user_id"], auth["organization_id"],
        )
        return CreateSessionResponse(session_id=row["id"], status=row["status"])

    except Exception as e:
        logger.error("Failed to create session for user %s: %s", auth["user_id"], str(e))
        raise RuntimeError(f"Failed to create session: {str(e)}")


def list_sessions(auth: dict) -> list[SessionResponse]:
    """
    Return sessions the caller is authorised to read.

    - Members: only their own sessions (owner_id == user_id).
    - Admins: all sessions within their organization.

    Args:
        auth: Auth context dict with user_id, organization_id, role.

    Returns:
        List of SessionResponse objects.
    """
    service_client = get_service_client()

    try:
        query = service_client.table("sessions").select(
            "id, title, status, created_at, owner_id, organization_id"
        )

        if auth["role"] == "member":
            query = query.eq("owner_id", auth["user_id"])
        else:
            # admin — all sessions within their organization only
            query = query.eq("organization_id", auth["organization_id"])

        result = query.execute()

        sessions = [
            SessionResponse(
                session_id=row["id"],
                title=row["title"],
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in result.data
        ]

        logger.info(
            "Listed %d session(s) for user %s (role=%s).",
            len(sessions), auth["user_id"], auth["role"],
        )
        return sessions

    except Exception as e:
        logger.error("Failed to list sessions for user %s: %s", auth["user_id"], str(e))
        raise RuntimeError(f"Failed to list sessions: {str(e)}")


def generate_session(session_id: str, auth: dict) -> GenerateResponse:
    """
    Run the LangGraph pipeline for a given session and persist the results.

    Steps:
        1. Load the session from Supabase.
        2. Authorise the caller.
        3. Set status → 'drafting'.
        4. Build and invoke the LangGraph pipeline.
        5. Persist the final state back to Supabase.
        6. Return GenerateResponse.

    Args:
        session_id: UUID of the session to generate.
        auth:       Auth context dict with user_id, organization_id, role.

    Returns:
        GenerateResponse with status, slides_url, and final_response.
    """
    # All database operations in this method use the service role client so
    # that the pipeline can write status updates and results on behalf of the
    # user without being blocked by user-scoped RLS policies.
    service_client = get_service_client()

    # ------------------------------------------------------------------
    # STEP 1 — Load session
    # ------------------------------------------------------------------
    try:
        result = service_client.table("sessions").select("*").eq("id", session_id).execute()
        if not result.data:
            raise ValueError(f"Session '{session_id}' not found.")
        session = result.data[0]
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to load session '{session_id}': {str(e)}")

    # ------------------------------------------------------------------
    # STEP 2 — Authorisation
    # ------------------------------------------------------------------
    if auth["role"] == "member":
        if session["owner_id"] != auth["user_id"]:
            raise PermissionError("Access denied: you do not own this session.")
    else:
        # admin
        if session["organization_id"] != auth["organization_id"]:
            raise PermissionError("Access denied: session belongs to a different organization.")

    # ------------------------------------------------------------------
    # STEP 3 — Mark as 'drafting' before running the graph.
    # Persisted immediately so callers can observe in-progress sessions.
    # 'drafting' is the first in-pipeline status value in schema.sql.
    # ------------------------------------------------------------------
    try:
        service_client.table("sessions").update({"status": "drafting"}).eq("id", session_id).execute()
    except Exception as e:
        raise RuntimeError(f"Failed to update session status to 'drafting': {str(e)}")

    logger.info(
        "Session generation started: id=%s user=%s role=%s",
        session_id, auth["user_id"], auth["role"],
    )

    # ------------------------------------------------------------------
    # STEP 4 — Build initial state
    # ------------------------------------------------------------------
    # All ProposalState fields must be present at invocation time.
    # - structured_proposal / review_scores are None until their respective
    #   agents populate them — the graph handles that progression.
    # - slide_content starts as an empty list; drafting_node fills it.
    # - failure_reason starts as None; review_node sets it on rejection.
    # - status is set to 'pending' here; the graph nodes update it as
    #   the pipeline advances through drafting → reviewing → approved/failed.
    initial_state = {
        # Auth context injected from the validated JWT
        "tenant_id": auth["organization_id"],
        "user_id": auth["user_id"],
        "user_role": auth["role"],
        # Raw user input for the intake agent
        "raw_input": session["raw_input"],
        # Pipeline runtime defaults
        "retry_count": 0,
        "status": "pending",
        # Google Slides — populated by drafting_node
        "slides_url": "",
        "slides_file_id": "",
        # Pipeline outputs — populated by their respective agents
        "structured_proposal": None,
        "slide_content": [],
        "review_scores": None,
        "failure_reason": None,
        # Final output — set by finalize_node or fail_node
        "final_response": "",
    }

    # ------------------------------------------------------------------
    # STEP 5 — Invoke the graph
    # ------------------------------------------------------------------
    try:
        final_state = GRAPH.invoke(initial_state)
    except Exception as e:
        # STEP 6 — Persist failure and re-raise
        err_msg = str(e)
        logger.error("Pipeline failed for session %s: %s", session_id, err_msg)
        try:
            service_client.table("sessions").update({
                "status": "failed",
                "final_response": err_msg,
            }).eq("id", session_id).execute()
        except Exception as db_err:
            logger.error(
                "Failed to persist pipeline failure for session %s: %s",
                session_id, str(db_err),
            )
        raise RuntimeError(f"Pipeline failed for session '{session_id}': {err_msg}")

    # ------------------------------------------------------------------
    # STEP 7 — Extract final state
    # 'approved' is returned by finalize_node; 'failed' by fail_node.
    # Both are valid values in the schema.sql CHECK constraint.
    # ------------------------------------------------------------------
    pipeline_status: str = final_state.get("status", "failed")
    slides_url: str = final_state.get("slides_url", "")
    slides_file_id: str = final_state.get("slides_file_id", "")
    final_response: str = final_state.get("final_response", "")

    # Log the final pipeline outcome before attempting DB persistence.
    logger.info(
        "Pipeline completed for session %s: final_status=%s slides_url=%s",
        session_id, pipeline_status, slides_url,
    )

    # ------------------------------------------------------------------
    # STEP 8 — Persist results
    # finalize_node sets status='approved'; fail_node sets status='failed'.
    # Only write slides fields on success — never overwrite a previously
    # stored slides_url/slides_file_id with empty strings on a failed run.
    # ------------------------------------------------------------------
    try:
        if pipeline_status == "approved":
            # Success: persist all pipeline outputs including Slides assets.
            update_payload = {
                "status": pipeline_status,
                "slides_url": slides_url,
                "slides_file_id": slides_file_id,
                "final_response": final_response,
            }
        else:
            # Failure: persist only status and reason; leave Slides columns intact.
            update_payload = {
                "status": pipeline_status,
                "final_response": final_response,
            }

        service_client.table("sessions").update(update_payload).eq("id", session_id).execute()
        logger.info("Database update completed for session %s.", session_id)

    except Exception as e:
        logger.error(
            "Failed to persist pipeline results for session %s: %s",
            session_id, str(e),
        )
        raise RuntimeError(f"Pipeline succeeded but database update failed: {str(e)}")

    # ------------------------------------------------------------------
    # STEP 9 — Return response
    # ------------------------------------------------------------------
    return GenerateResponse(
        session_id=session_id,
        status=pipeline_status,
        slides_url=slides_url if slides_url else None,
        final_response=final_response,
    )
