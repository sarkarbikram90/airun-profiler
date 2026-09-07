"""Unit tests for AI-Aware Causal Incident Graph engine."""

from airun.incident.graph import (
    IncidentNodeType,
    build_sample_incident_graph,
)


def test_network_fabric_incident_graph():
    """Verify network fabric stall causal graph."""
    graph = build_sample_incident_graph(
        workload_name="Training Job #8421",
        root_cause_type="network_fabric",
    )

    assert graph.incident_id.startswith("inc-")
    assert "network" in graph.title.lower()
    assert graph.root_cause_node_id == "node_switch"
    assert graph.total_wasted_cost_usd == 11800.0
    assert len(graph.nodes) >= 4
    assert len(graph.edges) >= 3

    # Check node types
    node_types = {n.node_type for n in graph.nodes}
    assert IncidentNodeType.NETWORK in node_types
    assert IncidentNodeType.SYNCHRONIZATION in node_types
    assert IncidentNodeType.HARDWARE in node_types
    assert IncidentNodeType.FINANCIAL_IMPACT in node_types


def test_pcie_degradation_incident_graph():
    """Verify PCIe degradation causal graph."""
    graph = build_sample_incident_graph(
        workload_name="Training Job #9910",
        root_cause_type="pcie_degradation",
    )

    assert graph.root_cause_node_id == "node_pcie"
    assert graph.total_wasted_cost_usd == 4280.0
    assert "remediation" in graph.remediation_action.lower() or len(graph.remediation_action) > 10
