# TODO — LangGraph Monitor

> Phased rollout. Each phase ships independently. See [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) for the full feature inventory + rationale.

## Decisions locked (2026-05-06)

- **Borrowed-code strategy:** re-port jeevy's debugger components at every phase boundary; `scripts/check_jeevy_drift.py` diffs lifted files against their jeevy origins and is run pre-ship for each phase
- **State decoder:** AsyncPostgresSaver in Phase 1, SQLite in Phase 2
- **UI library:** shadcn/ui — use its built-in dark mode; defer custom jeevy theme port
- **Default port:** 8740, overridable via `CHIMERA_MONITOR_PORT`
- **Build:** `dist/` gitignored; daemon auto-runs `npm run build` when missing or stale
- **Daemonization:** `os.fork()` + `os.setsid()` + stdio redirect; reuse existing `pidlock.py`. No `python-daemon` dep — it's maintenance-abandoned and has Python 3.12+ compat issues
- **Live updates:** client-side polling via RTK Query `pollingInterval: 2000` in Phase 1; SSE deferred to Phase 2. **Never** Postgres `LISTEN/NOTIFY` — installing a trigger would violate zero-instrumentation
- **Topology:** runtime introspection primary (`compiled_graph.get_graph()`); tree-sitter AST fallback when import fails or factory uses dynamic node names; UI badges AST-derived results as `(approximate — graph uses dynamic node construction)`
- **Optional deps:** gated behind `chimera[monitor]` extra; daemon entrypoint lazy-imports with `Install monitor extras: uv pip install 'chimera[monitor]'` exit message if missing
- **Qdrant view:** deferred to Phase 2 (not on the critical "see state, render topology" path)
- **Redaction:** server-side, default column-name allowlist (`*email*`, `*password*`, `*token*`, `*secret*`, `*ssn*`, `*pii*` → `<redacted>`); applied in/above `state_decoder.py` before JSON serialization

## Phase 1 — Foundation

### Backend

- [ ] Define `[monitor]` optional extra in `pyproject.toml`: `psycopg[binary]`, `tree-sitter-python`, `uvicorn[standard]`. FastAPI listed as direct dep with comment noting transitive via `mcp[cli]`. `qdrant-client` deferred to Phase 2.
- [ ] Lazy-import scaffolding: monitor entrypoint imports optional deps inside functions; missing-dep path prints `Install monitor extras: uv pip install 'chimera[monitor]'` and exits cleanly. Build this first — every other backend task depends on it.
- [ ] `src/chimera/monitor/cli.py` — `start` / `stop` / `status` subcommands wired into chimera entry point
- [ ] `src/chimera/monitor/daemon.py` — `os.fork()` + `os.setsid()` + stdio redirect to `~/.local/state/chimera/monitor.log`; PID at `~/.local/share/chimera/monitor.pid` via existing `pidlock.py`; SIGTERM handler for clean shutdown (SIGKILL after 5s)
- [ ] `src/chimera/monitor/build.py` — auto-build helper: detect missing/stale `monitor_ui/dist/` (mtime vs newest source under `monitor_ui/src/`), run `npm run build`, surface progress
- [ ] `src/chimera/monitor/server.py` — FastAPI app, `127.0.0.1` binding asserted at startup (raise on `0.0.0.0`), `CHIMERA_MONITOR_PORT` env override (default 8740)
- [ ] Startup banner — after discovery completes, before serving: print `monitoring N projects — local DBs only, do not point at prod` with the discovered DB hosts. Pre-serve phase, not behind a log level.
- [ ] `src/chimera/monitor/discovery/project.py` — detect langgraph projects from `config.ROOTS`
- [ ] `src/chimera/monitor/discovery/connections.py` — parse project `.env` for Postgres URLs (Qdrant URLs deferred to Phase 2)
- [ ] `src/chimera/monitor/discovery/introspector.py` — primary topology path: import the project's graph factory module, read `compiled_graph.get_graph().nodes` / `.edges()`. Returns `{nodes, edges, source: "introspection"}`.
- [ ] `src/chimera/monitor/discovery/ast_walker.py` — fallback only: tree-sitter walk for `StateGraph` nodes/edges/subgraphs when introspection raises or returns dynamic-node markers. Returns `{nodes, edges, source: "ast", approximate: true}`.
- [ ] `src/chimera/monitor/discovery/state_decoder.py` — msgpack/ormsgpack-aware deserializer with tolerant fallback for unknown types (display as opaque blob, don't crash)
- [ ] `src/chimera/monitor/discovery/redaction.py` — column-name allowlist redactor; recursive over nested dicts and lists of dicts; applied to every state payload before JSON serialization
- [ ] `api/projects.py` — list, switch, metadata
- [ ] `api/topology.py` — Mermaid generation per compiled graph; pass through the `approximate` flag so the UI can badge it
- [ ] `api/threads.py` — paginated list, single-thread detail; polling-friendly query uses indexed `(thread_id, checkpoint_id)` cursor filtered by `updated_at > last_seen`, not `SELECT *`

### Frontend

- [ ] `src/chimera/monitor_ui/` — Vite + React + TS scaffold
- [ ] Tailwind + shadcn init (`components.json`, `tailwind.config.ts`); use shadcn's built-in dark mode (no custom theme port)
- [ ] `vite.config.ts` — proxy `/api` to FastAPI on port 8740 for dev (HMR via `npm run dev` on `localhost:5173`)
- [ ] RTK store + RTK Query API slice with `pollingInterval: 2000` on threads/topology endpoints
- [ ] React Router routes per project
- [ ] Port `JsonTree` from jeevy's debugger
- [ ] Port `StateTab` from jeevy's debugger
- [ ] Port shell pattern: `AIDebuggerShell` → `MonitorShell`, header + sidebar + content (the navigation pattern everything else plugs into — port this first)
- [ ] Mermaid via npm package (not CDN — plays nicer with the Vite build); topology component renders compiled graph
- [ ] Approximate-topology UI badge — when `api/topology` returns `approximate: true`, show `(approximate — graph uses dynamic node construction)` next to the diagram
- [ ] Build script writes static assets that FastAPI serves

### Tests

- [ ] `tests/monitor/test_discovery.py` — project + connection detection
- [ ] `tests/monitor/test_introspector.py` — runtime introspection on a fixture graph
- [ ] `tests/monitor/test_ast_walker.py` — topology extraction on jeevy's `core/agents/graphs/` (fallback path)
- [ ] `tests/monitor/test_state_decoder.py` — msgpack roundtrip + unknown-type fallback
- [ ] `tests/monitor/test_redaction.py` — allowlist patterns; nested dicts; lists of dicts; redaction is server-side and irreversible on the wire
- [ ] `tests/monitor/test_extras_missing.py` — verify clean exit message when monitor extras not installed
- [ ] `tests/monitor/test_binding.py` — assert `127.0.0.1` enforced; startup fails on `0.0.0.0`
- [ ] Integration smoke: `chimera monitor start` against a fixture project, hit `/api/projects`, get expected payload

### Slash command

- [ ] `~/.claude/commands/chimera-monitor.md` — wraps start/stop/status

### Pre-ship

- [ ] `scripts/check_jeevy_drift.py` — diffs lifted files (`monitor_ui/src/components/threads/JsonTree.tsx`, `StateTab.tsx`, `MonitorShell.tsx`) against their jeevy origins; prints unified diffs of upstream changes since the last port
- [ ] Run `check_jeevy_drift.py`; re-port any meaningful drift before shipping

### Acceptance

- [ ] `chimera monitor start` daemonizes; survives shell exit
- [ ] Browser opens to dashboard, auto-discovers jeevy_portal
- [ ] Topology view renders jeevy's orchestrator graph as Mermaid (introspection path)
- [ ] Topology view renders chimera's own graphs with `(approximate)` badge (AST fallback path)
- [ ] Threads list paginates with 100+ threads
- [ ] State inspector deserializes + renders via JsonTree
- [ ] Redaction: a state field named `user_email` is rendered as `<redacted>` end-to-end
- [ ] Live update on a real state write within 2s (RTK Query polling)
- [ ] Startup banner prints expected DB hosts before serving
- [ ] Missing extras → clean exit message, no traceback
- [ ] `chimera monitor stop` kills cleanly

## Phase 2 — Run inspection

- [ ] **SQLite checkpointer support** — extend `state_decoder.py` + connection discovery to handle `langgraph-checkpoint-sqlite` backend. Unlocks dogfooding chimera-monitor against chimera's own chain runs.
- [ ] **Qdrant view** — add `qdrant-client` to `[monitor]` extra; `api/qdrant.py` (collections + sample points); port `CollectionsTab`, `SearchTab`, `SampleTab`, `PointDetailModal` from jeevy's debugger
- [ ] **SSE live updates** — `api/sse.py` (server-side polling pushed to clients via asyncio queues); `useSSE.ts` hook on the frontend; `vite.config.ts` proxy with explicit timeout config so dev SSE connections don't get severed
- [ ] **EventsTab port** — chronological event feed (port from jeevy, used by run timeline below)
- [ ] LLM call inspector — extract from message history, render prompts + responses
- [ ] Tool call trace — args / return / latency / retries per node
- [ ] Cost / token attribution per node — roll up `usage_metadata`
- [ ] Stream replay — playback finished `astream` output at 1x / 5x
- [ ] Stuck-thread detector — surface threads with stale-but-running status
- [ ] Run timeline — auto-detect `*_events` table, render chronologically (jeevy's `run_timeline_events` is the canary)
- [ ] Conversation playback — chat-UI render for graphs with `messages` in state

## Phase 3 — Comparison + analytics

- [ ] State diff between two checkpoints
- [ ] Run A/B compare with divergence highlighting
- [ ] Topology diff between git commits (AST walk at HEAD vs main)
- [ ] Heat map overlay on topology (24h / 7d node activity)
- [ ] Performance baseline (p50 / p95 per node, drift alerts)
- [ ] Live cost ticker (header)

## Phase 4 — Search + discovery

- [ ] Search threads by state field
- [ ] Search by tool call
- [ ] Search by error
- [ ] Cross-thread semantic search (embed run summaries to project's Qdrant)
- [ ] Auto-generated state schema docs (TypedDict walk)
- [ ] Self-documenting state schema via Gemini (cached, regenerated on schema change)
- [ ] Node responsibility view (docstring extraction)
- [ ] Tool catalog per profile

## Phase 5 — Cross-project + interactive

- [ ] Side-by-side topology compare across registered projects
- [ ] "Where else is this pattern used?" — node similarity search across projects
- [ ] Deprecated-node finder (AST + checkpointer history)
- [ ] Resume paused HITL from dashboard (write-side, with confirmation)
- [ ] Force rewind (fork from checkpoint)
- [ ] Inject state mid-run (with confirmation)
- [ ] Cancel stuck thread (`Command(goto=END)`)

## Phase 6 — Out-there features

Ship one at a time, lowest-effort first:

- [ ] AI run narrative (Gemini summarizes timeline as prose)
- [ ] AI run journal (auto post-mortem for errored / stuck runs)
- [ ] Auto-fixture generator (real run → pytest fixture file)
- [ ] Time-travel scrubber (slider across all checkpoints, video-player UX)
- [ ] Topology heatmap with live traffic animation
- [ ] Ghost-arrow predictor (next-node prediction for paused threads, "why?" button)
- [ ] Agent ghost-mode (replay with different model, cross-model arbitration)
- [ ] DNA fingerprint + clustering (run twins)
- [ ] State surface flash on mutation
- [ ] Anomaly detector (statistical baseline, flag drift)
- [ ] "What changed?" between deployments (topology + perf diff)
- [ ] Topology diff PR comment (git hook)
- [ ] Voice mode (probably skip)

## Cross-cutting

- [ ] All phases: Black + ruff clean
- [ ] All phases: `127.0.0.1` binding asserted at startup; test for the assertion
- [ ] All phases: run `scripts/check_jeevy_drift.py` before shipping; re-port any meaningful drift

### Cut order if Phase 1 scope expands

Drop in this order — recover scope without losing core value:

1. Approximate-topology UI badge (ship the data, hide the badge)
2. Threads list pagination polish (show first 100, no pager)
3. Multi-project sidebar (start single-project, hardcoded)
4. Lazy-load source checkpoints (load all on thread open)
5. Auto-build polish (require manual `npm run build` for first ship)
6. Shell sidebar polish (collapse animations, etc.)

Never cut: introspection, redaction, `127.0.0.1` assertion, extras-gating, integration smoke test, Mermaid topology rendering.

## Lifecycle

- [ ] Phase 1 ships → move task from `tasks/planned/` to `tasks/active/`
- [ ] All phases complete → move to `tasks/completed/`
- [ ] Generate SUMMARY.md
- [ ] Update chimera README.md with monitor as a top-level feature
