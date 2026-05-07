"""Integration smoke test — start the FastAPI app in-process and hit /api/projects.

Skipped if `chimera[monitor]` extras aren't installed in the test env.
"""

import pytest


@pytest.fixture(autouse=True)
def _skip_if_no_extras():
    pytest.importorskip("fastapi")


def test_app_builds_and_lists_projects():
    from fastapi.testclient import TestClient

    from chimera.monitor.server import build_app

    app = build_app()
    client = TestClient(app)
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Chimera always discovers itself via the roots registry
    names = [p["name"] for p in data]
    assert "chimera" in names
