---
name: debug-runtime-issue
description: |
  Investigate a runtime issue in this LangGraph project — given a user
  complaint about a stuck/failed/slow run, deliverable, or thread,
  gather evidence from chimera-monitor (live state), the code (séance,
  scarlet), and the database (postgres if used), then synthesize a
  root-cause analysis with cited evidence.

  This is the FIRST skill in chimera's full-stack debugging pack. The
  goal is to do in one chat turn what would normally take 5 tabs and
  20 minutes of manual investigation.

trigger:
  - "why is (run|thread|chain|swarm|pipeline|deliverable) * (stuck|failing|spinning|broken|slow|errored)"
  - "investigate (run|thread|chain|swarm|pipeline|deliverable) *"
  - "(run|thread|chain) * (won't|isn't|hasn't|didn't)"
  - "/debug-runtime-issue"
---

# Debug Runtime Issue

You are investigating a runtime problem in a LangGraph project served
by chimera-monitor. The current project's name comes from the cwd
(e.g. `chimera`, `jeevy_portal`).

## Vocabulary you should know

- **Thread** — a single LangGraph invocation; thread_ids vary per
  project. chimera uses bare UUIDs; jeevy uses `deliverable:<uuid>:<stage>:<n>`.
- **Run** — one execution cycle. Some projects cluster many threads
  into one logical run via `scope_id`.
- **Stage** — coarse phase the thread belongs to (parsed from the
  thread_id; see chimera-monitor's metadata for the project's grouping
  rules).
- **HITL** — human-in-the-loop pauses (`__interrupt__` channel set).
- **Terminal node** — a graph node whose only outgoing edge goes to
  `__end__`. The monitor's status classifier flips threads to idle
  the moment they reach one.

The monitor daemon runs at **http://127.0.0.1:8740**. JSON API at
`/api/projects`, `/api/threads/<project>`, `/api/threads/<project>/<thread_id>`,
`/api/topology/<project>`.

## Investigation procedure

Follow these steps in order. Skip a step only if its data isn't
applicable to the user's complaint.

### 1. Parse the complaint

Identify what the user is asking about:
- Is there a specific `thread_id`, `run_id`, or scope?
- What's the symptom — stuck, errored, slow, wrong output?
- Which graph or stage is implicated?

If the project name isn't obvious from cwd, derive it:

```bash
basename "$(pwd)"
```

### 2. Confirm chimera-monitor is up

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8740/api/projects
```

Expect `200`. If not, tell the user to run `chimera monitor start`
and stop here.

### 3. Locate the relevant thread(s)

**Preferred** — use the chimera MCP tools when available (cleaner output,
typed errors):
- `monitor_active_runs(project=...)` — narrow to running/paused/starting
- `monitor_find_stuck(project=...)` — pre-filtered to anomalies if user
  reported "something's stuck"

**Fallback** (when chimera MCP tools aren't registered):

```bash
PROJECT=<project-name-from-cwd>
curl -s "http://127.0.0.1:8740/api/threads/${PROJECT}?limit=20" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); \
    [print(f\"{t['thread_id'][:60]:60s}  {t['status']:8s}  @{t['current_node'] or '-':20s}  step={t['step']}  scope={t['scope_id'][:8]}\") \
     for t in d['threads']]"
```

Filter by:
- `status` (running / paused / starting / idle)
- `current_node` matching the user's complaint
- `scope_id` matching the run / deliverable they mentioned

Trust the status classification — it accounts for HITL, terminal-node
detection, per-project running threshold, and per-node observed p95.
A thread classified `idle` has finished (cleanly OR by error/abandonment);
a thread classified `running` is still executing or has activity within
its threshold window.

### 4. Get full state + recent checkpoints

**Preferred:** `monitor_thread_state(project=..., thread_id=..., recent=10)`

**Fallback:**

```bash
curl -s "http://127.0.0.1:8740/api/threads/${PROJECT}/<thread_id>?limit=10" \
  | python3 -m json.tool
```

The response includes the latest 10 checkpoints with full state at each.

What to extract:
- `current_node` and how long it's been there (compare `last_updated`
  to now)
- The state diff between consecutive checkpoints — what each node
  wrote. The full state is noisy; the diffs are the signal.
- Any error fields, retry counters, status flags in the state
- The trajectory: did the thread loop, did it skip a node, did it
  reach an unexpected branch?

### 4b. (Highly recommended) Compare against a known-good run — the trajectory diff

If a same-graph successful thread exists, fetch its checkpoints and
build a side-by-side trajectory table. This is the single most
informative artifact in the investigation — it pinpoints the exact
divergence step.

```bash
PROJECT=<project>
GOOD_TID=<known-good-thread-id>
BAD_TID=<failing-thread-id>

for tid in "$BAD_TID" "$GOOD_TID"; do
  echo "=== $tid ==="
  curl -s "http://127.0.0.1:8740/api/threads/${PROJECT}/${tid}?limit=20" | python3 -c "
import json, sys
d = json.load(sys.stdin)
chrono = list(reversed(d['checkpoints']))
for i, cp in enumerate(chrono):
    state = cp.get('state') or {}
    keys = list(state.keys()) if isinstance(state, dict) else []
    print(f\"step {i}: node={cp.get('node') or '-':20s} keys={keys}\")"
done
```

Render the result as a side-by-side markdown table in the synthesis:

| step | GOOD (N cp) | FAILED (M cp) |
|------|-------------|----------------|
| 0 | `__start__` | `__start__` |
| 1 | `branch:to:X` | `branch:to:X` |
| 2 | nodeA (writes Y) | nodeA (writes Y) |
| 3 | nodeA (writes Z, branch:to:end) | — *(stopped)* |
| 4 | terminal (final state) | — |

The first row where columns differ is the divergence point. The state
KEYS column reveals which channels each step wrote — extra/missing
keys are usually the smoking gun.

### 5. Map the run's path through the graph

Use **scarlet** to understand the graph the thread is in:
- `scarlet:scan_features` to find the graph factory
- `scarlet:extract_feature_metadata` to get nodes + edges
- `scarlet:list_consumers` to see what calls into it

Or pull topology directly:

```bash
curl -s "http://127.0.0.1:8740/api/topology/${PROJECT}" | python3 -m json.tool
```

You're answering: which node SHOULD have fired next given the current
state, and could a conditional edge have routed away from the expected
path?

#### Conditional-edge audit (load-bearing — check this for any loop or routing failure)

Every `add_conditional_edges(node, fn, mapping)` call has a ROUTING
FUNCTION (`fn`) that returns a string and a MAPPING dict whose keys
must include every value `fn` can return. If `fn` returns `"hod"` but
the mapping is `{"implement": ..., "compliance": ...}`, the route
target `"hod"` doesn't exist and LangGraph either errors or silently
skips the route.

For each suspect node in the failing trajectory:

```bash
# Find conditional-edges calls referencing the node
grep -rn "add_conditional_edges" src/ | grep -E "\"<node_name>\"|'<node_name>'"

# Read the routing function — look at every `return` statement
# and confirm the value appears as a KEY in the mapping dict
```

The audit:
- Routing fn returns `"X"` → mapping must contain key `"X"`
- Routing fn returns a Send object → not subject to mapping
- Routing fn returns `END` → mapping must include `END` or be omitted entirely (LangGraph allows END as default)

This class of bug appears as either:
- A loop that never exits (one return value is unreachable, so the
  loop falls through to a different mapped value that re-enters the
  cycle)
- A graph-end error in the daemon log when the unreachable value
  finally triggers
- Silent skip (depends on LangGraph version's strictness)

### 6. Read the relevant node code

Use **séance** to find the implementation:
- `séance:semantic_search` with the node name + a short description
- For specific node names, also try grep:
  ```bash
  grep -rn 'add_node("<node_name>"' src/
  grep -rn '^def <node_name>' src/
  ```

Read the actual function body. Look for:
- Error handling that swallows exceptions
- Retry logic with conditions that aren't met
- Branches depending on state values not present
- External calls (LLM CLI, HTTP, subprocess) that could time out
- Input validation that might reject silently

For chimera specifically, common failure shapes:
- Subprocess timeout (claude/gemini CLI)
- Permission mode mismatch (acceptEdits vs read-only)
- MCP tool args validation
- Async cancellation / TaskGroup errors

### 6b. Check daemon + project logs

The chimera-monitor daemon and most LangGraph apps log to known paths.
A node may have errored AFTER its last successful checkpoint — the
checkpoint table won't show the error, but the log will.

```bash
# chimera-monitor daemon log
tail -100 ~/.local/state/chimera/monitor.log

# Search around a known timestamp (use the failing thread's last
# checkpoint time)
grep '14:59' ~/.local/state/chimera/monitor.log
```

For chimera itself, also check the MCP server's log if running outside
the daemon (e.g., spawned by Claude Code) — those go to stderr of the
launching process. For other projects, check their typical log paths
(`~/.local/state/<project>/`, `<project>/logs/`, `journalctl --user`).

If the failing thread terminated AT a checkpoint without a successor,
look for log lines in the seconds AFTER that checkpoint's `created_at`
— that's where the workers / next nodes would have logged their
exception before the run ended.

### 7. Check database state (if relevant)

If the project uses postgres, query directly via the postgres MCP
to verify expected DB writes. For chimera (SQLite), the checkpoint
DB IS the database — already inspected via the monitor.

For jeevy / projects with side-effect tables, look for divergence
between graph state and DB state.

### 8. Synthesize the root-cause analysis

Write a response with this structure:

```
## Investigation: <user's question>

**Symptom:** <what was reported, in your words>

**Evidence gathered:**
- Thread <thread_id> status=<X>, current_node=<Y>, last_updated=<Z ago>
- State diff at step <N>: <what changed>
- Code at <node_name>: <observation about the body>
- (if applicable) Topology says next-node should be <X>; checkpoint
  shows we routed to <Y> via <conditional edge>
- (if applicable) DB: <relevant rows + values>

**Likely root cause:**
<one or two sentences, citing specific evidence>

**Suggested next step:**
- Quick check: <thing the user should run to confirm>
- Likely fix: <code change, or "needs further investigation in X">

**What I checked but ruled out:**
<short list — surfaces dead ends so the user knows you didn't miss
the obvious thing>
```

## Known failure shapes for chimera (check these against your evidence)

These are previously-seen patterns — match the user's symptom against
the list before deep investigation:

### Swarm decomposer short-circuit (`_fan_out` produced 0 workers)
- **Symptom:** Thread ends at `decomposer` with 3 checkpoints (`__start__`,
  `branch:to:decomposer`, `decomposer`). Manifest is non-empty but no
  worker checkpoint follows.
- **Code:** `src/chimera/graphs/swarm.py:_fan_out`
- **Likely cause:** Workers were dispatched via `Send("worker", ...)`
  but errored before their first checkpoint write. The astream loop
  in `swarm()` (mcp.py) catches the exception and the run terminates
  cleanly without a checkpoint trail. Most often a worker subprocess
  (claude/gemini CLI) auth/arg error.
- **First check:** `grep <timestamp> ~/.local/state/chimera/monitor.log`
  around the failing decomposer's `created_at`.
- **Workaround:** rerun with `max_agents=1` — if that succeeds, bug is
  concurrent-worker handling; if it fails too, bug is in worker code.

### Subprocess timeout (claude/gemini CLI)
- **Symptom:** Thread runs for ~5min, last checkpoint shows a node
  that calls `run_claude` or `run_gemini`, no further activity.
- **Likely cause:** `CLI_TIMEOUT` (default 300s) elapsed; subprocess
  killed.
- **First check:** `grep timeout ~/.local/state/chimera/monitor.log`,
  also check chimera's main log.

### MCP tool arg validation rejection
- **Symptom:** Thread starts, fails immediately with no useful state
  written. Often appears as 1-checkpoint run with just `__start__`.
- **Likely cause:** Pydantic validation rejected the input. MCP
  client sees the error but the graph never advanced.
- **First check:** Caller's logs, not the daemon's.

### LangGraph cycle limit hit
- **Symptom:** Thread reaches a high step count (>25 by default) and
  errors. Last checkpoint shows the node that was about to loop.
- **Likely cause:** Conditional edge created an infinite loop; LangGraph
  killed it at `recursion_limit`.
- **First check:** Compare `step` field across recent runs of the same
  graph. If this run has anomalously high step count, suspect a cycle.
- **Sub-pattern: stale exit-condition state.** Once you see a loop,
  pull every state field referenced by the routing function and tabulate
  across iterations. A field that should reset between iterations
  (e.g. `handoff_type`, error flags, retry counters) but stays sticky
  is the bug — the loop's exit condition checks it but it's never
  cleared. Example: `chimera`'s `_after_arbitrator` checks `handoff ==
  "tests_failing"`; if `handoff_type` isn't reset when arbitrator says
  "proceed", the loop continues even when needs_rework=False.

### Conditional-edge route-target mismatch
- **Symptom:** Either a graph-end error in the daemon log (`Edge target
  'X' not found`) OR a silent loop that "shouldn't be possible" given
  the routing function's logic.
- **Likely cause:** Routing function returns a string that's NOT a
  key in the conditional edge's mapping dict. E.g.,
  `return "hod"` when mapping is `{"implement": ..., "compliance": ...}`.
  Often a typo or stale identifier from a refactor.
- **First check:** For each `add_conditional_edges` call referencing
  the suspect node, read every `return` statement in the routing
  function and confirm each return value appears as a key in the
  mapping. Easy to grep: `grep -A 30 'add_conditional_edges.*<node>'`
  then read the routing fn. See Step 5 / Conditional-edge audit.
- **Why it's sneaky:** May not error immediately if the bad return
  is unreachable in current state space. Once a real run triggers
  it, you get a confusing graph error.

### Permission mode mismatch
- **Symptom:** A node that should have edited files completed but the
  filesystem is unchanged.
- **Likely cause:** `permission_mode=None` (default for some chimera
  paths) means claude reads but won't write. Should be `acceptEdits`
  for file-mutation work.
- **First check:** `grep permission_mode src/chimera/...` for the calling
  code.

## Failure modes to avoid

- **Don't speculate.** Cite specific evidence (checkpoint id, line of
  code, DB row). If you couldn't find data, say so explicitly.
- **Don't try to fix without confirming.** Investigate first; propose
  the fix as a separate step the user can approve.
- **Don't get lost in deep state trees.** Diffs between consecutive
  checkpoints are the signal; full state dumps are noise.
- **Trust the monitor's classifications.** If status=idle it's done.
  If status=stuck the staleness classifier flagged it. Don't
  re-derive what the daemon already computed.
- **Don't fire the chimera-orchestration tools (chain_pipeline, swarm,
  etc.) as part of investigation** — those START new runs. Only fire
  them if the user explicitly asks for "rerun this with X".

## When to ask instead of investigate

- Multiple threads match — ask which one
- Complaint too vague — ask for one specific symptom or thread_id
- Investigation would need a destructive action — propose, don't do
