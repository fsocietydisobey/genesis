"""AST-based topology extraction (fallback path).

Verifies the walker finds StateGraph instantiations + add_node/add_edge
calls in source code, even when the project's deps aren't importable.
"""

import textwrap

import pytest

from chimera.monitor.discovery import ast_walker


@pytest.fixture(autouse=True)
def _skip_if_no_tree_sitter():
    pytest.importorskip("tree_sitter")
    pytest.importorskip("tree_sitter_python")


def test_walker_extracts_nodes_and_edges(tmp_path):
    src = tmp_path / "graph.py"
    src.write_text(textwrap.dedent("""
        from langgraph.graph import StateGraph

        def build():
            g = StateGraph(dict)
            g.add_node("alpha", lambda s: s)
            g.add_node("beta", lambda s: s)
            g.add_edge("alpha", "beta")
            return g.compile()
    """))

    results = ast_walker.extract_from_path(tmp_path)
    [graph] = [r for r in results if r.nodes]
    assert graph.approximate is True
    assert graph.source == "ast"
    assert "alpha" in graph.nodes
    assert "beta" in graph.nodes
    assert ("alpha", "beta") in graph.edges


def test_walker_skips_files_without_stategraph(tmp_path):
    (tmp_path / "boring.py").write_text("def f(): return 1\n")
    results = ast_walker.extract_from_path(tmp_path)
    assert results == []


def test_walker_returns_error_on_missing_dir(tmp_path):
    results = ast_walker.extract_from_path(tmp_path / "does-not-exist")
    assert len(results) == 1
    assert results[0].error is not None
