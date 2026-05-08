"""`/api/anomalies` — recent self-watch anomaly results.

Surfaces what the in-daemon invariant checker has flagged. Used by
the `monitor_anomalies` MCP tool and by anyone curious about whether
the dashboard's claims match reality.
"""

from __future__ import annotations

from typing import Any

from .._optional import require
from .. import anomalies as anomalies_module


def build_router():
    fastapi = require("fastapi")
    router = fastapi.APIRouter()

    @router.get("/anomalies")
    async def list_anomalies(limit: int = 50, only_failures: bool = False) -> dict[str, Any]:
        items = anomalies_module.recent_anomalies(limit=limit)
        if only_failures:
            items = [it for it in items if not it.get("passed", True)]
        return {
            "count": len(items),
            "items": items,
        }

    return router
