# Genesis — Project Rules

## What this is

An autonomous multi-model AI orchestration system built on LangGraph. Six composable execution patterns unified under a Kabbalistic architecture.

Entry point: `genesis` — runs the MCP server over stdio.

## Project structure

```
src/genesis/
  core/              # State, guards, memory, fitness, directives, resource control
  graphs/            # 5 compiled StateGraphs
    spr4.py          # SPR-4 (phased pipeline) — chain_spr4
    clr.py           # CLR (evolution loop) — chain_clr
    pde.py           # PDE (parallel swarm) — swarm
    hvd.py           # HVD (meta-orchestrator) — chain_hvd
    supervisor.py    # Option B hub-and-spoke — chain
  nodes/             # 20 node factories, organized by pattern
    spr4/        # SPR-4: research, architect, implement, critic
    tfb/         # TFB: stress_tester, scope_analyzer, arbitrator, compliance, retry_controller, integration_gate
    pde/           # PDE: task_decomposer, worker, aggregator
    clr/       # CLR: health_scanner, classifier
    supervisor.py    # Option B supervisor
    validator.py     # Shared quality scorer
    human_review.py  # HITL via interrupt()
    gemini_assist.py # Debugging via Gemini CLI
    hvd_dispatcher.py  # HVD pattern selector
  subgraphs/         # SPR-4 phase subgraphs (research, planning, implementation, review)
  server/            # MCP server (13 tools) + background job manager
  config/            # YAML config loader, providers (Anthropic, Google)
  cli/               # CLI subprocess runners (run_claude, run_gemini)
  prompts/           # System prompts for research, architect, classifier
  tools/             # Filesystem tools, git tools
  log.py             # Structured logging (stderr only)
  pidlock.py         # PID lock to prevent zombie instances
docs/                # Genesis story, commands reference, usage guide
tasks/               # Pattern design docs (BUILD-ORDER.md, per-pattern folders)
scripts/             # Daemon scripts (ouroboros.sh, muther.sh)
```

## Conventions

### Python
- Python 3.12+. Use modern syntax: `str | None`, `list[str]`, `dict[str, Any]`.
- Async throughout — all MCP tool handlers and node functions are `async def`.
- Type hints on all function signatures.
- Imports: stdlib, then third-party, then `genesis.*` (absolute imports within the package).
- Use `uv add <package>` to add dependencies.

### Logging
- Use `from genesis.log import get_logger` and `log = get_logger("component_name")`.
- Log to stderr only — MCP uses stdout for protocol messages.
- Don't log prompt contents at INFO level (too large). Use DEBUG.

### Nodes
- Nodes are built via factory functions: `build_X_node()` returns an `async def`.
- Nodes take `OrchestratorState` and return a `dict` of state updates.
- Domain nodes (research, architect, implement) shell out to CLI subprocesses.
- Supervisor/validator/critic use cheap API models (Haiku).

### Graphs
- Each graph has its own checkpointer (AsyncSqliteSaver).
- Subgraphs compile without checkpointers — the parent handles persistence.
- `chain_spr4` triggers SPR-4. `swarm` triggers PDE. `chain_clr` triggers CLR. `chain_hvd` triggers HVD.

### CLI subprocesses
- All subprocess calls go through `run_cli()` in `cli/cli.py`.
- Always use `stdin=subprocess.DEVNULL` — prevents reading the MCP stdin pipe.
- Subprocesses run in threads via `asyncio.to_thread`.

## Pattern designations

| Code name | Designation | What it is |
|---|---|---|
| `chain_spr4` | **SPR-4** (Sequential Phase Runner) | 4-phase pipeline with Sefirot balanced forces |
| (inside SPR-4) | **TFB** (Tri-Force Balancer) | 6 balanced force nodes: Gevurah, Chesed, Tiferet, Hod, Netzach, Yesod |
| `chain_clr` | **CLR** (Closed-Loop Refiner) | Continuous evolution loop |
| `swarm` | **PDE** (Parallel Dispatch Engine) | Parallel swarm dispatch |
| (inside Nefesh) | **PDE-F** (Fibonacci Dispatch) | Graduated dispatch mode |
| `chain_hvd` | **HVD** (Hypervisor Daemon) | Meta-orchestrator |
| `chain_swp` | **SWP** (Shadow Worktree Purifier) | Dead code purging in shadow worktree (planned) |
| `chain_pob` | **POB** (Proactive Observation Builder) | Proactive tool-builder from the Qliphoth (planned) |
| (inside agents) | **ACL** (Atomic Component Library) | Immutable atomic primitives (planned) |
| The system | **Genesis** | Where intent becomes reality |

## Things to avoid

- Don't add dependencies without checking if an existing one covers the need.
- Don't log prompt contents at INFO level.
- Don't use sync I/O in async code paths.
- Don't commit `.env` or `*.db` files.
- Don't spawn subprocesses without `stdin=subprocess.DEVNULL`.
- Don't make MCP tools that block for minutes — use background jobs and polling.

## Running

```bash
uv run genesis              # Start the MCP server
LOG_LEVEL=DEBUG uv run genesis  # With debug logging
```
