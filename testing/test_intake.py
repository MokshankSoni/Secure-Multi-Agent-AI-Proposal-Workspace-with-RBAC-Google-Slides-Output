import os
import json
from dotenv import load_dotenv

# Load .env file containing the NVIDIA_API_KEY
load_dotenv()

# Set up required LLM environment variables for testing since they might not be in .env yet
os.environ.setdefault("LLM_MODEL", "meta/llama-3.3-70b-instruct")
# Keep provider empty to hit default NVIDIA NIM endpoints
os.environ.setdefault("LLM_PROVIDER", "") 

from app.agents.intake_agent import intake_node

# Create a mock state with the user's provided input
state = {
    "raw_input": """We are ABC Hospital.

We want an AI chatbot that helps patients book appointments,
answer FAQs, and reduce receptionist workload.

The project should be completed in 4 months.

Budget around $50,000.

We prefer a professional proposal.

The healthcare team will work with your AI engineers.

We want a scalable cloud solution."""
}

print("Running intake node...")

try:
    result = intake_node(state)
    proposal = result["structured_proposal"]
    print("\n[SUCCESS] Extraction successful! Here is the output:\n")
    print(proposal.model_dump_json(indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
