"""Tests for the project-roots registry (config._load_roots)."""

from __future__ import annotations

from pathlib import Path

import pytest

from chimera.cli.config import _load_roots


@pytest.fixture
def chimera_repo(tmp_path: Path) -> str:
    """A stand-in for the chimera repo path. Always-included root."""
    repo = tmp_path / "chimera_repo"
    repo.mkdir()
    return str(repo)


def test_missing_file_returns_only_chimera_repo(tmp_path: Path, chimera_repo: str):
    missing = tmp_path / "nope.yaml"
    roots = _load_roots(missing, chimera_repo=chimera_repo)
    assert roots == [chimera_repo]


def test_valid_file_includes_chimera_repo_first(tmp_path: Path, chimera_repo: str):
    project_a = tmp_path / "project_a"
    project_a.mkdir()
    project_b = tmp_path / "project_b"
    project_b.mkdir()

    cfg = tmp_path / "roots.yaml"
    cfg.write_text(f"roots:\n  - {project_a}\n  - {project_b}\n")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert roots[0] == chimera_repo
    assert str(project_a) in roots
    assert str(project_b) in roots


def test_tilde_expansion(tmp_path: Path, chimera_repo: str, monkeypatch):
    target = tmp_path / "home_root"
    target.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))

    cfg = tmp_path / "roots.yaml"
    cfg.write_text("roots:\n  - ~/home_root\n")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert str(target) in roots


def test_skips_nonexistent_paths(tmp_path: Path, chimera_repo: str):
    cfg = tmp_path / "roots.yaml"
    cfg.write_text("roots:\n  - /nonexistent/path/12345\n")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert roots == [chimera_repo]


def test_dedupes_repeated_paths(tmp_path: Path, chimera_repo: str):
    project = tmp_path / "project"
    project.mkdir()

    cfg = tmp_path / "roots.yaml"
    cfg.write_text(f"roots:\n  - {project}\n  - {project}\n  - {project}\n")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert roots.count(str(project)) == 1


def test_chimera_repo_not_duplicated_when_listed_explicitly(tmp_path: Path, chimera_repo: str):
    cfg = tmp_path / "roots.yaml"
    cfg.write_text(f"roots:\n  - {chimera_repo}\n")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert roots == [chimera_repo]


def test_malformed_yaml_falls_back(tmp_path: Path, chimera_repo: str):
    cfg = tmp_path / "roots.yaml"
    cfg.write_text("roots:\n  - foo\n bad: indentation\n   - bar")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert roots == [chimera_repo]


def test_missing_top_level_key(tmp_path: Path, chimera_repo: str):
    cfg = tmp_path / "roots.yaml"
    cfg.write_text("not_roots:\n  - /tmp\n")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert roots == [chimera_repo]


def test_empty_file(tmp_path: Path, chimera_repo: str):
    cfg = tmp_path / "roots.yaml"
    cfg.write_text("")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert roots == [chimera_repo]


def test_non_string_entries_are_skipped(tmp_path: Path, chimera_repo: str):
    project = tmp_path / "project"
    project.mkdir()

    cfg = tmp_path / "roots.yaml"
    cfg.write_text(f"roots:\n  - 42\n  - null\n  - {project}\n  - ''\n")

    roots = _load_roots(cfg, chimera_repo=chimera_repo)
    assert chimera_repo in roots
    assert str(project) in roots
    assert len(roots) == 2
