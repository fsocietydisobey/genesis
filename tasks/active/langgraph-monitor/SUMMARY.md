# LangGraph Monitor — Phase 1 Summary

**Status:** Phase 1 shipped 2026-05-06 → 2026-05-07 (multi-session sprint).
Phase 2+ items in [TODO.md](./TODO.md) remain.

## What shipped

A generic observability dashboard for any LangGraph project. Auto-discovers
projects from `config.ROOTS`, introspects compiled `StateGraph` topology
via runtime + AST fallback, tails the checkpointer (Postgres jsonb or
SQLite blob) for live state, and renders an n8n-style canvas with
multi-thread replay and per-step diff inspection.

Adapts to any LangGraph app — no per-project code required. Optional LLM
metadata cache (Claude Opus high) enriches displays with project
vocabulary, scope kinds, thread-id grouping, and run clustering rules.

### Backend (`src/chimera/monitor/`)

- FastAPI daemon, `127.0.0.1`-bound, `os.fork` daemonization, PID lock
- Lazy-imports gated behind `chimera[monitor]` extra
- Project discovery: scans registered roots for LangGraph factories
- Connection discovery: parses project `.env` files for Postgres URLs;
  walks data dirs for SQLite checkpointers
- Topology: runtime introspection primary; tree-sitter AST walker
  fallback for projects with dynamic node construction
- State decoder: msgpack/ormsgpack/jsonb tolerant; column-name redaction
  applied server-side
- Metadata scan: Claude Opus reads project source + sample thread_ids,
  derives node/graph roles, summaries, `thread_grouping` regex, and
  `run_clustering` rules. Cached on disk; auto-invalidated by source mtime
- API: `/projects`, `/topology/{name}`, `/threads/{name}`,
  `/threads/{name}/{thread_id}`

### Frontend (`monitor_ui/`)

- Vite + React + TS + Tailwind + shadcn/ui + RTK Query
- React Flow canvas (replaced original Mermaid plan during build —
  needed n8n-style drag/zoom and cluster backgrounds)
- Per-graph tabs + "All" view with cross-graph "invokes" edges
- Replay scrubber: per-thread + multi-thread merged-run mode
- Ghost overlay: numbered fired-nodes badges in execution order
- Two draggable cards: ActiveNodeCard (mirrors lit node, large mono),
  RunStepsCard (clickable chronological step list)
- NodeInspector: per-visit cards with diff-vs-previous-step toggle
  (default) and full-state toggle
- Theme toggle (dark / space-gray)
- Lock/unlock tab-following (pin to All view or auto-jump)
- Status counts header, runs sidebar with date dividers + sort modes

### CLI

```
chimera monitor start   # daemonize, auto-build frontend if stale
chimera monitor stop
chimera monitor status
chimera monitor rescan <project>   # refresh metadata cache
```

### Tests (`tests/monitor/`)

10 test modules: AST extraction (entry/end/conditional/for-loop unrolls),
Unicode-safe byte offsets, state decoder roundtrips, project + connection
discovery, redaction, metadata schema validation, extras-missing exit
message, daemon binding assertion, integration smoke.

## Key deviations from original plan

- **Mermaid → React Flow.** Mermaid couldn't deliver the drag/zoom and
  cluster-grouping UX you wanted. Pivoted to React Flow + dagre layout
  mid-build. Ghost overlay and step badges only feasible because of this.
- **Metadata-driven everything.** The original plan didn't include an LLM
  metadata layer. Added during the session because hardcoded heuristics
  (thread parsing, run clustering, scope labels) couldn't generalize
  across LangGraph apps. The scan is the load-bearing piece that makes
  the dashboard work for projects with very different conventions.
- **Run-mode replay.** Original plan was per-thread scrubbing only. You
  asked for "play the whole run start to end" — we built merged-timeline
  multi-thread replay with sister-thread checkpoint interleaving by
  timestamp.
- **Ghost overlay + cards.** Not in the original spec. Emerged from
  iterating on "I want to see what fired in what order without scrubbing."

## Verified against

- **jeevy_portal** (Postgres + Qdrant): 6 graphs enriched, multi-thread
  runs cluster into "Run abc…" cards correctly, diff view surfaces
  LangGraph internal `branch:to:*` channel transitions plus user-state
  changes, replay walks merged 32-step timelines across 3 sister threads
- **chimera** itself (SQLite): topology renders for the 8 compiled graphs,
  metadata scan derives `pattern: ([0-9a-f-]{36})$` for trailing-UUID
  threads

## Bookkeeping done

- `tasks/planned/langgraph-monitor/` → `tasks/active/langgraph-monitor/`
- README.md updated with monitor as top-level feature
- 9 commits squashed-conceptually into 4 thematic commits on `main`

## Phase 2 remaining (deferred to next session)

See TODO.md. Real candidates flagged during the session:

- Stuck-thread detector (sidebar warning on stale-but-running threads)
- SSE live updates (currently RTK polling at 2s — works but burns
  bandwidth on idle dashboards)
- Conversation playback (chat-UI render for graphs with `messages` channel)
- Run timeline events (jeevy-style `*_events` table; lower priority)

Explicitly NOT porting from jeevy: the `/ai-debugger` trace-tree view.
That's a chronological log paradigm that competes with the canvas-first
identity of this dashboard. Decided 2026-05-07.
