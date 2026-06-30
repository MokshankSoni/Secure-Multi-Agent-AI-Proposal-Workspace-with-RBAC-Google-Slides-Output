# Secure Multi-Agent AI Proposal Workspace

Backend for an AI proposal generation system built with FastAPI, LangGraph, and Google Slides API.

## Folder Structure

- `app/agents/`: Contains LangGraph node implementations.
- `app/graph/`: Contains graph state definitions, graph builder, and routing logic.
- `app/models/`: Contains TypedDicts, Enums, and shared schemas.
- `app/prompts/`: Contains LLM prompt templates.
- `app/services/`: Integrations with external services (Google Slides, LLM Provider, etc.).
- `app/utils/`: Shared utilities, logging, and constants.

## Setup Instructions

### Prerequisites
- Python 3.12+

### 1. Virtual Environment Setup
Create and activate a virtual environment:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Installing Dependencies
Install the required packages using `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

### 4. Running the Project
Run the FastAPI development server:

```bash
uvicorn main:app --reload
```

The root endpoint will be available at `http://localhost:8000/`.

## Example Pipeline Trace

Here is a showcase of the core AI Agent pipeline successfully chained end-to-end:

### 1. Intake Agent

**Input (Raw User Text)**
```text
We are ABC Hospital.
We want an AI chatbot that helps patients book appointments,
answer FAQs, and reduce receptionist workload.
The project should be completed in 4 months.
Budget around $50,000.
We prefer a professional proposal.
The healthcare team will work with your AI engineers.
We want a scalable cloud solution.
```

**Output (Structured `ProposalData`)**
```json
{
  "client_name": "ABC Hospital",
  "project_title": "AI Chatbot Implementation",
  "problem_statement": "Improving patient appointment booking, answering FAQs, and reducing receptionist workload",
  "objectives": [
    "Improve patient appointment booking efficiency",
    "Reduce receptionist workload"
  ],
  "proposed_solution": "Scalable cloud-based AI chatbot solution",
  "deliverables": [
    "AI chatbot system",
    "Integration with existing hospital systems"
  ],
  "timeline": "4 months",
  "budget_range": "$50,000",
  "target_industry": "healthcare",
  "tone": "professional",
  "team_members": ["healthcare team", "AI engineers"],
  "unique_value_prop": "scalable cloud solution"
}
```

### 2. Drafting Agent

**Output (`list[SlideData]`)**
```text
SLIDE 1: AI Chatbot Implementation for ABC Hospital
  Layout: TITLE

SLIDE 2: Problem Statement
  - Inefficient patient appointment booking process
  - Inaccurate or delayed responses to frequently asked questions
  - High receptionist workload leading to decreased productivity
  Notes: The current system is causing inefficiencies and affecting patient satisfaction
  Layout: BULLETS

SLIDE 3: Objectives
  - Improve patient appointment booking efficiency
  - Provide accurate answers to frequently asked questions
  - Reduce receptionist workload
  Notes: Our objectives are focused on enhancing the patient experience and streamlining operations
  Layout: BULLETS

... (Total 9 slides generated)
```

### 3. Review Agent

**Output (`ReviewResult`)**
```json
{
  "relevance_score": 9.0,
  "completeness_score": 9.5,
  "professionalism_score": 9.0,
  "clarity_score": 9.0,
  "composite_avg": 9.1,
  "passed": true,
  "feedback": "The proposal presentation accurately reflects the original proposal data, covering all key points and objectives. The language is professional, and the formatting is consistent and clean. The ideas are expressed clearly and concisely, making it easy to understand for the intended client. Overall, the proposal is well-structured and effectively communicates the proposed solution and its benefits."
}
```

## LangGraph Pipeline Architecture

The entire proposal generation system is orchestrated using a **LangGraph StateGraph** which acts as an autonomous state machine. 

### Graph Topology
```text
START
  │
  ▼
intake_node          ← Extracts structured ProposalData from raw user text
  │
  ▼
drafting_node        ← 1. Generates list[SlideData] via LLM
  │                  ← 2. Creates new Google Slides Presentation via Google Slides API
  │                  ← 3. Populates slides & Shares URL publicly
  ▼
review_node          ← Scores the presentation against quality standards
  │
  ▼
route_after_review()
  │
  ├── IF passed=True          → finalize_node → END (Returns URL to user)
  │
  ├── IF passed=False
  │   AND retries remain      → retry_node
  │                                 │
  │                                 ├── 1. Deletes failed Google Slides presentation from Drive
  │                                 ├── 2. Increments retry_count
  │                                 │
  │                                 └──► drafting_node  (Loops back with failure feedback)
  │
  └── IF passed=False 
      AND retries exhausted   → fail_node → END (Deletes failed presentation and throws error)
```

### Self-Healing Retry Loop
If the `review_node` determines the generated presentation does not meet the minimum threshold (e.g., missing budget details, poor tone, missing slides):
1. The **Router** reads `passed=False` and diverts the execution to the `retry_node`.
2. The **Retry Node** securely connects to Google Drive and **deletes** the failed presentation so that junk files do not accumulate.
3. The counter is incremented, and the graph loops back to the **Drafting Agent**.
4. The Drafting Agent receives a strengthened prompt that explicitly includes the `failure_reason` from the Review Agent, ensuring the LLM meaningfully improves the proposal rather than making superficial changes.
5. A brand new Google Slide deck is created and the review process starts again.
