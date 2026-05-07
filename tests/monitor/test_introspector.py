"""Runtime introspection on a fixture graph + on chimera's own graphs.

Chimera's factories use dynamic node names — the introspector should
either flag them as approximate or fail cleanly so the AST fallback
takes over.
"""

import textwrap

from chimera.monitor.discovery.introspector import introspect_module


def test_introspect_fixture_graph(tmp_path):
    src = tmp_path / "fixture_graph.py"
    src.write_text(textwrap.dedent("""
        from langgraph.graph import StateGraph, START, END

        def _noop(state):
            return state

        builder = StateGraph(dict)
        builder.add_node("plan", _noop)
        builder.add_node("execute", _noop)
        builder.add_edge(START, "plan")
        builder.add_edge("plan", "execute")
        builder.add_edge("execute", END)
        graph = builder.compile()
    """))

    results = introspect_module("fixture_graph", project_path=tmp_path)
    assert len(results) >= 1
    [graph] = [r for r in results if r.error is None and r.nodes]
    assert "plan" in graph.nodes
    assert "execute" in graph.nodes
    # Edge from "plan" → "execute" must be present
    assert ("plan", "execute") in graph.edges


def test_import_failure_returns_error_result(tmp_path):
    results = introspect_module("nonexistent.module.that.does.not.exist", project_path=tmp_path)
    assert len(results) == 1
    assert results[0].error is not None
    assert "import failed" in results[0].error
