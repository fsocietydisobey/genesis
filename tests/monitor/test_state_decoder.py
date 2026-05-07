"""Tests for the msgpack/json state decoder.

The decoder must handle both backends and never crash on unknown types.
"""

import json

import pytest

from chimera.monitor.discovery.state_decoder import decode


def test_json_roundtrip():
    payload = {"a": 1, "b": [1, 2, 3], "c": {"d": "e"}}
    raw = json.dumps(payload).encode("utf-8")
    assert decode("json", raw) == payload


def test_unknown_type_returns_opaque_marker():
    out = decode("unknown_format", b"some bytes")
    assert out == {"__opaque__": True, "encoding": "unknown_format", "size": len(b"some bytes")}


def test_none_data_returns_none():
    assert decode("msgpack", None) is None


def test_dict_passes_through_when_already_decoded():
    # psycopg returns jsonb columns as Python dicts already — the decoder
    # must not try to re-decode them.
    payload = {"a": 1, "b": [1, 2]}
    assert decode("any-type", payload) is payload


def test_list_passes_through_when_already_decoded():
    payload = [{"a": 1}, {"b": 2}]
    assert decode(None, payload) is payload


def test_invalid_json_returns_opaque_not_raise():
    out = decode("json", b"{not valid json")
    assert out["__opaque__"] is True
    assert out["encoding"] == "json"


def test_msgpack_roundtrip_when_lib_available():
    msgpack = pytest.importorskip("msgpack")
    payload = {"a": 1, "b": [1, 2, 3]}
    raw = msgpack.packb(payload)
    assert decode("msgpack", raw) == payload


def test_raw_json_decoded_via_fallback():
    # Plain JSON bytes with raw type hint — JSON-first ordering means
    # the dict comes through cleanly (msgpack would otherwise eat the
    # `{` byte as a positive fixint and return garbage).
    raw = json.dumps({"x": 1}).encode("utf-8")
    assert decode("raw", raw) == {"x": 1}


def test_raw_msgpack_decoded_via_fallback():
    msgpack = pytest.importorskip("msgpack")
    payload = {"a": 1, "b": [1, 2, 3]}
    raw = msgpack.packb(payload)
    out = decode("raw", raw)
    # msgpack roundtrip; msgpack returns bytes-keyed dicts by default —
    # accept either string or bytes keys (the decode call uses raw=False
    # only for the explicit "msgpack" type).
    assert out in (payload, {b"a": 1, b"b": [1, 2, 3]})
