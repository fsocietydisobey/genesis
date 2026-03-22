# Ein Sof (formerly MUTHER) — TODO

The capstone. Depends on Nitzotz (formerly ARIL), Chayah (formerly Ouroboros), and Nefesh (formerly Leviathan) being implemented.

```mermaid
flowchart LR
    P1["1. Directives"] --> P2["2. Dispatcher"]
    P2 --> P3["3. Entity lifecycle"]
    P3 --> P4["4. Unified memory"]
    P4 --> P5["5. Resource control"]
    P5 --> P6["6. Daemon"]
    P6 --> P7["7. Event triggers"]
```

---

## Phase 1: Directives — Special Order 937

- [ ] Create `DIRECTIVES.md` at project root — human-authored, agent-immutable
- [ ] Define categories: Security, Performance, Architecture, Process
- [ ] Create `src/orchestrator/graph_server/core/directives.py`:
  - [ ] `load_directives()` — parse DIRECTIVES.md into structured rules
  - [ ] `check_directives(diff)` — scan a git diff against all directives
  - [ ] Deterministic checks where possible (grep for `eval(`, check file sizes, check for `.env` in diff)
  - [ ] LLM-assisted check for architectural rules (single cheap API call)
  - [ ] Returns `DirectiveResult(passed: bool, violations: list[Violation])`
- [ ] Test: create a diff that adds `eval()` → verify directive checker catches it

---

## Phase 2: Dispatcher — pattern selection

- [ ] Create `src/orchestrator/graph_server/nodes/muther_dispatch.py`:
  - [ ] Reads `HealthReport` (from Chayah's fitness function)
  - [ ] Reads `SPEC.md` progress
  - [ ] Decides which pattern to spawn:
    - [ ] > 5 independent issues across disjoint files → Nefesh
    - [ ] Health declining + spec items remaining → Chayah
    - [ ] Single complex task from human → Nitzotz
    - [ ] Everything healthy + spec complete → Cryosleep (idle)
  - [ ] Output: `DispatchDecision(pattern, config, reasoning)`
- [ ] Config per pattern:
  - [ ] Chayah: max_cycles, budget, spec_focus
  - [ ] Nefesh: max_agents, budget, task_filter
  - [ ] Nitzotz: task_description, context
- [ ] Test: give dispatcher various health reports → verify correct pattern selection

---

## Phase 3: Entity lifecycle — spawn, monitor, absorb

- [ ] Create `src/orchestrator/graph_server/core/entity_manager.py`:
  - [ ] `spawn_entity(pattern, config)` — start the chosen graph in background
  - [ ] `monitor_entity(entity_id)` — check status, progress, budget usage
  - [ ] `kill_entity(entity_id)` — hard-terminate and revert changes
  - [ ] `absorb_results(entity_id)` — collect final state into Ein Sof's memory
- [ ] Entity states: `spawning → active → throttled → hibernated → completed → absorbed` or `killed`
- [ ] After entity completes: run directive check before absorbing
- [ ] If directive violation: revert all changes, log violation, optionally respawn with directive context
- [ ] Track active entities in state: `active_entities: list[dict]`
- [ ] Test: spawn a Nitzotz entity, let it complete, verify results are absorbed

---

## Phase 4: Unified memory — The Ocean

- [ ] Create `src/orchestrator/graph_server/core/ocean.py` (or extend existing memory.py):
  - [ ] Unified SQLite with tables per pattern:
    - [ ] `aril_runs` — task, outcome, decisions (existing memory.py)
    - [ ] `ouroboros_cycles` — cycle, action, health delta (existing evolution_memory.py)
    - [ ] `leviathan_swarms` — goal, agents_spawned, success_rate
    - [ ] `directive_violations` — what was purged and why
    - [ ] `muther_decisions` — pattern chosen, reasoning, outcome
  - [ ] `inject_context(pattern)` — query relevant tables and produce a context string for the entity
  - [ ] `record_decision(pattern, config, reasoning, outcome)` — log Ein Sof's dispatch decisions
- [ ] When spawning any entity, call `inject_context()` to provide ancestral memory
- [ ] Test: record 3 decisions, query context, verify it includes all 3

---

## Phase 5: Resource control — Cryosleep

- [ ] Create `src/orchestrator/graph_server/core/resource_control.py`:
  - [ ] `GlobalBudget` dataclass: max_daily_cost, max_concurrent_entities, max_entity_cost
  - [ ] `track_cost(entity_id, estimated_cost)` — accumulate per-entity and global cost
  - [ ] `should_throttle(entity_id)` — check if entity is burning tokens without improvement
  - [ ] `hibernate(entity_id)` — save entity state to checkpointer, stop execution
  - [ ] `wake(entity_id)` — resume hibernated entity from checkpointer
- [ ] Throttle rules:
  - [ ] Chayah: if 3 consecutive cycles with no health improvement → hibernate
  - [ ] Nefesh: if estimated cost exceeds max_entity_cost → stop spawning agents
  - [ ] Any entity: if global daily budget exceeded → hibernate all, page human
- [ ] Test: simulate a Chayah with no improvement → verify it gets hibernated

---

## Phase 6: Daemon — the persistent mainframe

- [ ] Create `scripts/muther.sh` — the outer daemon (replaces/extends ouroboros.sh):
  ```bash
  while true; do
      uv run muther "$@"
      EXIT_CODE=$?
      if [ $EXIT_CODE -eq 0 ]; then break; fi       # clean shutdown
      if [ $EXIT_CODE -eq 42 ]; then                 # self-modification restart
          echo "Ein Sof: self-modification detected. Restarting..."
          continue
      fi
      echo "Ein Sof: unexpected exit ($EXIT_CODE). Stopping."
      break
  done
  ```
- [ ] Create `src/orchestrator/graph_server/graphs/muther.py` with `build_muther_graph()`:
  - [ ] Graph: assess → dispatch → spawn_entity → monitor → directive_check → absorb → assess (loop)
  - [ ] The loop runs until: all healthy + spec complete + no active entities → clean exit
- [ ] Create entry point `muther` in `pyproject.toml`
- [ ] Add `chain_muther(goal?, budget?)` MCP tool for manual invocation
- [ ] Self-modification detection: same as Chayah — exit 42 if own code changed
- [ ] Test: run Ein Sof with a simple health assessment → verify it spawns the correct entity

---

## Phase 7: Event triggers (optional, future)

- [ ] Cron-based: Ein Sof runs assessment on a schedule (e.g. every hour)
- [ ] Git hook: post-commit triggers reassessment
- [ ] File watcher: `watchdog` library monitors the project directory for changes
- [ ] Webhook: GitHub webhook triggers on PR events (future, requires HTTP server)
- [ ] Human signal: `muther wake` CLI command or MCP tool to trigger immediate assessment
