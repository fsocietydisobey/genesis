"""Tests for the metadata cache + merge layer."""

from pathlib import Path

import pytest
import yaml

from chimera.monitor.discovery.introspector import TopologyResult
from chimera.monitor.metadata import cache, merge, schema


def test_schema_validates_minimal_doc():
    doc = schema.ProjectMetadata(
        project_name="x",
        project_path="/tmp/x",
        generated_at="2026-05-06T00:00:00Z",
    )
    assert doc.schema_version == 1
    assert doc.graphs == {}


def test_schema_rejects_unknown_top_level_field():
    with pytest.raises(Exception):
        schema.ProjectMetadata.model_validate(
            {
                "project_name": "x",
                "project_path": "/tmp",
                "generated_at": "2026-05-06T00:00:00Z",
                "rogue_field": True,
            }
        )


def test_schema_node_role_validates():
    g = schema.GraphMetadata(nodes={"router": schema.NodeMetadata(role="router")})
    assert g.nodes["router"].role == "router"
    with pytest.raises(Exception):
        schema.NodeMetadata(role="not_a_role")


def test_cache_path_is_unique_per_path(tmp_path):
    a = tmp_path / "project_a"
    b = tmp_path / "project_b"
    a.mkdir(); b.mkdir()
    assert cache.cache_path(a) != cache.cache_path(b)


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    project = tmp_path / "fixture"
    project.mkdir()
    metadata = schema.ProjectMetadata(
        project_name="fixture",
        project_path=str(project),
        generated_at="2026-05-06T00:00:00Z",
        summary="hello",
        graphs={
            "g1": schema.GraphMetadata(
                role="orchestrator",
                label="G1",
                layout="TB",
                nodes={"router": schema.NodeMetadata(role="router")},
            )
        },
    )
    cache.save(metadata)
    loaded = cache.load(project)
    assert loaded is not None
    assert loaded.project_name == "fixture"
    assert loaded.graphs["g1"].role == "orchestrator"
    assert loaded.graphs["g1"].nodes["router"].role == "router"


def test_load_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    project = tmp_path / "missing"
    project.mkdir()
    assert cache.load(project) is None


def test_load_returns_none_for_invalid_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    project = tmp_path / "broken"
    project.mkdir()
    cache_file = cache.cache_path(project)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(yaml.safe_dump({"only_some_fields": "yes"}))
    assert cache.load(project) is None


def test_is_stale_when_no_metadata(tmp_path):
    assert cache.is_stale(None, tmp_path) is True


def test_is_stale_when_source_newer(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    project = tmp_path / "p"
    project.mkdir()
    src = project / "graph.py"
    src.write_text("StateGraph(...)")
    metadata = schema.ProjectMetadata(
        project_name="p",
        project_path=str(project),
        generated_at="2026-05-06T00:00:00Z",
        source_mtime_max=0.0,
    )
    assert cache.is_stale(metadata, project) is True


def test_merge_attaches_role_label_and_layout():
    metadata = schema.ProjectMetadata(
        project_name="x",
        project_path="/tmp",
        generated_at="2026-05-06T00:00:00Z",
        graphs={
            "build_orchestrator_graph": schema.GraphMetadata(
                role="orchestrator",
                label="Orchestrator",
                summary="Routes deliverables.",
                layout="TB",
                invokes={"digest_lane": "build_digestion_graph"},
                nodes={
                    "router": schema.NodeMetadata(role="router", label="Decide route"),
                    "hitl_lane": schema.NodeMetadata(role="gate"),
                },
            )
        },
    )
    result = TopologyResult(
        nodes=["router", "hitl_lane", "chat_lane"],
        edges=[("router", "hitl_lane"), ("router", "chat_lane")],
        source="ast",
        approximate=True,
        graph_name="build_orchestrator_graph",
    )
    enriched = merge.enrich_topology(result, metadata)
    assert getattr(enriched, "graph_label") == "Orchestrator"
    assert getattr(enriched, "graph_summary") == "Routes deliverables."
    assert getattr(enriched, "layout") == "TB"
    assert getattr(enriched, "node_roles") == {"router": "router", "hitl_lane": "gate"}
    assert getattr(enriched, "node_labels") == {"router": "Decide route"}
    assert getattr(enriched, "invokes") == {"digest_lane": "build_digestion_graph"}


def test_merge_passthrough_when_no_metadata():
    result = TopologyResult(
        nodes=["a", "b"],
        edges=[("a", "b")],
        source="ast",
        approximate=True,
        graph_name="solo",
    )
    out = merge.enrich_topology(result, None)
    assert out is result
    assert not hasattr(out, "graph_label")


def test_merge_passthrough_when_graph_not_in_metadata():
    metadata = schema.ProjectMetadata(
        project_name="x",
        project_path="/tmp",
        generated_at="2026-05-06T00:00:00Z",
        graphs={"some_other_graph": schema.GraphMetadata()},
    )
    result = TopologyResult(
        nodes=["a"], edges=[], source="ast", approximate=True, graph_name="my_graph",
    )
    out = merge.enrich_topology(result, metadata)
    assert not hasattr(out, "graph_label")
