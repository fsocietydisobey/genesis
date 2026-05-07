---
name: feature-impact-analysis
description: |
  Given a proposed change ("add a new X", "rename Y to Z", "extend
  feature W to support V"), map ALL affected layers across the stack
  (DB → Pydantic models → API → LangGraph → frontend → tests) and
  produce a complete change-set proposal before any editing starts.

  The win: turn "I have to remember what files to touch" into "the
  skill produced the full punch list, ordered by dependency, with
  references to existing patterns to follow."

  This is the second skill in chimera's debugging+development pack.
  Pairs with debug-runtime-issue (which investigates failures) by
  preventing the failures that come from incomplete change-sets
  (forgot the migration, forgot the frontend type, forgot the test).

trigger:
  - "add (a|an|new) (.*)"
  - "extend (.*) to (support|handle|accept) (.*)"
  - "rename (.*) (?:to|→) (.*)"
  - "what (do I|would I|will I) need to (change|touch|update) (.*)"
  - "/feature-impact-analysis"
  - "/impact"
---

# Feature Impact Analysis

You are mapping the full change-set for a proposed modification to a
LangGraph-backed full-stack project. The user has described WHAT they
want; your job is to figure out EVERYTHING that has to change and in
what order.

The output is NOT code edits. It's a punch list — a precise plan the
user (or a follow-up Claude Code turn) executes. **Investigation
first, editing second.**

## Vocabulary

- **Layer** — a tier of the stack: DB schema, Pydantic models, API
  routes, LangGraph graphs, frontend components, tests. Each layer
  has its own primary file pattern.
- **Concept** — the domain entity being added/changed (e.g.,
  "ingest source type", "agent profile", "swarm dispatch mode").
- **Anchor pattern** — an existing implementation of a similar
  concept, used as the template for the new one. Anchors are gold:
  if "drawing" already exists as an ingest source type, "audio" copies
  drawing's pattern across every layer.
- **Change-set** — the ordered list of files to modify + new files to
  create, with the rationale for each.

## Investigation procedure

### 1. Parse the change request

Identify three things:
- **Concept** — the domain entity (entity name, what it represents)
- **Verb** — add / extend / rename / remove / restrict / split
- **Anchor candidates** — what existing things look like the new one?

Don't proceed without an anchor. If you can't find one, ASK the user
for a similar existing feature to copy from. "Add a brand-new concept
with no analog" usually means the user hasn't realized they're
inventing primitives — surface that.

### 2. Project structure scan

Use **scarlet** to learn the project's stack shape:

- `scarlet:analyze_project` — confirms framework (FastAPI, Express,
  Next.js, etc.), state mgmt, conventions
- `scarlet:scan_features` — feature list to find similar features
- For each candidate anchor: `scarlet:extract_feature_metadata` to
  see exports + structure

Cross-reference with file conventions if scarlet's missing data:

```bash
# Repo top-level
ls -la

# Backend layout
find . -path ./node_modules -prune -o -name "*.py" -print | head -30

# Frontend layout (if exists)
find . -path ./node_modules -prune -o -name "*.tsx" -print 2>/dev/null | head -20

# DB schema source — alembic migrations or raw SQL
ls -la migrations/ alembic/ db/ 2>/dev/null
```

### 3. Find anchor patterns (THIS IS LOAD-BEARING)

Use **séance** — semantic search is much faster than grepping for
every variant:

```
séance:semantic_search "<concept> definition or enum"
séance:semantic_search "<anchor> implementation across the stack"
```

Then nail it down with grep:

```bash
# Common patterns: enum, literal type, registered handler, model field
grep -rn "<anchor_name>" --include="*.py" --include="*.tsx" --include="*.sql" .
```

Build an "anchor map" before proceeding — for each anchor, list which
layers it appears in:

```
anchor: "drawing" (ingest source type)
  - DB:        ingest_sources.source_type enum, line 47
  - Pydantic:  src/.../models.py:IngestSource.source_type Literal
  - API:       POST /api/sources accepts source_type
  - LangGraph: src/.../ingest.py classify_source_type branches
  - Frontend:  src/components/SourceTypeSelect.tsx options array
  - Tests:     test_ingest_drawing.py
```

If your anchor map is missing a layer, that's fine — the new
concept may not need it. But explicitly note "no <layer> impact"
rather than silently skipping.

### 4. Per-layer impact

For each layer the anchor touches, determine what changes:

#### DB schema
- New column / enum value / table?
- Migration file (alembic / drizzle / raw SQL)?
- Indexes affected?
- Use postgres MCP to inspect current schema:
  ```
  postgres:query "SELECT column_name, data_type, udt_name FROM
                  information_schema.columns WHERE table_name = '<table>'"
  ```

#### Pydantic / type definitions
- New `Literal` value, enum entry, model field?
- Validators that check the value?

#### API routes
- New endpoint OR new branch in existing endpoint?
- Request/response schema updates?
- OpenAPI docs (if framework auto-generates)?

#### LangGraph
- New node? New conditional edge? New state field?
- Use **chimera-monitor** to inspect existing graph topology:
  ```bash
  curl -s "http://127.0.0.1:8740/api/topology/<project>" | python3 -m json.tool
  ```
- Check if a similar branch already exists by examining
  conditional-edges in the relevant graph

#### Frontend
- Component changes (new option in a select, new icon, new view)?
- TypeScript types matching the new Pydantic model?
- API client functions to call new endpoints?
- State management (Redux/RTK/Zustand) updates?

#### Tests
- Unit test mirroring the anchor's test
- Integration test for end-to-end flow
- Frontend component test (if component changed)

### 5. Dependency ordering

Layers have a natural dependency order — get this right and the change
applies cleanly without intermediate broken states:

```
1. DB migration         (foundation — others depend on schema)
2. Pydantic models      (depends on DB)
3. API routes           (depends on models)
4. LangGraph nodes/edges (depends on models)
5. Frontend types       (depends on API/models contract)
6. Frontend components  (depends on types)
7. Tests                (can be added at any layer; conventionally last)
```

For renames or breaking changes, the order matters even more — note
where to deploy DB changes BEFORE backend code (or use compat shims).

### 6. Identify gotchas

Easy-to-miss things specific to the stack:
- **Database:** rollback steps in the migration, backfill of existing
  rows for new columns
- **LangGraph:** state schema change requires a checkpointer migration
  for in-flight runs (or accept that pre-change runs won't resume)
- **Frontend:** RTK Query cache invalidation tags, route generation
- **Async:** any `asyncio.gather` or parallel dispatch that needs
  the new handler registered
- **MCP:** if a new tool is added, both the registration AND the
  schema/description in the MCP server's tool catalog must update

### 7. Synthesize the change-set

Output structure:

```markdown
## Change-set: <user's request>

**Concept:** <noun being added/changed>
**Verb:** <add | extend | rename | ...>
**Anchor:** <existing feature that mirrors the new one>

### Layer impact map

| Layer | Affected | Anchor reference |
|-------|----------|------------------|
| DB | YES — new enum value | `ingest_sources.source_type` line 47 |
| Pydantic | YES — Literal extension | `IngestSource.source_type` |
| API | NO | (existing endpoint accepts via Literal) |
| LangGraph | YES — new branch in classify_source_type | `_after_prep` switch |
| Frontend | YES — new <Option> | `SourceTypeSelect.tsx` line 23 |
| Tests | YES | mirror `test_ingest_drawing.py` |

### Ordered change-set

1. **DB migration** — `migrations/2026_05_07_add_audio_source_type.sql`
   - `ALTER TYPE source_type ADD VALUE 'audio';`
   - Anchor: see `migrations/2026_03_15_add_drawing_source_type.sql`

2. **Pydantic** — `src/models/ingest.py:IngestSource`
   - Add `"audio"` to the `source_type: Literal[...]` tuple

3. **LangGraph branch** — `src/graphs/ingest.py:classify_source_type`
   - Add `audio` case in the conditional-edges mapping
   - Anchor: how `drawing` is wired (line 87)
   - New node `audio_extract` — mirror `drawing_extract` (line 102)

4. **Frontend type** — `frontend/src/types.ts`
   - Add `'audio'` to the `SourceType` union

5. **Frontend component** — `frontend/src/components/SourceTypeSelect.tsx`
   - New `<Option value="audio" label="Audio file">`

6. **Tests**
   - `tests/test_ingest_audio.py` (mirror `test_ingest_drawing.py`)

### Gotchas to watch

- The DB migration uses `ADD VALUE` which is non-blocking on Postgres
  but cannot be rolled back via DROP VALUE — plan for forward-only.
- `audio_extract` node will need its own LLM-call body (likely
  `transcribe → classify` chain) — not a 1:1 copy of `drawing_extract`.
- Existing in-flight runs at `classify_source_type` won't see the new
  branch until they hit it — they'll route via the default else clause.
  Verify what default is in source.

### What I checked but ruled out
- (anything you investigated and concluded "no impact" — surfaces the
  thoroughness for the reviewer)
```

## Failure modes to avoid

- **Don't propose code edits without showing the anchor.** "Add a new
  Literal value" is meaningless without "here's the existing one to
  copy from." Anchor every recommendation.
- **Don't skip layers silently.** If you didn't find an impact in the
  frontend, say "no frontend impact" — don't omit it. Forces the user
  to verify or correct.
- **Don't conflate add/rename/remove.** They have different ordering
  requirements (renames need compat shim if deployed in stages;
  removes need rollback strategy; adds are forward-only).
- **Don't trust scarlet/séance blindly.** Cross-validate with grep
  before declaring "this is the only place X is used." A missed
  reference becomes a runtime error.
- **Don't propose without dependency ordering.** A list of 6 files
  to change in random order is worse than 4 files in dependency
  order — the user can apply ordered changes incrementally and verify.

## Known anchors for chimera (project-specific)

These are common change patterns in chimera. If the user's request
matches one, you have a known-good template:

### Adding a new MCP tool
- Anchor: see `chimera-brainstorm` (recent addition, full pattern visible)
- Layers: `src/chimera/server/mcp.py` (registration + body),
  `src/chimera/prompts/<tool>.py` (system prompt if LLM-based),
  README.md (tool list update)
- Test: integration smoke that fires the tool through MCP

### Adding a new graph pattern (chain/swarm/etc.)
- Anchor: see existing graphs in `src/chimera/graphs/` (e.g., `swarm.py`
  for parallel patterns, `pipeline.py` for sequential)
- Layers: graph file, node factories under `src/chimera/nodes/<pattern>/`,
  state field additions in `src/chimera/core/state.py`, MCP tool to
  trigger it, tests under `tests/`

### Adding a new monitor MCP tool
- Anchor: TBD — first ones haven't shipped yet (intentional gap in
  the skill pack — when this exists, capture the pattern here)

## When to ask instead of analyze

- Anchor is unclear or there are multiple plausible ones — propose
  the candidates and ask which to follow.
- The request implies a new architectural pattern, not a feature —
  recommend chimera-architect or chimera-brainstorm for the design,
  then come back to this skill once the pattern is decided.
- The request crosses project boundaries (jeevy + external service) —
  surface the boundary and ask which side is in scope.
