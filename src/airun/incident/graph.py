"""AI-Aware Causal Incident Graph Engine.

Implements the spec.md requirement:
"The wedge isn't 'we monitor GPUs'—it's 'we understand the causal graph of AI failures.'
Your 'AI-aware incident graph' concept is the real differentiator:
Training job -> Pod eviction -> GPU Xid error -> PCIe degradation -> Node failure ->
Rack switch retransmits -> training synchronization timeout.
Then the system automatically: detect -> diagnose -> correlate -> remediate -> document."
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class IncidentNodeType(str, Enum):
    WORKLOAD = "workload"  # Host workload or training pipeline
    HARDWARE = "hardware"  # GPU Xid error, thermal throttling, PCIe bus
    NETWORK = "network"  # Infiniband fabric, switch packet loss, retransmits
    STORAGE = "storage"  # Dataloader starvation, checkpoint timeout
    SYNCHRONIZATION = "synchronization"  # NCCL AllReduce barrier timeout, rank stall
    PLATFORM = "platform"  # Kubernetes pod eviction, OOM kill
    FINANCIAL_IMPACT = "financial_impact"  # Wasted compute dollars, idle accelerator cost


class IncidentNode(BaseModel):
    """A discrete failure state or event in the causal chain."""

    id: str
    node_type: IncidentNodeType
    title: str
    component: str
    severity: str = "critical"  # "critical", "warning", "info"
    description: str
    metrics: Dict[str, Any] = Field(default_factory=dict)


class IncidentEdge(BaseModel):
    """Causal linkage connecting one event to its downstream consequence."""

    source_id: str
    target_id: str
    relationship: str
    delay_ms: float = 0.0
    wasted_cost_usd: float = 0.0


class CausalIncidentGraph(BaseModel):
    """Complete causal dependency graph of an AI infrastructure incident."""

    incident_id: str
    title: str
    root_cause: str
    root_cause_node_id: str
    total_wasted_cost_usd: float
    total_lost_duration_ms: float
    nodes: List[IncidentNode] = Field(default_factory=list)
    edges: List[IncidentEdge] = Field(default_factory=list)
    remediation_action: str
    projected_daily_savings_usd: float = 0.0


def build_sample_incident_graph(
    workload_name: str = "Distributed Training Job #8421",
    root_cause_type: str = "pcie_degradation",  # "pcie_degradation", "network_fabric", "dataloader_starvation"
) -> CausalIncidentGraph:
    """
    Constructs a high-fidelity AI-aware incident graph illustrating causal propagation
    from physical silicon/fabric faults to wasted compute dollars.
    """
    inc_id = f"inc-{uuid.uuid4().hex[:8]}"

    if root_cause_type == "network_fabric":
        nodes = [
            IncidentNode(
                id="node_workload",
                node_type=IncidentNodeType.WORKLOAD,
                title=workload_name,
                component="Kubernetes Job (128x H100)",
                severity="critical",
                description="Distributed 70B MoE pre-training step synchronization",
            ),
            IncidentNode(
                id="node_switch",
                node_type=IncidentNodeType.NETWORK,
                title="Leaf Switch Port Buffer Overrun",
                component="Arista 7060X / Infiniband Fabric",
                severity="critical",
                description="PFC deadlock triggered 4.2% packet retransmissions across Spine 3",
                metrics={"retransmits_pct": 4.2, "spine_id": "spine-03-leaf-08"},
            ),
            IncidentNode(
                id="node_nccl",
                node_type=IncidentNodeType.SYNCHRONIZATION,
                title="NCCL AllReduce Barrier Timeout",
                component="torch.distributed.nccl",
                severity="critical",
                description="Rank 48 stalled waiting for AllGather gradient synchronization",
                metrics={"timeout_sec": 600, "stalled_ranks": [48, 49, 50, 51]},
            ),
            IncidentNode(
                id="node_gpu_idle",
                node_type=IncidentNodeType.HARDWARE,
                title="Accelerator Fabric Idle Wait",
                component="128x NVIDIA H100 SXM5",
                severity="critical",
                description="Cluster utilization collapsed from 88% to 14% for 38 minutes",
                metrics={"idle_accelerators": 128, "wasted_hours": 81.0},
            ),
            IncidentNode(
                id="node_impact",
                node_type=IncidentNodeType.FINANCIAL_IMPACT,
                title="Wasted Compute & Energy Spend",
                component="Cluster Cost Accounting",
                severity="critical",
                description="31% of accelerator time wasted waiting on network synchronization",
                metrics={"wasted_usd": 11800.0, "projected_daily_savings": 11800.0},
            ),
        ]
        edges = [
            IncidentEdge(
                source_id="node_switch",
                target_id="node_nccl",
                relationship="induced_barrier_stall",
                delay_ms=600000.0,
                wasted_cost_usd=3200.0,
            ),
            IncidentEdge(
                source_id="node_nccl",
                target_id="node_gpu_idle",
                relationship="starved_accelerator_pipeline",
                delay_ms=1680000.0,
                wasted_cost_usd=8600.0,
            ),
            IncidentEdge(
                source_id="node_gpu_idle",
                target_id="node_workload",
                relationship="halted_step_progress",
                delay_ms=2280000.0,
                wasted_cost_usd=11800.0,
            ),
            IncidentEdge(
                source_id="node_workload",
                target_id="node_impact",
                relationship="incurred_unrecoverable_burn",
                delay_ms=0.0,
                wasted_cost_usd=11800.0,
            ),
        ]
        return CausalIncidentGraph(
            incident_id=inc_id,
            title=f"Network Fabric Stall: 31% accelerator time wasted on {workload_name}",
            root_cause="Infiniband Leaf Switch PFC buffer congestion on Spine 3",
            root_cause_node_id="node_switch",
            total_wasted_cost_usd=11800.0,
            total_lost_duration_ms=2280000.0,
            nodes=nodes,
            edges=edges,
            remediation_action="Isolate Spine 3 leaf-08; re-route NCCL rail-optimized traffic to alternate leaf fabric; tune PFC headroom buffer.",
            projected_daily_savings_usd=11800.0,
        )

    else:  # "pcie_degradation"
        nodes = [
            IncidentNode(
                id="node_pcie",
                node_type=IncidentNodeType.HARDWARE,
                title="PCIe Gen5 Degradation (x16 -> x1)",
                component="Node gpu-worker-42 (Slot 3)",
                severity="critical",
                description="PCIe link degraded to Gen1 x1 after thermal spike (89°C)",
                metrics={"link_width": "x1", "expected_width": "x16", "temp_c": 89},
            ),
            IncidentNode(
                id="node_xid",
                node_type=IncidentNodeType.HARDWARE,
                title="GPU Xid 79 (Off the Bus)",
                component="NVIDIA Driver / DCGM",
                severity="critical",
                description="GPU 2 became unresponsive during host-to-device tensor transfer",
                metrics={"xid_code": 79, "gpu_index": 2},
            ),
            IncidentNode(
                id="node_evict",
                node_type=IncidentNodeType.PLATFORM,
                title="Kubernetes Pod Eviction & Node Drain",
                component="Kubelet / Kube-Scheduler",
                severity="warning",
                description="Node gpu-worker-42 marked NotReady; training pod terminated",
                metrics={"exit_code": 137, "reason": "NodeUnhealthy"},
            ),
            IncidentNode(
                id="node_loss",
                node_type=IncidentNodeType.FINANCIAL_IMPACT,
                title="Lost Training Checkpoint Progress",
                component="FinOps Accounting",
                severity="critical",
                description="Run aborted at 84% step progress without recent checkpoint save",
                metrics={"lost_hours": 4.5, "wasted_cost_usd": 4280.0},
            ),
        ]
        edges = [
            IncidentEdge(
                source_id="node_pcie",
                target_id="node_xid",
                relationship="triggered_bus_dropout",
                delay_ms=12000.0,
                wasted_cost_usd=400.0,
            ),
            IncidentEdge(
                source_id="node_xid",
                target_id="node_evict",
                relationship="forced_node_taint",
                delay_ms=45000.0,
                wasted_cost_usd=880.0,
            ),
            IncidentEdge(
                source_id="node_evict",
                target_id="node_loss",
                relationship="wasted_uncheckpointed_hours",
                delay_ms=16200000.0,
                wasted_cost_usd=3000.0,
            ),
        ]
        return CausalIncidentGraph(
            incident_id=inc_id,
            title=f"Hardware Degradation: PCIe x1 Throttling on {workload_name}",
            root_cause="PCIe Gen5 bus degradation caused by thermal junction saturation in rack 7",
            root_cause_node_id="node_pcie",
            total_wasted_cost_usd=4280.0,
            total_lost_duration_ms=16257000.0,
            nodes=nodes,
            edges=edges,
            remediation_action="Cordon gpu-worker-42; reseat riser card in slot 3; decrease checkpoint interval from 120min to 20min.",
            projected_daily_savings_usd=4280.0,
        )
