"""
Drafting prompt module.

Constructs a prompt for generating a structured proposal presentation from structured proposal data.
"""
from app.models.proposal import ProposalData


def build_drafting_prompt(
    proposal_data: ProposalData,
    retry_count: int,
    failure_reason: str | None,
) -> str:
    """
    Build a prompt instructing the LLM to generate a professional proposal presentation.

    Args:
        proposal_data: The structured proposal data extracted from user input.
        retry_count: The number of times this prompt has been retried.
        failure_reason: The reason the previous attempt failed, if applicable.

    Returns:
        A formatted prompt string ready to be sent to an LLM.
    """
    retry_block = ""
    if retry_count > 0 and failure_reason is not None:
        retry_block = f"""
## Previous Attempt Failed

The previous proposal did not meet quality standards.

Failure reason:
{failure_reason}

Improve the proposal significantly.
Do not recreate identical wording.
Address every issue mentioned above before generating the new proposal.
""".strip()

    return f"""
You are a senior business proposal writer with expertise in creating compelling, professional presentations for enterprise clients.

Your task is to generate a full proposal presentation based on the structured proposal data provided below.

## Quality Standards

- Use a professional and confident tone throughout.
- Every slide must contain clear, concise bullet points.
- Do not include placeholder text, filler content, or generic statements.
- All content must directly address the specific details in the proposal data.
- Tailor language and emphasis to the target industry and tone if provided.
- Do NOT use emojis, icons, or special characters of any kind. Plain text only.

## Slide Structure

Generate the following slides in order:

1. **Title Slide** — Project title, client name, and a brief tagline.
2. **Problem Statement** — Clearly articulate the core problem being solved.
3. **Objectives** — Present the project objectives as concise bullet points.
4. **Proposed Solution** — Describe the proposed approach in compelling terms.
5. **Timeline** — Outline the timeline in a readable format.
6. **Deliverables** — List all tangible deliverables clearly.
{"7. **Budget** — Summarize the budget range professionally." if proposal_data.budget_range else ""}
{"8. **Team** — Introduce team members and their relevant roles." if proposal_data.team_members else ""}
- **Next Steps** — Conclude with clear, actionable next steps for the client.

## Output Format

Return a single JSON object with a "slides" key containing an array of slide objects.
Each slide object must include:

- `slide_index`: integer (starting from 1)
- `title`: string (plain text only, no emojis)
- `body_text`: array of strings (one item per bullet or paragraph, plain text only)
- `speaker_notes`: string or null (plain text only)
- `layout_hint`: string (one of: "TITLE", "BULLETS", "TWO_COLUMN", "CLOSING")

Do not include any text before or after the JSON object.
Do not use emojis, unicode symbols, or any special characters in any field.

## Proposal Data

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
- **Team Members:** {", ".join(proposal_data.team_members) if proposal_data.team_members else "Not specified"}
- **Unique Value Proposition:** {proposal_data.unique_value_prop or "Not specified"}

{retry_block}
""".strip()
