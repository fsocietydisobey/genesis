# Genesis

Autonomous multi-model orchestration system. Six composable execution patterns — from sequential pipelines to parallel swarms to self-evolving loops — unified under a Kabbalistic architecture where intent descends through balanced forces into running code.

## The Story

A user's intent enters as a ray of light (the Kav). It flows through the Tree of Life — balanced by opposing creative and restrictive forces — until it manifests as physical reality: committed, tested, running code.

See [docs/genesis-story.md](docs/genesis-story.md) for the full Kabbalistic narrative.

## Patterns

| Pattern | Name | What it does | MCP tool |
|---|---|---|---|
| Base pipeline | **Nitzotz** (Divine Sparks) | 4-phase: research → plan → implement → review | `chain_aril` |
| Balanced forces | **Sefirot** (Emanations) | Gevurah attacks, Chesed proposes, Tiferet arbitrates | (inside Nitzotz) |
| Evolution loop | **Chayah** (Living Soul) | Continuous: assess → triage → execute → validate → loop | `chain_ouroboros` |
| Parallel swarm | **Nefesh** (Animal Soul) | Sovereign decomposes → N agents → merge → validate | `swarm` |
| Graduated dispatch | **Klipah** (Shells) | Fibonacci generations: 1 → 1 → 2 → 3 → 5 → consolidate | (inside `swarm`) |
| Meta-orchestrator | **Ein Sof** (The Infinite) | Monitors repo, spawns the right pattern, enforces directives | `chain_muther` |

## Quick Start

```bash
# Install
git clone git@github.com:fsocietydisobey/genesis.git
cd genesis
uv sync

# Configure API keys
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and GOOGLE_AI_API_KEY

# Run
uv run genesis
```

## Connect to Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "genesis": {
      "command": "uv",
      "args": ["--directory", "/path/to/genesis", "run", "genesis"],
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
aril add rate limiting to the API endpoints
```

## Tools (13)

| Tool | What it does |
|---|---|
| `chain_aril(task)` | Nitzotz + Sefirot pipeline |
| `chain_ouroboros(max_cycles)` | Chayah evolution loop |
| `swarm(goal, budget, max_agents)` | Nefesh parallel dispatch |
| `chain_muther(budget)` | Ein Sof meta-orchestrator |
| `research(question)` | Direct Gemini CLI |
| `architect(goal)` | Direct Claude CLI |
| `classify(task)` | Fast tier classification |
| `chain(task)` | Supervisor pipeline |
| `status(job_id)` | Poll job progress |
| `approve(job_id, feedback?)` | Approve/reject paused job |
| `history(thread_id)` | View checkpoints |
| `rewind(thread_id, checkpoint_id)` | Time-travel |
| `health()` | Server status |

## Documentation

- [Genesis Story](docs/genesis-story.md) — the Kabbalistic narrative
- [Commands Reference](docs/genesis-commands.md) — every command explained
- [Usage Guide](docs/usage-guide.md) — how to use from Cursor
- [Nitzotz Architecture](docs/nitzotz.md) — the base pipeline
