"""PID lock file to prevent multiple server instances.

On startup, checks if another instance is running. If so, kills it — UNLESS
that instance is one of our own ancestors (a parent chimera that spawned a
claude/gemini CLI which transitively spawned us as a grandchild MCP). Killing
an ancestor is the "circular MCP" footgun — see runners.py `--bare` for the
prevention side; this is the lock-side guard.

Writes current PID to the lock file. Cleans up on exit.
"""

import atexit
import os
import signal
from pathlib import Path

import psutil

from .log import get_logger

log = get_logger("pidlock")


def _lock_path(name: str) -> Path:
    """Get the lock file path for a server name."""
    run_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
    return run_dir / f"chimera-{name}.pid"


def _is_ancestor_of_self(pid: int) -> bool:
    """Return True if `pid` is an ancestor of the current process.

    Cross-platform via psutil. Returns False on any error (dead process,
    permission denied, etc.) — callers must remain correct in that case,
    so a False return only DECREASES the chance of killing a parent.
    """
    try:
        return any(p.pid == pid for p in psutil.Process().parents())
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.Error, OSError):
        return False


def acquire_lock(name: str) -> None:
    """Acquire a PID lock, killing any previous instance unless it's an ancestor.

    Args:
        name: Server name ("cli" or "graph").
    """
    lock = _lock_path(name)

    # Kill previous instance if lock file exists and it isn't an ancestor
    if lock.exists():
        try:
            old_pid = int(lock.read_text().strip())
            # Check if process is alive (raises ProcessLookupError if dead)
            os.kill(old_pid, 0)

            if _is_ancestor_of_self(old_pid):
                # We're a transitive child of the lock holder — likely spawned
                # by a CLI subprocess (claude/gemini) that re-loaded chimera
                # from ~/.claude.json despite --bare. Don't kill the parent.
                # Run detached without claiming the lock; we have our own stdio.
                log.info(
                    "lock held by ancestor (PID %d) — running detached, not claiming lock",
                    old_pid,
                )
                return

            # Not an ancestor — kill just this process, NOT the process group
            # (process group kill would take out Cursor's Extension Host)
            log.warning("killing previous %s server (PID %d)", name, old_pid)
            os.kill(old_pid, signal.SIGKILL)
        except (ValueError, ProcessLookupError, PermissionError, OSError):
            pass  # Stale lock file or process already dead

    # Write current PID
    lock.write_text(str(os.getpid()))
    log.info("acquired lock: %s (PID %d)", lock, os.getpid())

    # Clean up on exit
    def _release():
        try:
            # Only remove if it's still our PID
            if lock.exists() and lock.read_text().strip() == str(os.getpid()):
                lock.unlink()
                log.info("released lock: %s", lock)
        except Exception:
            pass

    atexit.register(_release)
