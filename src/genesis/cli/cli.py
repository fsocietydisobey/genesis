"""CLI subprocess execution helpers."""

import asyncio
import os
import shutil
import subprocess
import time
from typing import TYPE_CHECKING

from genesis.log import get_logger
from genesis.cli import config

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context

log = get_logger("cli")

# Track all running subprocesses for cleanup on shutdown
_active_pids: set[int] = set()

# How often to send heartbeat progress (seconds)
_HEARTBEAT_INTERVAL = 15


def cli_available(cmd: str) -> bool:
    """Check if a CLI tool exists (absolute path or on PATH)."""
    if os.path.isabs(cmd):
        return os.path.isfile(cmd) and os.access(cmd, os.X_OK)
    return shutil.which(cmd) is not None


def kill_all_subprocesses():
    """Kill all tracked subprocesses. Called on server shutdown."""
    import signal
    for pid in list(_active_pids):
        try:
            os.kill(pid, signal.SIGKILL)
            log.info("killed subprocess PID %d on shutdown", pid)
        except ProcessLookupError:
            pass
    _active_pids.clear()


def _run_subprocess(cmd: list[str], timeout: int, cwd: str) -> tuple[bytes, bytes, int]:
    """Run subprocess in a thread-safe way. Returns (stdout, stderr, returncode)."""
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _active_pids.add(proc.pid)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return stdout, stderr, proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise TimeoutError(f"CLI command timed out after {timeout}s: {' '.join(cmd[:2])}...")
    finally:
        _active_pids.discard(proc.pid)


async def run_cli(
    cmd: list[str],
    timeout: int | None = None,
    ctx: "Context | None" = None,
    label: str = "",
) -> str:
    """Run a CLI command as a subprocess and return stdout.

    Runs the subprocess in a thread via asyncio.to_thread so it does NOT
    block the event loop. Other MCP requests (like status()) can be handled
    concurrently.

    Args:
        cmd: Command and arguments to run.
        timeout: Max seconds to wait before killing the process.
        ctx: Optional MCP context for sending progress heartbeats.
        label: Optional label for progress messages.

    Returns:
        The process stdout as a string.

    Raises:
        TimeoutError: If the process exceeds the timeout.
        RuntimeError: If the process exits with a non-zero code.
    """
    if timeout is None:
        timeout = config.CLI_TIMEOUT

    # Input validation — reject excessively large commands
    total_len = sum(len(arg) for arg in cmd)
    if total_len > 500_000:
        raise ValueError(f"Command too large ({total_len} chars). Max 500KB.")

    cmd_short = " ".join(cmd[:3])
    progress_label = label or cmd_short
    log.info("running: %s (timeout=%ds)", cmd_short, timeout)
    t0 = time.monotonic()

    # Run subprocess in a thread — does NOT block the event loop
    try:
        stdout, stderr, returncode = await asyncio.to_thread(
            _run_subprocess, cmd, timeout, config.PROJECT_ROOT
        )
    except TimeoutError:
        elapsed = time.monotonic() - t0
        log.error("timeout after %.1fs: %s", elapsed, cmd_short)
        raise
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - t0
        log.error("async timeout after %.1fs: %s", elapsed, cmd_short)
        raise TimeoutError(f"CLI command timed out after {timeout}s: {' '.join(cmd[:2])}...")

    elapsed = time.monotonic() - t0
    output = stdout.decode()

    if returncode != 0:
        err = stderr.decode().strip()
        log.error("failed (code=%d, %.1fs): %s — %s", returncode, elapsed, cmd_short, err[:200])
        raise RuntimeError(
            f"CLI exited with code {returncode}: {err or '(no stderr)'}"
        )

    log.info("completed in %.1fs (%d chars): %s", elapsed, len(output), cmd_short)
    return output
