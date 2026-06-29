"""
Intake prompt module.

Constructs a prompt for extracting structured proposal information from raw user input.
"""


def build_intake_prompt(raw_input: str) -> str:
    """
    Build a prompt instructing the LLM to extract structured proposal data from raw user input.

    Args:
        raw_input: The unstructured text provided by the user describing their proposal needs.

    Returns:
        A formatted prompt string ready to be sent to an LLM.
    """
    return f"""
You are an expert business proposal analyst with deep experience in extracting structured information from unstructured text.

Your task is to carefully read the raw user input below and extract structured proposal information from it.

## Instructions

- Extract only what is explicitly stated or strongly implied by the input.
- Do NOT invent or fabricate any information.
- If an optional field is not present or cannot be inferred, return null for that field.
- The fields `objectives` and `deliverables` MUST always be arrays of strings, even if there is only one item.
- Return structured output only. Do not include commentary or explanation.

## Fields to Extract

| Field               | Type             | Required | Description                                           |
|---------------------|------------------|----------|-------------------------------------------------------|
| client_name         | string           | Yes      | The name of the client or company.                    |
| project_title       | string           | Yes      | A concise title for the project.                      |
| problem_statement   | string           | Yes      | The core problem or challenge being addressed.        |
| objectives          | array of strings | Yes      | A list of measurable goals for the project.           |
| proposed_solution   | string           | Yes      | The proposed approach to solving the problem.         |
| deliverables        | array of strings | Yes      | A list of tangible outputs to be produced.            |
| timeline            | string           | Yes      | The estimated project duration or schedule.           |
| budget_range        | string or null   | No       | The estimated budget range, if mentioned.             |
| target_industry     | string or null   | No       | The industry or sector the client operates in.        |
| tone                | string or null   | No       | The desired tone of the proposal (e.g., formal).      |
| team_members        | array or null    | No       | Names or roles of team members, if mentioned.         |
| unique_value_prop   | string or null   | No       | The unique differentiator or value proposition.       |

## Raw User Input

{raw_input}

## Output Format

Return a single JSON object containing all of the fields above.
Do not include any text before or after the JSON.
""".strip()
