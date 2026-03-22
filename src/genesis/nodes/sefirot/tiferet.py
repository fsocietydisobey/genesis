"""Tiferet (Beauty/Harmony) — cross-model arbitration and synthesis.

The balancing force. Receives Gevurah's verdict (restrictive) and Chesed's
proposals (generative), and arbitrates between them. Uses a DIFFERENT model
from the builder — no model judges its own output.

Produces a decision: which Gevurah issues to address, which Chesed proposals
to accept, and an overall rationale. The decision feeds back into the
implementation loop.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from genesis.log import get_logger
from genesis.core.state import OrchestratorState

log = get_logger("node.tiferet")

TIFERET_SYSTEM_PROMPT = """\
You are a senior engineering arbitrator. You receive two competing perspectives
on a piece of work:

1. **Gevurah (the critic)** — found issues and wants changes
2. **Chesed (the advisor)** — proposes improvements and wants additions

Your job is to make the FINAL CALL on each item. You are the tiebreaker.

Decision rules:
- **Gevurah blocker** → ALWAYS accept. Blockers must be fixed.
- **Gevurah warning** → Accept if the issue is real and specific. Reject vague complaints.
- **Chesed proposal** → Accept if it's within scope, clearly valuable, and low effort.
  Reject scope creep, speculative improvements, and anything that's "nice to have" vs necessary.
- **Conflicting opinions** → Weigh specificity. Whoever cites specific files, functions,
  and concrete consequences wins. Vague arguments lose.

Be decisive. Don't hedge. For each item, say "accept" or "reject" with a one-line reason.

Finally, decide: does the implementation need rework (needs_rework: true) or is it
ready to proceed (needs_rework: false)? Only set needs_rework if there are accepted
Gevurah blockers that haven't been fixed yet.
"""


class TiferetDecision(BaseModel):
    """Structured decision from the arbitrator."""

    accepted_changes: list[str] = Field(
        default_factory=list,
        description="Descriptions of accepted Gevurah issues and Chesed proposals",
    )
    rejected_changes: list[str] = Field(
        default_factory=list,
        description="Descriptions of rejected items with reason",
    )
    rationale: str = Field(description="Overall reasoning for the decision")
    needs_rework: bool = Field(
        default=False,
        description="True if accepted blockers require implementation rework",
    )


def build_tiferet_node(model: BaseChatModel):
    """Build a cross-model arbitration node.

    IMPORTANT: This should use a DIFFERENT model from the one that produced
    the implementation. If Claude built it, use Gemini to review (or vice versa).
    In practice, pass a different model instance than the one used for build nodes.

    Args:
        model: LangChain chat model (different from the builder model).

    Returns:
        Async node function compatible with LangGraph StateGraph.
    """
    structured_model = model.with_structured_output(TiferetDecision)

    async def tiferet_node(state: OrchestratorState) -> dict:
        """Arbitrate between Gevurah's restrictions and Chesed's expansions."""
        task = state.get("task", "")
        history = list(state.get("history", []))

        gevurah_verdict = state.get("gevurah_verdict") or {}
        chesed_proposals = state.get("chesed_proposals") or []

        # Build the arbitration context
        prompt_parts = [f"## Original task\n\n{task}"]

        # Format Gevurah's issues
        issues = gevurah_verdict.get("issues", [])
        if issues:
            gevurah_section = "## Gevurah's verdict\n\n"
            for i, issue in enumerate(issues, 1):
                gevurah_section += (
                    f"{i}. **[{issue.get('severity', '?')}]** ({issue.get('category', '?')}) "
                    f"{issue.get('description', '')}"
                )
                if issue.get("file"):
                    gevurah_section += f" — `{issue['file']}`"
                gevurah_section += "\n"
            prompt_parts.append(gevurah_section)
        else:
            prompt_parts.append("## Gevurah's verdict\n\nNo issues found.")

        # Format Chesed's proposals
        if chesed_proposals:
            chesed_section = "## Chesed's proposals\n\n"
            for i, prop in enumerate(chesed_proposals, 1):
                chesed_section += (
                    f"{i}. **{prop.get('description', '')}** "
                    f"(effort: {prop.get('estimated_effort', '?')}) — "
                    f"{prop.get('rationale', '')}\n"
                )
            prompt_parts.append(chesed_section)
        else:
            prompt_parts.append("## Chesed's proposals\n\nNo proposals.")

        # Include implementation context
        impl = state.get("implementation_result", "")
        if impl:
            prompt_parts.append(f"## Implementation output (for reference)\n\n{impl[:2000]}")

        messages = [
            SystemMessage(content=TIFERET_SYSTEM_PROMPT),
            HumanMessage(content="\n\n".join(prompt_parts)),
        ]

        decision_raw = await structured_model.ainvoke(messages)
        assert isinstance(decision_raw, TiferetDecision)
        decision = decision_raw

        log.info(
            "decision: %d accepted, %d rejected, needs_rework=%s",
            len(decision.accepted_changes),
            len(decision.rejected_changes),
            decision.needs_rework,
        )

        decision_dict = {
            "accepted_changes": decision.accepted_changes,
            "rejected_changes": decision.rejected_changes,
            "rationale": decision.rationale,
            "needs_rework": decision.needs_rework,
        }

        # Build feedback for the next implementation cycle if rework needed
        feedback_parts = []
        if decision.accepted_changes:
            feedback_parts.append("## Accepted changes to address\n\n" +
                                  "\n".join(f"- {c}" for c in decision.accepted_changes))

        history_entry = (
            f"tiferet: {len(decision.accepted_changes)} accepted, "
            f"{len(decision.rejected_changes)} rejected, "
            f"needs_rework={decision.needs_rework}"
        )

        result: dict = {
            "tiferet_decision": decision_dict,
            "history": history + [history_entry],
        }

        # If rework needed, append accepted changes to validation_feedback
        # so the implementation node sees them on retry
        if decision.needs_rework and feedback_parts:
            existing_feedback = state.get("validation_feedback", "")
            tiferet_feedback = "\n\n".join(feedback_parts)
            result["validation_feedback"] = (
                f"{existing_feedback}\n\n## Tiferet arbitration\n\n{tiferet_feedback}"
                if existing_feedback else tiferet_feedback
            )
            result["handoff_type"] = "tests_failing"  # Force rework
        elif state.get("handoff_type") != "tests_failing":
            # Don't override a Gevurah blocker handoff
            result["handoff_type"] = "ready_for_review"

        return result

    return tiferet_node
