"""
Slides response model.

Wraps a list of SlideData objects for structured LLM output parsing.
"""
from pydantic import BaseModel, Field, ConfigDict

from app.models.slide import SlideData


class SlidesResponse(BaseModel):
    """
    Wrapper model used as the structured output target for the Drafting Agent.

    The LLM returns a list of slides which is parsed directly into this model.
    Individual SlideData objects are then extracted and stored in the graph state.
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    slides: list[SlideData] = Field(description="The list of generated presentation slides.")
