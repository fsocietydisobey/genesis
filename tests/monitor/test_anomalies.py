"""Tests for the self-watch invariant checker.

Locks the persistence format + the recent_anomalies API behavior.
The actual checks (recent_thread_visibility, etc.) hit a live daemon
+ Postgres/SQLite, so they're tested via the integration smoke run
manually rather than unit-tested here — the unit tests focus on the
glue (logging, parsing, trimming).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from chimera.monitor import anomalies


def _patch_log(tmp_path: Path):
    """Redirect the JSONL log to a temp file."""
    return mock.patch.object(anomalies, "_LOG_FILE", tmp_path / "anomalies.jsonl")


def test_anomaly_result_to_dict_round_trip() -> None:
    r = anomalies.AnomalyResult(
        check="my_check",
        passed=False,
        project="proj",
        severity="error",
        detail="something broke",
        evidence={"x": 1},
        timestamp="2026-05-08T00:00:00+00:00",
    )
    d = r.to_dict()
    assert d["check"] == "my_check"
    assert d["passed"] is False
    assert d["evidence"] == {"x": 1}


def test_persist_appends_one_line_per_result(tmp_path: Path) -> None:
    with _patch_log(tmp_path):
        anomalies._persist([
            anomalies.AnomalyResult(check="a", passed=True),
            anomalies.AnomalyResult(check="b", passed=False, detail="oops"),
        ])
        anomalies._persist([
            anomalies.AnomalyResult(check="c", passed=True),
        ])
        # File should have 3 lines
        lines = (tmp_path / "anomalies.jsonl").read_text().splitlines()
        assert len(lines) == 3
        for line in lines:
            json.loads(line)  # each line is valid JSON


def test_recent_anomalies_returns_last_n(tmp_path: Path) -> None:
    with _patch_log(tmp_path):
        # Write 10 entries
        anomalies._persist([
            anomalies.AnomalyResult(check=f"check_{i}", passed=(i % 2 == 0))
            for i in range(10)
        ])
        last_3 = anomalies.recent_anomalies(limit=3)
        assert len(last_3) == 3
        # Most-recent ordering preserved
        assert [it["check"] for it in last_3] == ["check_7", "check_8", "check_9"]


def test_recent_anomalies_handles_missing_file(tmp_path: Path) -> None:
    with _patch_log(tmp_path):
        # File doesn't exist yet — should return [] rather than raise
        assert anomalies.recent_anomalies() == []


def test_recent_anomalies_skips_corrupt_lines(tmp_path: Path) -> None:
    """A malformed JSONL line shouldn't break the whole read."""
    with _patch_log(tmp_path):
        log_file = tmp_path / "anomalies.jsonl"
        log_file.write_text(
            json.dumps({"check": "a", "passed": True}) + "\n"
            + "not valid json\n"
            + json.dumps({"check": "b", "passed": False}) + "\n"
        )
        items = anomalies.recent_anomalies()
        assert [it["check"] for it in items] == ["a", "b"]


def test_recent_anomalies_clamps_limit(tmp_path: Path) -> None:
    with _patch_log(tmp_path):
        anomalies._persist([
            anomalies.AnomalyResult(check=f"c{i}", passed=True) for i in range(5)
        ])
        # limit > _MAX_RETURN should be clamped
        items = anomalies.recent_anomalies(limit=99999)
        assert len(items) == 5
        # limit 0 should be clamped to 1
        items = anomalies.recent_anomalies(limit=0)
        assert len(items) == 1


def test_check_registry_lists_known_checks() -> None:
    """All registered checks should be callable functions with the
    expected signature `(projects, *, base_url) -> awaitable`."""
    assert len(anomalies.CHECKS) >= 1
    for c in anomalies.CHECKS:
        assert callable(c)
        # Doc — checks should have a docstring explaining what they
        # invariantly verify
        assert c.__doc__ is not None
