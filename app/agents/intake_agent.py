"""
Intake agent module.

Implements the first node of the LangGraph pipeline.
Converts raw user input into a structured ProposalData object.
"""
import logging

from app.models.proposal import ProposalData
from app.models.state import ProposalState
from app.prompts.intake_prompt import build_intake_prompt
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def intake_node(state: ProposalState) -> dict:
    """
    LangGraph node that converts raw user input into a structured ProposalData.

    Reads raw_input from the graph state, builds the intake prompt,
    sends it to the LLM, and returns the parsed ProposalData.

    Args:
        state: The current LangGraph pipeline state.

    Returns:
        A dictionary with the key 'structured_proposal' containing the parsed ProposalData.

    Raises:
        Exception: Propagates any LLM or parsing failure to the graph for upstream handling.
    """
    logger.info("Intake node started.")

    raw_input = state["raw_input"]
    prompt = build_intake_prompt(raw_input)

    logger.info("Intake prompt generated.")

    try:
        llm = LLMService()
        proposal: ProposalData = llm.generate_structured_output(prompt, ProposalData)
    except Exception as exc:
        logger.error("Intake node failed to extract proposal: %s", exc)
        raise

    logger.info("Proposal extracted successfully.")

    return {"structured_proposal": proposal}
