"""Extraction pipeline: LangGraph graph builder + runner.

Thin orchestrator — nodes are in separate modules.
Graph: preprocess → extract → postprocess → store
"""

from .types import ExtractionState
from .preprocess import preprocess_node
from .extract import extract_node
from .postprocess import postprocess_node
from .store import store_node


def _should_continue(state: dict) -> str:
    """Conditional edge: stop on error, continue otherwise."""
    return "end" if state.get("status") == "error" else "continue"


def build_extraction_graph():
    """Build and compile the LangGraph extraction pipeline."""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(ExtractionState)
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("extract", extract_node)
    graph.add_node("postprocess", postprocess_node)
    graph.add_node("store", store_node)
    graph.set_entry_point("preprocess")
    graph.add_conditional_edges("preprocess", _should_continue, {"continue": "extract", "end": END})
    graph.add_conditional_edges("extract", _should_continue, {"continue": "postprocess", "end": END})
    graph.add_conditional_edges("postprocess", _should_continue, {"continue": "store", "end": END})
    graph.add_edge("store", END)
    return graph.compile()


_extraction_graph = None


def _get_graph():
    """Lazily build and cache the extraction graph."""
    global _extraction_graph
    if _extraction_graph is None:
        _extraction_graph = build_extraction_graph()
    return _extraction_graph


def run_extraction_pipeline(initial_state: dict) -> dict:
    """Run the full extraction pipeline.

    Args:
        initial_state: ExtractionState dict with document data.

    Returns:
        Final state dict after all nodes have executed.
    """
    return _get_graph().invoke(initial_state)
