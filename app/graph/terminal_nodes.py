"""
Terminal nodes module.

Contains the final LangGraph nodes that end the pipeline execution.

- finalize_node: Called when the proposal is approved.
- fail_node: Called when all retries are exhausted.
"""
import logging

from app.models.state import ProposalState
from app.services.google_service import GoogleSlidesService

logger = logging.getLogger(__name__)


def finalize_node(state: ProposalState) -> dict:
    """
    Terminal node executed when the review agent approves the proposal.

    Reads the public Google Slides URL from state and returns a success
    status. Does not call the LLM, Google APIs, or mutate the state directly.

    Args:
        state: The current LangGraph pipeline state.

    Returns:
        A dictionary with 'status' and 'final_response' keys.
    """
    slides_url = state.get("slides_url", "")

    logger.info("Finalization successful. Presentation URL: %s", slides_url)

    return {
        "status": "approved",
        "final_response": (
            f"Proposal approved successfully. "
            f"Google Slides available at: {slides_url}"
        ),
    }


def fail_node(state: ProposalState) -> dict:
    """
    Terminal node executed when all review retries are exhausted.

    Attempts to delete the failed draft presentation from Google Drive
    if a file ID exists in state. Deletion errors are logged but do not
    raise, so the pipeline always completes cleanly.

    Args:
        state: The current LangGraph pipeline state.

    Returns:
        A dictionary with 'status' and 'final_response' keys.
    """
    failure_reason = state.get("failure_reason", "Unknown reason.")
    slides_file_id = state.get("slides_file_id")

    if slides_file_id:
        try:
            google_service = GoogleSlidesService()
            google_service.delete_presentation(slides_file_id)
            logger.info("Failed presentation '%s' deleted successfully.", slides_file_id)
        except Exception as exc:
            logger.error(
                "Failed presentation cleanup error for '%s': %s",
                slides_file_id,
                exc,
            )

    return {
        "status": "failed",
        "final_response": (
            f"Proposal generation failed after maximum retries. "
            f"Reason: {failure_reason}"
        ),
    }
