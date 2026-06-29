"""
Slide models.

Defines the data structures representing presentation slides.
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SlideData(BaseModel):
    """
    Data model representing a presentation slide.
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True
    )

    slide_index: int = Field(description="The index position of the slide.")
    title: str = Field(description="The title of the slide.")
    body_text: list[str] = Field(description="The body text of the slide, formatted as a list of strings.")
    speaker_notes: Optional[str] = Field(default=None, description="The speaker notes for the slide.")
    layout_hint: str = Field(description="A hint for the intended slide layout.")
