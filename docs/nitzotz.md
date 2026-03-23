# Nitzotz (formerly ARIL) — The Divine Sparks

Nitzotz is the core execution pipeline within **Genesis** (formerly Malkuth) — the unified autonomous system where intent becomes reality. It provides a phased pipeline with hierarchical subgraphs, critic loops, multi-agent handoffs, and persistent memory.

## Architecture

```mermaid
flowchart TB
    START --> load_memory
    load_memory --> phase_router

    subgraph Loop["Phase routing loop"]
        phase_router
    end

    phase_router -->|"research"| research_phase
    phase_router -->|"planning"| planning_phase
    phase_router -->|"implementation"| implementation_phase
    phase_router -->|"review"| review_phase
    phase_router -->|"done"| save_memory

    research_phase --> phase_router
    planning_phase --> phase_router
    implementation_phase --> phase_router
    review_phase --> phase_router

    save_memory --> END

    subgraph research_phase["Research Phase"]
        R1[research node<br/>Gemini CLI] --> R2[critic<br/>Haiku]
        R2 -->|"needs_more_research"| R1
        R2 -->|"research_complete"| R_END((exit))
    end

    subgraph planning_phase["Planning Phase"]
        P1[architect node<br/>Claude CLI] --> P2[critic<br/>Haiku]
        P2 -->|"plan_revision"| P1
        P2 -->|"plan_approved"| P_END((exit))
    end

    subgraph implementation_phase["Implementation Phase"]
        G[guard<br/>plan_approved?] -->|yes| I1[implement node<br/>Claude CLI]
        G -->|no| I_BLOCK((blocked))
        I1 --> I2[critic<br/>Haiku]
        I2 -->|"tests_failing"| I1
        I2 -->|"ready_for_review"| I_END((exit))
    end

    subgraph review_phase["Review Phase"]
        V1[validator<br/>Haiku] --> H1[human_review<br/>HITL]
        H1 --> H2[set_handoff]
        H2 --> V_END((exit))
    end
```

## How it works

1. **load_memory** — loads context from past runs (SQLite) into `memory_context`
2. **phase_router** — reads `handoff_type` and routes to the next phase subgraph
3. **Phase subgraphs** — each runs its own inner loop (domain node → critic → loop/exit)
4. **save_memory** — persists run summary to SQLite for future runs

## Handoff routing table

| handoff_type | Next phase |
|---|---|
| `""` (initial) | research |
| `research_complete` | planning |
| `needs_more_research` | research (loop) |
| `plan_approved` | implementation |
| `plan_revision` | planning (loop) |
| `ready_for_review` | review |
| `tests_failing` | implementation (loop) |
| `done` | save_memory → END |
| `needs_impl_fix` | implementation |
| `plan_not_approved` | planning |

## State (Nitzotz extensions to OrchestratorState)

| Field | Type | Purpose |
|---|---|---|
| `phase` | str | Current phase name |
| `handoff_type` | str | Routing signal between phases |
| `critique` | str | Latest critic feedback |
| `plan_approved` | bool | Set by planning critic when plan passes |
| `human_approved` | bool | Set by human_review node |
| `implementation_versions` | list[dict] (append) | Versioned implementation attempts |
| `selected_implementation_id` | str | Best version picker |
| `phase_step` | int | Step counter within current phase |
| `max_phase_steps` | int | Max steps for current phase |
| `memory_context` | str | Injected context from past runs |

## MCP tool

```
chain_pipeline(task_description, context?, thread_id?)
```

Starts the Nitzotz pipeline in the background. Use `status(job_id)` to poll progress — messages include `[phase]` tags. The pipeline pauses for human approval in the review phase.

## Invariants

- Implementation phase requires `plan_approved = True` (enforced by guard node)
- Each phase has a max step limit (default 5, configurable)
- Critic quality threshold: 0.7 (below → loop, above → proceed)
- Human approval required before marking done

## Files

| File | Purpose |
|---|---|
| `graph_server/core/state.py` | Extended with Nitzotz fields |
| `graph_server/graphs/aril.py` | Parent graph with phase router |
| `graph_server/nodes/critic.py` | Phase-specific critic (validator + handoff) |
| `graph_server/core/guards.py` | Invariant enforcement functions |
| `graph_server/core/memory.py` | Persistent cross-run memory (SQLite) |
| `graph_server/subgraphs/research.py` | Research phase subgraph |
| `graph_server/subgraphs/planning.py` | Planning phase subgraph |
| `graph_server/subgraphs/implementation.py` | Implementation phase subgraph |
| `graph_server/subgraphs/review.py` | Review phase subgraph |
| `graph_server/server/mcp.py` | chain_pipeline tool + Nitzotz progress messages |

## Comparison with Option B

| | Option B (supervisor) | Genesis (Nitzotz pipeline) |
|---|---|---|
| **Routing** | Free-form LLM supervisor | Structured handoff_type values |
| **Flow** | Hub-and-spoke (flat) | Hierarchical (phase subgraphs) |
| **Quality gates** | Validator (optional) | Critic loops in every phase |
| **Safety** | Max 3 retries per node | plan_approved guard + step limits |
| **Memory** | None (checkpoints only) | Cross-run SQLite memory |
| **Flexibility** | High (can skip/reorder phases) | Lower (structured phase order) |
| **Predictability** | Lower (LLM decides everything) | Higher (bounded, auditable) |
