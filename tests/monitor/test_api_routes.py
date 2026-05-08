"""Tests for the FastAPI route extractor.

Locks the parsing behavior so future schema changes / refactors don't
silently break the full-stack-trace skill that depends on it.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from chimera.monitor.discovery import api_routes


def _write(tmp_path: Path, name: str, source: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(source), encoding="utf-8")
    return p


def test_extract_app_decorator(tmp_path: Path) -> None:
    _write(tmp_path, "main.py", """
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/health")
        async def health() -> dict:
            return {"ok": True}

        @app.post("/items")
        async def create_item(item: ItemModel) -> ItemModel:
            return item
    """)
    routes = api_routes.extract_from_path(tmp_path)
    paths = {(r.method, r.path) for r in routes}
    assert ("GET", "/health") in paths
    assert ("POST", "/items") in paths


def test_router_prefix_combined_with_path(tmp_path: Path) -> None:
    _write(tmp_path, "users.py", """
        from fastapi import APIRouter
        router = APIRouter(prefix="/users")

        @router.get("/{user_id}")
        async def get_user(user_id: str) -> dict:
            return {}

        @router.post("/")
        async def create_user(user: UserModel) -> dict:
            return {}
    """)
    routes = api_routes.extract_from_path(tmp_path)
    paths = {(r.method, r.path) for r in routes}
    assert ("GET", "/users/{user_id}") in paths
    assert ("POST", "/users") in paths


def test_graph_invocation_detected(tmp_path: Path) -> None:
    """Routes calling .ainvoke / .astream / build_*_graph() get flagged."""
    _write(tmp_path, "main.py", """
        from fastapi import FastAPI
        app = FastAPI()

        @app.post("/run")
        async def run_graph(req: RunRequest) -> dict:
            graph = build_pipeline_graph()
            result = await graph.ainvoke(req.dict())
            return {"thread_id": result["thread_id"]}

        @app.get("/health")
        async def health() -> dict:
            return {"ok": True}
    """)
    routes = api_routes.extract_from_path(tmp_path)
    by_handler = {r.handler: r for r in routes}
    assert by_handler["run_graph"].invokes_graph is True
    assert any("ainvoke" in h or "build_pipeline_graph" in h
               for h in by_handler["run_graph"].graph_hints)
    assert by_handler["health"].invokes_graph is False


def test_request_model_extracted(tmp_path: Path) -> None:
    _write(tmp_path, "main.py", """
        from fastapi import FastAPI
        app = FastAPI()

        @app.post("/items")
        async def create_item(item: ItemModel) -> ItemModel:
            return item
    """)
    routes = api_routes.extract_from_path(tmp_path)
    by_handler = {r.handler: r for r in routes}
    assert by_handler["create_item"].request_model == "ItemModel"


def test_response_model_kwarg(tmp_path: Path) -> None:
    _write(tmp_path, "main.py", """
        from fastapi import FastAPI
        app = FastAPI()

        @app.post("/items", response_model=ItemModel)
        async def create_item(payload):
            return payload
    """)
    routes = api_routes.extract_from_path(tmp_path)
    by_handler = {r.handler: r for r in routes}
    assert by_handler["create_item"].response_model == "ItemModel"


def test_skip_dirs_not_scanned(tmp_path: Path) -> None:
    _write(tmp_path, ".venv/lib/dep.py", """
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/should-not-appear")
        async def x() -> dict:
            return {}
    """)
    routes = api_routes.extract_from_path(tmp_path)
    assert not any(r.path == "/should-not-appear" for r in routes)


def test_unparseable_file_skipped(tmp_path: Path) -> None:
    """Syntax errors in a file shouldn't blow up the whole extraction."""
    _write(tmp_path, "broken.py", "from fastapi import FastAPI\nthis is not valid python")
    _write(tmp_path, "good.py", """
        from fastapi import FastAPI
        app = FastAPI()
        @app.get("/ok")
        async def ok() -> dict:
            return {}
    """)
    routes = api_routes.extract_from_path(tmp_path)
    paths = {r.path for r in routes}
    assert "/ok" in paths


def test_non_fastapi_file_skipped(tmp_path: Path) -> None:
    """Files that don't reference FastAPI are pre-filtered for speed."""
    _write(tmp_path, "model.py", """
        # Not a route file — pure data class
        from dataclasses import dataclass

        @dataclass
        class Item:
            name: str
    """)
    routes = api_routes.extract_from_path(tmp_path)
    assert routes == []
