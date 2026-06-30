"""
LangGraph graph builder module.

Constructs and compiles the full proposal generation pipeline as a
LangGraph StateGraph. Exposes a single build_graph() factory function.
"""
import logging

from langgraph.graph import StateGraph, START, END

from app.models.state import ProposalState
from app.agents.intake_agent import intake_node
from app.agents.drafting_agent import drafting_node
from app.agents.review_agent import review_node
from app.graph.router import route_after_review
from app.graph.terminal_nodes import finalize_node, fail_node

logger = logging.getLogger(__name__)


def retry_node(state: ProposalState) -> dict:
    """
    Clean up the previous failed presentation and increment the retry counter.

    If a slides_file_id exists in state, deletes the presentation from
    Google Drive before the Drafting Agent regenerates it. Deletion errors
    are caught and logged so a cleanup failure never halts the graph.

    Args:
        state: The current LangGraph pipeline state.

    Returns:
        A dictionary updating retry_count by 1.
    """
    slides_file_id = state.get("slides_file_id")

    if slides_file_id:
        try:
            from app.services.google_service import GoogleSlidesService
            google_service = GoogleSlidesService()
            google_service.delete_presentation(slides_file_id)
            logger.info("Deleted failed presentation '%s' before retry.", slides_file_id)
        except Exception as exc:
            logger.error(
                "Could not delete presentation '%s' during retry cleanup: %s",
                slides_file_id,
                exc,
            )

    return {"retry_count": state.get("retry_count", 0) + 1}


def build_graph():
    """
    Build and compile the proposal generation LangGraph pipeline.

    Graph structure:
        START → intake_node → drafting_node → review_node
            → route_after_review()
                ├── "finalize_node" → finalize_node → END
                ├── "fail_node"     → fail_node     → END
                └── "drafting_node" → retry_node → drafting_node (loop)

    Returns:
        A compiled LangGraph ready for invocation.
    """
    graph = StateGraph(ProposalState)

    # Register all nodes.
    graph.add_node("intake_node", intake_node)
    graph.add_node("drafting_node", drafting_node)
    graph.add_node("review_node", review_node)
    graph.add_node("retry_node", retry_node)
    graph.add_node("finalize_node", finalize_node)
    graph.add_node("fail_node", fail_node)

    # Linear edges: START → intake → drafting → review.
    graph.add_edge(START, "intake_node")
    graph.add_edge("intake_node", "drafting_node")
    graph.add_edge("drafting_node", "review_node")

    # Conditional routing after review.
    graph.add_conditional_edges(
        "review_node",
        route_after_review,
        {
            "finalize_node": "finalize_node",
            "drafting_node": "retry_node",
            "fail_node": "fail_node",
        },
    )

    # Retry loop: retry_node increments counter then re-enters drafting.
    graph.add_edge("retry_node", "drafting_node")

    # Terminal edges.
    graph.add_edge("finalize_node", END)
    graph.add_edge("fail_node", END)

    return graph.compile()
