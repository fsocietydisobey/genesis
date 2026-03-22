"""Ein Sof (MUTHER) graph — the meta-orchestrator.

The Infinite. Monitors the repository, performs Tzimtzum (contraction —
budget, directives), and spawns the right pattern: Chayah (evolution),
Nefesh (parallel swarm), or Nitzotz (single task).

Flow:
    assess → dispatch → execute_pattern → directive_check → absorb → assess (loop)
    or: assess → dispatch → cryosleep → END
"""

from __future__ import annotations

import asyncio

from langgraph.graph import END, START, StateGraph

from genesis.config import OrchestratorConfig, get_classify_model
from genesis.core.directives import check_directives
from genesis.core.fitness import assess_health
from genesis.core.resource_control import GlobalBudget
from genesis.core.state import OrchestratorState
from genesis.nodes.evolution.assess import build_assess_node
from genesis.nodes.ein_sof_dispatch import build_muther_dispatch_node
from genesis.tools.git_tools import git_checkpoint, git_revert
from genesis.log import get_logger

log = get_logger("muther")


async def _init_node(state: OrchestratorState) -> dict:
    """Initialize Ein Sof — set up budget and directives."""
    history = list(state.get("history", []))
    budget = GlobalBudget(
        max_daily_cost_usd=state.get("global_budget", {}).get("max_daily_cost_usd", 10.0),
    )

    return {
        "global_budget": budget.to_dict(),
        "muther_cycle": 0,
        "active_entities": [],
        "history": history + ["ein_sof: initialized — Tzimtzum (contraction) applied"],
    }


async def _execute_pattern_node(state: OrchestratorState) -> dict:
    """Execute the dispatched pattern.

    This node invokes the chosen graph (Chayah, Nefesh, or Nitzotz) directly.
    In a full implementation, this would spawn background jobs. For now, it
    does a direct invocation for simplicity.
    """
    from genesis.cli.prompts import build_prompt
    from genesis.cli.runners import run_claude

    history = list(state.get("history", []))
    decision = state.get("dispatch_decision") or {}
    pattern = decision.get("pattern", "cryosleep")
    task_desc = decision.get("task_description", "")
    cycle = state.get("muther_cycle", 0) + 1

    if pattern == "cryosleep":
        return {
            "muther_cycle": cycle,
            "history": history + [f"ein_sof(cycle {cycle}): cryosleep — nothing to do"],
        }

    # Git checkpoint before making changes
    await git_checkpoint(f"ein_sof baseline cycle {cycle}")

    log.info("cycle %d: executing %s — %s", cycle, pattern, task_desc[:60])

    # For now, execute via Claude CLI directly
    # Future: spawn the actual Chayah/Nefesh/Nitzotz graph as a background job
    prompt = build_prompt(
        "You are a senior software engineer. Execute this task precisely.",
        f"## Task\n\n{task_desc}" if task_desc else "## Task\n\nImprove the codebase based on current health assessment.",
        f"## Pattern: {pattern}",
    )

    try:
        result = await run_claude(prompt, timeout=600, permission_mode="acceptEdits")
        return {
            "implementation_result": result,
            "muther_cycle": cycle,
            "history": history + [f"ein_sof(cycle {cycle}): {pattern} completed"],
        }
    except Exception as e:
        log.error("cycle %d: %s execution failed — %s", cycle, pattern, e)
        return {
            "muther_cycle": cycle,
            "history": history + [f"ein_sof(cycle {cycle}): {pattern} failed — {e}"],
        }


async def _directive_check_node(state: OrchestratorState) -> dict:
    """Check the changes against DIRECTIVES.md (Special Order 937)."""
    history = list(state.get("history", []))
    cycle = state.get("muther_cycle", 0)

    # Get the diff
    proc = await asyncio.create_subprocess_exec(
        "git", "diff", "HEAD~1", "HEAD",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    diff = stdout.decode("utf-8", errors="replace")

    if not diff.strip():
        return {
            "directive_result": {"passed": True, "violations": []},
            "history": history + [f"directive_check(cycle {cycle}): no changes to check"],
        }

    result = check_directives(diff)

    result_dict = {
        "passed": result.passed,
        "violations": [
            {"directive": v.directive, "description": v.description,
             "severity": v.severity, "file": v.file}
            for v in result.violations
        ],
    }

    if not result.passed:
        # Revert the changes
        log.warning("cycle %d: directive violation — reverting!", cycle)
        await git_revert()
        return {
            "directive_result": result_dict,
            "history": history + [
                f"directive_check(cycle {cycle}): VIOLATION — "
                + "; ".join(f"{v.severity}: {v.description}" for v in result.violations)
                + " — changes reverted"
            ],
        }

    return {
        "directive_result": result_dict,
        "history": history + [f"directive_check(cycle {cycle}): clean"],
    }


def _after_dispatch(state: OrchestratorState) -> str:
    """Route based on dispatch decision."""
    decision = state.get("dispatch_decision") or {}
    pattern = decision.get("pattern", "cryosleep")
    if pattern == "cryosleep":
        return END
    return "execute_pattern"


def _after_directive(state: OrchestratorState) -> str:
    """Continue looping or exit."""
    cycle = state.get("muther_cycle", 0)
    max_cycles = 20  # Ein Sof's own cycle limit

    if cycle >= max_cycles:
        return END

    budget = state.get("global_budget") or {}
    if budget.get("budget_remaining", 10.0) <= 0:
        return END

    return "assess"  # Loop back


async def build_muther_graph(config: OrchestratorConfig):
    """Build and compile the Ein Sof (MUTHER) meta-orchestrator graph.

    Args:
        config: OrchestratorConfig with provider/role definitions.

    Returns:
        Tuple of (compiled StateGraph, AsyncSqliteSaver checkpointer).
    """
    import os
    from pathlib import Path

    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    data_dir = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    ) / "ai-orchestrator"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(data_dir / "muther_checkpoints.db")

    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()
    log.info("Ein Sof checkpointer ready: %s", db_path)

    model = get_classify_model(config)
    assess_node = build_assess_node()
    dispatch_node = build_muther_dispatch_node(model)

    graph = StateGraph(OrchestratorState)

    graph.add_node("init", _init_node)
    graph.add_node("assess", assess_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("execute_pattern", _execute_pattern_node)
    graph.add_node("directive_check", _directive_check_node)

    graph.add_edge(START, "init")
    graph.add_edge("init", "assess")
    graph.add_edge("assess", "dispatch")
    graph.add_conditional_edges("dispatch", _after_dispatch, {"execute_pattern": "execute_pattern", END: END})
    graph.add_edge("execute_pattern", "directive_check")
    graph.add_conditional_edges("directive_check", _after_directive, {"assess": "assess", END: END})

    compiled = graph.compile(checkpointer=checkpointer)
    return compiled, checkpointer
