# Usage Guide — AI Orchestrator

How to use each feature from Cursor or Claude Code. All tools are called via MCP — type the command in the chat.

---

## Option A — CLI Server (Daily Driver)

Direct tools that bypass the graph. Fast, simple, no pipeline overhead.

### research

Deep exploration using Gemini CLI. Use when you need to understand a domain, evaluate options, or gather information before designing.

**Intent:** "I don't understand this well enough to plan yet."

```
research("How do rate limiting algorithms work? Compare token bucket vs sliding window vs fixed window")
```

```
research("What auth patterns does this codebase use?", context="Looking at src/orchestrator/")
```

### architect

Design and planning using Claude Code CLI. Reads your codebase, produces a structured plan with file paths, steps, and verification.

**Intent:** "I know what I want — design the solution."

```
architect("Add WebSocket support for real-time job status updates")
```

```
architect("Refactor the config system to support per-environment overrides", constraints="Must be backward compatible with existing config.yaml")
```

### classify

Fast task classification. Tells you which tier a task falls into and the recommended pipeline.

**Intent:** "Is this a research task, an architecture task, or a quick fix?"

```
classify("Fix the typo in the error message on line 42")
```

```
classify("Migrate from REST to GraphQL for the dashboard API")
```

---

## Option B — LangGraph Pipeline (Supervisor)

The hub-and-spoke supervisor graph. A central supervisor (Haiku) dynamically decides which node to call next. More flexible than ARIL but less structured.

### chain

Start the full supervisor pipeline. The supervisor decides the flow: research → architect → validate → human review → implement. Streams progress and pauses for human approval.

**Intent:** "Handle this task end-to-end. I'll approve before you implement."

```
chain("Add error recovery to the CLI subprocess runners")
```

```
chain("Implement cost tracking per API call", context="Track token usage for Anthropic and Google providers separately")
```

After starting, poll progress and approve:

```
status(job_id="abc123")
```

```
approve(job_id="abc123")
```

Or reject with feedback:

```
approve(job_id="abc123", feedback="Use per-request tracking, not per-session")
```

### history

View checkpoint history for a thread. See every supervisor decision, validation score, and state at each step.

**Intent:** "What happened in this pipeline run?"

```
history(thread_id="abc-def-123")
```

### rewind

Time-travel to a previous checkpoint and re-run from that point. Optionally change the task.

**Intent:** "That took a wrong turn at step 4 — go back and try differently."

```
rewind(thread_id="abc-def-123", checkpoint_id="ckpt-456")
```

```
rewind(thread_id="abc-def-123", checkpoint_id="ckpt-456", new_task="Same feature but use Redis instead of Memcached")
```

---

## Genesis — Nitzotz (formerly ARIL) (Phased Pipeline with Sefirot)

Nitzotz (The Divine Sparks) — the core pipeline within **Genesis** (formerly Malkuth), the unified autonomous system. A structured 4-phase pipeline with quality-gated progression, balanced forces (Sefirot), and persistent memory. More predictable and safer than Option B's free-form supervisor.

### chain_aril

Start the Nitzotz pipeline. Runs through four phases automatically, pausing for human approval in the review phase.

**Intent:** "Handle this complex task through a disciplined process — research it, design it, build it, then let me review."

```
chain_aril("Add rate limiting to the API endpoints")
```

```
chain_aril("Migrate the checkpoint storage from SQLite to PostgreSQL", context="Must support concurrent read/write from multiple server instances")
```

**What happens inside:**

| Phase | What runs | Sefirot forces |
|---|---|---|
| **Research** | Gemini CLI explores the domain → critic scores → loop if needed | — |
| **Planning** | Claude CLI designs the plan → **Gevurah** attacks the plan for flaws → critic scores → loop if needed | Restrictive |
| **Implementation** | Claude CLI implements → **Gevurah** attacks the code → **Chesed** proposes improvements → **Tiferet** arbitrates → **Hod** formats/lints | Full triad |
| **Review** | **Yesod** runs full test suite + pyright + git diff → human approval gate | Restrictive |

**Progress messages include phase tags:**

```
status(job_id="abc123")
```

You'll see output like:
```
[research] Research completed
[planning] Architect: plan ready
[planning] Gevurah: fail — 2 blockers, 1 warning — hallucinated file path in step 3
[planning] Architect: plan ready (revised)
[planning] Critic: scored 0.82 → plan_approved
[implementation] Guard: passed
[implementation] Implementation completed
[implementation] Gevurah: pass_with_warnings — 0 blockers, 2 warnings
[implementation] Chesed: proposed 2 improvements — add input validation; add tests
[implementation] Tiferet: 2 accepted, 0 rejected, needs_rework=false
[implementation] Hod: 3 files formatted, 1 lint fix
[review] Yesod: PASSED — pytest: 42 passed, pyright: 0 errors
Paused — waiting for human approval (ARIL review phase)
```

Then approve:

```
approve(job_id="abc123")
```

---

## Sefirot Nodes (Inside ARIL)

These run automatically inside ARIL's phases. You don't call them directly — they're wired into the subgraphs. But understanding what they do helps you interpret the progress messages.

### Gevurah — Adversarial Validator

**Where:** Planning phase (after architect), Implementation phase (after implement)

**What it does:** Actively tries to break the output. Doesn't ask "is this good?" — asks "how can I break this?" Produces a structured verdict with issues categorized as blocker/warning/note.

**Categories it checks:**
- Correctness — logic errors, missing edge cases
- Security — injection, unvalidated input, exposed secrets
- Hallucination — file paths or function names that don't exist
- Scope creep — changes not requested by the plan
- Breaking changes — modified interfaces without updating callers

**In progress output:** `Gevurah: fail — 2 blockers, 1 warning` or `Gevurah: pass_with_warnings`

### Chesed — Scope Expansion Proposer

**Where:** Implementation phase (after Gevurah)

**What it does:** Reads the implementation and proposes up to 3 improvements the plan didn't mention — missing error handling, tests that should accompany the changes, adjacent code with the same bug.

**Important:** Chesed does NOT implement. It proposes. Tiferet decides which proposals to accept.

**In progress output:** `Chesed: proposed 2 improvements — add input validation; add tests for new endpoint`

### Tiferet — Cross-Model Arbitrator

**Where:** Implementation phase (after Chesed)

**What it does:** Receives Gevurah's objections and Chesed's proposals. Decides what to accept and what to reject. Uses a different model from the one that built the code (no self-review). If accepted changes require rework, loops back to the implement node.

**Decision rules:**
- Gevurah blocker → always accept (must fix)
- Gevurah warning → accept if specific and real
- Chesed proposal → accept if within scope and clearly valuable
- Conflicting opinions → whoever cites specific files and consequences wins

**In progress output:** `Tiferet: 3 accepted, 1 rejected, needs_rework=true`

### Hod — Compliance Formatter

**Where:** Implementation phase (after Tiferet, before exit)

**What it does:** Runs `ruff format` and `ruff check --fix` on the codebase. Pure deterministic tooling — zero LLM cost. Enforces the repository's formatting and linting standards.

**In progress output:** `Hod: 3 files formatted, 1 lint fix`

### Netzach — Strategic Retry Engine

**Where:** Available in all phases (wired on failure paths)

**What it does:** When a node fails, Netzach analyzes the failure pattern and chooses a retry strategy instead of naively retrying with the same prompt:
- **retry** — append error feedback (attempt 1)
- **escalate** — switch to a more capable model (attempt 2, same error)
- **decompose** — break into smaller sub-tasks (attempt 3)
- **exit** — graceful exit with best partial result (max retries)

**In progress output:** `Netzach: architect attempt 2 → escalate — same hallucination error, need different model`

### Yesod — Integration Gate

**Where:** Review phase (before human approval)

**What it does:** Runs a comprehensive validation suite before the human even sees the output:
- Full test suite (`pytest`)
- Type checker (`pyright`)
- Git diff review — flags changes to sensitive files (.env, credentials, checkpoints.db)

All deterministic — no LLM calls. If Yesod fails, the pipeline routes back for fixes before bothering the human.

**In progress output:** `Yesod: PASSED — pytest: 42 passed, pyright: 0 errors, git diff: 5 files changed (clean)`

---

## Planned Features (Not Yet Implemented)

### Chayah (formerly Ouroboros) — Continuous Self-Improvement

**Intent:** "Improve this codebase autonomously toward the spec until there's nothing left to do."

```
# Future command
chain_ouroboros(spec="SPEC.md", max_cycles=50, budget=5.0)
```

Continuous loop: assess health → generate task from SPEC.md → execute via Nitzotz → validate → commit or revert → repeat until convergence.

### Nefesh (formerly Leviathan) — Parallel Swarm

**Intent:** "Fix all 30 of these problems at once."

```
# Future command
swarm("Fix all pyright errors in the codebase", budget=2.0, max_agents=8)
```

Central planner decomposes goal into N independent tasks with exclusive file ownership, fans out via Send(), merges results atomically.

### Klipah (formerly Fibonacci) — Graduated Parallel Dispatch

**Intent:** "Build this layered system — schema first, then APIs, then UI."

```
# Future command (extension of swarm)
swarm("Build REST API with auth and admin dashboard", budget=5.0, max_agents=10)
# Sovereign detects layered dependencies → uses Fibonacci dispatch automatically
```

When the Sovereign detects tasks with dependencies, it dispatches in graduated generations (1 → 1 → 2 → 3 → 5) instead of all at once, then consolidates in reverse.

### Ein Sof (formerly MUTHER) — Autonomous Meta-Orchestrator

**Intent:** "Run the whole system. You decide what to do."

```
# Future command
# Run as daemon: scripts/muther.sh
# Or via MCP: chain_muther(spec="SPEC.md", budget=10.0)
```

Monitors the repository, decides whether to spawn Chayah (steady improvement), Nefesh (batch fix), or Nitzotz (single task). Enforces immutable directives. Controls compute budgets. The "leave it running" system.

---

## Cursor Chat Commands

In Cursor, you don't need to type function calls. Just start your message with a keyword and Cursor routes it automatically. These are defined in `.cursor/rules/mcp-routing.mdc`.

### Implemented

| You type in chat | What Cursor calls | What it does |
|---|---|---|
| `aril add rate limiting to the API` | `chain_aril("add rate limiting to the API")` | Full Nitzotz + Sefirot pipeline |
| `graph refactor the auth module` | `chain("refactor the auth module")` | Option B supervisor pipeline |
| `research how do rate limiters work` | `research("how do rate limiters work")` | Gemini CLI exploration |
| `architect add WebSocket support` | `architect("add WebSocket support")` | Claude CLI design |
| `classify fix the typo on line 42` | `classify("fix the typo on line 42")` | Fast tier classification |
| `status` | `status()` | Show all running/paused jobs |
| `status abc123` | `status(job_id="abc123")` | Show specific job |
| `approve` | `approve(job_id="<latest>")` | Approve most recent paused job |
| `reject use Redis instead` | `approve(job_id="<latest>", feedback="use Redis instead")` | Reject with feedback |
| `history` | `history(thread_id="<latest>")` | Show checkpoint history |
| `rewind` | `rewind(thread_id, checkpoint_id)` | Time-travel to checkpoint |
| `health` | `health()` | Server status check |
| `gemini <anything>` | Routes to Gemini tool by intent | Research, explain, compare |
| `claude <anything>` | Routes to Claude tool by intent | Architect, implement, review, debug |

### Planned (not yet available)

| You type in chat | What it will do |
|---|---|
| `ouroboros start` | Start Chayah continuous evolution loop |
| `ouroboros stop` | Stop evolution loop gracefully |
| `leviathan fix all pyright errors` | Start Nefesh parallel swarm |
| `muther start` | Start Ein Sof meta-orchestrator |
| `muther stop` | Stop Ein Sof gracefully |

---

## Quick Reference (Function Call Syntax)

For direct MCP tool calls (Claude Code, MCP Inspector, or when Cursor routing doesn't trigger):

| Command | What it does | When to use |
|---|---|---|
| `research(question)` | Gemini CLI exploration | "I need to understand this first" |
| `architect(goal)` | Claude CLI design | "Design the solution" |
| `classify(task)` | Fast tier classification | "What kind of task is this?" |
| `chain(task)` | Option B supervisor pipeline | "Handle this with dynamic routing" |
| `chain_aril(task)` | Genesis (Nitzotz pipeline) + Sefirot | "Handle this with structured phases and quality gates" |
| `status(job_id)` | Poll job progress | "What's happening?" |
| `approve(job_id)` | Approve paused job | "Looks good, proceed" |
| `approve(job_id, feedback)` | Reject with feedback | "Change X before proceeding" |
| `history(thread_id)` | View checkpoint history | "What happened in this run?" |
| `rewind(thread_id, ckpt)` | Time-travel to checkpoint | "Go back and try differently" |
| `health()` | Server status check | "Is the server running?" |
