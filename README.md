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
