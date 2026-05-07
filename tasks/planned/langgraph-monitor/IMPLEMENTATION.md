# LangGraph Monitor

> Zero-instrumentation observability for LangGraph apps. Auto-discovers a project's graphs, connects to its Postgres + Qdrant + workers, surfaces topology and runtime state through a local web dashboard. Differentiator vs LangSmith / LangGraph Studio: attaches to any langgraph project without SDK calls or `langgraph dev` server.

## 1. Context / Background

**The pain.** Debugging a LangGraph run today means stitching together: `psql` queries against the checkpointer tables, raw msgpack-deserialized state blobs, log tails from worker processes, occasional Qdrant SDK calls, and your own mental model of the graph topology. There's no single place where state, topology, and runtime activity converge.

**Why chimera should host this.** Chimera already has the registered-roots registry (cross-project file access), runs as a daemon-capable Python process, and has the LangGraph dependencies + AsyncPostgresSaver knowledge baked in. Adding a local web dashboard turns chimera from "wrapper around Claude/Gemini" into a genuine *sensory access* tool — same category as Specter (browser), Séance (semantic code), Scarlet (AST). That positioning is what makes chimera worth keeping.

**Differentiator.** LangSmith requires SDK telemetry calls in your code, cloud-hosted, paid. LangGraph Studio only monitors graphs spawned via `langgraph dev`. OpenTelemetry / Datadog require instrumentation. Chimera-monitor is **zero-instrumentation** — point it at a project, it discovers the graphs by AST and reads runtime state directly from Postgres + Qdrant. No SDK calls, no vendor, all local.

## 2. Current State

**No monitor exists yet.** But jeevy_portal already ships an AI Debugger with most of the UI primitives we need. The Next.js feature folder lives at `/home/_3ntropy/work/jeevy_portal/frontend/src/features/ai-debugger/` and includes:

- `AIDebuggerShell.js` — full-viewport shell, header + collapsible sidebar + content area
- `shell/shellRegistry.js` — view-plugin pattern (drop a new view in, it shows up in the sidebar)
- `views/langgraph/StateTab.js` — run state + sources + event history with collapsible sections
- `views/langgraph/EventsTab.js` — timeline events
- `views/langgraph/JsonTree.js` — recursive collapsible JSON renderer
- `views/langgraph/eventClassify.js` — event categorization heuristics
- `views/langgraph/context.js` — SSE-driven state cache + lazy source-checkpoint fetch
- `views/qdrant/{Collections,Search,Sample}Tab.js` + `PointDetailModal.js`
- `LangGraphView.module.css` — dark theme, status pills, pulse animations
- Popout-window pattern: `/ai-debugger` is in `STANDALONE_PATHS` and renders bare (no app chrome). This is exactly the "monitoring popup" the task targets.

**Strategy:** lift these components into the chimera-monitor frontend. Don't reinvent. Components are well-factored — they don't depend on jeevy's RTK store; they use their own context hooks. Porting cost is moderate, not zero.

## 3. Target Behavior

A `chimera monitor` CLI command that:

1. Daemonizes a FastAPI server on `127.0.0.1:<port>` (default 8740, configurable).
2. Opens a browser tab to the dashboard.
3. Discovers all LangGraph projects from chimera's roots registry (`~/.config/chimera/roots.yaml`).
4. For each project: AST-extracts graph topology, connects to its Postgres + Qdrant, exposes via API.
5. Frontend (Vite + React + RTK + shadcn + Mermaid.js) renders the dashboard.
6. Survives Claude Code restarts — true daemon, not an MCP child.
7. `chimera monitor stop` kills it cleanly.

Multi-project sidebar nav. Each project has its own routes: `/<project>/topology`, `/<project>/threads`, `/<project>/qdrant`, etc.

## 4. Stack Decisions

**Frontend** (locked):

- **Vite + React + RTK Query + Redux Toolkit** — explicitly NOT Next.js. Joseph dislikes Next bloat.
- **shadcn/ui** — Radix-based, copy-paste components, no runtime dep beyond a small CLI.
- **Tailwind CSS** — required by shadcn.
- **Mermaid.js** via CDN — for topology rendering.
- **React Router** — multi-project routing.
- **Lift from jeevy:** `JsonTree.js`, `eventClassify.js`, the shell registry pattern, the dark-theme CSS (port from CSS modules to Tailwind), Qdrant tabs.

**Backend** (locked):

- **FastAPI** — already a transitive chimera dep via `mcp[cli]`.
- **uvicorn** for the daemon.
- **psutil** for process inspection (already a chimera dep).
- **psycopg[binary]** for Postgres access — *optional* via `chimera[monitor]` extra.
- **aiosqlite** for SQLite checkpointer access — already a chimera dep (langgraph-checkpoint-sqlite pulls it).
- **qdrant-client** — *optional* via `chimera[monitor]` extra; not used until Phase 2.
- **tree-sitter-python** — *optional* via `chimera[monitor]` extra; runtime introspection is preferred over AST when available.
- **SSE** for live updates — server uses asyncio queues, client uses native `EventSource`. WebSockets deferred to Phase 5 (when interactive write-side lands).

All optional deps gated behind `chimera[monitor]`. Daemon entrypoint imports lazily; if a dep is missing, prints `Install monitor extras: uv pip install 'chimera[monitor]'` and exits cleanly.

**Wire format:** JSON over HTTP + SSE. RTK Query handles polling + cache invalidation client-side (single API slice, no UI Redux slices — minimal usage).

**Daemonization:** `chimera monitor start` uses `os.fork()` + `os.setsid()` + stdio redirect to `~/.local/state/chimera/monitor.log`. ~30 lines, no external dep. PID at `~/.local/share/chimera/monitor.pid`. `stop` reads PID and SIGTERMs (SIGKILL after 5s). `status` checks PID liveness and reports URL. Alternative: register as a `systemctl --user` service — defer to user choice, don't ship a unit file by default.

**Live updates: polling, not LISTEN/NOTIFY — and client-side polling in Phase 1.** AsyncPostgresSaver ships no triggers; installing one would violate zero-instrumentation. Phase 1: RTK Query `pollingInterval: 2000` polls the REST endpoints from the browser. Backend query uses an indexed `(thread_id, checkpoint_id)` cursor filtered by `updated_at > last_seen`, never `SELECT *`. Phase 2 absorbs polling server-side and pushes diffs over SSE — same backend code path, push instead of pull. Same approach works for SQLite (poll mtime + query) — uniform across both backends.

**Topology extraction: runtime introspection first, AST fallback.** Importing the project's graph factory module and reading `compiled_graph.nodes` / `compiled_graph.get_graph().edges()` is faster and accurate. Tree-sitter AST walking only runs when import fails (missing deps in the target project's venv) or when factory functions use dynamic node names (e.g. chimera's own factories). The AST result is marked "(approximate — graph uses dynamic node construction)" in the UI.

**Auto-build:** the daemon checks for `monitor_ui/dist/` on startup. If missing or older than the newest source file in `monitor_ui/src/`, it runs `npm run build` synchronously and reports progress before serving. `dist/` is gitignored. The user never touches the build step.

**Dev workflow:** when iterating on the frontend, run `npm run dev` from `monitor_ui/`. Vite serves on `localhost:5173` with HMR; `vite.config.ts` proxies `/api` and `/sse` to the FastAPI daemon (default port `8740`). Production path (the daemon serving `dist/` directly) is the same code, different invocation.

## 5. Feature Inventory

Grouped by category. Phasing in §6.

### Topology + threads (foundation — Phase 1)

- Auto-discover LangGraph projects from `chimera.cli.config.ROOTS` (presence of `langgraph` dep + `StateGraph` somewhere in the tree)
- Auto-detect Postgres + SQLite checkpointer connection strings from project `.env` files
- **Topology via runtime introspection** (import + read `compiled_graph.get_graph()`); AST fallback via tree-sitter when import fails
- Mermaid render of every discovered compiled graph in the project
- Threads list — paginated, filterable by status (running / paused / completed / failed) — works against AsyncPostgresSaver AND SQLite checkpointer
- Single thread view — current node, last update, deserialized state via JsonTree
- Lazy-load source checkpoints when expanded (port from jeevy's debugger context)
- **Live updates via 1–2s polling**, pushed to clients over SSE (no Postgres triggers — preserves zero-instrumentation)
- **Default redaction layer** — column-name allowlist with secure defaults (`*email*`, `*password*`, `*token*`, `*secret*`, `*ssn*`, `*pii*` always redacted to `<redacted>` in state payloads)
- Startup banner: "monitoring N projects — local DBs only, do not point at prod" with the discovered DB hosts shown

### Run-level deep inspection (Phase 2)

- **Qdrant view** — Collections / Sample / Search tabs ported from jeevy's debugger (deferred from Phase 1 — not on the critical "see state, render topology" path)
- **LLM call inspector** — for any node, full prompt + response of every LLM call, token counts, latency
- **Tool call trace** — per-node tool invocations with args, return, latency, retries
- **Cost / token attribution per node** — roll up `usage_metadata` from message history into per-node and per-run breakdowns
- **Stream replay** — play `astream` output of a finished thread at 1x or 5x
- **Stuck-thread detector** — surface threads whose last checkpoint is >N min old with status `running`
- **Run timeline** — chronological event feed (project-conditional; only renders if a `*_events` table is detected)
- **Conversation playback** — for graphs with `messages` in state, render as scrollable chat UI

### Comparison + analytics (Phase 3)

- **State diff between checkpoints** — git-diff-style for serialized state, same thread or across threads
- **Run A/B compare** — two runs of the same graph end-to-end with divergence highlighting
- **Topology diff between git commits** — AST walk at HEAD vs main, surface "renamed node X, removed edge Y, changed reducer on field Z"
- **Heat map** — color overlay on topology by node activity (24h / 7d) — find hot bottlenecks and dead nodes
- **Performance baseline** — track node latency p50/p95 over time, alert on drift
- **Live cost ticker** — single header number: $ spent today across all chimera-monitored projects, ticks up live

### Search + query (Phase 4)

- **Search threads by state field** — "all threads where `deliverable_id == X`" or "all threads paused at HITL output gate"
- **Search by tool call** — "every run that invoked `search_source_extractions`"
- **Search by error** — "every thread that hit `429` in Phase 1 in the last 7 days"
- **Cross-thread semantic search** — embed each run's `(task description, final state, key messages)` into Qdrant; search with natural language ("runs where the user got frustrated") — reuses the project's existing Qdrant infrastructure

### Discovery + docs (Phase 4)

- **Auto-generated state schema docs** — walk TypedDict definitions, surface field types + reducers + reading-nodes / writing-nodes — a live, accurate state spec
- **Self-documenting state schema** — Gemini reads node code + docstrings + tests, generates "what is this field for?" docs per field
- **Node responsibility view** — extract docstrings, surface alongside the topology
- **Tool catalog per profile** — for projects with profile/agent variants (jeevy has estimator + project_manager), show which tools each profile binds

### Cross-project (Phase 5)

- **Side-by-side topology compare** — two projects rendered in adjacent Mermaid panels
- **"Where else is this pattern used?"** — click a node, chimera scans other registered projects for similarly-shaped subgraphs
- **Deprecated-node finder** — combine AST + runtime checkpointer history; flag nodes never entered in N days

### Interaction / write-side (Phase 5, gated behind a "this is dangerous" badge)

- **Resume paused HITL** — approve / reject from the dashboard instead of the product UI
- **Force rewind** — fork a thread from a checkpoint with optional state edits
- **Inject state mid-run** — edit a state field on a running thread (with confirmation)
- **Cancel stuck thread** — send `Command(goto=END)` to terminate

### Out-there features (Phase 6 — lowest-effort first, ship in any order)

- **AI run narrative** — Gemini summarizes a run's timeline as English prose, click "explain this run"
- **AI run journal** — auto-generated post-mortems for any thread that errored or got stuck, browsable
- **Auto-fixture generator** — "save this run as a fixture" → exports state as a `pytest` fixture, real runs become regression tests
- **Time-travel scrubber** — slider across all checkpoints of a thread, drag to any point, see state at that step (video-player UX)
- **Topology heatmap with traffic** — already in Phase 3, but with animation: pulse nodes as they're entered in real time
- **Ghost-arrow predictor** — for paused threads, ask Claude/Gemini to predict next node, render as translucent arrow on topology with "why?" button
- **Agent ghost-mode** — replay a finished thread with a different model (Claude→Gemini), see node-by-node divergence — built-in cross-model arbitration without touching prod
- **DNA fingerprint + clustering** — fingerprint = `[sequence of nodes visited, hash of final state shape]`, cluster similar runs
- **State surface flash** — when a mutation happens (e.g. `update_langgraph_state` lands), affected Postgres tables + Qdrant collections briefly glow in the UI
- **Anomaly detector** — running statistical baseline of state shape per node, flag drift (no labels needed)
- **"What changed?" between deployments** — combine topology-diff + performance-baseline; "yesterday's Phase 1 averaged 32s, today's averages 91s — what node changed?"
- **Topology diff PR comment** — git hook posts AST-topology diff as PR comment (Codecov-style but for graph structure)
- **Voice mode** — narrate runs in real-time. Honestly probably skip; here for completeness

### NOT building

- Multi-user / org features — solo personal tool
- Native instrumentation SDK — would break the zero-instrumentation positioning
- Log aggregation — that's not what monitor is for, stay focused
- Cloud hosting — local-only, `127.0.0.1` is the auth layer

## 6. Phased rollout

| Phase | Scope | Ships when |
|---|---|---|
| 1 — Foundation | Daemon, auto-build, project discovery, topology view (introspection + AST fallback), threads list, state inspector, redaction layer, extras-gating, AsyncPostgresSaver only, RTK Query polling for live updates | Threads list shows real jeevy data, state inspector renders msgpack-deserialized state with PII redacted |
| 2 — Run inspection | **Qdrant view** (deferred from Phase 1), **SSE live updates** (replaces RTK Query polling), **EventsTab port**, **SQLite checkpointer support** (dogfood against chimera's own chains), LLM/tool traces, cost attribution, stream replay, stuck-thread detector, run timeline, conversation playback | Click a finished thread → see every LLM call inline; chimera's own chains visible in monitor |
| 3 — Comparison + analytics | State diff, A/B compare, topology diff, heat map, perf baseline, live cost ticker | Two runs of the same graph render side-by-side with divergence highlighted |
| 4 — Search + discovery | All search modes, semantic search, schema docs, node responsibilities, tool catalog | "Find runs where Phase 1 escalated" returns results |
| 5 — Cross-project + interactive | Topology compare, pattern discovery, deprecated-node finder, write-side actions | Resume a paused HITL from the dashboard |
| 6 — Out-there | AI narrative, fixture gen, time-travel, ghost mode, anomaly detector, etc. | One feature at a time, ship in any order |

Each phase is independently shippable. Phase 6 features can be cherry-picked based on what's actually missed during use.

### Cut order if Phase 1 scope expands

Pre-identified so it's not litigated under pressure. Drop in this order — recover scope without losing core value:

1. Approximate-topology UI badge (ship the data, hide the badge)
2. Threads list pagination polish (show first 100, no pager)
3. Multi-project sidebar (start single-project, hardcoded)
4. Lazy-load source checkpoints (load all on thread open)
5. Auto-build polish (require manual `npm run build` for first ship)
6. Shell sidebar polish (collapse animations, etc.)

**Never cut:** runtime introspection, redaction layer, `127.0.0.1` binding assertion, extras-gating, integration smoke test, Mermaid topology rendering.

## 7. File Map

### chimera repo additions

```
chimera/
  src/chimera/
    monitor/
      __init__.py
      cli.py                  # `chimera monitor start/stop/status` subcommands
      daemon.py               # os.fork() + setsid() + stdio redirect, reuses pidlock.py
      server.py               # FastAPI app, asserts 127.0.0.1 binding
      build.py                # auto npm run build when dist/ missing or stale
      api/
        projects.py           # list registered projects, discovery
        topology.py           # introspection + AST, Mermaid generation
        threads.py            # checkpointer queries, polling-friendly indexed cursor
        qdrant.py             # Phase 2 — collection + point inspection
        events.py             # Phase 2 — generic *_events / *_runs table support
        sse.py                # Phase 2 — server-side polling pushed via SSE
      discovery/
        project.py            # detect langgraph projects from config.ROOTS
        connections.py        # parse .env files for DB URLs (Qdrant in Phase 2)
        introspector.py       # primary topology — runtime introspection
        ast_walker.py         # fallback topology — tree-sitter
        state_decoder.py      # msgpack/ormsgpack-aware deserialization
        redaction.py          # column-name allowlist redactor
    monitor_ui/               # Vite + React + RTK + shadcn frontend
      package.json
      vite.config.ts
      tailwind.config.ts
      components.json         # shadcn config
      src/
        App.tsx
        store.ts              # RTK store
        api.ts                # RTK Query API slice
        components/
          shell/              # ported from jeevy: AIDebuggerShell, ShellHeader, ShellSidebar
          topology/
            TopologyView.tsx
            MermaidPanel.tsx
            HeatmapOverlay.tsx
          threads/
            ThreadsList.tsx
            ThreadDrawer.tsx
            JsonTree.tsx     # ported from jeevy
            StateTab.tsx     # ported from jeevy
            EventsTab.tsx    # ported from jeevy
            LLMCallInspector.tsx
            ConversationPlayback.tsx
          qdrant/             # ported from jeevy
          ui/                 # shadcn primitives (Button, Tabs, Drawer, Dialog, etc.)
        routes/
          ProjectRoutes.tsx
        hooks/
          useSSE.ts
        styles/
          globals.css
  tests/
    monitor/
      test_discovery.py       # project detection
      test_ast_walker.py      # topology extraction
      test_state_decoder.py   # msgpack roundtrip
  pyproject.toml              # define [monitor] extra: psycopg[binary], tree-sitter-python, uvicorn[standard]; FastAPI as direct dep (transitive via mcp[cli], pinned for safety); qdrant-client added in Phase 2
```

### Slash command in `~/.claude/commands/`

- `chimera-monitor.md` — wraps `chimera monitor start/stop/status` (ergonomics, last to land)

## 8. Risks / Gotchas

- **Daemonization edge cases.** double-fork + `setsid` + stdio redirect + PID file + clean SIGTERM shutdown. ~30 lines but every line matters. `python-daemon` is **not** the answer here — it's maintenance-abandoned (last release 2021) and has known Python 3.12+ compat issues. Reuse chimera's existing `pidlock.py` for PID management.
- **State deserialization.** AsyncPostgresSaver uses msgpack + ormsgpack with a custom serializer config. Reading the raw bytes requires the same config. Build a tolerant decoder that gracefully handles unknown types (display as opaque blob, don't crash).
- **Multi-tenant safety.** Pointed at a prod DB, the inspector shows everything. Server-side redaction layer with default column-name allowlist (`*email*`, `*password*`, `*token*`, `*secret*`, `*ssn*`, `*pii*` → `<redacted>`). Applied in/above `state_decoder.py` before JSON serialization — never client-side. Defense in depth alongside the `127.0.0.1` binding.
- **Scope creep.** The full feature inventory is large. Hard rule: keep Phase 1 small. The cut-order list in §6 is the pre-committed answer — never expand the phase scope, drop items in that order if you find yourself reaching.
- **Borrowed jeevy code drift.** Locked decision: re-port at every phase boundary. `scripts/check_jeevy_drift.py` diffs lifted files (`JsonTree`, `StateTab`, `MonitorShell` in Phase 1) against their jeevy origins and prints unified diffs of upstream changes since the last port. Run pre-ship for each phase. npm package extraction was considered and rejected (single-consumer overhead).
- **Vite + Node.js dep in chimera.** Chimera was Python-only; adding a frontend means Node.js for development (not runtime — Vite builds static assets that FastAPI serves). Document the dev setup clearly. Consider committing the built `dist/` to avoid forcing Node on chimera consumers.
- **Polling performance.** Per-project polling against the checkpointer tables every 1–2s. Use an indexed cursor over `(thread_id, checkpoint_id)` filtered by `updated_at > last_seen`, **not** `SELECT *`. Cheap at jeevy's volume; revisit only if it becomes a bottleneck. Phase 2 SSE will absorb server-side polling and push diffs over a single connection per client — at that point add server-side throttling (max N events/sec per project) for projects with 10000+ checkpoints/day.
- **Heterogeneous langgraph projects.** Not every project uses AsyncPostgresSaver — some use SQLite, in-memory, or none. Phase 1 supports Postgres only; SQLite lands in Phase 2; in-memory documented as Phase 6 backlog.
- **Auth.** `127.0.0.1` binding is the auth layer. Don't accidentally bind to `0.0.0.0`. Startup assertion + dedicated test (`tests/monitor/test_binding.py`).

## 9. Verification

### Phase 1 acceptance

- [ ] `chimera monitor start` daemonizes; survives killing the current shell
- [ ] Missing monitor extras → clean exit message (`Install monitor extras: ...`), no traceback
- [ ] Startup banner prints `monitoring N projects — local DBs only, do not point at prod` with discovered DB hosts before serving
- [ ] Dashboard auto-discovers jeevy_portal from the roots registry
- [ ] Topology view renders jeevy's orchestrator graph (root + 4 subgraphs) as Mermaid via runtime introspection
- [ ] Topology view renders chimera's own graphs via AST fallback, badged `(approximate — graph uses dynamic node construction)`
- [ ] Threads list paginates correctly with 100+ threads
- [ ] State inspector deserializes msgpack state and renders via JsonTree
- [ ] Redaction: a state field named `user_email` is rendered as `<redacted>` end-to-end (server-side)
- [ ] Live update via RTK Query polling: trigger a state write in jeevy, dashboard refreshes within 2s
- [ ] `chimera monitor stop` kills the daemon cleanly; no orphan processes

### Phase 2 acceptance

- [ ] Click a thread → see LLM calls with prompts + responses
- [ ] Cost attribution sums to within 5% of the LLM provider's billing dashboard
- [ ] Stream replay produces same outputs as the original run
- [ ] Stuck-thread detector surfaces a deliberately-stalled test run

### Cross-cutting

- [ ] Pointed at a project WITHOUT langgraph deps → graceful "no langgraph projects detected" message, no crash
- [ ] Pointed at a project WITH langgraph but WITHOUT Postgres checkpointer → topology view works, threads view shows "no checkpointer detected"
- [ ] Multi-project switching: jeevy_portal + a synthetic test project both render correctly in the same session
- [ ] `127.0.0.1` binding enforced — startup fails if `0.0.0.0` is configured

## 10. Locked decisions (2026-05-06)

- **Borrowed-code strategy:** re-port jeevy's debugger components at every chimera-monitor phase boundary. `scripts/check_jeevy_drift.py` diffs lifted files against their jeevy origins pre-ship. Single-consumer tool; npm package overhead isn't justified.
- **State decoder scope:** AsyncPostgresSaver in Phase 1. SQLite added in Phase 2 (unlocks dogfooding chimera-monitor against chimera's own chain runs). In-memory skipped.
- **UI component library:** shadcn/ui. Copy-paste components, owned in-repo, use built-in dark mode (custom jeevy theme port deferred).
- **Default port:** `8740`, overridable via `CHIMERA_MONITOR_PORT` env var.
- **Build artifacts:** `dist/` is gitignored. `chimera monitor start` runs `npm run build` automatically when `dist/` is missing or source has changed since the last build. The build step is internal to the daemon — user never invokes it.
- **Daemonization:** `os.fork()` + `os.setsid()` + stdio redirect; reuse existing `pidlock.py`. No `python-daemon` dep — maintenance-abandoned with Python 3.12+ compat issues.
- **Live updates:** RTK Query `pollingInterval: 2000` in Phase 1; SSE deferred to Phase 2. **Never** Postgres `LISTEN/NOTIFY` — installing a trigger would violate zero-instrumentation.
- **Topology extraction:** runtime introspection primary (`compiled_graph.get_graph()`); tree-sitter AST fallback when import fails or factory uses dynamic node names. UI badges AST-derived results as `(approximate — graph uses dynamic node construction)`.
- **Optional deps:** gated behind `chimera[monitor]` extra (`psycopg[binary]`, `tree-sitter-python`, `uvicorn[standard]` in Phase 1; `qdrant-client` added in Phase 2). Daemon entrypoint lazy-imports with clean `Install monitor extras: uv pip install 'chimera[monitor]'` exit message if missing.
- **Qdrant view:** deferred to Phase 2 — not on the critical "see state, render topology" path.
- **Redaction:** server-side, default column-name allowlist (`*email*`, `*password*`, `*token*`, `*secret*`, `*ssn*`, `*pii*` → `<redacted>`); applied in/above `state_decoder.py` before JSON serialization.
