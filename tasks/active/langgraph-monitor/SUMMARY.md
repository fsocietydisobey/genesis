# LangGraph Monitor — Summary

**Status:** Phase 1 + most of Phase 2 shipped (2026-05-06 → 2026-05-07).
Still in `tasks/active/` rather than `tasks/completed/` because Phase 2+
items remain on the table.

## What this is

A generic observability dashboard for any LangGraph project. Auto-discovers
projects from the chimera roots registry, introspects compiled `StateGraph`
topology via runtime + AST fallback, tails the checkpointer (Postgres jsonb
or SQLite blob) for live state, and renders an n8n-style canvas with
multi-thread replay, per-step diff inspection, and adaptive stuck detection.

Generic across LangGraph apps — no per-project code required. An optional
LLM metadata cache (Claude Opus high) enriches displays with project
vocabulary, scope kinds, thread-id grouping, run clustering, and per-app
running-threshold values. A runtime observation collector mines checkpoint
history every 5 min and feeds the next refinement scan, so the system gets
sharper with every refresh.

## Phase 1 — shipped 2026-05-06

Foundational dashboard: project discovery, connection discovery (Postgres +
SQLite), AST-based topology extraction, FastAPI backend on `127.0.0.1:8740`,
React/Vite frontend with React Flow canvas, RTK Query polling, replay
scrubber, ghost overlay, NodeInspector, theme toggle. See git history for
details; covered by tests under `tests/monitor/`.

## Phase 2 — shipped 2026-05-07 (today)

### Status detection — every signal now generic

| Signal | Source | Per-app? |
|---|---|---|
| HITL paused | `__interrupt__` channel | LangGraph schema |
| Just started | `source=input, step≤0` | LangGraph schema |
| Terminal (writes) | `metadata.writes` contains `__end__` | When LangGraph populates it |
| Terminal (topology) | AST: only outgoing edges to `__end__` | Per-project, automatic |
| Project running threshold | Metadata scan (`running_threshold_seconds`) | Per-project, LLM-derived (clamped 60-1800s) |
| Per-node running threshold | Observation collector p95 × 2 | Adaptive, learns from history |
| Frontend stale/stuck badges | `running_threshold × {1, 3}` | Scales with backend threshold |

The terminal-via-topology fix was the headline bug — jeevy's LangGraph version
writes `metadata.writes = null` for every checkpoint, so the writes-based
`__end__` detection never fired. Threads stayed "running" for 5+ min after
graph_end. Now they flip to idle the moment they reach a node whose only
outgoing edge goes to `__end__`.

### Auto-follow

- Most-recently-started running thread wins focus (was: most-recently-updated,
  which favored chatty orchestrator over ingest workers).
- Stale manual focus releases when a sister thread (same `scope_id`) gets fresh
  activity — so clicking ingest #17 to inspect doesn't leave the dashboard
  pinned there after digestion spawns.
- Lock-mode focused vs sister-thread visually distinct: emerald pulse for
  focused, sky-blue static ring for sisters.

### Stuck detection

- Frontend staleness classifier flags running threads exceeding `running_threshold`
  (stale) and `running_threshold × 3` (stuck).
- Sidebar / live-runs card / project header all show flagged threads with
  amber/red treatment.
- "Last checkpoint Ns ago" hint on every focused/lit node — surfaces
  "marker hasn't moved but seconds keep ticking" so users understand when
  the next node is running below the checkpointer's resolution.

### Learning loop (the headline Phase 2 work)

Three layers, each cheap on its own:

1. **Observation collector** (no AI) — daemon background task, runs every 5 min.
   Mines per-(graph, node) duration distributions (p50/p95/max) and
   empirical end-node frequencies. Persists to a separate cache file so it
   doesn't race with the LLM scan.

2. **Adaptive per-node thresholds at runtime** (no AI) — when a node has 5+
   observed visits, threshold becomes `max(p95 × 2, max × 1.2, 30s)` capped
   at 1h. Falls back to project-wide default for under-observed nodes. So
   `persist` (jeevy: p95 ~0.1s) gets a tight 30s window while
   `correspondence_phase1` (p95 = 55min) gets the cap.

3. **Refinement scan** (LLM, periodic) — each rescan now reads:
   - codebase (unchanged)
   - previous metadata file (what we decided last time)
   - observation file (what actually happened)
   The LLM compares prior reasoning to new evidence and refines. System
   gets sharper across rescans without extra user effort. Cost: one LLM
   call per refresh interval, never per-poll.

### Bug fixes that shipped today

- `Send`/`Command` objects in checkpoint state crashed FastAPI's JSON encoder
  (500s on threads detail). Fixed via `to_jsonable()` sanitizer.
- chimera's own SQLite checkpoints couldn't decode (msgpack via ormsgpack
  failed on LangGraph's extension types). Fixed by routing through
  `JsonPlusSerializer`.
- Running-threshold of 30s was way too tight for LLM-bearing nodes (jeevy's
  drawing_extract is 60-180s between writes). Bumped default to 300s and
  made it per-project metadata.
- 8 commits worth of cascading UX fixes around auto-follow, multi-thread
  display, focus-release semantics.

## Verified against

- **jeevy_portal** (Postgres + Qdrant): 6 graphs enriched, 58 threads
  mined, observation collector found 37 distinct nodes. Empirical end-nodes
  (`persist` 17×, `commit` 11×, `output_lane` 11×) cross-validated against
  AST-derived terminals. `running_threshold_seconds = 900` derived by Claude
  from the codebase + observations.
- **chimera** itself (SQLite): topology renders, decoder handles msgpack,
  metadata scan derives appropriate thread parsing.

## Distribution

Repo made public at `github.com/fsocietydisobey/chimera`. MIT license. Jeevy
team can clone + `uv pip install -e '.[monitor]'`. Quickstart in README.

## Phase 2 candidates still open (deferred)

See TODO.md. Real candidates:

- **Conversation playback** (chat-UI render of `messages` channel for chat-style
  graphs like jeevy's chat_lane subgraph)
- **SSE upgrade** (replace polling — low priority; polling at 2s feels live)
- **Run timeline events** (jeevy-specific `*_events` table convention; requires
  per-project event-source config to stay generic)

Explicitly NOT porting from jeevy: the `/ai-debugger` trace-tree view.
That's a chronological log paradigm that competes with the canvas-first
identity of this dashboard. Decided 2026-05-07.
