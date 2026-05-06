"""Regression tests for the circular-MCP pidlock bug.

Background: when chimera's `architect`/`research` shells out to `claude`, the
spawned claude used to read ~/.claude.json and spawn its own chimera child.
That child ran acquire_lock("graph"), found the parent's lock, and SIGKILL'd
the parent. The fix has two layers:

1. Spawn claude with --strict-mcp-config + empty config (in cli/runners.py)
   so no child chimera spawns at all.
2. Lock-side guard: if the existing lock holder is one of our ancestors,
   don't kill — run detached without claiming the lock.

These tests pin layer 2.
"""

from __future__ import annotations

import os
from pathlib import Path

import psutil
import pytest

from chimera.pidlock import _is_ancestor_of_self, _lock_path, acquire_lock

# ----- _is_ancestor_of_self -----------------------------------------------


def test_self_is_not_own_ancestor():
    assert _is_ancestor_of_self(os.getpid()) is False


def test_direct_parent_is_ancestor():
    assert _is_ancestor_of_self(os.getppid()) is True


def test_init_is_ancestor():
    # PID 1 is everyone's ancestor on Linux. (On macOS launchd is PID 1.)
    assert _is_ancestor_of_self(1) is True


def test_dead_pid_is_not_ancestor():
    # Pick a PID unlikely to exist. If it happens to exist the test is vacuous,
    # not wrong — _is_ancestor_of_self should still return False for a non-ancestor.
    bogus = 4_000_000
    assert _is_ancestor_of_self(bogus) is False


def test_grandparent_is_ancestor():
    # Walk up two levels via psutil, then verify _is_ancestor_of_self agrees.
    parents = psutil.Process().parents()
    if len(parents) < 2:
        pytest.skip("need at least a grandparent to test transitive ancestry")
    grandparent_pid = parents[1].pid
    assert _is_ancestor_of_self(grandparent_pid) is True


def test_sibling_is_not_ancestor():
    # Find any live PID that is NOT in our ancestor chain.
    ancestors = {p.pid for p in psutil.Process().parents()} | {os.getpid()}
    candidate = next(
        (p.pid for p in psutil.process_iter(["pid"]) if p.pid not in ancestors),
        None,
    )
    if candidate is None:
        pytest.skip("no non-ancestor live PID found (unlikely on a real system)")
    assert _is_ancestor_of_self(candidate) is False


# ----- acquire_lock circular-MCP guard ------------------------------------


def test_acquire_lock_does_not_kill_ancestor(tmp_path, monkeypatch):
    """Simulates the circular bug: existing lock holds an ancestor PID.
    acquire_lock must NOT take the lock and must NOT signal the ancestor.
    """
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    parent_pid = os.getppid()
    lock = _lock_path("test-circular")
    lock.write_text(str(parent_pid))

    # Should noop: parent stays alive, lock file content unchanged.
    acquire_lock("test-circular")

    assert lock.read_text().strip() == str(parent_pid), (
        "acquire_lock overwrote the lock; should have refused due to ancestor"
    )
    # Parent process is still alive (psutil raises if not).
    psutil.Process(parent_pid)


def test_acquire_lock_takes_lock_when_no_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    lock = _lock_path("test-fresh")
    assert not lock.exists()

    acquire_lock("test-fresh")

    assert lock.read_text().strip() == str(os.getpid())


def test_acquire_lock_clears_stale_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    lock = _lock_path("test-stale")
    lock.write_text("4000000")  # bogus PID, almost certainly dead

    acquire_lock("test-stale")

    assert lock.read_text().strip() == str(os.getpid()), "acquire_lock should have replaced stale lock with our PID"


# ----- belt-and-suspenders ------------------------------------------------


def test_lock_path_uses_xdg_runtime_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    p = _lock_path("foo")
    assert Path(p).parent == tmp_path
    assert Path(p).name == "chimera-foo.pid"
