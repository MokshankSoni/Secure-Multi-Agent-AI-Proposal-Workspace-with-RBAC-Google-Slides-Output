"""
Review agent module.

Implements the third node of the LangGraph pipeline.
Evaluates the generated slide content against the structured proposal using the LLM.
"""
import logging
from typing import Optional

from app.models.review import ReviewResult
from app.models.state import ProposalState
from app.prompts.review_prompt import build_review_prompt
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


def review_node(state: ProposalState) -> dict:
    """
    LangGraph node that evaluates the generated slide presentation.

    Reads the structured proposal and slide content from the graph state,
    builds the review prompt, sends it to the LLM, and returns the review
    scores and any failure reason.

    Args:
        state: The current LangGraph pipeline state.

    Returns:
        A dictionary with:
          - 'review_scores': the populated ReviewResult instance.
          - 'failure_reason': the feedback string if the review failed, otherwise None.

    Raises:
        Exception: Propagates any LLM or parsing failure to the graph for upstream handling.
    """
    logger.info("Review node started.")

    proposal = state["structured_proposal"]
    slide_content = state["slide_content"]

    prompt = build_review_prompt(
        proposal_data=proposal,
        slide_content=slide_content,
    )

    logger.info("Review prompt generated.")

    try:
        llm = LLMService()
        review_result: ReviewResult = llm.generate_structured_output(prompt, ReviewResult)
    except Exception as exc:
        logger.error("Review node failed to evaluate presentation: %s", exc)
        raise

    failure_reason: Optional[str] = review_result.feedback if not review_result.passed else None

    logger.info(
        "Review completed successfully. Passed: %s, Composite Avg: %.2f",
        review_result.passed,
        review_result.composite_avg,
    )

    return {
        "review_scores": review_result,
        "failure_reason": failure_reason,
    }
