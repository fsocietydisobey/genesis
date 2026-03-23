# Genesis — Command Reference

**Genesis** (formerly Malkuth) is the autonomous engineering system. It encompasses all execution patterns: Nitzotz (formerly ARIL), Sefirot, Chayah (formerly Ouroboros), Nefesh (formerly Leviathan), Klipah (formerly Fibonacci), and Ein Sof (formerly MUTHER).

This doc lists every command you can use from Cursor chat, what it triggers, and what to expect.

---

## Quick Reference

| You type | What triggers | Pattern |
|---|---|---|
| `pipeline <task>` | `chain_pipeline(task)` | Pipeline + Balanced forces |
| `graph <task>` | `chain(task)` | Supervisor (Option B) |
| `research <question>` | `research(question)` | Direct Gemini CLI |
| `architect <goal>` | `architect(goal)` | Direct Claude CLI |
| `classify <task>` | `classify(task)` | Fast classification |
| `status` | `status()` | Show all jobs |
| `status <job_id>` | `status(job_id)` | Show specific job |
| `approve` | `approve(job_id)` | Approve paused job |
| `reject <feedback>` | `approve(job_id, feedback)` | Reject with feedback |
| `history` | `history(thread_id)` | Show checkpoints |
| `rewind` | `rewind(thread_id, ckpt)` | Time-travel |
| `health` | `health()` | Server status |

---

## Nitzotz — Phased Pipeline

The core execution engine. Four phases with quality-gated progression.

### Commands

**Start a pipeline:**
```
pipeline add rate limiting to the API endpoints
```

```
pipeline migrate the database from SQLite to PostgreSQL
```

```
pipeline add WebSocket support for real-time notifications, must work with existing FastAPI backend
```

**What happens:**
1. Research phase — Gemini explores the domain
2. Planning phase — Claude designs the architecture
3. Implementation phase — Claude implements the plan
4. Review phase — integration tests + human approval

**What to expect in status output:**
```
[research] Research completed
[planning] Architect: plan ready
[planning] Critic: scored 0.85 → plan_approved
[implementation] Implementation completed
[review] Yesod: PASSED
Paused — waiting for human approval
```

**After it pauses:**
```
approve
```
or
```
reject use a different rate limiting algorithm, token bucket instead of sliding window
```

---

## Sefirot — Balanced Forces (Inside Nitzotz)

Sefirot nodes run automatically inside Nitzotz's phases. You don't trigger them separately — they're part of the pipeline. But you'll see them in progress output.

### What you'll see

**Gevurah (adversarial critic) — attacks the output:**
```
[planning] Gevurah: fail — 2 blockers, 1 warning — hallucinated file path in step 3
[implementation] Gevurah: pass_with_warnings — 0 blockers, 2 warnings
```

Blockers force rework. Warnings pass to Tiferet for arbitration.

**Chesed (scope proposer) — suggests improvements:**
```
[implementation] Chesed: proposed 2 improvements — add input validation for rate limit config; add tests for middleware
```

Chesed proposes, it doesn't implement. Tiferet decides.

**Tiferet (arbitrator) — resolves expansion vs restriction:**
```
[implementation] Tiferet: 2 accepted, 0 rejected, needs_rework=false
[implementation] Tiferet: 1 accepted, 1 rejected, needs_rework=true
```

If `needs_rework=true`, the implementation loops back for another round.

**Hod (formatter) — enforces compliance:**
```
[implementation] Hod: 3 files formatted, 1 lint fix
```

Deterministic. Runs `ruff format` + `ruff check --fix`. Zero LLM cost.

**Yesod (integration gate) — final validation:**
```
[review] Yesod: PASSED — pytest: 42 passed, 0 failed, pyright: 0 errors
[review] Yesod: FAILED — pytest: 40 passed, 2 failed
```

Runs full test suite + type checker + git diff review before human sees anything.

**Netzach (retry engine) — on failures:**
```
[planning] Netzach: architect attempt 2 → retry — appending error feedback
[implementation] Netzach: implement attempt 3 → escalate — same error pattern, switching model
```

Appears only when a node fails. Chooses retry/escalate/decompose/exit.

---

## CLR — Continuous Refinement

Self-improving loop. Assesses health, generates tasks, executes, validates, commits or reverts, loops until convergence.

### Commands

```
refiner start
```
Start the refinement loop. Reads SPEC.md, assesses health, generates tasks, executes, validates, commits or reverts, loops until convergence.

```
chain_refiner(max_cycles=50, budget=5.0)
```
Start via MCP tool with custom budget.

### What to expect

```
[cycle 1] Assess: health 0.62 — 5 tests failing, 12 pyright errors
[cycle 1] Triage: fix — 5 failing tests (priority: defects first)
[cycle 1] Nitzotz: researching test failures...
[cycle 1] Validate: health 0.68 → improvement, committing
[cycle 2] Assess: health 0.68 — 0 tests failing, 12 pyright errors
[cycle 2] Triage: batch fix — 12 pyright errors (dispatching to Nefesh)
...
[cycle 8] Assess: health 0.91 — all tests passing, 0 pyright errors
[cycle 8] Triage: feature — next spec item: "Add cost tracking per request"
[cycle 8] Nitzotz: researching cost tracking...
...
[cycle 15] Converged — health 0.94, no improvement in 5 cycles. Stopping.
```

---

## PDE — Parallel Swarm

Parallel dispatch engine. Decomposes into N independent tasks, fans out workers, merges atomically.

### Commands

```
swarm fix all pyright errors
```

```
swarm add unit tests for all untested modules
```

```
swarm migrate all API endpoints from v1 to v2
```

### What to expect

```
Sovereign: decomposed into 8 tasks (flat dispatch — all independent)
Worker 1/8: fixing auth.py — completed
Worker 2/8: fixing models.py — completed
Worker 3/8: fixing utils.py — failed (timeout)
...
Merge: combining 7/8 successful workers
Integrity check: pytest — 42 passed, 0 failed
Result: 7/8 tasks completed, 1 failed (timeout)
```

---

## PDE-F — Graduated Dispatch

Extension to PDE for tasks with layered dependencies. Triggered automatically when the decomposer detects task dependencies. No separate command.

```
swarm build a REST API with auth, admin dashboard, and payment integration
```

### What to expect

```
Sovereign: decomposed into 10 tasks (klipah dispatch — layered dependencies detected)
Gen 1 (1 agent): designing database schema — completed
Gen 2 (1 agent): building API core on schema — completed
Gen 3 (2 agents): auth service, user endpoints — completed
Gen 4 (3 agents): admin dashboard, payment gateway, notification service — completed
Gen 5 (5 agents): cart UI, search, email templates, inventory sync, reports — completed
Consolidation: 5 → 3 reviewers → 2 reviewers → 1 final review
Integrity check: pytest — 67 passed, 0 failed
Result: all 10 tasks completed across 5 generations
```

---

## HVD — Meta-Orchestrator

The autonomous supervisor. Monitors the repo, decides what to run, spawns patterns as needed.

### Commands

```
hypervisor start
```
Start the hypervisor. Monitors repo health, dispatches refinement/swarm/pipeline as needed.

```
chain_hypervisor(budget=10.0)
```
Start via MCP tool with custom daily budget.

### What to expect

```
Ein Sof: scanning repository...
Ein Sof: health 0.58 — 8 tests failing, 20 pyright errors
Ein Sof: dispatching Nefesh for batch pyright remediation (20 independent errors)
Ein Sof: Nefesh completed — 18/20 fixed
Ein Sof: health 0.72 — 8 tests failing, 2 pyright errors
Ein Sof: dispatching Chayah for steady improvement (spec items remaining: 4)
Ein Sof: Chayah cycle 1 — fixing test failures...
Ein Sof: Chayah cycle 3 — implementing "cost tracking per request"...
Ein Sof: directive check — CLEAN
Ein Sof: Chayah converged at cycle 7 — health 0.93
Ein Sof: all spec items complete, entering idle
```

---

## Job Management

These work across all pipeline types (Nitzotz, Chayah, Nefesh).

### Check status

```
status
```
Shows all recent jobs with their state.

```
status abc123
```
Shows a specific job's progress, last 5 messages, and result if completed.

### Approve or reject

```
approve
```
Approves the most recent paused job. The pipeline continues to implementation.

```
reject the plan uses an outdated API, switch to v3
```
Rejects with feedback. The architect revises with your feedback as context.

### View history

```
history
```
Shows checkpoint history for the most recent thread — every supervisor decision, validation score, and state at each step.

### Time-travel

```
rewind
```
Lists available checkpoints. Pick one to rewind to and re-run from that point.

---

## Cursor Rules

These keywords are defined in `.cursor/rules/mcp-routing.mdc`. When Cursor sees them at the start of a message, it routes to the corresponding MCP tool automatically.

| Keyword prefix | Routes to | Notes |
|---|---|---|
| `pipeline` | `chain_pipeline()` | Full pipeline with balanced forces |
| `graph` | `chain()` | Option B supervisor pipeline |
| `refiner start` | `chain_refiner()` | Continuous refinement loop |
| `swarm` | `swarm()` | Parallel dispatch |
| `hypervisor start` | `chain_hypervisor()` | Meta-orchestrator |
| `components validate` | `chain_components()` | Component library validation |
| `deadcode start` | `chain_deadcode()` | Dead code elimination |
| `toolbuilder start` | `chain_toolbuilder()` | Proactive tool-builder |
| `research`, `deep dive` | `research()` | Gemini CLI |
| `plan`, `design`, `architect` | `architect()` | Claude CLI |
| `classify` | `classify()` | Fast tier classification |
| `status` | `status()` | Job status |
| `approve` | `approve()` | Approve paused job |
| `reject` | `approve(feedback=...)` | Reject with feedback |
| `history` | `history()` | Checkpoint history |
| `rewind` | `rewind()` | Time-travel |
| `health` | `health()` | Server health check |
