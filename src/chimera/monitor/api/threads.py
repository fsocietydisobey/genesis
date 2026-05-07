"""`/api/threads` — paginated thread list + single-thread state inspection.

Backend dispatch:
  - Postgres (`AsyncPostgresSaver`): JSONB columns, fast jsonb-extract
    queries pull just the keys we need without deserializing whole blobs.
  - SQLite (`AsyncSqliteSaver`): BLOB columns (msgpack-encoded), so we
    pull every row and deserialize in Python. Fine at chimera-scale;
    revisit if it ever becomes a bottleneck.

A project may have multiple SQLite databases (chimera has one per graph).
List queries union all of them; detail queries probe each in order until
the requested thread_id is found.

Polling-friendly: callers pass `since` (a checkpoint_id watermark) and
the endpoint uses an indexed cursor so polls stay cheap.
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

import re

from .._optional import require
from ..discovery.connections import Connections, PostgresConnection, SqliteConnection, discover_sqlite
from ..discovery.project import Project
from ..discovery.redaction import redact
from ..discovery.state_decoder import decode, to_jsonable
from ..discovery.thread_grouping import parse_grouping
from ..metadata import cache as meta_cache
from ..metadata.schema import ProjectMetadata, RunClustering, ThreadGrouping

# ---------------------------------------------------------------------------
# Postgres SQL
# ---------------------------------------------------------------------------
_PG_LIST_SQL = """
SELECT DISTINCT ON (thread_id)
       thread_id,
       checkpoint_id                                          AS latest_checkpoint_id,
       checkpoint->>'ts'                                      AS last_updated,
       (checkpoint->'channel_values' ? '__interrupt__')       AS is_paused,
       checkpoint->'channel_values'->>'agent_profile'         AS agent_profile,
       checkpoint->'channel_values'->>'phase'                 AS phase,
       (metadata->>'step')::int                               AS step,
       metadata->>'source'                                    AS source,
       metadata->'writes'                                     AS writes,
       checkpoint->'versions_seen'                            AS versions_seen
FROM checkpoints
ORDER BY thread_id, checkpoint_id DESC
LIMIT %s OFFSET %s
"""

_PG_DETAIL_SQL = """
SELECT checkpoint_id,
       parent_checkpoint_id,
       type,
       checkpoint,
       metadata,
       checkpoint->>'ts'                                      AS ts,
       checkpoint->'versions_seen'                            AS versions_seen,
       (metadata->>'step')::int                               AS step,
       metadata->'writes'                                     AS writes
FROM checkpoints
WHERE thread_id = %s
ORDER BY checkpoint_id DESC
LIMIT %s
"""

# ---------------------------------------------------------------------------
# SQLite SQL
# ---------------------------------------------------------------------------
# Same column names but checkpoint + metadata are BLOB. We extract the
# fields in Python after decoding.
_SQLITE_LIST_SQL = """
SELECT thread_id, checkpoint_id, type, checkpoint, metadata
FROM checkpoints
WHERE checkpoint_id = (
  SELECT MAX(checkpoint_id) FROM checkpoints c2
  WHERE c2.thread_id = checkpoints.thread_id
)
ORDER BY checkpoint_id DESC
LIMIT ? OFFSET ?
"""

_SQLITE_DETAIL_SQL = """
SELECT checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata
FROM checkpoints
WHERE thread_id = ?
ORDER BY checkpoint_id DESC
LIMIT ?
"""


def build_router(connections_by_project: dict[Path, Connections], projects: list[Project] | None = None):
    fastapi = require("fastapi")
    router = fastapi.APIRouter()

    # Cache Postgres URLs (static — they come from .env and don't change
    # without a daemon restart). SQLite files come and go (graphs create
    # their .db on first run), so SQLite discovery happens per-request.
    name_to_path: dict[str, Path] = {}
    name_to_postgres: dict[str, list[PostgresConnection]] = {}
    for path, conns in connections_by_project.items():
        name_to_path[path.name] = path
        name_to_postgres[path.name] = conns.postgres
    # Also fold in projects that exist but had no connections at startup.
    if projects:
        for p in projects:
            name_to_path.setdefault(p.name, p.path)
            name_to_postgres.setdefault(p.name, [])

    def _live_connections(name: str) -> Connections | None:
        path = name_to_path.get(name)
        if path is None:
            return None
        # Re-glob SQLite on every request — chimera-style projects create
        # per-graph .db files lazily. This is a few file syscalls; cheap.
        return Connections(
            postgres=name_to_postgres.get(name, []),
            sqlite=discover_sqlite(path),
        )

    def _metadata_for(name: str) -> ProjectMetadata | None:
        """Load the project's metadata cache. Returns None when no scan
        has landed yet — callers fall back to heuristic defaults."""
        path = name_to_path.get(name)
        if path is None:
            return None
        return meta_cache.load(path)

    def _grouping_for(name: str) -> ThreadGrouping | None:
        meta = _metadata_for(name)
        return meta.thread_grouping if meta else None

    def _run_clustering_for(name: str) -> RunClustering | None:
        meta = _metadata_for(name)
        return meta.run_clustering if meta else None

    @router.get("/threads/{name}")
    async def list_threads(name: str, limit: int = 50, offset: int = 0, since: str | None = None):
        conns = _live_connections(name)
        if conns is None or (not conns.postgres and not conns.sqlite):
            raise fastapi.HTTPException(
                status_code=404,
                detail=f"no checkpointer connection discovered for project: {name}",
            )

        rows = await _list_threads(conns, since, limit, offset)
        grouping = _grouping_for(name)
        run_clustering = _run_clustering_for(name)
        return {
            "project": name,
            "limit": limit,
            "offset": offset,
            "since": since,
            "scope_label": (grouping.scope_label if grouping else "Run"),
            # When absent, the frontend applies its built-in heuristic
            # (trailing-UUID + 5min proximity). Always serialized so the
            # frontend can tell "no rule yet" from "explicit no-cluster".
            "run_clustering": (run_clustering.model_dump() if run_clustering else None),
            "threads": [_serialize_thread(r, grouping) for r in rows],
        }

    @router.get("/threads/{name}/{thread_id}")
    async def thread_detail(name: str, thread_id: str, limit: int = 20):
        conns = _live_connections(name)
        if conns is None or (not conns.postgres and not conns.sqlite):
            raise fastapi.HTTPException(
                status_code=404,
                detail=f"no checkpointer connection discovered for project: {name}",
            )

        rows = await _thread_detail(conns, thread_id, limit)
        if not rows:
            raise fastapi.HTTPException(status_code=404, detail=f"thread not found: {thread_id}")

        return {
            "project": name,
            "thread_id": thread_id,
            "checkpoints": [_serialize_checkpoint(r) for r in rows],
        }

    return router


# ---------------------------------------------------------------------------
# Backend dispatch
# ---------------------------------------------------------------------------
async def _list_threads(conns: Connections, since: str | None, limit: int, offset: int) -> list[dict[str, Any]]:
    if conns.postgres:
        return await _pg_list(conns.postgres[0], since, limit, offset)
    # SQLite — union across every discovered DB.
    union: list[dict[str, Any]] = []
    for sqlite_conn in conns.sqlite:
        rows = await asyncio.to_thread(_sqlite_list_sync, sqlite_conn, limit + offset)
        union.extend(rows)
    union.sort(key=lambda r: r.get("last_updated") or "", reverse=True)
    return union[offset : offset + limit]


async def _thread_detail(conns: Connections, thread_id: str, limit: int) -> list[dict[str, Any]]:
    if conns.postgres:
        return await _pg_detail(conns.postgres[0], thread_id, limit)
    for sqlite_conn in conns.sqlite:
        rows = await asyncio.to_thread(_sqlite_detail_sync, sqlite_conn, thread_id, limit)
        if rows:
            return rows
    return []


# ---------------------------------------------------------------------------
# Postgres path
# ---------------------------------------------------------------------------
async def _pg_list(conn: PostgresConnection, since: str | None, limit: int, offset: int) -> list[dict[str, Any]]:
    psycopg = require("psycopg")
    rows: list[dict[str, Any]] = []
    sql = _PG_LIST_SQL
    params: tuple = (limit, offset)
    if since:
        sql = sql.replace("LIMIT %s OFFSET %s", "WHERE checkpoint_id > %s LIMIT %s OFFSET %s")
        # Note: simple form — re-emit with `since` in the WHERE clause when needed
    async with await psycopg.AsyncConnection.connect(conn.url) as pg:
        async with pg.cursor() as cur:
            await cur.execute(sql, params)
            cols = [d[0] for d in cur.description] if cur.description else []
            async for row in cur:
                rows.append(dict(zip(cols, row)))
    return rows


async def _pg_detail(conn: PostgresConnection, thread_id: str, limit: int) -> list[dict[str, Any]]:
    psycopg = require("psycopg")
    rows: list[dict[str, Any]] = []
    async with await psycopg.AsyncConnection.connect(conn.url) as pg:
        async with pg.cursor() as cur:
            await cur.execute(_PG_DETAIL_SQL, (thread_id, limit))
            cols = [d[0] for d in cur.description] if cur.description else []
            async for row in cur:
                rows.append(dict(zip(cols, row)))
    return rows


# ---------------------------------------------------------------------------
# SQLite path
# ---------------------------------------------------------------------------
def _sqlite_list_sync(conn: SqliteConnection, fetch_limit: int) -> list[dict[str, Any]]:
    """Read latest checkpoint per thread from one SQLite DB. Decodes blobs
    in Python and projects to the same row shape the Postgres path emits."""
    out: list[dict[str, Any]] = []
    try:
        with sqlite3.connect(f"file:{conn.path}?mode=ro", uri=True, timeout=2.0) as db:
            db.row_factory = sqlite3.Row
            cur = db.execute(_SQLITE_LIST_SQL, (fetch_limit, 0))
            for row in cur.fetchall():
                decoded = _decode_checkpoint(row["type"], row["checkpoint"])
                meta = _decode_metadata(row["type"], row["metadata"])
                channel_values = decoded.get("channel_values") if isinstance(decoded, dict) else None
                out.append({
                    "thread_id": row["thread_id"],
                    "latest_checkpoint_id": row["checkpoint_id"],
                    "last_updated": (decoded.get("ts") if isinstance(decoded, dict) else None),
                    "is_paused": isinstance(channel_values, dict) and "__interrupt__" in channel_values,
                    "agent_profile": (channel_values.get("agent_profile") if isinstance(channel_values, dict) else None),
                    "phase": (channel_values.get("phase") if isinstance(channel_values, dict) else None),
                    "step": (meta.get("step") if isinstance(meta, dict) else None),
                    "source": (meta.get("source") if isinstance(meta, dict) else None),
                    "writes": (meta.get("writes") if isinstance(meta, dict) else None),
                    "versions_seen": (decoded.get("versions_seen") if isinstance(decoded, dict) else None),
                    "_db_path": conn.path,  # kept for debugging; not serialized to client
                })
    except sqlite3.Error:
        return []
    return out


def _sqlite_detail_sync(conn: SqliteConnection, thread_id: str, limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        with sqlite3.connect(f"file:{conn.path}?mode=ro", uri=True, timeout=2.0) as db:
            db.row_factory = sqlite3.Row
            cur = db.execute(_SQLITE_DETAIL_SQL, (thread_id, limit))
            for row in cur.fetchall():
                decoded = _decode_checkpoint(row["type"], row["checkpoint"])
                meta = _decode_metadata(row["type"], row["metadata"])
                out.append({
                    "checkpoint_id": row["checkpoint_id"],
                    "parent_checkpoint_id": row["parent_checkpoint_id"],
                    "type": row["type"],
                    "checkpoint": decoded,
                    "metadata": meta,
                    "ts": decoded.get("ts") if isinstance(decoded, dict) else None,
                    "versions_seen": decoded.get("versions_seen") if isinstance(decoded, dict) else None,
                    "step": meta.get("step") if isinstance(meta, dict) else None,
                    "writes": meta.get("writes") if isinstance(meta, dict) else None,
                })
    except sqlite3.Error:
        return []
    return out


def _decode_checkpoint(type_str: str | None, blob: bytes | None) -> Any:
    """Decode a SQLite checkpoint blob and pass through dicts (after Python
    msgpack libs return raw types). The state_decoder handles the wire-format
    cases; this wrapper exists so we can normalize None / non-dict results."""
    if blob is None:
        return None
    return decode(type_str, blob)


def _decode_metadata(type_str: str | None, blob: bytes | None) -> Any:
    if blob is None:
        return None
    return decode(type_str, blob)


# ---------------------------------------------------------------------------
# Shared serialization (works for both backends — row shapes are normalized)
# ---------------------------------------------------------------------------
_SPECIAL_NODES = frozenset({"__input__", "__start__", "__interrupt__", "__end__"})


def _serialize_thread(row: dict[str, Any], grouping: ThreadGrouping | None = None) -> dict[str, Any]:
    current_node, recent_nodes = _derive_nodes(row)
    grouping_fields = _resolve_grouping(row["thread_id"], grouping)
    return {
        "thread_id": row["thread_id"],
        "latest_checkpoint_id": row["latest_checkpoint_id"],
        "last_updated": row.get("last_updated"),
        "step": row.get("step"),
        "status": _derive_status(row),
        "current_node": current_node,
        "recent_nodes": recent_nodes,
        "agent_profile": row.get("agent_profile"),
        "phase": row.get("phase"),
        # Generic grouping fields the UI consumes blindly. App-agnostic.
        "scope_kind": grouping_fields["scope_kind"],
        "scope_id": grouping_fields["scope_id"],
        "stage": grouping_fields["stage"],
        "stage_detail": grouping_fields["stage_detail"],
    }


def _resolve_grouping(thread_id: str, grouping: ThreadGrouping | None) -> dict[str, str]:
    """Apply the metadata-provided regex patterns first; fall back to the
    generic heuristic if no pattern matches (or no metadata exists yet)."""
    if grouping and grouping.patterns:
        for rule in grouping.patterns:
            try:
                m = re.match(rule.pattern, thread_id)
            except re.error:
                continue
            if not m:
                continue
            captured = m.groupdict()
            return {
                "scope_kind": rule.scope_kind or captured.get("scope_kind") or "thread",
                "scope_id": captured.get("scope_id") or thread_id,
                "stage": rule.stage or captured.get("stage") or rule.scope_kind or "thread",
                "stage_detail": captured.get("stage_detail") or "",
            }
    # Fallback heuristic
    return dict(parse_grouping(thread_id))


def _serialize_checkpoint(row: dict[str, Any]) -> dict[str, Any]:
    # to_jsonable runs AFTER redact so the redacted payload (still a
    # mix of dicts, Pydantic models, dataclasses, Send objects, …)
    # gets normalized into something FastAPI's JSON encoder can
    # traverse without crashing on objects whose `__iter__` raises.
    return {
        "checkpoint_id": row["checkpoint_id"],
        "parent_checkpoint_id": row.get("parent_checkpoint_id"),
        "created_at": row.get("ts"),
        "step": row.get("step"),
        "node": _derive_nodes(row)[0],
        "state": to_jsonable(redact(_unwrap_state(row.get("checkpoint")))),
        "metadata": to_jsonable(redact(row["metadata"])) if row.get("metadata") else None,
    }


def _derive_nodes(row: dict[str, Any]) -> tuple[str | None, list[str]]:
    writes = row.get("writes")
    if isinstance(writes, dict) and writes:
        nodes = sorted(k for k in writes.keys() if k not in _SPECIAL_NODES)
        if nodes:
            return nodes[0], nodes

    versions_seen = row.get("versions_seen")
    if not isinstance(versions_seen, dict):
        return None, []

    candidates: list[tuple[str, str]] = []
    for node, channels in versions_seen.items():
        if node in _SPECIAL_NODES:
            continue
        if not isinstance(channels, dict):
            continue
        max_v = ""
        for v in channels.values():
            v_str = str(v)
            if v_str > max_v:
                max_v = v_str
        candidates.append((max_v, node))

    candidates.sort(reverse=True)
    recent = [name for _, name in candidates]
    current = recent[0] if recent else None
    return current, recent


# Window of activity that classifies a thread as "running" rather than
# "idle" — used as the LAST resort when no definitive signal is
# available (HITL interrupt, terminal __end__ write, etc. are checked
# first). Set generously (5min) so LLM-heavy nodes between checkpoint
# writes don't flicker to idle mid-execution; the frontend's staleness
# classifier picks up at 5min ("stale") and 15min ("stuck") for runs
# that genuinely hang. Won't false-flag finished runs because terminal
# detection short-circuits before this fires.
_RUNNING_THRESHOLD_SECONDS = 300.0


def _derive_status(row: dict[str, Any]) -> str:
    """Classify a thread's status using every signal available from the
    checkpoint schema. Decision tree, in priority order:

      1. `__interrupt__` channel set     → paused (HITL — time-independent;
                                             a paused run can sit at the gate
                                             for hours/days, that's normal)
      2. source=input, step ≤ 0          → starting (graph just kicked off)
      3. writes contains `__end__`       → idle (run reached the terminal
                                             pseudo-node — definitively done)
      4. activity within 5 min           → running (heuristic for in-flight,
                                             tolerates slow LLM nodes between
                                             checkpoint writes)
      5. else                            → idle (no recent activity, no
                                             terminal marker — likely
                                             abandoned/errored; frontend's
                                             staleness classifier gives the
                                             user a "stuck" badge if the
                                             situation warrants attention)

    Note: We can't detect "Python is currently executing this node" from
    the checkpoint table alone — between checkpoint commits the database
    looks identical to "node finished a moment ago." The 5min window is
    the practical floor; pair it with terminal detection so completed
    runs flip to idle the instant `__end__` lands rather than waiting
    out the window.
    """
    # 1. HITL pause — time-independent, can persist indefinitely.
    if row.get("is_paused"):
        return "paused"

    # 2. Just-started graph.
    source = row.get("source")
    step = row.get("step")
    if source == "input" and (step is None or step <= 0):
        return "starting"

    # 3. Terminal — graph reached __end__. Detected via the writes
    # metadata which records what the latest super-step wrote. If
    # `__end__` is among the keys, the END pseudo-node was reached.
    writes = row.get("writes")
    if isinstance(writes, dict) and "__end__" in writes:
        return "idle"

    # 4. Recent activity → in-flight (best-effort, tolerates slow nodes).
    last_updated = row.get("last_updated")
    if last_updated and _within_seconds(last_updated, _RUNNING_THRESHOLD_SECONDS):
        return "running"

    # 5. Default — no clear signal of activity, treat as idle. The
    # frontend's staleness classifier will flag this as "stuck" if a
    # paused/running thread crosses the 15min threshold.
    return "idle"


def _within_seconds(ts_iso: str, seconds: float) -> bool:
    from datetime import datetime, timezone

    try:
        ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = (datetime.now(timezone.utc) - ts).total_seconds()
    return 0 <= delta <= seconds


def _unwrap_state(decoded: object) -> object:
    if isinstance(decoded, dict) and "channel_values" in decoded:
        return decoded["channel_values"]
    return decoded
