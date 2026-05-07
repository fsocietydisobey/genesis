"""Tests for project + connection discovery."""

from pathlib import Path

from chimera.monitor.discovery.connections import discover_postgres
from chimera.monitor.discovery.project import discover


def test_chimera_repo_detected_as_langgraph_project():
    chimera_root = Path(__file__).resolve().parents[2]
    projects = discover([str(chimera_root)])
    assert len(projects) == 1
    assert projects[0].name == "chimera"
    assert projects[0].detected_via == "pyproject"


def test_non_langgraph_dir_not_detected(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n")
    projects = discover([str(tmp_path)])
    assert projects == []


def test_source_scan_detects_langgraph_via_imports(tmp_path: Path):
    (tmp_path / "graph.py").write_text(
        "from langgraph.graph import StateGraph\n"
        "g = StateGraph(dict)\n"
    )
    projects = discover([str(tmp_path)])
    assert len(projects) == 1
    assert projects[0].detected_via == "source-scan"


def test_pyproject_with_langgraph_dep_detected(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\n'
        'name = "x"\n'
        'dependencies = ["langgraph>=0.4"]\n'
    )
    projects = discover([str(tmp_path)])
    assert len(projects) == 1
    assert projects[0].detected_via == "pyproject"


def test_postgres_url_in_env_discovered(tmp_path: Path):
    (tmp_path / ".env").write_text(
        "OTHER_VAR=hello\n"
        "DATABASE_URL=postgresql://user:pass@db.example.com:5432/mydb\n"
    )
    conns = discover_postgres(tmp_path)
    assert len(conns) == 1
    assert conns[0].var == "DATABASE_URL"
    assert conns[0].host == "db.example.com:5432"
    assert conns[0].database == "mydb"


def test_postgres_url_async_psycopg_scheme_discovered(tmp_path: Path):
    (tmp_path / ".env").write_text(
        'CHECKPOINT_DSN="postgresql+psycopg://u:p@host/db"\n'
    )
    conns = discover_postgres(tmp_path)
    assert len(conns) == 1
    assert conns[0].host == "host"


def test_no_postgres_url_returns_empty(tmp_path: Path):
    (tmp_path / ".env").write_text("FOO=bar\n")
    assert discover_postgres(tmp_path) == []


def test_missing_env_returns_empty(tmp_path: Path):
    assert discover_postgres(tmp_path) == []


def test_export_prefix_handled(tmp_path: Path):
    (tmp_path / ".env").write_text("export DATABASE_URL=postgres://x@y/z\n")
    conns = discover_postgres(tmp_path)
    assert len(conns) == 1
