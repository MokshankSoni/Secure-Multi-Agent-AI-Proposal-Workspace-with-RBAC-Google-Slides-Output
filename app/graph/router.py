"""
LangGraph routing module.

Contains the conditional routing function that determines the next node
to execute after the review node completes.
"""
from typing import Literal

from app.models.state import ProposalState

MAX_RETRIES: int = 3


def route_after_review(
    state: ProposalState,
) -> Literal["finalize_node", "drafting_node", "fail_node"]:
    """
    Determine the next LangGraph node to execute after the review node.

    Reads review_scores.passed and retry_count from the state.
    Does NOT mutate the state.

    Args:
        state: The current LangGraph pipeline state.

    Returns:
        "finalize_node"  — if the review passed.
        "drafting_node"  — if the review failed and retries remain.
        "fail_node"      — if the review failed and all retries are exhausted.
    """
    review_scores = state["review_scores"]
    retry_count = state.get("retry_count", 0)

    if review_scores.passed:
        return "finalize_node"

    if retry_count < MAX_RETRIES:
        return "drafting_node"

    return "fail_node"
