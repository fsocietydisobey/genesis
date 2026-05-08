# Changelog

Format inspired by [Keep a Changelog](https://keepachangelog.com/).
Versions follow rough semver but pre-1.0 — minor bumps are allowed
to break things.

## [Unreleased]

### Added
- **Skill pack** (`.claude/skills/`) — chimera as a Claude Code
  distribution that turns it into a LangGraph-aware dev environment:
  - `debug-runtime-issue` — investigate stuck/failing/slow runs by
    composing chimera-monitor + séance + scarlet + postgres MCPs
  - `feature-impact-analysis` — given a proposed change, map all
    affected layers (DB → API → graph → UI → tests) before editing
  - `full-stack-trace` — follow a user action through every layer
    to identify where the chain broke
- **`chimera install [target]`** — copies the skill bundle into a
  project's `.claude/skills/`. Idempotent; backs up existing skills.
- **`chimera doctor [target]`** — probes which skills + MCP servers
  are reachable, reports READY vs PARTIAL.
- **5 monitor MCP tools** (`monitor_projects`, `monitor_active_runs`,
  `monitor_thread_state`, `monitor_find_stuck`, `monitor_topology`)
  — let Claude query LangGraph runtime state directly from chat.
- **`chimera monitor restart`** — convenience subcommand for
  reloading the daemon after code changes.
- **CONTRIBUTING.md, CHANGELOG.md, LICENSE** — repo prep for
  external contributors.

### Fixed
- **Implementation rework loop self-bounds correctly.** Three
  compounding bugs that caused chimera's pipeline to loop
  `implement → stress → scope → arbitrate` until LangGraph's
  recursion_limit:
  - `implementation_loop_step` counter never incremented
  - `handoff_type="tests_failing"` never cleared even when arbitrator
    decided to proceed
  - `_after_arbitrator` returned `"hod"` (typo) — not in edge mapping
  Regression test in `tests/test_implementation_loop.py`.
- **Monitor daemon stability** — Send/Command objects in checkpoint
  state no longer crash JSON encoding; chimera SQLite checkpoints
  decode via LangGraph's JsonPlusSerializer; running threshold
  scales per-project; topology-aware terminal detection flips
  threads to idle the moment graph_end fires.
- **Auto-follow** correctly tracks newly-spawned sister threads as
  multi-stage runs progress through stages.

### Changed
- Frontend stale/stuck thresholds scale with per-project
  `running_threshold_seconds` instead of hardcoded 5/15min.
- Monitor's status decision tree is now exhaustive across the
  checkpoint schema (HITL, terminal, project threshold, per-node
  observed p95, fallback to recency).

### Learning loop
- **Observation collector** runs every 5 min in the daemon, mining
  per-(graph, node) duration distributions and empirical end-node
  frequencies. Persisted alongside metadata.
- **Adaptive per-node thresholds** at runtime use observed p95 to
  bound stuck detection per-node — `persist` (p95 ~0.1s) gets a
  tight 30s window while `correspondence_phase1` (p95 = 55min)
  gets the full 1h cap.
- **Refinement scans** read previous metadata + observations as
  input alongside the codebase — Claude refines rules based on
  real evidence, system gets sharper across rescans.

## [0.1.0] — 2026-05-06

### Added
- Initial public release of chimera-monitor (Phase 1 of the
  langgraph-monitor task).
- 9 graph patterns (SPR-4 pipeline, PDE swarm, CLR refiner, HVD
  hypervisor, ACL components, DCE deadcode, POB toolbuilder,
  supervisor hub-and-spoke, balanced-forces).
- 14 MCP tools for orchestration.
- chimera-brainstorm tool (Claude divergent + critique with
  parallel Gemini prior-art survey, later dropped to Claude-only).
- Tests under `tests/monitor/` covering AST extraction, state
  decoding, discovery, redaction, smoke.
- README + initial documentation.
