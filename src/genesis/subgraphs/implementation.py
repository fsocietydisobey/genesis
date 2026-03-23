"""Implementation phase subgraph — TFB balanced forces.

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
from genesis.nodes.tfb.scope_analyzer import build_scope_analyzer_node
from genesis.nodes.tfb.stress_tester import build_stress_tester_node
from genesis.nodes.tfb.compliance import build_compliance_node
from genesis.nodes.spr4.implement import build_implement_node
from genesis.nodes.tfb.arbitrator import build_arbitrator_node


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
    """Route based on Arbitrator's arbitration decision."""
    tiferet = state.get("arbitration_decision") or {}
    handoff = state.get("handoff_type", "")

    # Stress Tester blocker or Arbitrator says rework needed
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
    """Build the implementation phase subgraph with TFB balanced forces.

    Flow: guard → implement → gevurah → chesed → tiferet → hod → exit
    With loop: if tiferet says needs_rework → back to implement

    Args:
        critic_model: LangChain model for Stress Tester and ScopeAnalyzer (Haiku).
        review_model: LangChain model for Arbitrator (should be different from
            the builder for cross-model review). Falls back to critic_model.

    Returns:
        Compiled StateGraph (no checkpointer — parent handles that).
    """
    implement_node = build_implement_node()
    stress_tester_node = build_stress_tester_node(critic_model)
    scope_analyzer_node = build_scope_analyzer_node(critic_model)
    arbitrator_node = build_arbitrator_node(review_model or critic_model)
    compliance_node = build_compliance_node()

    graph = StateGraph(OrchestratorState)

    graph.add_node("guard", _guard_node)
    graph.add_node("implement", implement_node)
    graph.add_node("gevurah", stress_tester_node)
    graph.add_node("chesed", scope_analyzer_node)
    graph.add_node("tiferet", arbitrator_node)
    graph.add_node("hod", compliance_node)

    # Entry
    graph.add_edge(START, "guard")
    graph.add_conditional_edges(
        "guard",
        _after_guard,
        {"implement": "implement", END: END},
    )

    # Implementation → Stress Tester (attack) → ScopeAnalyzer (propose) → Arbitrator (arbitrate)
    graph.add_edge("implement", "gevurah")
    graph.add_edge("gevurah", "chesed")
    graph.add_edge("chesed", "tiferet")

    # Arbitrator decides: rework or proceed to Compliance
    graph.add_conditional_edges(
        "tiferet",
        _after_tiferet,
        {"implement": "implement", "hod": "hod"},
    )

    # Compliance (format) → exit
    graph.add_edge("hod", END)

    return graph.compile()
