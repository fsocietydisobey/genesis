"""Regression tests for the implementation subgraph's rework loop.

These guard against the cycle-limit-hit bug surfaced 2026-05-07:
  - `phase_step` was being read but never incremented inside the
    subgraph, so the step-limit fallback exit never fired.
  - `handoff_type="tests_failing"` was sticky across iterations, so
    even when the arbitrator decided `needs_rework=False`, the
    routing function's OR clause forced re-entry into `implement`.
  - `_after_arbitrator` returned `"hod"` (typo) — not a key in the
    conditional-edges mapping `{"implement", "compliance"}`.

Net effect: the implement → stress → scope → arbitrate loop ran
until LangGraph's recursion_limit forced termination. These tests
lock the fixed behavior so the bug doesn't regress silently.
"""

from chimera.subgraphs.implementation import _after_arbitrator


def test_after_arbitrator_returns_compliance_when_no_rework_needed():
    """Happy path: arbitrator says proceed → route to compliance."""
    state = {
        "arbitration_decision": {"needs_rework": False},
        "handoff_type": "ready_for_review",
        "implementation_loop_step": 1,
        "max_phase_steps": 5,
    }
    assert _after_arbitrator(state) == "compliance"


def test_after_arbitrator_loops_when_rework_needed_and_under_cap():
    """Loop continues when needs_rework=True and counter is under cap."""
    state = {
        "arbitration_decision": {"needs_rework": True},
        "handoff_type": "tests_failing",
        "implementation_loop_step": 1,
        "max_phase_steps": 5,
    }
    assert _after_arbitrator(state) == "implement"


def test_after_arbitrator_exits_at_step_cap_even_if_rework_needed():
    """Loop self-bounds at max_phase_steps even when arbitrator
    insists on rework — otherwise we hit LangGraph's recursion_limit."""
    state = {
        "arbitration_decision": {"needs_rework": True},
        "handoff_type": "tests_failing",
        "implementation_loop_step": 5,  # >= max
        "max_phase_steps": 5,
    }
    assert _after_arbitrator(state) == "compliance"


def test_after_arbitrator_returns_keys_present_in_edge_mapping():
    """Every return value of _after_arbitrator must be a key in the
    conditional-edges mapping configured in build_implementation_subgraph
    (`{"implement", "compliance"}`). Catches the 'hod' typo class of bug.
    """
    valid_targets = {"implement", "compliance"}
    # Sweep state combinations
    for needs_rework in (True, False):
        for handoff in ("", "tests_failing", "ready_for_review", "plan_not_approved"):
            for step in (0, 1, 4, 5, 10):
                state = {
                    "arbitration_decision": {"needs_rework": needs_rework},
                    "handoff_type": handoff,
                    "implementation_loop_step": step,
                    "max_phase_steps": 5,
                }
                result = _after_arbitrator(state)
                assert result in valid_targets, (
                    f"_after_arbitrator returned {result!r} for state {state!r}; "
                    f"must be one of {valid_targets}"
                )
