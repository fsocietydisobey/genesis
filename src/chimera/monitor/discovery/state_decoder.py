"""msgpack-aware state deserializer for AsyncPostgresSaver checkpoints.

LangGraph's AsyncPostgresSaver writes serialized state as `(type, data)`
pairs where `type` is a short string identifier ("msgpack", "json",
"pickle", etc.). This decoder handles the common types and degrades
gracefully for unknown types (returns an opaque-blob marker rather
than crashing — exactly what the inspector needs).
"""

from __future__ import annotations

import json
from typing import Any

_OPAQUE = "<opaque blob — unknown encoding>"


def decode(serializer_type: str | None, data: Any) -> Any:
    """Decode a (type, data) pair from a checkpoint row.

    Returns a Python object suitable for JSON serialization (after
    redaction). Unknown types return a marker dict instead of raising.

    Pass-throughs:
      - `data is None` → None
      - `data` is already a dict / list (e.g. psycopg returned jsonb as
        a Python object) → returned as-is. The serializer_type is ignored
        in that case because there's nothing to decode.
    """
    if data is None:
        return None
    if isinstance(data, (dict, list)):
        return data

    serializer_type = (serializer_type or "").lower()

    if serializer_type in ("json", "application/json"):
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return {"__opaque__": True, "encoding": serializer_type, "size": len(data)}

    if serializer_type in ("msgpack", "ormsgpack", "application/x-msgpack"):
        return _decode_msgpack(data, serializer_type)

    if serializer_type in ("", "raw", "bytes"):
        # No type hint — try JSON first (strict, won't accept non-JSON),
        # then msgpack, then opaque. JSON-first because msgpack will happily
        # decode arbitrary bytes that start with a valid format byte
        # (e.g. `{` is byte 0x7b which is a valid msgpack positive fixint).
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
            pass
        try:
            return _decode_msgpack(data, "msgpack")
        except _DecodeError:
            pass
        return {"__opaque__": True, "encoding": "raw", "size": len(data)}

    return {"__opaque__": True, "encoding": serializer_type, "size": len(data) if data else 0}


class _DecodeError(Exception):
    pass


def _decode_msgpack(data: bytes, encoding: str) -> Any:
    """Try ormsgpack first (LangGraph's preferred), fall back to msgpack."""
    try:
        import ormsgpack  # type: ignore
        try:
            return ormsgpack.unpackb(data)
        except Exception:
            pass
    except ImportError:
        pass

    try:
        import msgpack  # type: ignore
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception as exc:
            raise _DecodeError(str(exc)) from exc
    except ImportError as exc:
        raise _DecodeError(f"no msgpack lib available: {exc}") from exc
