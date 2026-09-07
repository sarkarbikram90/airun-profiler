"""Unit tests for Golden Signals hierarchy and asynchronous event queue."""

from __future__ import annotations

from airun.events.models import (
    DCGMSample,
    GoldenSignals,
    GoldenSignalsEconomics,
    GoldenSignalsEfficiency,
    GoldenSignalsInfrastructure,
    GoldenSignalsReliability,
    TelemetryBatch,
)
from airun.events.queue import EventMessage, EventQueue


def test_golden_signals_hierarchy_structure():
    """Verify 4-layer hierarchy initializes with default values."""
    signals = GoldenSignals(
        economics=GoldenSignalsEconomics(
            cost_per_effective_gpu_hour_usd=42.50,
            cost_per_token_usd=0.000002,
            financial_bleed_hourly_usd=5.80,
            total_wasted_spend_usd=12.40,
            waste_percentage=22.5,
        ),
        efficiency=GoldenSignalsEfficiency(
            mfu_pct=52.0,
            achieved_tflops=514.0,
            gpu_sm_utilization_pct=81.0,
            memory_bandwidth_utilization_pct=72.0,
            pcie_utilization_pct=45.0,
        ),
        reliability=GoldenSignalsReliability(
            job_failure_rate_pct=1.2,
            mean_time_to_recovery_ms=850.0,
            retry_count=2,
            checkpoint_frequency_min=20.0,
        ),
        infrastructure=GoldenSignalsInfrastructure(
            power_draw_watts=420.0,
            thermal_throttling=False,
            pcie_error_count=0,
            network_retransmits_pct=0.015,
            pue=1.20,
        ),
    )

    assert signals.economics.cost_per_effective_gpu_hour_usd == 42.50
    assert signals.efficiency.mfu_pct == 52.0
    assert signals.reliability.retry_count == 2
    assert signals.infrastructure.power_draw_watts == 420.0


def test_dcgm_telemetry_batch():
    """Verify DCGM metric sampling and batch payload serialization."""
    sample = DCGMSample(
        timestamp="2026-09-07T18:00:00Z",
        gpu_id=0,
        node_name="gke-gpu-node-1",
        sm_util_pct=78.5,
        memory_used_mb=45000.0,
        temperature_c=58.0,
        power_watts=385.0,
        pcie_tx_bytes_sec=1200000.0,
        pcie_rx_bytes_sec=900000.0,
    )

    batch = TelemetryBatch(
        batch_id="batch-001",
        cluster_id="us-central1-gke-prod",
        node_id="gke-gpu-node-1",
        accelerator_type="h100",
        num_gpus=8,
        samples=[sample],
        published_at="2026-09-07T18:00:01Z",
    )

    dump = batch.model_dump()
    assert dump["batch_id"] == "batch-001"
    assert len(dump["samples"]) == 1
    assert dump["samples"][0]["sm_util_pct"] == 78.5


def test_pubsub_event_queue():
    """Verify EventQueue subscribe, publish, batch publish, and history."""
    queue = EventQueue(topic="telemetry-test-topic")
    received_events = []

    def on_event(msg: EventMessage):
        received_events.append(msg)

    queue.subscribe("telemetry.gpu.metrics", on_event)

    msg1 = queue.publish("telemetry.gpu.metrics", {"sm_util": 85.0, "node": "node-1"})
    assert msg1.event_type == "telemetry.gpu.metrics"
    assert len(received_events) == 1
    assert received_events[0].payload["sm_util"] == 85.0

    # Batch publish
    queue.publish_batch(
        "telemetry.gpu.metrics",
        [{"sm_util": 86.0}, {"sm_util": 87.0}],
    )
    assert len(received_events) == 3

    # History query
    history = queue.get_history(event_type="telemetry.gpu.metrics")
    assert len(history) == 3

    queue.clear()
    assert len(queue.get_history()) == 0
