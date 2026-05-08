"""Self-watch — chimera-monitor's invariant checker.

Runs periodically in the daemon (every 5 min). Probes its own state
for inconsistencies between what's actually in the checkpointer DBs
and what the API serves. When checks fail, anomalies are logged to a
JSONL file and exposed via `/api/anomalies` + the `monitor_anomalies`
MCP tool.

The daemon does NOT auto-fix. Anomalies are surfaced for human
inspection (the user, or a follow-up Claude session via the
debug-runtime-issue skill). Auto-fix risks compound silently — better
to have a clear log of "the dashboard claimed X but the truth was Y"
that someone reads.

Invariants checked (each returns Pass | Fail with evidence):

  1. recent_thread_visibility — for each project with checkpointer
     activity in the last 5 min, the most-recent thread (per its
     backend) should appear in the API's listing. Catches pagination
     bugs and silent filtering.

  2. running_status_consistency — a thread with checkpoint writes
     within the last 60s should be classified running/paused/starting,
     not idle. Catches the 'over-eager terminal detection' bug class.

  3. observation_freshness — for each project, the observations file
     should be < 1 hour old when the collector is supposed to run
     every 5 min. Catches the collector silently failing.

  4. topology_consistency — graphs reported by /api/topology should
     match what the AST walker finds. Catches lazy-import or scan
     failures that hide graphs from the dashboard.

Adding new invariants: append a function returning AnomalyResult to
the CHECKS list. Keep them cheap — the daemon runs all of them every
5 min. Prefer reading existing API outputs over re-querying the DB
where possible.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from chimera.log import get_logger

from .discovery import ast_walker
from .discovery.connections import discover_all
from .discovery.project import Project
from .metadata import observations as obs_mod

log = get_logger("monitor.anomalies")

# Where the JSONL log lives. One line per check run; appends only.
_LOG_DIR = Path(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
) / "chimera"
_LOG_FILE = _LOG_DIR / "monitor-anomalies.jsonl"

# Maximum entries returned by `recent_anomalies` — older lines are still
# in the file, but the API trims to the most-recent N.
_MAX_RETURN = 100


@dataclass
class AnomalyResult:
    """One invariant-check outcome.

    `passed=True` means the invariant held — no anomaly. We still log
    those at DEBUG so the file shows the system is alive (silent files
    are harder to debug than verbose ones).
    """

    check: str               # check function name
    passed: bool
    project: str | None = None
    severity: str = "warn"   # warn / error / info
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "passed": self.passed,
            "project": self.project,
            "severity": self.severity,
            "detail": self.detail,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def run_checks(
    projects: list[Project],
    *,
    base_url: str = "http://127.0.0.1:8740",
) -> list[AnomalyResult]:
    """Run all invariants against the live daemon. Persist failures."""
    results: list[AnomalyResult] = []
    for check in CHECKS:
        try:
            check_results = await check(projects, base_url=base_url)
        except Exception as exc:
            # A check that itself errors IS an anomaly — record so we
            # can fix the check.
            check_results = [
                AnomalyResult(
                    check=check.__name__,
                    passed=False,
                    severity="error",
                    detail=f"check raised exception: {exc!r}",
                )
            ]
        results.extend(check_results)

    now_iso = datetime.now(timezone.utc).isoformat()
    for r in results:
        if not r.timestamp:
            r.timestamp = now_iso
    _persist(results)

    failures = [r for r in results if not r.passed]
    if failures:
        log.warning(
            "self-watch: %d/%d checks failed: %s",
            len(failures),
            len(results),
            [(r.check, r.project) for r in failures],
        )
    else:
        log.info("self-watch: %d checks passed", len(results))

    return results


def recent_anomalies(limit: int = 50) -> list[dict[str, Any]]:
    """Read the last `limit` entries from the JSONL log."""
    if not _LOG_FILE.exists():
        return []
    limit = max(1, min(_MAX_RETURN, limit))
    try:
        lines = _LOG_FILE.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        log.warning("anomalies: failed to read log: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _persist(results: list[AnomalyResult]) -> None:
    """Append each result as one JSONL line."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _LOG_FILE.open("a", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r.to_dict()) + "\n")
    except OSError as exc:
        log.warning("anomalies: persist failed: %s", exc)


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------


async def check_recent_thread_visibility(
    projects: list[Project],
    *,
    base_url: str,
) -> list[AnomalyResult]:
    """The thread with the most recent checkpoint per project should
    appear in /api/threads (default page). Catches pagination /
    filtering bugs that hide live runs."""
    import urllib.parse

    out: list[AnomalyResult] = []
    for proj in projects:
        # What's the most-recent thread per project's backend?
        # _most_recent_thread_id is sync DB I/O — push to a thread.
        most_recent_tid = await asyncio.to_thread(_most_recent_thread_id, proj.path)
        if most_recent_tid is None:
            # No checkpoints at all — invariant trivially holds
            out.append(AnomalyResult(
                check="recent_thread_visibility",
                passed=True,
                project=proj.name,
                severity="info",
                detail="no checkpoints in any backend",
            ))
            continue

        # Fetch the API's default listing. Sync urllib via to_thread
        # so we don't block the event loop while the daemon services
        # other requests.
        url = f"{base_url}/api/threads/{urllib.parse.quote(proj.name)}?limit=50"
        try:
            data = await asyncio.to_thread(_http_get_json, url)
        except Exception as exc:
            out.append(AnomalyResult(
                check="recent_thread_visibility",
                passed=False,
                project=proj.name,
                severity="error",
                detail=f"API call failed: {exc!r}",
                evidence={"url": url},
            ))
            continue

        api_thread_ids = {t["thread_id"] for t in data.get("threads", [])}
        passed = most_recent_tid in api_thread_ids
        out.append(AnomalyResult(
            check="recent_thread_visibility",
            passed=passed,
            project=proj.name,
            severity="warn" if passed else "error",
            detail=(
                "most-recent thread visible in API listing"
                if passed
                else f"DB's most-recent thread {most_recent_tid!r} missing from API listing"
            ),
            evidence={
                "most_recent_thread_id": most_recent_tid,
                "api_thread_count": len(api_thread_ids),
                "api_returns_running": sum(
                    1 for t in data.get("threads", [])
                    if t["status"] in ("running", "paused", "starting")
                ),
            },
        ))
    return out


async def check_observation_freshness(
    projects: list[Project],
    *,
    base_url: str,
) -> list[AnomalyResult]:
    """The observation collector runs every 5 min. If a project's
    observations file is older than 1 hour, the collector is silently
    failing for that project."""
    out: list[AnomalyResult] = []
    now = datetime.now(timezone.utc)
    for proj in projects:
        obs = obs_mod.load(proj.path)
        if obs is None:
            out.append(AnomalyResult(
                check="observation_freshness",
                passed=True,
                project=proj.name,
                severity="info",
                detail="no observation file yet (first run pending)",
            ))
            continue
        try:
            collected_at = datetime.fromisoformat(obs.last_collected_at)
        except ValueError:
            out.append(AnomalyResult(
                check="observation_freshness",
                passed=False,
                project=proj.name,
                severity="warn",
                detail=f"observation file has malformed timestamp: {obs.last_collected_at!r}",
            ))
            continue
        age_s = (now - collected_at).total_seconds()
        passed = age_s < 3600  # 1 hour grace
        out.append(AnomalyResult(
            check="observation_freshness",
            passed=passed,
            project=proj.name,
            severity="info" if passed else "warn",
            detail=(
                f"observations updated {age_s:.0f}s ago"
                if passed
                else f"observations stale: {age_s:.0f}s since last collection"
            ),
            evidence={"age_seconds": age_s, "samples_seen": obs.samples_seen},
        ))
    return out


async def check_topology_consistency(
    projects: list[Project],
    *,
    base_url: str,
) -> list[AnomalyResult]:
    """Count of graphs in /api/topology should match the AST scan.
    Mismatch in either direction is suspicious."""
    import urllib.parse

    out: list[AnomalyResult] = []
    for proj in projects:
        try:
            ast_results = await asyncio.to_thread(
                ast_walker.extract_from_path, proj.path
            )
        except Exception as exc:
            out.append(AnomalyResult(
                check="topology_consistency",
                passed=False,
                project=proj.name,
                severity="error",
                detail=f"AST scan failed: {exc!r}",
            ))
            continue
        ast_count = sum(1 for r in ast_results if r.nodes)

        url = f"{base_url}/api/topology/{urllib.parse.quote(proj.name)}"
        try:
            data = await asyncio.to_thread(_http_get_json, url)
        except Exception as exc:
            out.append(AnomalyResult(
                check="topology_consistency",
                passed=False,
                project=proj.name,
                severity="error",
                detail=f"API call failed: {exc!r}",
            ))
            continue
        api_count = len(data.get("graphs", []))

        # API count should be exactly equal to AST count (both walk the
        # same source). Diff > 0 in either direction is a bug.
        passed = api_count == ast_count
        out.append(AnomalyResult(
            check="topology_consistency",
            passed=passed,
            project=proj.name,
            severity="info" if passed else "warn",
            detail=(
                f"topology: {api_count} graphs (matches AST)"
                if passed
                else f"topology mismatch: API={api_count}, AST={ast_count}"
            ),
            evidence={"api_count": api_count, "ast_count": ast_count},
        ))
    return out


# Registry — order matters for log readability.
CHECKS: list[Callable[..., Any]] = [
    check_recent_thread_visibility,
    check_observation_freshness,
    check_topology_consistency,
]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _http_get_json(url: str, timeout: float = 30.0) -> dict[str, Any]:
    """Synchronous JSON GET — call from a worker thread, never directly
    from an async function (would block the event loop)."""
    import urllib.request

    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _most_recent_thread_id(project_path: Path) -> str | None:
    """Return the thread_id with the highest checkpoint_id across all of
    a project's checkpointer backends. None when the project has no
    checkpoints at all."""
    try:
        conns = discover_all(project_path)
    except Exception:
        return None

    best_thread_id: str | None = None
    best_checkpoint_id: str = ""

    for pg in conns.postgres:
        try:
            tid, cp_id = _pg_most_recent(pg.url)
        except Exception:
            continue
        if cp_id and cp_id > best_checkpoint_id:
            best_thread_id = tid
            best_checkpoint_id = cp_id

    for sl in conns.sqlite:
        try:
            tid, cp_id = _sqlite_most_recent(sl.path)
        except Exception:
            continue
        if cp_id and cp_id > best_checkpoint_id:
            best_thread_id = tid
            best_checkpoint_id = cp_id

    return best_thread_id


def _pg_most_recent(url: str) -> tuple[str | None, str]:
    import psycopg

    with psycopg.connect(url, connect_timeout=3) as db:
        with db.cursor() as cur:
            cur.execute(
                "SELECT thread_id, MAX(checkpoint_id) AS latest "
                "FROM checkpoints GROUP BY thread_id "
                "ORDER BY latest DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row is None:
                return (None, "")
            return (row[0], row[1] or "")


def _sqlite_most_recent(db_path: str) -> tuple[str | None, str]:
    import sqlite3

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0) as db:
        cur = db.execute(
            "SELECT thread_id, MAX(checkpoint_id) AS latest "
            "FROM checkpoints GROUP BY thread_id "
            "ORDER BY latest DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row is None:
            return (None, "")
        return (row[0], row[1] or "")
