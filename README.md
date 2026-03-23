# CHIMERA

Autonomous multi-model orchestration system. Nine composable LangGraph execution patterns — from sequential pipelines to parallel swarms to self-evolving loops to proactive tool-builders.

## Patterns

| Designation | Full name | What it does | MCP tool |
|---|---|---|---|
| **SPR-4** | Sequential Phase Runner | 4-phase pipeline: research → plan → implement → review | `chain_spr4` |
| **TFB** | Tri-Force Balancer | Stress tester attacks, scope analyzer proposes, arbitrator decides | (inside SPR-4) |
| **CLR** | Closed-Loop Refiner | Continuous: assess → classify → execute → validate → loop | `chain_clr` |
| **PDE** | Parallel Dispatch Engine | Task decomposer → N workers → aggregator → validate | `swarm` |
| **PDE-F** | Graduated Dispatch | Fibonacci generations: 1 → 1 → 2 → 3 → 5 → consolidate | (inside `swarm`) |
| **HVD** | Hypervisor Daemon | Monitors repo, spawns the right pattern, enforces directives | `chain_hvd` |
| **ACL** | Atomic Component Library | Immutable tested primitives — prevents hallucination | (planned) |
| **DCE** | Dead Code Eliminator | Dead code removal in isolated git worktree | (planned) |
| **POB** | Proactive Observation Builder | Watches behavior, builds developer tools unsolicited | (planned) |

## Quick Start

```bash
git clone git@github.com:fsocietydisobey/chimera.git
cd chimera
uv sync

# Configure API keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and GOOGLE_AI_API_KEY

# Run
uv run chimera
```

## Connect to Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "chimera": {
      "command": "uv",
      "args": ["--directory", "/path/to/chimera", "run", "chimera"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "GOOGLE_AI_API_KEY": "AIza..."
      }
    }
  }
}
```

Then in Cursor chat:

```
spr4 add rate limiting to the API endpoints
```

## Tools (13)

| Tool | What it does |
|---|---|
| `chain_spr4(task)` | SPR-4 pipeline with TFB balanced forces |
| `chain_clr(max_cycles)` | CLR continuous refinement loop |
| `swarm(goal, budget, max_agents)` | PDE parallel dispatch |
| `chain_hvd(budget)` | HVD meta-orchestrator |
| `research(question)` | Direct Gemini CLI |
| `architect(goal)` | Direct Claude CLI |
| `classify(task)` | Fast tier classification |
| `chain(task)` | Supervisor pipeline |
| `status(job_id)` | Poll job progress |
| `approve(job_id, feedback?)` | Approve/reject paused job |
| `history(thread_id)` | View checkpoints |
| `rewind(thread_id, checkpoint_id)` | Time-travel |
| `health()` | Server status |

## Project Structure

```
src/chimera/
├── graphs/          # 5 compiled StateGraphs (spr4, clr, pde, hvd, supervisor)
├── nodes/
│   ├── spr4/        # Pipeline: research, architect, implement, critic
│   ├── tfb/         # Balanced forces: stress_tester, scope_analyzer, arbitrator, compliance, retry_controller, integration_gate
│   ├── pde/         # Parallel dispatch: task_decomposer, worker, aggregator
│   ├── clr/         # Refinement loop: health_scanner, classifier
│   └── hvd_dispatcher.py
├── subgraphs/       # SPR-4 phase subgraphs
├── core/            # State, guards, memory, fitness, directives, resource control
├── server/          # MCP server (13 tools) + background jobs
├── config/          # Config loader, providers (Anthropic, Google)
├── cli/             # CLI subprocess runners (run_claude, run_gemini)
├── prompts/         # System prompts
└── tools/           # Filesystem tools, git tools
```

## Documentation

- [Design Philosophy](docs/genesis-story.md) — the architectural narrative
- [Commands Reference](docs/genesis-commands.md) — every command explained
- [Usage Guide](docs/usage-guide.md) — how to use from Cursor
- [Architecture Patterns](tasks/architecture-patterns-technical.md) — technical reference
