"""
Drafting agent module.

Implements the second node of the LangGraph pipeline.
Converts a structured ProposalData into a list of SlideData objects using the LLM,
then immediately creates, populates, and shares a Google Slides presentation.
"""
import logging

from app.models.slides_response import SlidesResponse
from app.models.slide import SlideData
from app.models.state import ProposalState
from app.prompts.drafting_prompt import build_drafting_prompt
from app.services.llm_service import LLMService
from app.services.google_service import GoogleSlidesService

logger = logging.getLogger(__name__)


def drafting_node(state: ProposalState) -> dict:
    """
    LangGraph node that converts a structured proposal into slide content
    and immediately publishes it to Google Slides.

    Steps:
      1. Reads structured_proposal, retry_count, and failure_reason from state.
      2. Builds the drafting prompt and calls the LLM via LLMService.
      3. Creates a Google Slides presentation using GoogleSlidesService.
      4. Populates the presentation with the generated SlideData.
      5. Shares the presentation and saves the public URL.

    Args:
        state: The current LangGraph pipeline state.

    Returns:
        A dictionary with slide_content, slides_file_id, and slides_url.

    Raises:
        Exception: Propagates any LLM or Google API failure to the graph.
    """
    logger.info("Drafting node started.")

    proposal = state["structured_proposal"]
    retry_count = state.get("retry_count", 0)
    failure_reason = state.get("failure_reason", None)

    prompt = build_drafting_prompt(
        proposal_data=proposal,
        retry_count=retry_count,
        failure_reason=failure_reason,
    )

    logger.info("Drafting prompt generated.")

    try:
        llm = LLMService()
        slides_response: SlidesResponse = llm.generate_structured_output(prompt, SlidesResponse)
    except Exception as exc:
        logger.error("Drafting node failed to generate slides: %s", exc)
        raise

    slides: list[SlideData] = slides_response.slides
    logger.info("Slides generated successfully. Total slides: %d", len(slides))

    # Create, populate, and share the Google Slides presentation.
    try:
        google_service = GoogleSlidesService()
        presentation_id = google_service.create_presentation(proposal.project_title)
        google_service.populate_presentation(presentation_id, slides)
        public_url = google_service.share_presentation(presentation_id)
    except Exception as exc:
        logger.error("Drafting node failed during Google Slides creation: %s", exc)
        raise

    logger.info("Presentation created and shared. URL: %s", public_url)

    return {
        "slide_content": slides,
        "slides_file_id": presentation_id,
        "slides_url": public_url,
    }
