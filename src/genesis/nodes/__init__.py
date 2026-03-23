"""Node factories for all Genesis patterns."""

# SPR-4 (Sequential Phase Runner)
from genesis.nodes.spr4.architect import build_architect_node
from genesis.nodes.spr4.critic import build_critic_node
from genesis.nodes.spr4.implement import build_implement_node
from genesis.nodes.spr4.research import build_research_node

# TFB (Tri-Force Balancer)
from genesis.nodes.tfb.stress_tester import build_stress_tester_node
from genesis.nodes.tfb.scope_analyzer import build_scope_analyzer_node
from genesis.nodes.tfb.arbitrator import build_arbitrator_node
from genesis.nodes.tfb.compliance import build_compliance_node
from genesis.nodes.tfb.retry_controller import build_retry_controller_node
from genesis.nodes.tfb.integration_gate import build_integration_gate_node

# PDE (Parallel Dispatch Engine)
from genesis.nodes.pde.task_decomposer import build_task_decomposer_node
from genesis.nodes.pde.worker import build_pde_worker_node
from genesis.nodes.pde.aggregator import build_pde_aggregator_node

# CLR (Closed-Loop Refiner)
from genesis.nodes.clr.health_scanner import build_health_scanner_node
from genesis.nodes.clr.classifier import build_classifier_node

# HVD (Hypervisor Daemon)
from genesis.nodes.hvd_dispatcher import build_hvd_dispatcher_node

# Shared
from genesis.nodes.gemini_assist import build_gemini_assist_node
from genesis.nodes.human_review import build_human_review_node
from genesis.nodes.supervisor import build_supervisor_node
from genesis.nodes.validator import build_validator_node

__all__ = [
    # SPR-4
    "build_architect_node",
    "build_critic_node",
    "build_implement_node",
    "build_research_node",
    # TFB
    "build_stress_tester_node",
    "build_scope_analyzer_node",
    "build_arbitrator_node",
    "build_compliance_node",
    "build_retry_controller_node",
    "build_integration_gate_node",
    # PDE
    "build_task_decomposer_node",
    "build_pde_worker_node",
    "build_pde_aggregator_node",
    # CLR
    "build_health_scanner_node",
    "build_classifier_node",
    # HVD
    "build_hvd_dispatcher_node",
    # Shared
    "build_gemini_assist_node",
    "build_human_review_node",
    "build_supervisor_node",
    "build_validator_node",
]
