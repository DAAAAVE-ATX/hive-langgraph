"""LangGraph wiring: Q33N -> conditional worker -> BAT -> loop or end."""

from langgraph.graph import END, StateGraph

from hive_lg.nodes import (
    bat_validator,
    coder_bee,
    q33n_orchestrator,
    researcher_bee,
    writer_bee,
)
from hive_lg.state import HiveState


MAX_ATTEMPTS = 3


def _route_from_q33n(state):
    """Conditional edge: send to the worker Q33N picked."""
    return state.get("worker_type", "researcher")


def _route_from_bat(state):
    """Conditional edge: pass -> end, fail -> retry same worker or end on cap."""
    if state.get("bat_verdict") == "pass":
        return "end"
    if state.get("attempt_count", 0) >= MAX_ATTEMPTS:
        return "end_max_retries"
    return state.get("worker_type", "researcher")


def _mark_max_retries(state):
    """Tag the final state when the retry cap is hit without a pass."""
    return {"max_retries_exceeded": True}


def build_graph():
    """Compile and return the hive StateGraph.

    Returns:
        A compiled LangGraph runnable.
    """
    g = StateGraph(HiveState)

    g.add_node("q33n", q33n_orchestrator)
    g.add_node("researcher", researcher_bee)
    g.add_node("coder", coder_bee)
    g.add_node("writer", writer_bee)
    g.add_node("bat", bat_validator)
    g.add_node("finalize_max_retries", _mark_max_retries)

    g.set_entry_point("q33n")

    g.add_conditional_edges(
        "q33n",
        _route_from_q33n,
        {"researcher": "researcher", "coder": "coder", "writer": "writer"},
    )

    g.add_edge("researcher", "bat")
    g.add_edge("coder", "bat")
    g.add_edge("writer", "bat")

    g.add_conditional_edges(
        "bat",
        _route_from_bat,
        {
            "end": END,
            "end_max_retries": "finalize_max_retries",
            "researcher": "researcher",
            "coder": "coder",
            "writer": "writer",
        },
    )

    g.add_edge("finalize_max_retries", END)

    return g.compile()
