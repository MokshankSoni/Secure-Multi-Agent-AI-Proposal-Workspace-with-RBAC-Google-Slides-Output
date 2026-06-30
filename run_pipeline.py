import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure basic logging to see what the agents are doing
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

from app.graph.builder import build_graph

# The raw input that starts the pipeline
initial_state = {
    "raw_input": """We are ABC Hospital.

We want an AI chatbot that helps patients book appointments,
answer FAQs, and reduce receptionist workload.

The project should be completed in 4 months.

Budget around $50,000.

We prefer a professional proposal.

The healthcare team will work with your AI engineers.

We want a scalable cloud solution."""
}

print("==================================================")
print("Starting Full LangGraph Pipeline...")
print("==================================================")

try:
    # 1. Build the graph
    graph = build_graph()

    # 2. Invoke the graph with the initial state
    # This automatically runs Intake -> Drafting (creates slides) -> Review -> (retry loop if needed) -> Finalize
    final_state = graph.invoke(initial_state)

    print("\n==================================================")
    print("Pipeline Execution Complete!")
    print("==================================================")
    
    # Check the final routing status
    if "final_response" in final_state:
        print("\nFinal Result:")
        print(final_state["final_response"])
        
    print("\nFinal State Snapshot:")
    print(f"Retry Count: {final_state.get('retry_count', 0)}")
    
    if "review_scores" in final_state:
        scores = final_state["review_scores"]
        print("\nReview Scores:")
        print(f"  Passed: {scores.passed}")
        print(f"  Average: {scores.composite_avg}/10")
        print(f"  Feedback: {scores.feedback}")

except Exception as e:
    import traceback
    traceback.print_exc()
