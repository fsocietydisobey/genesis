# Architecture Patterns — Mythology, Philosophy, and Integration

The unified system is called **Genesis** (formerly Malkuth) — where intent becomes reality.

This document describes the architectural patterns in the AI Orchestrator, their mythological symbolism, how they work technically, and how they integrate into the Genesis system.

---

## The Pantheon

Each pattern is named for a Kabbalistic or philosophical concept that captures its core behavior. These aren't arbitrary names — the concepts describe the same structural dynamics the patterns implement.

```mermaid
flowchart TB
    M["Ein Sof<br/>The Infinite"] -->|"spawns"| O["Chayah<br/>evolution"]
    M -->|"spawns"| L["Nefesh<br/>parallel swarm"]
    M -->|"spawns"| A["Nitzotz<br/>phased pipeline"]

    O -->|"uses"| A2["Nitzotz<br/>per-task execution"]
    O -->|"uses"| L2["Nefesh<br/>batch operations"]
    A2 -.->|"enhanced by"| S["Sefirot<br/>balanced forces"]
    A -.->|"enhanced by"| S2["Sefirot<br/>balanced forces"]
    L -.->|"dispatch mode"| F["Klipah<br/>graduated fan-out"]
    L2 -.->|"dispatch mode"| F

    style M fill:#1a1a2e,stroke:#e94560,color:#fff
    style O fill:#48bb78,stroke:#276749,color:#fff
    style L fill:#e53e3e,stroke:#9b2c2c,color:#fff
    style A fill:#4a90d9,stroke:#2c5282,color:#fff
    style A2 fill:#4a90d9,stroke:#2c5282,color:#fff
    style L2 fill:#e53e3e,stroke:#9b2c2c,color:#fff
    style S fill:#ffd700,stroke:#b8860b,color:#000
    style S2 fill:#ffd700,stroke:#b8860b,color:#000
    style F fill:#9f7aea,stroke:#553c9a,color:#fff
```

| Pattern | Named for | Core idea | Task docs |
|---|---|---|---|
| **Nitzotz** (formerly ARIL) | The Divine Sparks — gather and assemble | Sequential phases with critic loops | `tasks/aril/` |
| **Chayah** (formerly Ouroboros) | The Living Soul | Continuous self-improvement loop | `tasks/ouroboros/` |
| **Nefesh** (formerly Leviathan) | The Animal Soul | Parallel swarm with central merge | `tasks/leviathan/` |
| **Sefirot** | Kabbalistic Tree of Life | Balanced expansion/restriction forces | `tasks/sefirot/` |
| **Ein Sof** (formerly MUTHER) | The Infinite | Meta-orchestrator, Graph of Graphs | `tasks/muther/` |
| **Klipah** (formerly Fibonacci) | The Shells/Husks | Graduated parallel dispatch — scales concurrency with foundation | `tasks/fibonacci/` |

---

## 1. Nitzotz — The Divine Sparks

**Formerly: Autonomous Research & Implementation Lab (ARIL)**

### Symbolism

Nitzotz represents the divine sparks scattered through creation — fragments of light that must be gathered, refined, and assembled into a unified whole. In this architecture, a complex task is broken into phases, each gathering and refining a spark of understanding. The scientist (agent) follows a methodology: observe (research), hypothesize (plan), experiment (implement), peer review (review). Nothing leaves the lab without passing inspection.

### What it does

A phased pipeline with hierarchical subgraphs. A high-level goal enters and flows through four phases, each containing a critic loop that ensures quality before advancing:

```mermaid
flowchart LR
    Goal["Goal"] --> R["Research<br/>Gemini CLI"]
    R --> P["Planning<br/>Claude CLI"]
    P --> I["Implementation<br/>Claude CLI"]
    I --> V["Review<br/>Human approval"]
    V --> Done["Done"]

    R -.->|"critic loop"| R
    P -.->|"critic loop"| P
    I -.->|"critic loop"| I
```

**Key properties:**
- Sequential phases — each must complete before the next begins
- Critic loops — quality-gated progression within each phase
- Structured handoffs — explicit `handoff_type` values drive routing
- Human approval required before marking done
- Bounded — max steps per phase prevent infinite loops

### When to use

Single complex tasks that need research, design, and careful implementation. "Add OAuth to the app." "Migrate the database schema." Tasks where the process matters as much as the outcome.

---

## 2. Chayah — The Living Soul

**Formerly: Ouroboros — The Self-Devouring Serpent**

### Symbolism

Chayah is the Living Soul in Kabbalistic tradition — the highest level of soul that connects to the divine will, representing the animating life force that drives continuous renewal and transformation. Unlike the static lower soul levels, Chayah is always in motion, always seeking to elevate and refine.

In this architecture, the agent embodies this living force — continuously assessing its codebase (perceiving), transforming what's broken (healing), creating new functionality (manifesting), and cycling endlessly. The output of each cycle becomes the input of the next. The codebase is simultaneously the thing being perceived and the thing being transformed.

Chayah is also self-contained — it doesn't need external input once started. It reads its own health, generates its own tasks, and judges its own results. It is autonomous in the purest sense: a living soul that sustains itself until equilibrium is reached.

### What it does

A continuous evolution loop that wraps Nitzotz. It assesses the codebase health, generates a task (from a product spec and fitness function), executes it via Nitzotz, validates the result, commits or reverts, and loops:

```mermaid
flowchart TB
    Assess["Assess<br/>run tests, lint, pyright"] --> Triage{Triage}
    Triage -->|"fix"| Nitzotz["Nitzotz<br/>(execute task)"]
    Triage -->|"feature"| Nitzotz
    Triage -->|"batch fix"| Nefesh["Nefesh<br/>(parallel swarm)"]
    Triage -->|"idle"| Stop["Converged"]
    Nitzotz --> Validate["Validate<br/>score before vs after"]
    Nefesh --> Validate
    Validate -->|"worse"| Revert["git revert"]
    Validate -->|"better"| Commit["git commit"]
    Revert --> Assess
    Commit --> Assess
    Stop --> END
```

**Key properties:**
- No natural end state — runs until convergence, budget exhaustion, or human intervention
- Fitness function is immutable — the agent cannot game its own evaluation
- Git is the safety net — every change is committed before validation, reverted if score drops
- The spec is the only source of features — no hallucinated goals
- Outer daemon handles self-modification (exit code 42 → restart with new code)

### When to use

Steady, autonomous improvement of a codebase toward a defined spec. Leave it running overnight. Let it fix all the pyright errors, add missing tests, and implement stretch goals one by one.

---

## 3. Nefesh — The Animal Soul

**Formerly: Leviathan — The Beast of Many Tentacles**

### Symbolism

Nefesh is the Animal Soul in Kabbalistic tradition — the vital, instinctive force that animates physical action. Unlike the higher soul levels that deliberate and plan, Nefesh acts with immediate, coordinated physicality — many limbs working in concert under a single animating will.

In this architecture, Nefesh is a central intelligence (the Sovereign) that commands many agents simultaneously. Where Chayah is a single living force working alone, Nefesh is many agents reaching into the codebase at once. Each agent handles one task, but they all serve the Sovereign's unified plan.

Nefesh's power is breadth — it touches everything at once. Its weakness is coordination — if the agents clash, chaos follows. The Sovereign's job is to ensure they don't, by giving each agent exclusive territory (file ownership).

### What it does

A parallel swarm execution engine. A Sovereign planner decomposes a large goal into N independent, file-disjoint tasks and dispatches them concurrently via LangGraph's `Send()` API:

```mermaid
flowchart TB
    Goal["Goal<br/>'fix all 30 pyright errors'"] --> S["Sovereign<br/>decompose into N tasks"]
    S --> A1["Agent 1<br/>fix auth.py"]
    S --> A2["Agent 2<br/>fix models.py"]
    S --> A3["Agent 3<br/>fix utils.py"]
    S --> AN["Agent N<br/>fix routes.py"]
    A1 --> M["Merge<br/>combine + validate"]
    A2 --> M
    A3 --> M
    AN --> M
    M --> Test["Run tests"]
    Test -->|"pass"| Commit
    Test -->|"fail"| Revert
```

**Key properties:**
- File ownership is exclusive — no two agents modify the same file (v1)
- Budget-gated — max agents, max cost, per-agent timeout
- Atomic batch — if tests fail after merge, ALL changes revert (no partial success)
- The Sovereign doesn't implement — it decomposes and dispatches
- Diminishing returns past ~8 parallel agents on a single repo

### When to use

Batch operations on many independent files. "Fix all 30 pyright errors." "Add unit tests for 10 untested modules." "Migrate all API endpoints from v1 to v2." Tasks where the work is wide (many files) but shallow (each change is simple).

---

## 4. Sefirot — The Tree of Life

### Symbolism

The Sefirot are the ten emanations of the Kabbalistic Tree of Life — the structure through which the infinite divine will descends into finite physical reality. They are arranged in three pillars:

- **Pillar of Mercy (Expansion)** — creative, generative, unbounded force
- **Pillar of Severity (Restriction)** — critical, limiting, corrective force
- **Central Pillar (Balance)** — synthesis that harmonizes the two opposing forces

The Tree teaches that creation requires both forces in tension. Pure expansion (Chesed/Mercy) without restriction produces chaos — bloated, hallucinated code. Pure restriction (Gevurah/Severity) without expansion produces nothing — every output is rejected. Only through Tiferet (Beauty/Harmony) — the synthesis of both — does creation manifest properly.

This maps directly to the fundamental problem in agent systems: **how do you balance creative generation with quality enforcement?** A passive critic (score and gate) isn't enough. You need active opposing forces that argue, and a synthesizer that resolves their tension.

### The Sefirot mapped to agents

```mermaid
flowchart TB
    subgraph Expansion["Pillar of Expansion (creative)"]
        Ch["Chokhmah (Wisdom)<br/>Research / Ideation<br/>Gemini CLI"]
        Cs["Chesed (Mercy)<br/>Builder / Implement<br/>scope expansion"]
        Nt["Netzach (Endurance)<br/>Strategic Retry<br/>refuses to give up"]
    end

    subgraph Balance["Central Pillar (synthesis)"]
        Kt["Keter (Crown)<br/>User's intent<br/>the goal itself"]
        Tf["Tiferet (Beauty)<br/>Code Review<br/>cross-model arbitration"]
        Ys["Yesod (Foundation)<br/>Integration Gate<br/>final checkpoint"]
        Mk["Malkuth (Kingdom)<br/>Running Code<br/>committed codebase"]
    end

    subgraph Restriction["Pillar of Restriction (critical)"]
        Bn["Binah (Understanding)<br/>Architect / Structure<br/>Claude CLI"]
        Gv["Gevurah (Severity)<br/>Adversarial Critic<br/>tries to break the code"]
        Hd["Hod (Submission)<br/>Format / Lint / Docs<br/>enforces repo laws"]
    end

    Kt --> Ch
    Kt --> Bn
    Ch --> Cs
    Bn --> Gv
    Cs --> Tf
    Gv --> Tf
    Tf --> Nt
    Tf --> Hd
    Nt --> Ys
    Hd --> Ys
    Ys --> Mk

    style Expansion fill:#1a3a5c,stroke:#4a90d9,color:#fff
    style Balance fill:#1a3c1a,stroke:#48bb78,color:#fff
    style Restriction fill:#3c1a1a,stroke:#e53e3e,color:#fff
    style Kt fill:#ffd700,stroke:#b8860b,color:#000
    style Mk fill:#9f7aea,stroke:#553c9a,color:#fff
```

### What it does

Sefirot is not a graph — it's a **design philosophy** expressed as individual node factories that enhance Nitzotz's subgraphs. The core contribution is splitting the implementation phase into three active forces:

1. **Chesed (Builder)** — implements the plan AND proposes improvements beyond it
2. **Gevurah (Critic)** — doesn't just score output, actively tries to break it
3. **Tiferet (Reviewer)** — uses a different model to arbitrate between the two

Plus three process nodes:
4. **Hod (Formatter)** — deterministic formatting, linting, documentation
5. **Netzach (Retry Engine)** — strategic retry that escalates approach on repeated failure
6. **Yesod (Integration Gate)** — comprehensive validation before commit

**Key properties:**
- Every creative action has a paired restrictive action
- No model judges its own output (cross-model review)
- Applied incrementally — each node is independently valuable
- Not a separate graph — wired into Nitzotz's existing subgraphs

### When to use

Always. Sefirot principles should be applied to any agent pipeline where quality matters. Start with Gevurah (adversarial critic) and Tiferet (cross-model review) — they provide the most value.

---

## 5. Ein Sof — The Infinite

**Formerly: MUTHER — The Primordial Mainframe**

### Symbolism

Ein Sof is the Kabbalistic concept of the Infinite — the boundless, limitless divine essence that exists before and beyond all emanation. Ein Sof is not one of the Sefirot; it is the source from which all Sefirot flow. It doesn't create directly — it is the womb of creation itself, the primordial ocean from which all forms emerge.

In this architecture, Ein Sof doesn't explore, plan, or implement. It is the omniscient operating system that everything else runs on. It monitors the repository, decides what kind of entity needs to be born, spawns it, watches it work, enforces its directives, and absorbs the results when it's done. It doesn't write code — it decides who writes code.

### What it does

A meta-orchestrator — a Graph of Graphs. Ein Sof monitors the repository state and spawns the right pattern:

```mermaid
flowchart TB
    subgraph EinSof["Ein Sof (The Infinite)"]
        Monitor["Monitor<br/>watch repository"] --> Assess["Assess<br/>health + spec"]
        Assess --> Dispatch{Dispatch}
        Dispatch -->|"evolution"| O["Spawn Chayah"]
        Dispatch -->|"batch crisis"| L["Spawn Nefesh"]
        Dispatch -->|"single task"| A["Spawn Nitzotz"]
        Dispatch -->|"nothing needed"| Sleep["Cryosleep"]
        O --> Check["Directive check"]
        L --> Check
        A --> Check
        Check -->|"clean"| Absorb["Absorb into memory"]
        Check -->|"violation"| Purge["Revert + restart"]
        Absorb --> Monitor
        Purge --> Monitor
    end
```

**Key properties:**
- Doesn't write code — spawns entities that do
- Enforces immutable directives — checked after every entity completes
- Controls compute budget (Cryosleep) — can throttle, hibernate, or kill entities
- Maintains unified memory (The Ocean) — all patterns contribute to and draw from one store
- Outer daemon handles self-modification restarts

### When to use

When you want fully autonomous operation. Ein Sof is the "leave it running" system — it decides what needs to happen, picks the right tool, and manages the execution. It's the capstone that makes the other patterns self-directing.

---

## 6. Klipah — The Shells

**Formerly: Fibonacci — The Golden Spiral**

### Symbolism

Klipah (plural: Klipot) are the shells or husks in Kabbalistic tradition — the outer layers that contain and constrain the divine light. Each shell must be formed before the light within it can be revealed. The husks are not evil — they are necessary structure. Without shells, the light disperses and cannot be used. Creation requires containment before expansion.

In this architecture, Klipah describes how concurrency should scale. You don't throw 10 agents at an empty repo — you start with one architect, then one foundation builder, then two core services, then three features, then five polish tasks. Each generation's width is bounded by the structural integrity of the previous. The shells form layer by layer, each containing the light of the previous before the next can be created.

The reverse spiral (consolidation) mirrors the breaking of shells — the specialized parts merge back into a unified whole, each merge step combining fewer, larger pieces until the full light is revealed.

### What it does

A graduated dispatch mode inside Nefesh. Instead of fanning out all agents at once, Klipah dispatches in generations that follow the Fibonacci sequence:

```mermaid
flowchart TB
    subgraph G1["Gen 1 — 1 agent"]
        W1["schema"]
    end

    subgraph G2["Gen 2 — 1 agent"]
        W2["API core"]
    end

    subgraph G3["Gen 3 — 2 agents"]
        W3a["auth service"]
        W3b["user endpoints"]
    end

    subgraph G4["Gen 4 — 3 agents"]
        W4a["frontend"]
        W4b["payments"]
        W4c["admin"]
    end

    subgraph G5["Gen 5 — 5 agents"]
        W5a["cart"]
        W5b["search"]
        W5c["email"]
        W5d["inventory"]
        W5e["reports"]
    end

    W1 --> W2
    W2 --> W3a
    W2 --> W3b
    W3a --> W4a
    W3a --> W4b
    W3b --> W4c
    W4a --> W5a
    W4a --> W5b
    W4b --> W5c
    W4c --> W5d
    W4c --> W5e

    subgraph Consolidation["Reverse consolidation"]
        R3["3 reviewers merge pairs"]
        R2["2 reviewers merge"]
        R1["1 final reviewer"]
        R1 --> Done["Validated merge"]
    end

    W5a --> R3
    W5b --> R3
    W5c --> R3
    W5d --> R3
    W5e --> R3
    R3 --> R2 --> R1

    style G1 fill:#ffd700,stroke:#b8860b,color:#000
    style G2 fill:#ffd700,stroke:#b8860b,color:#000
    style G3 fill:#4a90d9,stroke:#2c5282,color:#fff
    style G4 fill:#48bb78,stroke:#276749,color:#fff
    style G5 fill:#e53e3e,stroke:#9b2c2c,color:#fff
    style Consolidation fill:#1a3c1a,stroke:#48bb78,color:#fff
```

**How it works with Nefesh:**

Nefesh's Sovereign already decomposes goals into tasks with a `dependencies` field. Klipah reads those dependencies, sorts tasks into layers by depth, and dispatches one layer at a time. If all tasks are independent → flat dispatch (existing Nefesh). If tasks have layered dependencies → Klipah dispatch.

**Key properties:**
- Concurrency scales with foundation — no premature parallelism
- Each generation can reference previous generations' outputs
- Reverse consolidation merges branches back down with integration reviewers
- Token budgets scale with generation (Fibonacci proportional allocation)
- Not a separate graph — a dispatch mode inside Nefesh

### When to use

Greenfield builds with layered dependencies. "Build a full-stack app." "Implement a microservice architecture." Tasks where the work has a natural dependency structure — schema before API, API before frontend, frontend before polish.

---

## Integration Architecture

### The Three Integration Mechanisms

Not everything is a subgraph of everything else. The patterns connect through three distinct mechanisms, each appropriate for different coupling needs:

```mermaid
flowchart TB
    subgraph L4["Layer 4: Process level"]
        M["Ein Sof<br/>supervisor process"]
    end

    subgraph L3["Layer 3: Graph level"]
        O["Chayah"]
        L["Nefesh"]
        A["Nitzotz"]
        F["Klipah<br/>(Nefesh mode)"]
    end

    subgraph L2["Layer 2: Subgraph level"]
        R["research_phase"]
        P["planning_phase"]
        I["implementation_phase"]
        V["review_phase"]
    end

    subgraph L1["Layer 1: Node level"]
        GV["Gevurah"]
        CH["Chesed"]
        TF["Tiferet"]
        HD["Hod"]
        NT["Netzach"]
        YS["Yesod"]
    end

    M -.->|"background jobs"| O
    M -.->|"background jobs"| L
    M -.->|"background jobs"| A

    O ==>|"subgraph embed"| A
    O -.->|"direct invoke"| L
    L -.->|"dispatch mode"| F

    A ==>|"subgraph embed"| R
    A ==>|"subgraph embed"| P
    A ==>|"subgraph embed"| I
    A ==>|"subgraph embed"| V

    I ==>|"nodes wired in"| GV
    I ==>|"nodes wired in"| CH
    I ==>|"nodes wired in"| TF
    I ==>|"nodes wired in"| HD
    V ==>|"nodes wired in"| YS

    style L4 fill:#1a1a2e,stroke:#e94560,color:#fff
    style L3 fill:#0d1117,stroke:#58a6ff,color:#fff
    style L2 fill:#161b22,stroke:#8b949e,color:#fff
    style L1 fill:#21262d,stroke:#ffd700,color:#fff
```

### Mechanism 1: Node wiring (Sefirot → Nitzotz subgraphs)

**Coupling:** Tight. Same StateGraph, same state type, direct edges.

Sefirot nodes are factory functions (`build_gevurah_node()`, etc.) added to Nitzotz's subgraph StateGraphs with `graph.add_node()`. They participate in the subgraph's internal loop:

```python
# Inside implementation subgraph
graph.add_node("implement", implement_node)     # Chesed role (builder)
graph.add_node("gevurah", gevurah_node)          # adversarial critic
graph.add_node("chesed", chesed_propose_node)    # scope expansion
graph.add_node("tiferet", tiferet_node)          # cross-model arbitration
graph.add_node("hod", hod_node)                  # format + lint

graph.add_edge("implement", "gevurah")
graph.add_edge("gevurah", "chesed")
graph.add_edge("chesed", "tiferet")
graph.add_edge("tiferet", "hod")
# tiferet decides: loop back to implement, or exit
```

No special integration needed. They're just nodes.

### Mechanism 2: Subgraph embedding (Nitzotz phases, Nitzotz inside Chayah)

**Coupling:** Moderate. Compiled graph added as a node. Shared state type. Child blocks parent until complete.

A compiled StateGraph is added as a node in a parent graph. LangGraph handles state flow — the child receives the parent's state, runs all its internal nodes, and returns state updates:

```python
# Nitzotz parent graph
research_phase = build_research_subgraph(model).compile()
parent.add_node("research_phase", research_phase)  # subgraph as node

# Chayah graph
aril_graph = build_aril_graph(config)  # compiled, no checkpointer
ouroboros.add_node("execute_aril", aril_graph)     # Nitzotz as subgraph node
```

**Constraint:** Both graphs must use the same state type (`OrchestratorState`). The child graph blocks the parent — the parent waits for the child to complete before continuing. You cannot kill or throttle a subgraph mid-execution.

**Used for:**
- Nitzotz's four phase subgraphs inside the Nitzotz parent graph
- Nitzotz inside Chayah (when triage chooses a single complex task)

### Mechanism 3: Background jobs (Ein Sof → everything, Chayah → Nefesh)

**Coupling:** Loose. Separate graphs, separate checkpointers. Spawned as asyncio tasks. Monitored via job system.

The parent starts a graph as a background asyncio task and monitors it through the existing job infrastructure (`create_job()`, `get_job()`, `format_job_status()`):

```python
# Ein Sof spawning an entity
async def spawn_entity(state):
    pattern = state["dispatch_decision"]["pattern"]

    if pattern == "ouroboros":
        graph, cp = await build_ouroboros_graph(config)
    elif pattern == "leviathan":
        graph, cp = await build_leviathan_graph(config)
    elif pattern == "aril":
        graph, cp = await build_aril_graph(config)

    job = create_job()
    job._task = asyncio.create_task(run_graph(graph, state, job))
    return {"active_entities": [...]}
```

**Why not subgraph embedding here?** Because Ein Sof needs to:
- Run multiple entities concurrently
- Monitor cost and progress asynchronously
- Kill or hibernate entities that are burning tokens
- Continue its own assessment loop while entities run

You can't do any of this with subgraph embedding (which blocks the parent).

**Used for:**
- Ein Sof spawning Chayah, Nefesh, or Nitzotz
- Chayah invoking Nefesh for batch operations (Nefesh's `Send()` fan-out needs to be the top-level pattern)

### Communication between patterns

| From → To | Mechanism | What flows |
|---|---|---|
| Sefirot ↔ Nitzotz subgraphs | Node wiring (edges) | Full `OrchestratorState` via LangGraph |
| Nitzotz phases ↔ Nitzotz parent | Subgraph embedding | Full `OrchestratorState` via LangGraph |
| Nitzotz ↔ Chayah | Subgraph embedding | Full `OrchestratorState` via LangGraph |
| Chayah → Nefesh | Direct `ainvoke()` | Task description + budget config |
| Ein Sof → any pattern | Background job | Initial state + injected memory context |
| Any pattern → Ein Sof | Job completion | Final state + health score delta |
| Across all runs | SQLite memory (The Ocean) | Summaries, decisions, violations, outcomes |

### Why the coupling varies

```mermaid
flowchart LR
    subgraph Tight["Tight coupling"]
        NW["Node wiring<br/>Sefirot → Nitzotz<br/>─────────────<br/>Same graph<br/>Direct edges<br/>No overhead<br/>Can't kill"]
    end

    subgraph Moderate["Moderate coupling"]
        SE["Subgraph embedding<br/>Nitzotz ↔ Chayah<br/>─────────────<br/>Same state type<br/>Child blocks parent<br/>Moderate overhead<br/>Can't kill"]
    end

    subgraph Loose["Loose coupling"]
        BJ["Background jobs<br/>Ein Sof → all<br/>─────────────<br/>Different checkpointers<br/>Async, monitored<br/>Full job lifecycle<br/>Can kill/throttle"]
    end

    Tight --> Moderate --> Loose

    style Tight fill:#276749,stroke:#48bb78,color:#fff
    style Moderate fill:#9c4221,stroke:#ed8936,color:#fff
    style Loose fill:#9b2c2c,stroke:#e53e3e,color:#fff
```

The higher in the hierarchy, the looser the coupling. This is the right design because Ein Sof needs to kill things, Chayah needs to manage Nefesh's budget, but Nitzotz's subgraphs just need to run in sequence.

---

## The Full Stack

When everything is implemented, the complete system looks like:

```mermaid
flowchart TB
    subgraph EinSof_L["Ein Sof (scripts/muther.sh)"]
        MU["Monitor + Dispatch + Directives"]
    end

    subgraph Chayah_L["Chayah (graphs/ouroboros.py)"]
        OL["assess → triage → execute → validate → loop"]
    end

    subgraph Nitzotz_L["Nitzotz (graphs/aril.py)"]
        AL["phase_router"]

        subgraph Research["research_phase"]
            RP["research → critic → loop/exit"]
        end
        subgraph Planning["planning_phase"]
            PP["architect → critic → loop/exit"]
        end
        subgraph Implementation["implementation_phase (+ Sefirot)"]
            IP["guard → implement → gevurah → chesed → tiferet → hod"]
        end
        subgraph Review["review_phase (+ Sefirot)"]
            VP["yesod → human_review → set_handoff"]
        end

        AL --> Research
        AL --> Planning
        AL --> Implementation
        AL --> Review
    end

    subgraph Nefesh_L["Nefesh (graphs/leviathan.py)"]
        SV["sovereign"] -->|"flat or klipah"| DM{dispatch mode}
        DM -->|"flat"| AG1["agent 1"] & AG2["agent 2"] & AGN["agent N"]
        DM -->|"klipah"| FG1["gen 1: 1"] --> FG2["gen 2: 1"] --> FG3["gen 3: 2"] --> FG4["gen 4: 3"]
        AG1 --> MG["merge + validate"]
        AG2 --> MG
        AGN --> MG
        FG4 --> FC["consolidation<br/>3 → 2 → 1"]
        FC --> MG
    end

    MU -.->|"background job"| Chayah_L
    MU -.->|"background job"| Nefesh_L
    MU -.->|"background job"| Nitzotz_L
    OL ==>|"subgraph embed"| Nitzotz_L
    OL -.->|"direct invoke"| Nefesh_L

    style EinSof_L fill:#1a1a2e,stroke:#e94560,color:#fff
    style Chayah_L fill:#0d3320,stroke:#48bb78,color:#fff
    style Nitzotz_L fill:#0d1730,stroke:#4a90d9,color:#fff
    style Nefesh_L fill:#300d0d,stroke:#e53e3e,color:#fff
    style Implementation fill:#21262d,stroke:#ffd700,color:#fff
    style Review fill:#21262d,stroke:#ffd700,color:#fff
```

### Implementation order

```mermaid
flowchart LR
    A["Nitzotz<br/>(implemented ✓)"] --> S["Sefirot<br/>(enhances Nitzotz)"]
    A --> O["Chayah<br/>(wraps Nitzotz)"]
    A --> L["Nefesh<br/>(parallel complement)"]
    S --> O2["Apply Sefirot to Nitzotz"]
    O --> M["Ein Sof<br/>(spawns all)"]
    L --> M
    L --> F["Klipah<br/>(extends Nefesh)"]
```

1. **Nitzotz** — implemented. The execution engine everything else builds on.
2. **Sefirot** — next. Enhances Nitzotz's subgraphs with balanced forces. Independent of other patterns.
3. **Chayah** — after Sefirot. Wraps Nitzotz in a continuous loop. Needs Nitzotz + fitness function.
4. **Nefesh** — parallel to Chayah. Independent parallel swarm. Needs Nitzotz for comparison.
5. **Ein Sof** — after Chayah + Nefesh. The capstone that unifies everything. Needs all other patterns.
6. **Klipah** — after Nefesh. Extends Nefesh's Sovereign with graduated, dependency-aware dispatch.
