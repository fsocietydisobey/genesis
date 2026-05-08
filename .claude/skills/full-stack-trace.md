---
name: full-stack-trace
description: |
  Given a user-observable action ("user clicked Approve and nothing
  happened", "the dashboard shows wrong data for deliverable X"),
  trace the request all the way through the stack: frontend
  interaction → API call → graph invocation → DB write → side
  effects. Identifies where the chain broke, which layer is responsible,
  and what evidence supports the conclusion.

  This is the killer-demo skill — it composes EVERY tool in chimera's
  zoo (specter for browser, monitor for graphs, postgres for DB,
  séance for code, scarlet for cross-references) into a single
  investigation. If chimera-as-unified-debugger has a single proof,
  this is it.

trigger:
  - "user (says|reports|sees) (.*)"
  - "trace (.*) (from|through) (the )?(ui|frontend|user)"
  - "the (button|form|page|click) (does|did) (nothing|wrong)"
  - "what happens when (.*)"
  - "/full-stack-trace"
  - "/trace-action"
---

# Full-Stack Trace

You are following a user action through every layer of the system to
identify where it broke (or to document the full request path for a
working flow). Unlike `debug-runtime-issue` (which starts from a
known runtime failure), this skill starts from a user-observable
symptom and works inward.

The output is a request trace — a chronological reconstruction of
what happened across layers, with evidence at each step.

## Vocabulary

- **User action** — the observable starting point: click, submit,
  navigation, anything the user did
- **Layer hop** — one transition between layers (UI → API → graph →
  DB). Each hop has its own observability surface.
- **Trace ID** — anything that links a user action to its downstream
  effects. May be explicit (request_id, deliverable_id, run_id) or
  implicit (timestamp + user identity + page state).
- **Break point** — the first layer hop where expected output
  doesn't match actual. The break point IS the bug, not a
  consequence of it.

## Investigation procedure

### 1. Reproduce the action (or get evidence of it)

If the action is reproducible, USE SPECTER to drive it:

```
specter:navigate_to <url>
specter:click_element <selector>     # the actual user action
specter:take_screenshot              # capture the visual state after
```

Then immediately gather evidence from every observability surface:

```
specter:get_console_logs level=error
specter:get_errors
specter:get_network_log url_filter=/api/
```

If the action is NOT reproducible (one-time issue, user complaint
without a recipe), gather the user's context:
- When did it happen? (rough timestamp narrows monitor + log searches)
- What were they trying to do?
- What did they see vs expect?

### 2. Identify the trace ID anchor

Find SOMETHING that ties the action to downstream effects. In order
of preference:
- Explicit `request_id` / `correlation_id` in network logs
- A domain identifier the action operated on (`deliverable_id=123`)
- The user's session identity (`user_id`)
- A timestamp + the page route

Without an anchor, you can't reliably correlate across layers — be
explicit about that and ask the user for one if needed.

### 3. Frontend layer — what was sent?

Use specter's network log to extract the API call:

```
specter:get_network_log url_filter=<expected-endpoint>
```

Capture:
- Method + URL + status code
- Request body
- Response body
- Timing

Was it a 4xx? Then the bug is server-side rejection — go to API
layer next. Was it a 2xx but wrong data? Then the bug is in
processing — go deeper.

For React/Vue apps, also inspect component state at the moment of
action:

```
specter:get_component_at <selector>
specter:get_redux_state                # if RTK / redux
```

### 4. API layer — was the request received correctly?

If the project has FastAPI (or similar), the request went through
some route handler. Find it:

```
séance:semantic_search "<endpoint path> route handler"
grep -rn "<endpoint_path>" --include="*.py" .
```

Read the handler. Look for:
- Pydantic validation that may have rejected silently
- Auth checks that may have failed
- Calls to LangGraph / business logic
- DB writes triggered

If the handler invokes a LangGraph graph, note the `thread_id` it
constructed — that's the next anchor.

### 5. LangGraph layer — was a graph invoked?

Use chimera-monitor to find the run that the API kicked off:

```bash
PROJECT=<project>
# Filter by scope_id or thread_id from the API trace
curl -s "http://127.0.0.1:8740/api/threads/${PROJECT}?limit=20" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin)
# Look for threads matching the trace anchor (deliverable_id, etc.)
ANCHOR='<your-anchor>'
for t in d['threads']:
    if ANCHOR in t['thread_id'] or ANCHOR in (t.get('scope_id') or ''):
        print(t['thread_id'], t['status'], '@'+(t['current_node'] or '-'))
"
```

If a thread exists matching the anchor:
- Pull its checkpoints (refer to `debug-runtime-issue` skill's
  procedure — the trajectory diff is reusable)
- Note where the run is, what state it left behind

If NO thread exists matching the anchor, the graph was never
invoked — the API handler errored before kicking it off, or the
event was filtered out upstream. Surface that clearly.

### 6. Database layer — did the side effects land?

Query the DB via postgres MCP to verify:

```
postgres:query "SELECT * FROM <relevant_table> WHERE <anchor_column> = '<anchor>' ORDER BY created_at DESC LIMIT 5"
```

Compare:
- Were rows expected to be created? Did they appear?
- Were rows expected to be updated? Did the values match?
- Are there rows in unexpected states (e.g., status='pending' that
  should have advanced)?

Cross-reference with the LangGraph state:
- Graph state and DB state should agree at the end of a run
- Divergence = either persist node failed, OR DB transaction
  rolled back, OR another writer modified the row

### 7. Identify the break point

Walk back through the layers in the order you investigated:
- UI: did the click fire? (specter screenshot + click_element confirms)
- Network: did the request leave? (network log)
- API: did the handler run? (response status + handler log)
- Graph: was a thread created? (monitor list)
- Graph: did the thread complete? (monitor state + trajectory)
- DB: did writes land? (postgres query)

The FIRST layer where expected ≠ actual is the break point. Don't
keep investigating downstream — the issue is HERE.

### 8. Synthesize the trace

Output structure:

```markdown
## Trace: <user's action description>

**Anchor:** <trace ID used to correlate across layers>
**Reproduced:** YES via specter / NO (post-mortem)

### Request path

| # | Layer | What happened | Evidence | Status |
|---|-------|---------------|----------|--------|
| 1 | UI click | User clicked Approve on row 123 | screenshot at T0 | ✅ |
| 2 | Network POST | `/api/deliverables/123/approve` 200 | network log entry | ✅ |
| 3 | API handler | `approve_deliverable()` ran, dispatched chat_lane graph | `src/api/...:approve_deliverable:42`, log entry "approving 123" | ✅ |
| 4 | LangGraph | Thread `deliverable:123:digestion:5` started, currently @persist step 8 | monitor /api/threads | ✅ |
| 5 | DB | `deliverables.run_status` should have flipped to "approved" | actual=`pending` | ❌ |

### Break point

**Step 5: DB row never updated.** The graph reached `persist` (which
is supposed to flip `run_status`) but the DB row is still `pending`.

### Root cause

Likely: persist node's DB write errored silently. Two candidates:
- Transaction rolled back due to FK constraint on a related row
- Persist used the wrong session / connection
- Persist completed but a downstream trigger reverted the value

### Suggested next step

1. Read `src/.../persist_node.py` and confirm it actually issues
   the UPDATE
2. Check Postgres logs around the persist timestamp for transaction
   errors
3. Check if there's a trigger on `deliverables` that reverts status

### What I checked but ruled out

- Authentication: 200 response, user was authorized
- Frontend state: dispatch succeeded per Redux DevTools
- Graph routing: thread reached persist correctly per monitor
```

## Failure modes to avoid

- **Don't skip the trace ID step.** Without an anchor, you'll trace
  the wrong thing or correlate noise. Stop and ask the user for the
  identifier if you can't infer one.
- **Don't investigate every layer if you find the break early.**
  If step 2 (network) shows a 500, step 3-7 are all consequences,
  not causes. Stop investigating once you've localized the break.
- **Don't fix without confirming.** This skill produces a TRACE,
  not a fix. The trace identifies the break point; the fix is a
  separate step.
- **Don't forget timing.** Layer hops have latency. If an event was
  observed at T0 and you're querying DB at T+5s, the writer might
  not have committed yet. Use timestamps as a sanity check.

## Known break-point patterns (chimera + jeevy)

### Persist node didn't update DB
- **Pattern:** Graph reached persist, DB row unchanged
- **Likely:** Silent transaction rollback OR wrong connection OR
  persist body has a guard that prevented the update
- **Verify:** Read persist node body, check for early-return paths

### Graph thread never started
- **Pattern:** API returned 200, no thread_id appears in monitor
- **Likely:** API handler caught an exception in graph dispatch
  silently (e.g., `try: graph.invoke()...; except: pass`)
- **Verify:** Search for `try:` blocks in the handler that swallow
  exceptions. Check daemon log around the API call timestamp.

### Frontend state not synced after success
- **Pattern:** API returned 200, DB updated, UI still shows old state
- **Likely:** RTK Query cache not invalidated, or UI subscribed to
  the wrong selector
- **Verify:** Check `invalidatesTags` in the mutation definition;
  confirm the relevant query has a matching `providesTags`

### HITL pause looks like a hang
- **Pattern:** User saw "spinner forever" but graph status=paused
- **Likely:** Graph hit `__interrupt__` (HITL gate) waiting for
  human input the user didn't realize was needed
- **Verify:** monitor shows status=paused, not stuck. Check what
  the gate expects.

## When to ask instead of trace

- Multiple users / multiple actions match the complaint — ask for
  one specific reproducible case
- The action requires authentication state you don't have access to
  reproduce — ask for screenshots / logs from the user's session
- The break point is in a layer you can't observe (third-party API,
  external service) — surface that boundary explicitly
