"""Pydantic models for the auto-generated project metadata cache.

Schema version 1. All fields except `schema_version` and `project_name`
are optional — a brand-new cache from an LLM scan that can't classify a
graph still validates as a usable (if minimal) document.

The schema is intentionally narrow: only fields that DRIVE diagram
rendering. We don't store anything purely descriptive; if it's not
going to change a pixel on screen, it doesn't belong here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Roles drive diagram styling. Keep this list in sync with the classDef
# palette in api/topology.py.
NodeRole = Literal[
    "entry",       # __start__-like — gold pill
    "exit",        # __end__-like — green pill
    "router",      # decision/dispatch — purple diamond
    "gate",        # HITL / approval — amber rectangle
    "critic",      # validation / quality check — red rectangle
    "synthesis",   # aggregation / commit / merge — green rectangle
    "executor",    # main work — slate rectangle (default)
]

GraphRole = Literal[
    "orchestrator",   # top-level — invokes one or more subgraphs
    "subgraph",       # invoked by an orchestrator
    "leaf",           # standalone, neither invokes nor is invoked
]

LayoutDirection = Literal["TB", "BT", "LR", "RL"]


class NodeMetadata(BaseModel):
    """Per-node enrichment. None = AST default applies."""

    role: NodeRole | None = None
    label: str | None = None        # display name (overrides node id)
    summary: str | None = None      # one-line description, used in tooltips


class GraphMetadata(BaseModel):
    """Per-graph enrichment."""

    role: GraphRole | None = None
    label: str | None = None
    summary: str | None = None
    layout: LayoutDirection = "LR"
    # Map from this graph's node name → the name of the graph it invokes.
    # Drives inter-graph subgraph edges in the unified view.
    invokes: dict[str, str] = Field(default_factory=dict)
    # Per-node enrichment. Missing entries fall back to defaults.
    nodes: dict[str, NodeMetadata] = Field(default_factory=dict)


class ThreadIdPattern(BaseModel):
    """One regex rule for parsing a project's thread_ids into grouping fields.

    The regex must use named groups: `scope_id` (required), `stage`
    (optional), `stage_detail` (optional). When `scope_kind` is not a
    capture group, the static value below is used. Multiple patterns
    are tried in order; first match wins.
    """

    pattern: str                      # Python regex with named groups
    scope_kind: str                   # static label when not captured (e.g. "deliverable")
    stage: str | None = None          # static stage label if regex doesn't capture it


class ThreadGrouping(BaseModel):
    """Project-specific configuration for parsing thread_ids."""

    # Display label for the scope group header (e.g. "Deliverable", "Run", "Chain")
    scope_label: str = "Run"
    # Patterns tried in order. Empty list = use the heuristic fallback.
    patterns: list[ThreadIdPattern] = Field(default_factory=list)
    # Sample thread_ids Claude inspected during the scan. Stored for
    # debugging when patterns produce wrong results — the user can read
    # the cache file to see what Claude saw.
    examples: list[str] = Field(default_factory=list)


class ProjectMetadata(BaseModel):
    """The full cache document for one project."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    project_name: str
    project_path: str
    # ISO-8601 UTC timestamp of when this cache was written.
    generated_at: str
    # Newest mtime across the project's graph source files at scan time.
    # Used as the cache invalidation watermark.
    source_mtime_max: float = 0.0
    # Free-form architecture summary (Gemini's headline take on the project).
    summary: str = ""
    # Per-graph enrichment, keyed by the same graph_name the AST walker emits.
    graphs: dict[str, GraphMetadata] = Field(default_factory=dict)
    # Project-specific thread_id parsing rules. Optional — when absent
    # the backend falls back to the generic heuristic in
    # discovery/thread_grouping.py.
    thread_grouping: ThreadGrouping | None = None
