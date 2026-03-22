"""PID lock file to prevent multiple server instances.

On startup, checks if another instance is running. If so, kills it.
Writes current PID to the lock file. Cleans up on exit.
"""

import atexit
import os
import signal
from pathlib import Path

from .log import get_logger

log = get_logger("pidlock")


def _lock_path(name: str) -> Path:
    """Get the lock file path for a server name."""
    run_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
    return run_dir / f"ai-orchestrator-{name}.pid"


def acquire_lock(name: str) -> None:
    """Acquire a PID lock, killing any previous instance.

    Args:
        name: Server name ("cli" or "graph").
    """
    lock = _lock_path(name)

    # Kill previous instance if lock file exists
    if lock.exists():
        try:
            old_pid = int(lock.read_text().strip())
            # Check if process is alive
            os.kill(old_pid, 0)
            # It's alive — kill just this process, NOT the process group
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
