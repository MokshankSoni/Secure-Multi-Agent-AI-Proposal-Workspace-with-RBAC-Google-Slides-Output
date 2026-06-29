"""
Drafting agent module.

Implements the second node of the LangGraph pipeline.
Converts a structured ProposalData into a list of SlideData objects using the LLM.
"""
import logging

from app.models.slides_response import SlidesResponse
from app.models.slide import SlideData
from app.models.state import ProposalState
from app.prompts.drafting_prompt import build_drafting_prompt
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def drafting_node(state: ProposalState) -> dict:
    """
    LangGraph node that converts a structured proposal into slide content.

    Reads the structured proposal, retry count, and any failure reason from
    the graph state, builds the drafting prompt, sends it to the LLM, and
    returns the generated slides.

    Args:
        state: The current LangGraph pipeline state.

    Returns:
        A dictionary with the key 'slide_content' containing a list of SlideData instances.

    Raises:
        Exception: Propagates any LLM or parsing failure to the graph for upstream handling.
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

    return {"slide_content": slides}
