"""Implementation phase subgraph — Sephirotic balanced forces.

Full flow with expansion/restriction/synthesis:
    guard → implement → gevurah (attack) → chesed (propose) → tiferet (arbitrate) → hod (format)
    → tiferet decides: loop back to implement, or exit as ready_for_review

The guard node enforces the plan_approved invariant — implementation
cannot proceed without an approved architecture plan.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from genesis.core.guards import require_plan_approved
from genesis.core.state import OrchestratorState
from genesis.nodes.sefirot.chesed import build_chesed_node
from genesis.nodes.sefirot.gevurah import build_gevurah_node
from genesis.nodes.sefirot.hod import build_hod_node
from genesis.nodes.pipeline.implement import build_implement_node
from genesis.nodes.sefirot.tiferet import build_tiferet_node


async def _guard_node(state: OrchestratorState) -> dict:
    """Enforce plan_approved invariant before implementation."""
    if not require_plan_approved(state):
        history = list(state.get("history", []))
        return {
            "handoff_type": "plan_not_approved",
            "history": history + ["guard: blocked implementation — plan not approved"],
        }
    return {}


def _after_guard(state: OrchestratorState) -> str:
    """Block implementation if plan is not approved."""
    if state.get("handoff_type") == "plan_not_approved":
        return END
    return "implement"


def _after_tiferet(state: OrchestratorState) -> str:
    """Route based on Tiferet's arbitration decision."""
    tiferet = state.get("tiferet_decision") or {}
    handoff = state.get("handoff_type", "")

    # Gevurah blocker or Tiferet says rework needed
    if tiferet.get("needs_rework") or handoff == "tests_failing":
        # Check step limit
        step = state.get("phase_step", 0)
        max_steps = state.get("max_phase_steps", 5)
        if step >= max_steps:
            return "hod"  # Max steps — format what we have and exit
        return "implement"  # Loop back for rework

    return "hod"  # Proceed to formatting


def build_implementation_subgraph(
    critic_model: BaseChatModel,
    review_model: BaseChatModel | None = None,
):
    """Build the implementation phase subgraph with Sephirotic balanced forces.

    Flow: guard → implement → gevurah → chesed → tiferet → hod → exit
    With loop: if tiferet says needs_rework → back to implement

    Args:
        critic_model: LangChain model for Gevurah and Chesed (Haiku).
        review_model: LangChain model for Tiferet (should be different from
            the builder for cross-model review). Falls back to critic_model.

    Returns:
        Compiled StateGraph (no checkpointer — parent handles that).
    """
    implement_node = build_implement_node()
    gevurah_node = build_gevurah_node(critic_model)
    chesed_node = build_chesed_node(critic_model)
    tiferet_node = build_tiferet_node(review_model or critic_model)
    hod_node = build_hod_node()

    graph = StateGraph(OrchestratorState)

    graph.add_node("guard", _guard_node)
    graph.add_node("implement", implement_node)
    graph.add_node("gevurah", gevurah_node)
    graph.add_node("chesed", chesed_node)
    graph.add_node("tiferet", tiferet_node)
    graph.add_node("hod", hod_node)

    # Entry
    graph.add_edge(START, "guard")
    graph.add_conditional_edges(
        "guard",
        _after_guard,
        {"implement": "implement", END: END},
    )

    # Implementation → Gevurah (attack) → Chesed (propose) → Tiferet (arbitrate)
    graph.add_edge("implement", "gevurah")
    graph.add_edge("gevurah", "chesed")
    graph.add_edge("chesed", "tiferet")

    # Tiferet decides: rework or proceed to Hod
    graph.add_conditional_edges(
        "tiferet",
        _after_tiferet,
        {"implement": "implement", "hod": "hod"},
    )

    # Hod (format) → exit
    graph.add_edge("hod", END)

    return graph.compile()
