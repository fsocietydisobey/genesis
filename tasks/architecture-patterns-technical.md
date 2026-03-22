# Architecture Patterns — Technical Reference

**System name: Genesis** (formerly Malkuth) (technical designation TBD)

This document describes the execution patterns in the AI Orchestrator, their operational characteristics, and how they integrate into the Genesis system.

---

## System Overview

The orchestrator implements five complementary execution patterns, each optimized for a different workload profile. They compose hierarchically — higher-level patterns spawn and manage lower-level ones.

```mermaid
flowchart TB
    M["HVD<br/>Hypervisor Daemon"] -->|"forks"| O["CLR<br/>Closed-Loop Refiner"]
    M -->|"forks"| L["PDE<br/>Parallel Dispatch Engine"]
    M -->|"forks"| A["SPR-4<br/>Sequential Phase Runner"]

    O -->|"invokes"| A2["SPR-4<br/>task execution"]
    O -->|"invokes"| L2["PDE<br/>batch operations"]
    A2 -.->|"enhanced by"| S["TFB<br/>Tri-Force Balancer"]
    A -.->|"enhanced by"| S2["TFB<br/>Tri-Force Balancer"]
    L -.->|"dispatch mode"| F["PDE-F<br/>Fibonacci Mode"]
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

| Designation | Full name | Execution model | Workload profile |
|---|---|---|---|
| **SPR-4** | Sequential Phase Runner (4-stage) | Serial pipeline with quality gates | Single complex task |
| **CLR** | Closed-Loop Refiner | Continuous assess-execute-validate cycle | Steady autonomous improvement |
| **PDE** | Parallel Dispatch Engine | Fan-out/fan-in with central merge | Batch independent operations |
| **TFB** | Tri-Force Balancer | Paired expansion/restriction node modules | Quality enhancement (applied to SPR-4) |
| **HVD** | Hypervisor Daemon | Process-level supervisor, spawns other patterns | Autonomous meta-orchestration |
| **PDE-F** | PDE Fibonacci Mode | Graduated generation-based dispatch within PDE | Layered dependent tasks, greenfield builds |

---

## 1. SPR-4 — Sequential Phase Runner (4-Stage)

### Operational Profile

A serial pipeline that processes a complex task through four quality-gated stages. Each stage runs an internal validation loop, advancing only when output quality exceeds threshold.

```mermaid
flowchart LR
    Goal["Input<br/>task specification"] --> R["Stage 1: Search<br/>divergent exploration"]
    R --> P["Stage 2: Design<br/>convergent planning"]
    P --> I["Stage 3: Build<br/>code generation"]
    I --> V["Stage 4: Verify<br/>human approval gate"]
    V --> Done["Output<br/>committed artifact"]

    R -.->|"quality loop"| R
    P -.->|"quality loop"| P
    I -.->|"quality loop"| I
```

**Characteristics:**
- Four serial stages — each must pass before the next begins
- Internal quality loops — validator scores output, loops if below threshold (0.7)
- Structured inter-stage routing via explicit handoff signals
- Human approval gate required before final commit
- Bounded — configurable max iterations per stage prevent runaway execution

### Optimal workload

Single complex tasks requiring multi-phase processing. Tasks where output quality is more important than execution speed.

---

## 2. CLR — Closed-Loop Refiner

### Operational Profile

A continuous execution cycle that wraps SPR-4. Monitors system health metrics, generates tasks from a specification document, executes them, validates the delta, and persists or reverts based on objective fitness scoring.

```mermaid
flowchart TB
    Assess["Health Assessment<br/>test suite, type checker, linter"] --> Triage{Priority Classifier}
    Triage -->|"defect repair"| SPR["SPR-4<br/>(serial execution)"]
    Triage -->|"feature build"| SPR
    Triage -->|"batch remediation"| PDE["PDE<br/>(parallel execution)"]
    Triage -->|"no action required"| Stop["Convergence<br/>exit loop"]
    SPR --> Validate["Delta Validation<br/>score_after vs score_before"]
    PDE --> Validate
    Validate -->|"regression"| Revert["Rollback<br/>git revert"]
    Validate -->|"improvement"| Commit["Persist<br/>git commit"]
    Revert --> Assess
    Commit --> Assess
    Stop --> END
```

**Characteristics:**
- No terminal state — cycles until convergence, budget exhaustion, or operator interrupt
- Fitness function is read-only — the executing process cannot modify its own evaluation criteria
- Version control as checkpoint mechanism — all mutations committed before validation, reverted on regression
- Specification document is the sole task source — prevents unbounded scope generation
- Outer watchdog process handles runtime code modification (exit code 42 → process restart)

### Optimal workload

Sustained autonomous codebase improvement toward a defined target specification. Unattended long-running execution.

---

## 3. PDE — Parallel Dispatch Engine

### Operational Profile

A fan-out/fan-in execution engine. A central planner decomposes a goal into N independent, resource-disjoint tasks and dispatches them for concurrent execution. Results are merged and validated atomically.

```mermaid
flowchart TB
    Goal["Input<br/>'remediate 30 type errors'"] --> S["Task Decomposer<br/>partition into N work units"]
    S --> A1["Worker 1<br/>module auth"]
    S --> A2["Worker 2<br/>module models"]
    S --> A3["Worker 3<br/>module utils"]
    S --> AN["Worker N<br/>module routes"]
    A1 --> M["Result Aggregator<br/>combine + validate"]
    A2 --> M
    A3 --> M
    AN --> M
    M --> Test["Integration Test"]
    Test -->|"pass"| Commit["Persist"]
    Test -->|"fail"| Revert["Rollback ALL"]
```

**Characteristics:**
- Resource ownership is exclusive — no two workers modify the same file (v1, pessimistic concurrency)
- Budget-gated — max worker count, max estimated cost, per-worker timeout
- Atomic batch semantics — integration test failure reverts ALL worker outputs (no partial commits)
- Task decomposer does not execute — it partitions and dispatches only
- Diminishing throughput returns beyond ~8 concurrent workers on a single repository

### Optimal workload

High-volume independent remediation across disjoint files. Type error batches, lint fixes, test generation for untested modules, API migration across endpoints.

---

## 4. TFB — Tri-Force Balancer

### Operational Profile

Not a standalone execution engine. A set of paired node modules that enhance SPR-4's build and verify stages by introducing explicit generative/restrictive/synthetic force balancing.

```mermaid
flowchart TB
    subgraph Generative["Generative Pipeline (expansion)"]
        DS["Divergent Search Unit<br/>exploration + ideation"]
        SE["Scope Expansion Analyzer<br/>proposes improvements"]
        AR["Adaptive Retry Scheduler<br/>persistent re-attempt"]
    end

    subgraph Synthetic["Synthesis Pipeline (balance)"]
        GI["Goal Ingestion Module<br/>task specification"]
        CA["Cross-Model Arbitration Unit<br/>resolves expansion vs restriction"]
        IV["Integration Validation Gate<br/>final checkpoint"]
        PA["Production Artifact<br/>committed output"]
    end

    subgraph Restrictive["Restrictive Pipeline (contraction)"]
        CP["Convergent Planning Unit<br/>structural design"]
        ST["Adversarial Stress Tester<br/>finds failure modes"]
        CE["Compliance Enforcement Module<br/>formatting + linting"]
    end

    GI --> DS
    GI --> CP
    DS --> SE
    CP --> ST
    SE --> CA
    ST --> CA
    CA --> AR
    CA --> CE
    AR --> IV
    CE --> IV
    IV --> PA

    style Generative fill:#1a3a5c,stroke:#4a90d9,color:#fff
    style Synthetic fill:#1a3c1a,stroke:#48bb78,color:#fff
    style Restrictive fill:#3c1a1a,stroke:#e53e3e,color:#fff
    style GI fill:#ffd700,stroke:#b8860b,color:#000
    style PA fill:#9f7aea,stroke:#553c9a,color:#fff
```

**The three forces:**

| Force | Pipeline | Role | Failure mode if unchecked |
|---|---|---|---|
| **Generative** | Expansion | Creates, explores, proposes additions | Bloated output, hallucinated artifacts, scope creep |
| **Restrictive** | Contraction | Validates, rejects, enforces constraints | Analysis paralysis, nothing gets produced |
| **Synthetic** | Balance | Arbitrates between the two, produces final output | N/A — this IS the resolution mechanism |

**Node modules:**

| Module | Designation | Pipeline | Function |
|---|---|---|---|
| Goal Ingestion | GI | Synthetic | Receives task specification |
| Divergent Search | DS | Generative | Broad exploration, multiple approaches |
| Convergent Planner | CP | Restrictive | Structured design with constraints |
| Scope Expansion Analyzer | SE | Generative | Proposes improvements beyond spec (max 3) |
| Adversarial Stress Tester | ST | Restrictive | Actively finds failure modes, security issues, hallucinations |
| Cross-Model Arbitration | CA | Synthetic | Different model resolves expansion vs restriction |
| Adaptive Retry Scheduler | AR | Generative | Strategic retry with escalation on repeated failure |
| Compliance Enforcement | CE | Restrictive | Deterministic formatting, linting, documentation |
| Integration Validation Gate | IV | Synthetic | Full test suite + type check + diff review before commit |
| Production Artifact | PA | Synthetic | The committed, validated output |

**Characteristics:**
- Every generative module has a paired restrictive module
- No model evaluates its own output (cross-model arbitration enforces this)
- Each module is independently deployable — can be added to SPR-4 incrementally
- Not a standalone graph — wired into SPR-4's existing stage subgraphs

### Optimal workload

Always applicable. Should be applied to any pipeline where output quality is a primary concern. Start with the Adversarial Stress Tester (ST) and Cross-Model Arbitration (CA) — highest ROI modules.

---

## 5. HVD — Hypervisor Daemon

### Operational Profile

A process-level supervisor that monitors system state and forks the appropriate execution pattern. Does not execute tasks directly — manages the lifecycle of child processes that do.

```mermaid
flowchart TB
    subgraph HVD_S["HVD (Hypervisor Daemon)"]
        Monitor["State Monitor<br/>health metrics + spec progress"] --> Assess["Health Assessment"]
        Assess --> Dispatch{Pattern Selector}
        Dispatch -->|"sustained improvement"| O["Fork CLR"]
        Dispatch -->|"batch remediation"| L["Fork PDE"]
        Dispatch -->|"single task"| A["Fork SPR-4"]
        Dispatch -->|"no action"| Sleep["Resource Suspension"]
        O --> Check["Policy Enforcement<br/>Immutable Policy Set"]
        L --> Check
        A --> Check
        Check -->|"compliant"| Absorb["Absorb to Telemetry Store"]
        Check -->|"violation"| Purge["Rollback + re-fork"]
        Absorb --> Monitor
        Purge --> Monitor
    end
```

**Subsystems:**

| Subsystem | Function |
|---|---|
| **State Monitor** | Periodic health assessment (test results, type errors, spec progress) |
| **Pattern Selector** | Chooses CLR, PDE, or SPR-4 based on current state and workload profile |
| **Immutable Policy Set (IPS)** | Rules checked after every child process completes. Violations trigger rollback. Not modifiable by child processes. |
| **Unified Telemetry Store (UTS)** | SQLite database. All patterns write execution telemetry. HVD queries it when configuring child processes. |
| **Resource Suspension** | Budget tracking. Can throttle, suspend, or terminate child processes that exceed cost limits. |

**Child process lifecycle:**

```mermaid
stateDiagram-v2
    [*] --> Forking: dispatch decision
    Forking --> Active: process started
    Active --> Completed: process finished
    Active --> Throttled: low ROI
    Active --> Terminated: policy violation / budget
    Throttled --> Active: conditions improve
    Throttled --> Suspended: no progress
    Suspended --> Active: operator wake / event
    Completed --> PolicyCheck: IPS scan
    PolicyCheck --> Absorbed: compliant
    PolicyCheck --> Purged: violation
    Absorbed --> [*]
    Purged --> [*]
    Terminated --> [*]
```

**Characteristics:**
- Does not execute tasks — forks child processes that do
- Enforces immutable policies — checked post-execution, before results are committed
- Controls resource allocation — can throttle, suspend, or terminate children
- Maintains cross-process telemetry — all patterns contribute to and draw from one store
- Outer watchdog handles HVD's own runtime code modifications

### Optimal workload

Fully autonomous operation. The operator defines the spec, sets the budget, and walks away. HVD decides what to run, when, and for how long.

---

## 6. PDE-F — Graduated Fibonacci Dispatch

### Operational Profile

An extension to PDE's Task Decomposer that dispatches workers in graduated generations rather than all at once. When tasks have layered dependencies (Gen 2 needs Gen 1's outputs), flat dispatch fails because workers lack the context they need. PDE-F sorts tasks by dependency depth, dispatches one generation at a time, and merges each generation's results into state before dispatching the next.

After all generations complete, branches are consolidated in reverse order — the widest generation's outputs are merged in pairs, then those pairs merged again, spiraling back down to a single unified result.

```mermaid
flowchart TB
    subgraph G1["Gen 1 — 1 worker"]
        W1["schema"]
    end

    subgraph G2["Gen 2 — 1 worker"]
        W2["API core"]
    end

    subgraph G3["Gen 3 — 2 workers"]
        W3a["auth service"]
        W3b["user endpoints"]
    end

    subgraph G4["Gen 4 — 3 workers"]
        W4a["frontend"]
        W4b["payments"]
        W4c["admin"]
    end

    subgraph G5["Gen 5 — 5 workers"]
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

**Characteristics:**
- Generation width follows Fibonacci sequence: 1, 1, 2, 3, 5, 8...
- Each generation completes and merges before the next dispatches
- Workers in later generations receive previous generations' outputs as context
- Reverse consolidation merges branches with integration reviewers at each level
- Token budget scales proportionally: foundational work gets modest allocation, specialized work gets more
- Integrated into PDE's existing Sovereign — the Sovereign chooses flat or Fibonacci based on dependency analysis

**Dispatch mode selection:**

| Task manifest | Dispatch mode | Why |
|---|---|---|
| All tasks have empty `dependencies` | **Flat** (existing PDE) | No ordering needed, maximize parallelism |
| Some tasks depend on others | **Fibonacci** (PDE-F) | Must build foundation before parallelizing |

### Optimal workload

Greenfield builds with layered dependencies. Multi-service architectures where schema must exist before API, API before frontend, frontend before integration tests. Any task where premature parallelism would cause agents to hallucinate incompatible interfaces.

---

## Integration Architecture

### Interconnection Mechanisms

The five patterns connect through three distinct mechanisms at different levels of the process hierarchy:

```mermaid
flowchart TB
    subgraph L4["Layer 4: Process Supervisor"]
        M["HVD<br/>Hypervisor Daemon"]
    end

    subgraph L3["Layer 3: Execution Engines"]
        O["CLR<br/>Closed-Loop Refiner"]
        L["PDE<br/>Parallel Dispatch"]
        A["SPR-4<br/>Phase Runner"]
        F["PDE-F<br/>Fibonacci Mode"]
    end

    subgraph L2["Layer 2: Stage Subgraphs"]
        R["Stage 1: Search"]
        P["Stage 2: Design"]
        I["Stage 3: Build"]
        V["Stage 4: Verify"]
    end

    subgraph L1["Layer 1: Force-Balanced Modules"]
        GV["Stress Tester"]
        CH["Scope Analyzer"]
        TF["Arbitration Unit"]
        HD["Compliance Module"]
        NT["Retry Scheduler"]
        YS["Integration Gate"]
    end

    M -.->|"child process"| O
    M -.->|"child process"| L
    M -.->|"child process"| A

    O ==>|"embedded subgraph"| A
    O -.->|"direct invocation"| L
    L -.->|"dispatch mode"| F

    A ==>|"embedded subgraph"| R
    A ==>|"embedded subgraph"| P
    A ==>|"embedded subgraph"| I
    A ==>|"embedded subgraph"| V

    I ==>|"module wiring"| GV
    I ==>|"module wiring"| CH
    I ==>|"module wiring"| TF
    I ==>|"module wiring"| HD
    V ==>|"module wiring"| YS

    style L4 fill:#1a1a2e,stroke:#e94560,color:#fff
    style L3 fill:#0d1117,stroke:#58a6ff,color:#fff
    style L2 fill:#161b22,stroke:#8b949e,color:#fff
    style L1 fill:#21262d,stroke:#ffd700,color:#fff
```

### Mechanism 1: Module wiring (TFB → SPR-4 stages)

**Coupling:** Tight. Same state graph, same state schema, direct edges.

TFB modules are factory functions added to SPR-4's stage subgraphs via `graph.add_node()`. They participate in the stage's internal processing loop. No special integration infrastructure required.

### Mechanism 2: Subgraph embedding (SPR-4 stages, SPR-4 inside CLR)

**Coupling:** Moderate. Compiled graph added as a node. Shared state schema. Child blocks parent until completion.

A compiled state graph is registered as a node in a parent graph. The runtime handles state flow — the child receives the parent's state, executes its internal nodes, and returns state deltas. Both graphs must share the same state type. The child blocks the parent.

**Used for:** SPR-4's four stage subgraphs inside the SPR-4 parent. SPR-4 inside CLR (when the priority classifier routes to serial execution).

### Mechanism 3: Child process forking (HVD → all, CLR → PDE)

**Coupling:** Loose. Separate graphs, separate checkpoint stores. Spawned as async tasks. Monitored via job registry.

The parent starts a graph as a background async task and monitors it through the job infrastructure. The parent can poll status, throttle, suspend, or terminate children independently.

**Why not subgraph embedding?** The supervisor must:
- Run multiple children concurrently
- Monitor resource consumption asynchronously
- Terminate children that exceed budget
- Continue its own monitoring loop while children execute

Subgraph embedding blocks the parent, making all of this impossible.

**Used for:** HVD forking CLR, PDE, or SPR-4. CLR invoking PDE for batch operations.

### Inter-Pattern Data Flow

| From → To | Mechanism | Payload |
|---|---|---|
| TFB ↔ SPR-4 stages | Module wiring | Full state schema via graph runtime |
| SPR-4 stages ↔ SPR-4 parent | Subgraph embedding | Full state schema via graph runtime |
| SPR-4 ↔ CLR | Subgraph embedding | Full state schema via graph runtime |
| CLR → PDE | Direct invocation | Task specification + budget configuration |
| HVD → any pattern | Child process fork | Initial state + telemetry context injection |
| Any pattern → HVD | Process completion | Final state + health score delta |
| Cross-run | Unified Telemetry Store | Execution summaries, decisions, policy violations |

### Coupling Spectrum

```mermaid
flowchart LR
    subgraph Tight["Tight coupling"]
        NW["Module wiring<br/>TFB → SPR-4<br/>─────────────<br/>Same graph instance<br/>Direct edges<br/>Zero overhead<br/>Cannot terminate"]
    end

    subgraph Moderate["Moderate coupling"]
        SE["Subgraph embedding<br/>SPR-4 ↔ CLR<br/>─────────────<br/>Same state schema<br/>Child blocks parent<br/>Moderate overhead<br/>Cannot terminate"]
    end

    subgraph Loose["Loose coupling"]
        BJ["Child process fork<br/>HVD → all<br/>─────────────<br/>Separate checkpoints<br/>Async monitoring<br/>Full lifecycle mgmt<br/>Can terminate"]
    end

    Tight --> Moderate --> Loose

    style Tight fill:#276749,stroke:#48bb78,color:#fff
    style Moderate fill:#9c4221,stroke:#ed8936,color:#fff
    style Loose fill:#9b2c2c,stroke:#e53e3e,color:#fff
```

The higher in the process hierarchy, the looser the coupling. This is the correct design — the supervisor must be able to terminate children, CLR must manage PDE's budget, but SPR-4's stages just need to run in sequence.

---

## Complete System Topology

```mermaid
flowchart TB
    subgraph HVD_L["HVD (Hypervisor Daemon)"]
        MU["Monitor + Dispatch + Policy Enforcement"]
    end

    subgraph CLR_L["CLR (Closed-Loop Refiner)"]
        OL["assess → classify → execute → validate → loop"]
    end

    subgraph SPR_L["SPR-4 (Sequential Phase Runner)"]
        AL["Stage Router"]

        subgraph S1["Stage 1: Search"]
            RP["divergent search → quality gate → loop/advance"]
        end
        subgraph S2["Stage 2: Design"]
            PP["convergent design → quality gate → loop/advance"]
        end
        subgraph S3["Stage 3: Build (+ TFB modules)"]
            IP["guard → build → stress test → scope analyze → arbitrate → comply"]
        end
        subgraph S4["Stage 4: Verify (+ TFB modules)"]
            VP["integration gate → human approval → handoff"]
        end

        AL --> S1
        AL --> S2
        AL --> S3
        AL --> S4
    end

    subgraph PDE_L["PDE (Parallel Dispatch Engine)"]
        SV["task decomposer"] -->|"flat or fibonacci"| DM{dispatch mode}
        DM -->|"flat"| AG1["worker 1"] & AG2["worker 2"] & AGN["worker N"]
        DM -->|"fibonacci"| FG1["gen 1: 1"] --> FG2["gen 2: 1"] --> FG3["gen 3: 2"] --> FG4["gen 4: 3"]
        AG1 --> MG["result aggregator"]
        AG2 --> MG
        AGN --> MG
        FG4 --> FC["consolidation<br/>3 → 2 → 1"]
        FC --> MG
    end

    MU -.->|"child process"| CLR_L
    MU -.->|"child process"| PDE_L
    MU -.->|"child process"| SPR_L
    OL ==>|"embedded subgraph"| SPR_L
    OL -.->|"direct invocation"| PDE_L

    style HVD_L fill:#1a1a2e,stroke:#e94560,color:#fff
    style CLR_L fill:#0d3320,stroke:#48bb78,color:#fff
    style SPR_L fill:#0d1730,stroke:#4a90d9,color:#fff
    style PDE_L fill:#300d0d,stroke:#e53e3e,color:#fff
    style S3 fill:#21262d,stroke:#ffd700,color:#fff
    style S4 fill:#21262d,stroke:#ffd700,color:#fff
```

### Implementation Dependencies

```mermaid
flowchart LR
    A["SPR-4<br/>(implemented)"] --> S["TFB<br/>(enhances SPR-4)"]
    A --> O["CLR<br/>(wraps SPR-4)"]
    A --> L["PDE<br/>(parallel complement)"]
    S --> O2["Apply TFB to SPR-4"]
    O --> M["HVD<br/>(supervises all)"]
    L --> M
    L --> F["PDE-F<br/>(extends PDE)"]
```

1. **SPR-4** — implemented. The base execution engine.
2. **TFB** — next. Enhances SPR-4 stages with force-balanced modules. Independent of other patterns.
3. **CLR** — after TFB. Wraps SPR-4 in a continuous loop. Requires SPR-4 + fitness function.
4. **PDE** — parallel to CLR. Independent parallel dispatch. Requires SPR-4 for comparison.
5. **HVD** — after CLR + PDE. The unifying supervisor. Requires all other patterns.
6. **PDE-F** — after PDE. Graduated Fibonacci dispatch mode for dependency-aware parallel execution.
