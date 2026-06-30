import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

from app.agents.intake_agent import intake_node
from app.agents.drafting_agent import drafting_node
from app.agents.review_agent import review_node
from app.services.google_service import GoogleSlidesService

# Raw user input
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

try:
    # Step 1: Intake Agent
    print("Step 1: Running Intake Agent...")
    intake_result = intake_node(state)
    state["structured_proposal"] = intake_result["structured_proposal"]
    print("[OK] Proposal data extracted successfully.\n")

    # Step 2: Drafting Agent
    print("Step 2: Running Drafting Agent...")
    drafting_result = drafting_node(state)
    state["slide_content"] = drafting_result["slide_content"]
    slides = state["slide_content"]
    print(f"[OK] {len(slides)} slides generated successfully.\n")

    # Step 3: Review Agent
    print("Step 3: Running Review Agent...")
    review_result = review_node(state)
    state.update(review_result)
    scores = state["review_scores"]
    print("\n[OK] Review complete!\n")
    print("=" * 60)
    print("REVIEW SCORES")
    print(f"  Relevance      : {scores.relevance_score}/10")
    print(f"  Completeness   : {scores.completeness_score}/10")
    print(f"  Professionalism: {scores.professionalism_score}/10")
    print(f"  Clarity        : {scores.clarity_score}/10")
    print(f"  Composite Avg  : {scores.composite_avg}/10")
    print(f"  Passed         : {scores.passed}")
    print(f"  Feedback       : {scores.feedback}")
    print("=" * 60)

    if state["failure_reason"]:
        print(f"\n[FAIL] Proposal failed review: {state['failure_reason']}")
    else:
        print("\n[PASS] Proposal passed review. Generating Google Slides presentation...")
        
        # Step 4: Google Slides Service
        google_service = GoogleSlidesService()
        
        # Create presentation
        presentation_id = google_service.create_presentation(state["structured_proposal"].project_title)
        state["slides_file_id"] = presentation_id
        print(f"[OK] Presentation created with ID: {presentation_id}")
        
        # Populate content
        print("Populating presentation with slides...")
        google_service.populate_presentation(presentation_id, state["slide_content"])
        print("[OK] Slides populated successfully.")
        
        # Share and get URL
        print("Sharing presentation publicly...")
        public_url = google_service.share_presentation(presentation_id)
        state["slides_url"] = public_url
        
        print(f"\n[SUCCESS] Google Slides generated successfully!")
        print(f"Access the presentation here: {public_url}")

except Exception as e:
    import traceback
    traceback.print_exc()
