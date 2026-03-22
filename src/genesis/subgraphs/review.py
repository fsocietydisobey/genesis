"""Review phase subgraph — Yesod integration gate + human approval.

Runs the Yesod integration validator (full test suite + type checker + diff review),
then pauses for human approval via the existing human_review node.

    yesod (integration gate) → human_review (PAUSED) → exit

The human sets human_approved on approval or provides feedback on rejection.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from genesis.core.state import OrchestratorState
from genesis.nodes.human_review import build_human_review_node
from genesis.nodes.yesod import build_yesod_node


async def _set_review_handoff(state: OrchestratorState) -> dict:
    """Set handoff_type based on human review decision."""
    history = list(state.get("history", []))
    review_status = state.get("human_review_status", "")

    if review_status == "approved":
        return {
            "handoff_type": "done",
            "human_approved": True,
            "history": history + ["review: human approved — marking done"],
        }
    else:
        feedback = state.get("human_feedback", "")
        return {
            "handoff_type": "needs_impl_fix",
            "history": history + [f"review: human rejected — {feedback}"],
        }


def build_review_subgraph(validator_model: BaseChatModel):
    """Build the review phase subgraph with Yesod integration gate.

    Flow: yesod (integration) → human_review (HITL) → set_handoff → exit

    Args:
        validator_model: LangChain model (unused — Yesod is deterministic,
            but kept for API consistency with other subgraph builders).

    Returns:
        Compiled StateGraph (no checkpointer — parent handles that).
    """
    yesod_node = build_yesod_node()
    human_review_node = build_human_review_node()

    graph = StateGraph(OrchestratorState)

    graph.add_node("yesod", yesod_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("set_handoff", _set_review_handoff)

    graph.add_edge(START, "yesod")
    graph.add_edge("yesod", "human_review")
    graph.add_edge("human_review", "set_handoff")
    graph.add_edge("set_handoff", END)

    return graph.compile()
