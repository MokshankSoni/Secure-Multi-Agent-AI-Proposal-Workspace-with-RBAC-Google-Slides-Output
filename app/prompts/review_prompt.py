"""
Review prompt module.

Constructs a prompt for evaluating a generated proposal presentation against structured proposal data.
"""
from app.models.proposal import ProposalData
from app.models.slide import SlideData


def build_review_prompt(
    proposal_data: ProposalData,
    slide_content: list[SlideData],
) -> str:
    """
    Build a prompt instructing the LLM to evaluate a proposal presentation.

    Args:
        proposal_data: The original structured proposal data used to draft the presentation.
        slide_content: The list of generated slides to be reviewed.

    Returns:
        A formatted prompt string ready to be sent to an LLM.
    """
    slides_text = "\n\n".join(
        f"Slide {slide.slide_index}: {slide.title}\n"
        + "\n".join(f"  - {line}" for line in slide.body_text)
        + (f"\n  Speaker Notes: {slide.speaker_notes}" if slide.speaker_notes else "")
        for slide in slide_content
    )

    return f"""
You are a senior proposal quality reviewer with expertise in evaluating business presentations.

Your task is to review the generated proposal presentation against the original structured proposal data using four evaluation dimensions.

## Evaluation Dimensions

Evaluate each dimension on a scale from 0 to 10:

1. **Relevance** — Does the presentation accurately reflect the original proposal data? Are the key points faithfully represented?

2. **Completeness** — Are all required sections present and sufficiently detailed? Are objectives, deliverables, and the proposed solution fully covered?

3. **Professionalism** — Is the language professional, polished, and appropriate for a business audience? Is formatting consistent and clean?

4. **Clarity** — Are ideas expressed clearly and concisely? Is the presentation easy to understand for the intended client?

## Scoring Rules

- Each dimension is scored from 0 to 10.
- Compute the `composite_avg` as the arithmetic mean of all four scores.
- The proposal **passes** if:
  - `composite_avg` >= 7.5
  - AND no individual score is below 6.
- If the proposal fails, provide concise written feedback explaining exactly what needs to be improved.

## Output Format

Return a single JSON object with the following fields:

- `relevance_score`: float
- `completeness_score`: float
- `professionalism_score`: float
- `clarity_score`: float
- `composite_avg`: float
- `passed`: boolean
- `feedback`: string (required if failed, brief summary if passed)

Do not include any text before or after the JSON object.

## Original Proposal Data

- **Client Name:** {proposal_data.client_name}
- **Project Title:** {proposal_data.project_title}
- **Problem Statement:** {proposal_data.problem_statement}
- **Objectives:** {", ".join(proposal_data.objectives)}
- **Proposed Solution:** {proposal_data.proposed_solution}
- **Deliverables:** {", ".join(proposal_data.deliverables)}
- **Timeline:** {proposal_data.timeline}
- **Budget Range:** {proposal_data.budget_range or "Not specified"}
- **Target Industry:** {proposal_data.target_industry or "Not specified"}
- **Tone:** {proposal_data.tone or "Professional"}
- **Unique Value Proposition:** {proposal_data.unique_value_prop or "Not specified"}

## Generated Presentation

{slides_text}
""".strip()
