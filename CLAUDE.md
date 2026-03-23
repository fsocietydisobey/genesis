# CHIMERA — Project Rules

## What this is

Autonomous multi-model AI orchestration system built on LangGraph. Nine composable execution patterns unified under a Kabbalistic architecture.

Entry point: `chimera` — runs the MCP server over stdio.

## Project structure

```
src/chimera/
  core/              # State, guards, memory, fitness, directives, resource control
  graphs/            # 8 compiled StateGraphs
    pipeline.py      # SPR-4 (phased pipeline) — chain_pipeline
    refiner.py       # CLR (evolution loop) — chain_refiner
    swarm.py         # PDE (parallel swarm) — swarm
    hypervisor.py    # HVD (meta-orchestrator) — chain_hypervisor
    supervisor.py    # Option B hub-and-spoke — chain
    components.py    # ACL (component library) — chain_components
    deadcode.py      # DCE (dead code eliminator) — chain_deadcode
    toolbuilder.py   # POB (proactive tool-builder) — chain_toolbuilder
  nodes/             # Node factories, organized by pattern
    pipeline/        # Pipeline: research, architect, implement, critic
    balanced/        # Balanced forces: stress_tester, scope_analyzer, arbitrator, compliance, retry_controller, integration_gate
    swarm/           # Swarm: task_decomposer, worker, aggregator
    refiner/         # Refiner: health_scanner, classifier
    components/      # Components: scanner, validator, enforcer
    deadcode/        # Dead code: seeker, shatterer, reaper
    toolbuilder/     # Tool builder: watcher, friction, proposer, forge, pr_creator
    supervisor.py    # Option B supervisor
    validator.py     # Shared quality scorer
    human_review.py  # HITL via interrupt()
    gemini_assist.py # Debugging via Gemini CLI
    hypervisor_dispatcher.py  # Hypervisor pattern selector
  subgraphs/         # Pipeline phase subgraphs (research, planning, implementation, review)
  server/            # MCP server (16 tools) + background job manager
  config/            # YAML config loader, providers (Anthropic, Google)
  cli/               # CLI subprocess runners (run_claude, run_gemini)
  prompts/           # System prompts for research, architect, classifier
  tools/             # Filesystem tools, git tools, worktree management
  log.py             # Structured logging (stderr only)
  pidlock.py         # PID lock to prevent zombie instances
docs/                # CHIMERA story, commands reference, usage guide
tasks/               # Pattern design docs (BUILD-ORDER.md, per-pattern folders)
scripts/             # Daemon scripts (ouroboros.sh, muther.sh)
```

## Conventions

### Python
- Python 3.12+. Use modern syntax: `str | None`, `list[str]`, `dict[str, Any]`.
- Async throughout — all MCP tool handlers and node functions are `async def`.
- Type hints on all function signatures.
- Imports: stdlib, then third-party, then `chimera.*` (absolute imports within the package).
- Use `uv add <package>` to add dependencies.

### Logging
- Use `from chimera.log import get_logger` and `log = get_logger("component_name")`.
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
- `chain_pipeline` triggers SPR-4. `swarm` triggers PDE. `chain_refiner` triggers CLR. `chain_hypervisor` triggers HVD.

### CLI subprocesses
- All subprocess calls go through `run_cli()` in `cli/cli.py`.
- Always use `stdin=subprocess.DEVNULL` — prevents reading the MCP stdin pipe.
- Subprocesses run in threads via `asyncio.to_thread`.

## Pattern designations

| MCP tool | Designation | What it is |
|---|---|---|
| `chain_pipeline` | **SPR-4** (Sequential Phase Runner) | 4-phase pipeline with balanced forces |
| (inside pipeline) | **TFB** (Tri-Force Balancer) | 6 balanced force nodes |
| `chain_refiner` | **CLR** (Closed-Loop Refiner) | Continuous evolution loop |
| `swarm` | **PDE** (Parallel Dispatch Engine) | Parallel swarm dispatch |
| (inside swarm) | **PDE-F** (Fibonacci Dispatch) | Graduated dispatch mode |
| `chain_hypervisor` | **HVD** (Hypervisor Daemon) | Meta-orchestrator |
| `chain_components` | **ACL** (Atomic Component Library) | Immutable atomic primitives |
| `chain_deadcode` | **DCE** (Dead Code Eliminator) | Dead code purging in shadow worktree |
| `chain_toolbuilder` | **POB** (Proactive Observation Builder) | Proactive tool-builder |
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
uv run chimera              # Start the MCP server
LOG_LEVEL=DEBUG uv run chimera  # With debug logging
```
