"""
Review models.

Defines the data structures representing the results of a review.
"""
from pydantic import BaseModel, Field, ConfigDict


class ReviewResult(BaseModel):
    """
    Data model representing the result of an AI review.
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True
    )

    relevance_score: float = Field(description="Score indicating the relevance of the proposal.")
    completeness_score: float = Field(description="Score indicating the completeness of the proposal.")
    professionalism_score: float = Field(description="Score indicating the professionalism of the proposal.")
    clarity_score: float = Field(description="Score indicating the clarity of the proposal.")
    composite_avg: float = Field(description="The composite average score of the review.")
    passed: bool = Field(description="Indicates whether the review passed the minimum requirements.")
    feedback: str = Field(description="Written feedback explaining what passed or what needs to be improved.")
