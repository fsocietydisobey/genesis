"""Graph construction — all CHIMERA execution patterns."""

from chimera.graphs.spr4 import build_spr4_graph
from chimera.graphs.clr import build_clr_graph
from chimera.graphs.pde import build_pde_graph
from chimera.graphs.hvd import build_hvd_graph
from chimera.graphs.supervisor import build_orchestrator_graph

__all__ = [
    "build_orchestrator_graph",
    "build_spr4_graph",
    "build_clr_graph",
    "build_pde_graph",
    "build_hvd_graph",
]
