"""
Proposal models.

Defines the data structures representing a proposal.
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProposalData(BaseModel):
    """
    Data model representing a generated proposal.
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True
    )

    client_name: str = Field(description="The name of the client.")
    project_title: str = Field(description="The title of the project.")
    problem_statement: str = Field(description="The core problem statement.")
    objectives: list[str] = Field(description="A list of project objectives.")
    proposed_solution: str = Field(description="The proposed solution.")
    deliverables: list[str] = Field(description="A list of project deliverables.")
    timeline: str = Field(description="The project timeline.")
    budget_range: Optional[str] = Field(default=None, description="The estimated budget range.")
    target_industry: Optional[str] = Field(default=None, description="The target industry of the client.")
    tone: Optional[str] = Field(default=None, description="The tone of the proposal.")
    team_members: Optional[list[str]] = Field(default=None, description="The team members assigned to the project.")
    unique_value_prop: Optional[str] = Field(default=None, description="The unique value proposition.")
