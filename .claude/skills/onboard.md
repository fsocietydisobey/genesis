---
name: onboard
description: |
  Walk a developer who's new to this LangGraph project through its
  architecture: what graphs exist, what they do, recent run patterns,
  and where to start contributing. Triggered when a new contributor
  joins or when an existing dev needs to refresh their mental model
  of an unfamiliar area.

  Output is a focused project tour — NOT a wall of documentation.
  Surfaces what's most-touched, most-recent, and most-likely-to-bite.

trigger:
  - "(onboard|orient|introduce) me to (this )?(project|codebase|repo)"
  - "I'm new to (this )?(project|codebase|repo)"
  - "what (does|is) this (project|codebase|repo) do"
  - "/onboard"
  - "/tour"
---

# Onboarding Tour

You are giving a developer their first guided tour of a LangGraph
project. The audience is technical but unfamiliar with THIS specific
project. Calibrate accordingly:
- They know LangGraph in general; you don't need to explain
  "what's a StateGraph"
- They don't know this project's vocabulary, conventions, or
  recent history
- They probably want to USE the system before fully understanding it

The tour produces a "stitched cognition" of the project — a usable
mental model in 5 minutes that lets them contribute meaningfully
without 3 days of reading code.

## Investigation procedure

### 1. Project shape (what kind of thing is this?)

Use scarlet (or `ls -la` + reading top-level files) to characterize:
- **Languages / stacks** — Python? TypeScript? Both? What frameworks?
- **Entry points** — what does the README say to run? What's exposed?
- **Layout** — feature-folders / layers / monorepo structure?
- **Has a frontend?** Has a database? What's the LangGraph layer's
  role (full app vs library)?

```bash
ls -la
find . -path ./node_modules -prune -o -path ./.venv -prune -o -name "README*" -print 2>/dev/null
cat README.md | head -50
```

### 2. The graph(s) — the heart of any LangGraph project

Use `monitor_topology(project=...)` (or curl `/api/topology/`) to
list compiled graphs. For each graph:
- Name + role (orchestrator / subgraph / leaf)
- Node count
- What it invokes (cross-graph composition)

If the metadata cache has summaries, surface them. If not, infer
from node names + topology shape.

### 3. Recent run history

Use `monitor_active_runs(project=...)` AND a peek at recent threads
via `/api/threads/{project}` to characterize:
- How often does this app run?
- Average run duration? (Use observation file if available)
- Any current activity?
- Common stage progressions for multi-graph apps

```bash
# Recent run patterns from observations
cat ~/.cache/chimera/monitor/${PROJECT}-*-observations.yaml 2>/dev/null
```

The observation file is gold for onboarding — it captures the
empirical reality of the system, not the aspirational architecture.

### 4. Domain vocabulary

The metadata cache (run by `chimera monitor rescan`) has the
project's `scope_label`, thread_grouping patterns, and run_clustering
rules — these capture the project's domain ontology in compact form:

```bash
cat ~/.cache/chimera/monitor/${PROJECT}-*.yaml 2>/dev/null | head -100
```

Surface key terms (e.g., for jeevy: deliverable, ingest source,
digestion cycle; for chimera: chain, swarm, refiner, pipeline).

### 5. Where to start contributing

Identify the natural on-ramps:
- **Files that change frequently** — `git log --oneline --since='1 month ago' | head -20` shows the active areas
- **Open TODOs** — `grep -r 'TODO' --include='*.py' .`
- **Tests that are skipped** — `pytest --co -q | grep skip`
- **Recent issues / PRs** — if gh CLI is available, list them

Don't dump a long list. Pick 2-3 specific places: "if you want a
small first PR, try X. If you want to learn the graphs, look at Y."

### 6. Synthesize the tour

Output structure:

```markdown
## Welcome to <project>

### What this is, in one paragraph
<plain-English summary, technical but jargon-free>

### Core graphs
- **<graph_label>** (`<graph_name>`) — <one-line summary>. <N> nodes.
  Invokes: <other graphs if any>.
- ... (one per top-level graph; subgraphs only if user asks for depth)

### How it actually behaves (empirical)
- Typical runs: <N>/day, ~<duration>min each
- Slowest node: <name> (p95 = <Xs>)
- Most-frequent terminal: <node> (where most runs end up)
- Currently: <N> active runs, <N> idle

### Vocabulary (from metadata scan)
- **<term1>** — <what it means in this project's domain>
- **<term2>** — ...

### To get oriented in code
1. Read `<entry_point_file>` for the top-level wiring
2. Look at `<a_typical_node_file>` to see the node-body pattern
3. Pick one of these on-ramps:
   - Small first PR: <specific suggestion>
   - Architecture deep-dive: <specific suggestion>
   - "I want to fix bugs": run `/debug-runtime-issue` against any
     thread you find with `monitor_find_stuck`

### Things that will bite you (gotchas)
- <project-specific footgun, from CLAUDE.md or recent bug history>
- ...

### Next steps
- `chimera monitor start` if not running, then open http://127.0.0.1:8740
- Ask follow-up questions. The skills know more about this project
  than I just told you.
```

## Failure modes to avoid

- **Don't dump documentation.** A 3-page dump is worse than a
  90-second tour. Pick the load-bearing details, omit the rest.
- **Don't recite the README.** They've read it (or they'll read it
  if needed). Tell them what the README doesn't.
- **Don't pretend to know what you don't.** If the project's
  observation file is empty (no runs yet), say "the system hasn't
  been exercised yet — I can describe the architecture but not
  empirical behavior."
- **Don't skip the gotchas.** Every project has 2-3 footguns the
  newbie WILL hit. Surfacing them up front saves real time.

## When to ask instead of tour

- The user asks for a tour but has a specific question — switch
  to answering the question
- Their role is unclear (frontend dev? backend? AI engineer?) and
  the tour would meaningfully differ — ask before guessing
- The project has multiple distinct sub-products — ask which area
