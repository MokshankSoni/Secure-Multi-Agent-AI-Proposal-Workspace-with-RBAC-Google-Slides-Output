"""
State models.

Defines the core LangGraph state used across the proposal generation pipeline.
"""
from typing import TypedDict, Optional

from app.models.proposal import ProposalData
from app.models.slide import SlideData
from app.models.review import ReviewResult


class ProposalState(TypedDict):
    """
    The graph state used across LangGraph nodes.
    Maintains the state as a TypedDict while utilizing Pydantic models for nested data structures.
    """
    # Authentication Context
    tenant_id: str
    user_id: str
    user_role: str

    # Pipeline Runtime
    retry_count: int
    status: str

    # Google Slides
    slides_url: str
    slides_file_id: str

    # User Input
    raw_input: str

    # Pipeline Outputs
    structured_proposal: ProposalData
    slide_content: list[SlideData]
    review_scores: ReviewResult
    failure_reason: Optional[str]

    # Final Output
    final_response: str
